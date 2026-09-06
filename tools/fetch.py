#!/usr/bin/env python3
"""Pull every Kleros dispute on all three chains into data/snapshot.json.

Full fetch every run (under 3,000 disputes; no incremental state). Each source
is fetched into memory, checked for completeness, and only then written — so a
half-failed run leaves the previous snapshot untouched.

    python3 tools/fetch.py                 # write data/snapshot.json, print summary
    python3 tools/fetch.py --out x.json
    python3 tools/fetch.py --compare       # also diff against the constants in index.html

Sources (all plain HTTPS, no keys):
  Gnosis V1    Klerosboard subgraph on Graph Studio (disputes, courts, counter)
  Arbitrum V2  Goldsky coreneo (disputes, courts, counter) + DRT (template category)
  Ethereum V1  Klerosboard `stats-fees-by-dispute` (court + arbitrable + ts for
               every dispute that paid fees) + Blockscout DisputeCreation logs
               for the rest + KlerosLiquid.disputes() for the court of any id
               the fee endpoint lacks
  Tiles        Klerosboard functions (active jurors, fees, staked per chain)
  Names        Scout Address Tags via Envio, then Blockscout implementation name

Python 3.9+, stdlib only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import socket
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
UA = {"content-type": "application/json", "user-agent": "artisanal-klerosboard/1.0 (+https://artisanal-klerosboard.netlify.app)"}

GNOSIS_SUBGRAPH = "https://api.studio.thegraph.com/query/66145/klerosboard-gnosis/version/latest"
CORENEO = "https://api.goldsky.com/api/public/project_cmgx9all3003atlp2bqha1zif/subgraphs/kleros-v2-coreneo/v0.17.2/gn"
DRT = "https://api.goldsky.com/api/public/project_cmgx9all3003atlp2bqha1zif/subgraphs/kleros-v2-drt/v0.12.0/gn"
KLEROSBOARD_FN = "https://klerosboard.com/.netlify/functions/"
ENVIO = "https://indexer.hyperindex.xyz/1a2f51c/v1/graphql"
SCOUT_TAGS_REGISTRY = "0x66260c69d03837016d88c9877e61e08ef74c59f2"
ETH_BLOCKSCOUT = "https://eth.blockscout.com"
ETH_KLEROS_LIQUID = "0x988b3a538b618c7a603e1c11ab82cd16dbe28069"
ETH_RPC = "https://ethereum-rpc.publicnode.com"
V1_DISPUTE_CREATION_TOPIC = "0x141dfc18aa6a56fc816f44f0e9e2f1ebc92b15ab167770e17db5b084c10ed995"
DISPUTES_SELECTOR = "0x564a565d"  # disputes(uint256) on KlerosLiquid
PAGE = 1000

V1_PERIODS = ["evidence", "commit", "vote", "appeal", "execution"]


# ── HTTP ────────────────────────────────────────────────────────────────

def http(url: str, body: Optional[dict] = None, retries: int = 5, timeout: int = 90) -> Any:
    data = json.dumps(body).encode() if body is not None else None
    last: Optional[Exception] = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=UA, method="POST" if data else "GET")
            return json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode())
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, socket.timeout, ConnectionResetError, json.JSONDecodeError) as e:  # noqa: PERF203
            last = e
            time.sleep(2 ** i)
    raise RuntimeError(f"HTTP failed after {retries} tries: {url}: {last}")


def gql(url: str, query: str, variables: Optional[dict] = None) -> dict:
    out = http(url, {"query": query, "variables": variables or {}})
    if out.get("errors"):
        raise RuntimeError(f"GraphQL errors from {url}: {out['errors'][:2]}")
    if "data" not in out:
        raise RuntimeError(f"No data from {url}: {str(out)[:200]}")
    return out["data"]


def paginate(url: str, entity: str, fields: str, order: str = "id", extra_where: str = "") -> List[dict]:
    """Cursor-paginate `entity(where:{id_gt}, orderBy:id)` until a short page.

    Numeric-string ids (Gnosis/Arbitrum disputes) sort lexicographically in
    The Graph, so we page on the raw string id and de-duplicate afterwards.
    """
    rows: List[dict] = []
    seen = set()
    last = ""
    for _ in range(200):
        where = f'id_gt: "{last}"' + (", " + extra_where if extra_where else "")
        q = f"{{ {entity}(first: {PAGE}, orderBy: {order}, orderDirection: asc, where: {{ {where} }}) {{ {fields} }} }}"
        batch = gql(url, q)[entity]
        for r in batch:
            if r["id"] not in seen:
                seen.add(r["id"])
                rows.append(r)
        if len(batch) < PAGE:
            break
        last = batch[-1]["id"]
    else:
        raise RuntimeError(f"pagination of {entity} did not terminate")
    return rows


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


# ── Sources ─────────────────────────────────────────────────────────────

def fetch_gnosis() -> Dict[str, Any]:
    counter = gql(GNOSIS_SUBGRAPH, '{ klerosCounter(id:"ID"){ disputesCount activeJurors totalETHFees totalTokenRedistributed tokenStaked courtsCount } }')["klerosCounter"]
    courts = gql(GNOSIS_SUBGRAPH, "{ courts(first: 100, orderBy: id) { id disputesNum activeJurors tokenStaked hiddenVotes parent { id } } }")["courts"]
    rows = paginate(GNOSIS_SUBGRAPH, "disputes", "id subcourtID { id } startTime arbitrable { id } period ruled")
    expected = int(counter["disputesCount"])
    if len(rows) != expected:
        raise RuntimeError(f"gnosis: fetched {len(rows)} disputes, counter says {expected}")
    disputes = [{
        "chain": "gnosis", "id": int(r["id"]), "court": int(r["subcourtID"]["id"]),
        "arbitrable": r["arbitrable"]["id"].lower(), "ts": int(r["startTime"]),
        "period": r["period"], "ruled": bool(r["ruled"]),
    } for r in rows]
    return {
        "asOf": now_iso(), "source": GNOSIS_SUBGRAPH,
        "counter": {k: (int(v) if k in ("disputesCount", "activeJurors", "courtsCount") else v) for k, v in counter.items()},
        "courts": [{"id": int(c["id"]), "disputes": int(c["disputesNum"]), "jurors": int(c["activeJurors"]),
                    "stakedPNK": int(c["tokenStaked"]) / 1e18, "hiddenVotes": c["hiddenVotes"],
                    "parent": int(c["parent"]["id"]) if c.get("parent") else None} for c in courts],
        "disputes": disputes,
    }


def fetch_arbitrum() -> Dict[str, Any]:
    counter = gql(CORENEO, '{ counter(id:"0"){ cases casesRuled casesVoting casesAppealing paidETH redistributedPNK activeJurors stakedPNK } }')["counter"]
    courts = gql(CORENEO, "{ courts(first: 100, orderBy: id) { id name numberDisputes numberStakedJurors stake paidETH paidPNK hiddenVotes minStake feeForJuror timesPerPeriod parent { id } } }")["courts"]
    rows = paginate(CORENEO, "disputes", "id createdAt court { id } arbitrated { id } period ruled templateId")
    expected = int(counter["cases"])
    if len(rows) != expected:
        raise RuntimeError(f"arbitrum: fetched {len(rows)} disputes, counter says {expected}")
    templates = paginate(DRT, "disputeTemplates", "id templateData")
    category: Dict[str, str] = {}
    title: Dict[str, str] = {}
    for t in templates:
        try:
            j = json.loads(t["templateData"])
            category[t["id"]] = (j.get("category") or "").strip()
            title[t["id"]] = (j.get("title") or "").strip()
        except (json.JSONDecodeError, AttributeError):
            category[t["id"]] = ""
    disputes = [{
        "chain": "arbitrum", "id": int(r["id"]), "court": int(r["court"]["id"]),
        "arbitrable": r["arbitrated"]["id"].lower(), "ts": int(r["createdAt"]),
        "period": r["period"], "ruled": bool(r["ruled"]), "templateId": r.get("templateId"),
        "category": category.get(r.get("templateId") or "", "") or None,
        "title": title.get(r.get("templateId") or "", "") or None,
    } for r in rows]
    uncategorised = sum(1 for d in disputes if not d["category"])
    return {
        "asOf": now_iso(), "source": CORENEO, "templatesSource": DRT,
        "counter": {"cases": int(counter["cases"]), "casesRuled": int(counter["casesRuled"]),
                    "casesVoting": int(counter["casesVoting"]), "casesAppealing": int(counter["casesAppealing"]),
                    "activeJurors": int(counter["activeJurors"]), "stakedPNK": int(counter["stakedPNK"]) / 1e18,
                    "paidETH": int(counter["paidETH"]) / 1e18, "redistributedPNK": int(counter["redistributedPNK"]) / 1e18},
        "courts": [{"id": int(c["id"]), "name": c["name"], "disputes": int(c["numberDisputes"]),
                    "jurors": int(c["numberStakedJurors"]), "stakedPNK": int(c["stake"]) / 1e18,
                    "paidETH": int(c["paidETH"]) / 1e18, "paidPNK": int(c["paidPNK"]) / 1e18,
                    "hiddenVotes": c["hiddenVotes"], "minStakePNK": int(c["minStake"]) / 1e18,
                    "feeForJurorETH": int(c["feeForJuror"]) / 1e18,
                    "timesPerPeriod": [int(x) for x in c["timesPerPeriod"]],
                    "parent": int(c["parent"]["id"]) if c.get("parent") else None} for c in courts if int(c["numberDisputes"]) > 0 or int(c["numberStakedJurors"]) > 0],
        "templates": len(templates), "uncategorisedDisputes": uncategorised,
        "disputes": disputes,
    }


def eth_logs(from_block: int, to_block: int) -> List[dict]:
    url = (f"{ETH_BLOCKSCOUT}/api?module=logs&action=getLogs&address={ETH_KLEROS_LIQUID}"
           f"&fromBlock={from_block}&toBlock={to_block}&topic0={V1_DISPUTE_CREATION_TOPIC}")
    res = http(url).get("result") or []
    if len(res) >= 1000:  # Blockscout caps a page; split the range
        mid = (from_block + to_block) // 2
        return eth_logs(from_block, mid) + eth_logs(mid + 1, to_block)
    return res


def eth_disputes_call(ids: List[int]) -> Dict[int, dict]:
    out: Dict[int, dict] = {}
    for i in range(0, len(ids), 15):
        chunk = ids[i:i + 15]
        body = [{"jsonrpc": "2.0", "id": k, "method": "eth_call",
                 "params": [{"to": ETH_KLEROS_LIQUID, "data": DISPUTES_SELECTOR + hex(k)[2:].rjust(64, "0")}, "latest"]} for k in chunk]
        for r in http(ETH_RPC, body):
            if r.get("result") and r["result"] != "0x":
                w = r["result"][2:]
                out[r["id"]] = {"court": int(w[0:64], 16), "arbitrable": "0x" + w[64 + 24:128],
                                "period": V1_PERIODS[int(w[64 * 3:64 * 4], 16)], "ruled": bool(int(w[64 * 7:64 * 8], 16))}
    return out


def fetch_ethereum() -> Dict[str, Any]:
    fees = http(f"{KLEROSBOARD_FN}stats-fees-by-dispute?chainId=1")["data"]
    by_id: Dict[int, dict] = {}
    for f in fees:
        i = int(f["disputeId"])
        by_id[i] = {"chain": "mainnet", "id": i, "court": int(f["courtId"]), "arbitrable": f["arbitrableId"].lower(),
                    "ts": int(f["timestamp"]), "period": None, "ruled": None, "feeETH": f["ethAmount"], "feeUSD": f["usdAmount"]}
    # DisputeCreation logs give the authoritative id set + timestamps; scan from the
    # KlerosLiquid deployment block (5,672,000 ≈ May 2018) in halves when a page fills.
    head = int(http(f"{ETH_BLOCKSCOUT}/api/eth-rpc", {"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []})["result"], 16)
    logs = eth_logs(5_600_000, head)
    ids_from_logs = {int(lg["topics"][1], 16): int(lg["timeStamp"], 16) for lg in logs}
    max_id = max(ids_from_logs) if ids_from_logs else max(by_id)
    missing = [i for i in range(max_id + 1) if i not in by_id]
    for i, ts in ids_from_logs.items():
        if i in by_id and abs(by_id[i]["ts"] - ts) > 0:
            by_id[i]["ts"] = ts  # log timestamp = creation; fee timestamp is later
    resolved = eth_disputes_call(missing) if missing else {}
    for i in missing:
        r = resolved.get(i)
        if not r:
            raise RuntimeError(f"mainnet: dispute {i} in neither fee endpoint nor disputes()")
        by_id[i] = {"chain": "mainnet", "id": i, "court": r["court"], "arbitrable": r["arbitrable"].lower(),
                    "ts": ids_from_logs.get(i), "period": r["period"], "ruled": r["ruled"], "feeETH": None, "feeUSD": None}
    disputes = [by_id[i] for i in sorted(by_id)]
    if len(disputes) != max_id + 1:
        raise RuntimeError(f"mainnet: {len(disputes)} disputes but max id is {max_id}")
    return {"asOf": now_iso(), "source": f"{KLEROSBOARD_FN}stats-fees-by-dispute + {ETH_BLOCKSCOUT} logs + {ETH_RPC} disputes()",
            "fromFeeEndpoint": len(fees), "fromDisputesCall": len(missing), "logsSeen": len(logs), "disputes": disputes}


def fetch_klerosboard_tiles() -> Dict[str, Any]:
    out: Dict[str, Any] = {"asOf": now_iso(), "source": KLEROSBOARD_FN, "chains": {}}
    for cid, key in ((1, "mainnet"), (100, "gnosis"), (42161, "arbitrum")):
        j = http(f"{KLEROSBOARD_FN}stats-active-jurors?chainId={cid}&freq=M")["data"]
        ks = sorted(j, key=int)
        fees = http(f"{KLEROSBOARD_FN}stats-fees?chainId={cid}&freq=M")["data"]
        staked = http(f"{KLEROSBOARD_FN}stats-staked-percentage?chainId={cid}&freq=M")["data"]
        out["chains"][key] = {
            "activeJurors": j[ks[-1]] if ks else None,
            "activeJurorsMonth": dt.datetime.fromtimestamp(int(ks[-1]) / 1000, dt.timezone.utc).strftime("%Y-%m") if ks else None,
            "feesPaid": round(sum(fees.get("ETHAmount", {}).values()), 4),
            "feesPaidUSD": round(sum(fees.get("ETHAmount_usd", {}).values()), 2),
            "stakedPNK": list(staked.get("total_staked", {}).values())[-1] if staked.get("total_staked") else None,
        }
    return out


def resolve_names(addresses: List[tuple]) -> Dict[str, Dict[str, Optional[str]]]:
    """(chainId, address) → {scout, implementation}."""
    out: Dict[str, Dict[str, Optional[str]]] = {}
    for cid, addr in addresses:
        key = f"eip155:{cid}:{addr}"
        scout = None
        try:
            q = f'{{ LItem(where:{{registryAddress:{{_eq:"{SCOUT_TAGS_REGISTRY}"}}, key0:{{_eq:"{key}"}}}}, limit:1){{ key1 key2 }} }}'
            items = http(ENVIO, {"query": q}).get("data", {}).get("LItem", [])
            scout = items[0]["key1"] if items else None
        except Exception:  # noqa: BLE001 — names are best-effort
            pass
        impl = None
        try:
            host = "gnosis.blockscout.com" if cid == 100 else "eth.blockscout.com" if cid == 1 else None
            if host:
                d = http(f"https://{host}/api/v2/addresses/{addr}")
                impls = d.get("implementations") or []
                impl = (impls[0].get("name") if impls else None) or d.get("name")
        except Exception:  # noqa: BLE001
            pass
        out[key] = {"scout": scout, "implementation": impl}
    return out


# ── Derivations used by --compare ────────────────────────────────────────

def month_key(ts: Optional[int]) -> Optional[str]:
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%Y-%m") if ts else None


def compare_with_page(snapshot: Dict[str, Any]) -> List[str]:
    html = (ROOT / "index.html").read_text()
    lines: List[str] = []

    def num(pattern: str) -> Optional[int]:
        m = re.search(pattern, html)
        return int(m.group(1).replace(",", "")) if m else None

    hero = num(r'id="metric-disputes">([0-9,]+)<')
    totals = {ch: len(snapshot["chains"][ch]["disputes"]) for ch in ("mainnet", "gnosis", "arbitrum")}
    lines.append(f"hero total: page {hero} vs chain {sum(totals.values())}")
    for ch, label in (("mainnet", "Ethereum"), ("gnosis", "Gnosis"), ("arbitrum", "Arbitrum")):
        pg = num(r'([0-9,]+) ' + label + r'\b')
        lines.append(f"{ch}: page {pg} vs chain {totals[ch]}" + ("" if pg == totals[ch] else "   <-- DRIFT"))
    # per-court allTime vs chain
    for ch in ("gnosis", "mainnet", "arbitrum"):
        block = re.search(r"            %s: \[\n(.*?)\n            \]" % ch, html, re.S)
        if not block:
            continue
        page_courts = {int(m.group(1)): int(m.group(2)) for m in re.finditer(r"\{ id: (\d+),\s+name: \"[^\"]+\",.*?allTime: (\d+)", block.group(1))}
        chain_courts = Counter(d["court"] for d in snapshot["chains"][ch]["disputes"])
        for cid_, n in sorted(chain_courts.items()):
            pg = page_courts.get(cid_)
            if pg != n:
                lines.append(f"  {ch} court {cid_}: page {pg} vs chain {n}   <-- DRIFT")
        for cid_ in page_courts:
            if cid_ not in chain_courts and page_courts[cid_] > 0:
                lines.append(f"  {ch} court {cid_}: page {page_courts[cid_]} vs chain 0   <-- DRIFT")
    lines.append("  (mainnet per-court counts are CURRENT court from the fee endpoint; court 0 absorbs appealed cases, so court 0 +N / origin −N vs the page's creation-court split is expected)")
    # V2 consumer categories — page groups "Lavalle, Mendoza" under Mendoza
    alias = {"Lavalle, Mendoza": "Mendoza", "Government Entities": "Gov. Entities"}
    cats: Counter = Counter()
    for d in snapshot["chains"]["arbitrum"]["disputes"]:
        if d["court"] in (29, 32):
            cats[alias.get(d["category"] or "", d["category"] or "(blank)")] += 1
    block = re.search(r"const v2ConsumerCategories = \[(.*?)\];", html, re.S)
    page_cats = {m.group(1): int(m.group(2)) for m in re.finditer(r'\{ name: "([^"]+)", count: (\d+)', block.group(1))} if block else {}
    for k, v in cats.most_common():
        pg = page_cats.get(k)
        if pg is not None and pg != v:
            lines.append(f"  §10 {k}: page {pg} vs templates {v}   <-- DRIFT")
    return lines


# ── Main ─────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "data" / "snapshot.json"))
    ap.add_argument("--compare", action="store_true", help="diff the snapshot against index.html constants")
    ap.add_argument("--no-names", action="store_true", help="skip arbitrable name resolution (faster)")
    args = ap.parse_args()

    t0 = time.time()
    chains: Dict[str, Any] = {}
    for name, fn in (("gnosis", fetch_gnosis), ("arbitrum", fetch_arbitrum), ("mainnet", fetch_ethereum)):
        t = time.time()
        chains[name] = fn()
        print(f"  {name:<9} {len(chains[name]['disputes']):>5} disputes  {time.time() - t:5.1f}s", file=sys.stderr)
    tiles = fetch_klerosboard_tiles()
    print(f"  tiles     jurors {tiles['chains']['mainnet']['activeJurors']}/{tiles['chains']['gnosis']['activeJurors']}/{tiles['chains']['arbitrum']['activeJurors']}", file=sys.stderr)

    names: Dict[str, Any] = {}
    if not args.no_names:
        wanted = sorted({(100, d["arbitrable"]) for d in chains["gnosis"]["disputes"]} | {(1, d["arbitrable"]) for d in chains["mainnet"]["disputes"]})
        # only arbitrables active in the last 400 days, to keep the run short
        cutoff = int(time.time()) - 400 * 86400
        recent = {(100 if d["chain"] == "gnosis" else 1, d["arbitrable"]) for ch in ("gnosis", "mainnet") for d in chains[ch]["disputes"] if d["ts"] and d["ts"] >= cutoff}
        names = resolve_names([w for w in wanted if w in recent])
        print(f"  names     {sum(1 for v in names.values() if v['scout'])} scout / {sum(1 for v in names.values() if v['implementation'])} impl of {len(names)}", file=sys.stderr)

    # sanity: unique (chain,id), monotonically dense ids per chain
    for ch, data in chains.items():
        ids = [d["id"] for d in data["disputes"]]
        if len(ids) != len(set(ids)):
            raise RuntimeError(f"{ch}: duplicate dispute ids")
        if sorted(ids) != list(range(len(ids))):
            raise RuntimeError(f"{ch}: dispute ids are not dense 0..n-1")

    snapshot = {
        "generatedAt": now_iso(),
        "totals": {ch: len(chains[ch]["disputes"]) for ch in chains},
        "chains": chains,
        "klerosboard": tiles,
        "arbitrableNames": names,
    }
    snapshot["totals"]["all"] = sum(snapshot["totals"].values())

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(snapshot, indent=1))
    tmp.replace(out)
    print(f"wrote {out} — {snapshot['totals']['all']} disputes in {time.time() - t0:.0f}s", file=sys.stderr)

    # summary
    by_month: Dict[str, Counter] = defaultdict(Counter)
    for ch in chains:
        for d in chains[ch]["disputes"]:
            by_month[month_key(d["ts"])][ch] += 1
    recent_months = sorted(m for m in by_month if m)[-4:]
    print("last months:", "  ".join(f"{m}: " + "/".join(str(by_month[m][c]) for c in ("mainnet", "gnosis", "arbitrum")) for m in recent_months))
    if args.compare:
        print("\n".join(compare_with_page(snapshot)))


if __name__ == "__main__":
    main()
