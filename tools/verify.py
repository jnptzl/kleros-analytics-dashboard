#!/usr/bin/env python3
"""Render gate for the artisanal Kleros dashboard.

Serves the repo over HTTP, opens index.html in headless Chromium, reads every
chart and tile the way a visitor sees them, and ASSERTS the cross-panel
invariants that used to be checked by hand. Exits non-zero on any failure, so
it can gate a deploy.

    python3 tools/verify.py                      # run all gates, print a report
    python3 tools/verify.py --report out.json    # also write the measurements
    python3 tools/verify.py --dump-text out.txt  # dump visible text across the
                                                 # whole interaction matrix
                                                 # (diff two dumps to prove a
                                                 # refactor changed nothing)
    python3 tools/verify.py --screenshot page.png

Browser: uses $DASHBOARD_CHROME if set (a Chrome/Chromium binary), otherwise
Playwright's bundled Chromium (`playwright install chromium`). Python 3.9+.
"""
from __future__ import annotations

import argparse
import datetime as dt
import http.server
import json
import os
import socket
import socketserver
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent

CHAINS = ["all", "gnosis", "mainnet", "arbitrum"]
PERIODS = ["30d", "90d", "1y", "all"]
RANGES = ["90d", "12m", "2y", "all"]
VIEWS = ["stacked", "grouped"]
APP_PERIODS = ["30d", "90d", "1y", "all"]

# Documented, deliberate tolerance: one Ethereum dispute predates the first
# month in monthlyDataByCourt (2019-03), so the yearly chart is allowed to be
# exactly one below the hero. Anything else is a failure.
YEARLY_TOLERANCE = 1

READ_STATE = """() => {
  const t = id => (document.getElementById(id) || {}).textContent;
  const num = s => parseInt(String(s || '').replace(/[^0-9]/g, ''), 10);
  const chart = id => Chart.getChart(id);
  const out = {};
  out.hero = num(t('metric-disputes'));
  out.heroRecent = num(t('metric-disputes-recent'));
  out.heroYear = num(t('metric-disputes-year'));
  out.heroRefresh = t('hero-refresh');
  out.footerRefresh = t('footer-refresh');
  out.lastRefreshConst = LAST_REFRESH;
  out.courtsTile = num(t('metric-courts'));
  out.courtsSub = t('metric-courts-sub');
  out.jurorsTile = num(t('metric-jurors'));
  // chain ledger line under the hero
  const ledger = [...document.querySelectorAll('.mark-e, .mark-g, .mark-a')]
    .map(m => m.parentElement).filter(p => p && /Ethereum|Gnosis|Arbitrum/.test(p.textContent));
  out.ledger = {};
  ledger.slice(0, 3).forEach(p => {
    const txt = p.textContent;
    const n = num(txt.split(/Ethereum|Gnosis|Arbitrum/)[0]);
    if (/Ethereum/.test(txt)) out.ledger.mainnet = n;
    else if (/Gnosis/.test(txt)) out.ledger.gnosis = n;
    else if (/Arbitrum/.test(txt)) out.ledger.arbitrum = n;
  });
  const sumAll = o => Object.values(o).reduce((a, b) => a + b, 0);
  out.courtsAllTime = {
    gnosis: courtsData.gnosis.reduce((a, c) => a + c.allTime, 0),
    mainnet: courtsData.mainnet.reduce((a, c) => a + c.allTime, 0),
    arbitrum: courtsData.arbitrum.reduce((a, c) => a + c.allTime, 0),
  };
  out.monthlySums = {};
  for (const ch of ['gnosis', 'mainnet', 'arbitrum']) {
    out.monthlySums[ch] = Object.values(monthlyDataByCourt[ch]).reduce((a, m) => a + sumAll(m), 0);
  }
  const yc = chart('yearlyChart');
  out.yearlySum = yc.data.datasets.reduce((a, d) => a + d.data.reduce((x, y) => x + y, 0), 0);
  out.v2Stats = Object.assign({}, v2Stats);
  out.v2CourtsJurorsMissing = courtsData.arbitrum.filter(c => typeof c.jurors !== 'number').map(c => c.id);
  out.v2Ledger = courtsData.arbitrum.reduce((a, c) => a + c.allTime, 0);
  out.appsArbitrum = applicationsData.filter(a => a.chain === 'arbitrum').reduce((a, x) => a + x.allTime, 0);
  out.v2MonthlyLastCumulative = v2MonthlyData[v2MonthlyData.length - 1].cumulative;
  out.v2MonthlyDisputesSum = v2MonthlyData.reduce((a, m) => a + m.disputes, 0);
  out.consumerSum = v2ConsumerCategories.reduce((a, c) => a + c.count, 0);
  out.consumerHeader = num((document.querySelector('h3 .num') || {}).textContent);
  out.curationSum = v2CurationCategories.reduce((a, c) => a + c.count, 0);
  out.curationCourt = (courtsData.arbitrum.find(c => c.id === 31) || {}).allTime;
  out.agenticSum = (typeof v2AgenticCategories !== 'undefined') ? v2AgenticCategories.reduce((a, c) => a + c.count, 0) : null;
  out.agenticCourt = (courtsData.arbitrum.find(c => c.id === 34) || {}).allTime;
  out.useCaseSum = chart('useCaseChart').data.datasets[0].data.reduce((a, b) => a + b, 0);
  // V2 key-stat tiles (static markup) vs v2Stats constant
  const eyebrows = [...document.querySelectorAll('.eyebrow')];
  // The hero also has an "Active courts" eyebrow; the V2 key-stat grid is the LAST match.
  const tileAfter = label => { const es = eyebrows.filter(x => x.textContent.trim() === label && x.parentElement && x.parentElement.querySelector('.display-small')); const e = es[es.length - 1]; return e ? e.parentElement.querySelector('.display-small').textContent : null; };
  out.v2TileTotal = num(t('v2-total-cases') || tileAfter('Total cases'));
  out.v2TileCourts = num(t('v2-active-courts') || tileAfter('Active courts'));
  out.v2ActiveCourts = courtsData.arbitrum.length;
  return out;
}"""

READ_DONUT = """() => {
  const dc = Chart.getChart('distributionChart');
  return { sum: dc.data.datasets[0].data.reduce((a, b) => a + b, 0), labels: dc.data.labels };
}"""

READ_TIMELINE = """() => {
  const tc = Chart.getChart('timelineChart');
  const li = tc.data.labels.length - 1;
  const bars = tc.data.datasets.filter(d => d.type === 'bar').reduce((a, d) => a + (d.data[li] || 0), 0);
  const line = tc.data.datasets.find(d => d.type !== 'bar');
  return { label: tc.data.labels[li], bars, line: line ? line.data[li] : null, nBars: tc.data.datasets.filter(d => d.type === 'bar').length };
}"""

READ_TEXT = "() => document.body.innerText"


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args: Any) -> None:  # noqa: D401
        pass


def serve(root: Path) -> "tuple[socketserver.TCPServer, int]":
    handler = lambda *a, **k: _Quiet(*a, directory=str(root), **k)  # noqa: E731
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.TCPServer(("127.0.0.1", 0), handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port


class Gate:
    def __init__(self) -> None:
        self.failures: List[str] = []
        self.passes: List[str] = []

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        (self.passes if ok else self.failures).append(f"{name}{' — ' + detail if detail else ''}")

    def eq(self, name: str, a: Any, b: Any) -> None:
        self.check(name, a == b, f"{a} vs {b}")


def parse_refresh(s: Optional[str]) -> Optional[dt.date]:
    if not s:
        return None
    try:
        return dt.datetime.strptime(s.strip(), "%d %b %Y").date()
    except ValueError:
        return None


def run(args: argparse.Namespace) -> int:
    from playwright.sync_api import sync_playwright

    srv, port = serve(ROOT)
    url = f"http://127.0.0.1:{port}/index.html"
    gate = Gate()
    report: Dict[str, Any] = {"url": url, "matrix": []}
    text_dump: List[str] = []
    errors: List[str] = []

    launch_kwargs: Dict[str, Any] = {}
    chrome = os.environ.get("DASHBOARD_CHROME")
    if chrome:
        launch_kwargs["executable_path"] = chrome
    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page(viewport={"width": 1400, "height": 900}, color_scheme="dark")
        page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.on("requestfailed", lambda r: errors.append(f"requestfailed: {r.url}") if r.url.startswith(url.rsplit('/', 1)[0]) else None)
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(800)

        st = page.evaluate(READ_STATE)
        report["state"] = st

        # ── Static invariants ────────────────────────────────────────────
        ledger_sum = sum(st["ledger"].values())
        gate.eq("hero total == Ethereum + Gnosis + Arbitrum ledger line", st["hero"], ledger_sum)
        for ch in ("gnosis", "mainnet", "arbitrum"):
            gate.eq(f"{ch}: ledger line == Σ courtsData.allTime", st["ledger"].get(ch), st["courtsAllTime"][ch])
        gate.eq("gnosis: Σ monthlyDataByCourt == ledger", st["monthlySums"]["gnosis"], st["ledger"].get("gnosis"))
        gate.eq("arbitrum: Σ monthlyDataByCourt == ledger", st["monthlySums"]["arbitrum"], st["ledger"].get("arbitrum"))
        gate.check("mainnet: Σ monthlyDataByCourt == ledger − 1 (pre-2019-03 case, documented)",
                   st["ledger"].get("mainnet") - st["monthlySums"]["mainnet"] in (0, YEARLY_TOLERANCE),
                   f"{st['monthlySums']['mainnet']} vs {st['ledger'].get('mainnet')}")
        gate.check("Σ yearlyData == hero (±1 documented)", 0 <= st["hero"] - st["yearlySum"] <= YEARLY_TOLERANCE,
                   f"{st['yearlySum']} vs {st['hero']}")
        gate.eq("V2: apps-Arbitrum allTime == V2 court ledger", st["appsArbitrum"], st["v2Ledger"])
        gate.eq("V2: court ledger == v2Stats.totalCases", st["v2Ledger"], st["v2Stats"]["totalCases"])
        gate.eq("V2: v2Stats.totalCases == 'Total cases' tile", st["v2Stats"]["totalCases"], st["v2TileTotal"])
        gate.eq("V2: 'Active courts' tile == courtsData.arbitrum rows", st["v2TileCourts"], st["v2ActiveCourts"])
        gate.eq("V2: last cumulative in v2MonthlyData == totalCases", st["v2MonthlyLastCumulative"], st["v2Stats"]["totalCases"])
        gate.eq("V2: Σ v2MonthlyData.disputes == Σ monthlyDataByCourt.arbitrum", st["v2MonthlyDisputesSum"], st["monthlySums"]["arbitrum"])
        gate.eq("§10: Σ consumer categories == header count", st["consumerSum"], st["consumerHeader"])
        gate.eq("§13: Σ curation categories == court 31 allTime", st["curationSum"], st["curationCourt"])
        if st["agenticSum"] is not None:
            gate.eq("§14: Σ agentic categories == court 34 allTime", st["agenticSum"], st["agenticCourt"])
        gate.check("V2 courts all carry a juror count", not st["v2CourtsJurorsMissing"], str(st["v2CourtsJurorsMissing"]))
        gate.check("use-case chart within hero total", st["useCaseSum"] <= st["hero"], f"{st['useCaseSum']} vs {st['hero']}")
        gate.eq("hero refresh stamp == LAST_REFRESH", st["heroRefresh"], st["lastRefreshConst"])
        gate.eq("footer refresh stamp == LAST_REFRESH", st["footerRefresh"], st["lastRefreshConst"])
        d = parse_refresh(st["lastRefreshConst"])
        gate.check("LAST_REFRESH parses as 'DD Mon YYYY'", d is not None, str(st["lastRefreshConst"]))
        if d is not None and args.max_age_days is not None:
            age = (dt.date.today() - d).days
            gate.check(f"LAST_REFRESH within {args.max_age_days} days", age <= args.max_age_days, f"{age} days old")
        gate.check("hero deltas are positive integers", st["heroRecent"] >= 0 and st["heroYear"] >= st["heroRecent"],
                   f"30d={st['heroRecent']} 12m={st['heroYear']}")

        # ── Interaction matrix ───────────────────────────────────────────
        def snapshot(tag: str) -> None:
            if args.dump_text:
                text_dump.append(f"===== {tag} =====\n" + page.evaluate(READ_TEXT))

        for ch in CHAINS:
            page.evaluate(f"setChain('{ch}')")
            for per in PERIODS:
                page.evaluate(f"setTimePeriod('{per}')")
                donut = page.evaluate(READ_DONUT)
                rec: Dict[str, Any] = {"chain": ch, "period": per, "donut": donut["sum"]}
                if per == "all":
                    expected = st["hero"] if ch == "all" else st["ledger"].get(ch)
                    gate.eq(f"donut[{ch}/all] sums to ledger", donut["sum"], expected)
                report["matrix"].append(rec)
                snapshot(f"chain={ch} period={per}")
            for rng in RANGES:
                page.evaluate(f"setTimeRange('{rng}')")
                for view in VIEWS:
                    page.evaluate(f"setTimelineView('{view}')")
                    tl = page.evaluate(READ_TIMELINE)
                    gate.check(f"timeline[{ch}/{rng}/{view}] bars == total line (latest month)",
                               tl["line"] is None or tl["bars"] == tl["line"], f"{tl['bars']} vs {tl['line']}")
                    report["matrix"].append({"chain": ch, "range": rng, "view": view, **tl})
                    snapshot(f"chain={ch} range={rng} view={view}")
            for ap in APP_PERIODS:
                page.evaluate(f"setAppsPeriod('{ap}')")
                snapshot(f"chain={ch} apps={ap}")
            # court panel open/close for the first listed court
            page.evaluate("(() => { const r = document.querySelector('#courts-list .court-row'); if (r) r.click(); })()")
            page.wait_for_timeout(150)
            snapshot(f"chain={ch} panel")
            page.evaluate("closeCourtPanel()")
        page.evaluate("setChain('all'); setTimeRange('12m'); setTimePeriod('30d'); setAppsPeriod('all')")
        page.wait_for_timeout(300)

        gate.check("no console / page / request errors across the matrix", not errors, "; ".join(errors[:5]))

        if args.screenshot:
            page.screenshot(path=args.screenshot, full_page=True)
        browser.close()
    srv.shutdown()

    report["passes"] = gate.passes
    report["failures"] = gate.failures
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=1))
    if args.dump_text:
        Path(args.dump_text).write_text("\n".join(text_dump))

    for p_ in gate.passes:
        print(f"  ok   {p_}")
    for f in gate.failures:
        print(f"  FAIL {f}")
    print(f"\n{len(gate.passes)} passed, {len(gate.failures)} failed — hero {st['hero']}, refresh {st['lastRefreshConst']}")
    return 2 if gate.failures else 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", help="write measurements + results as JSON")
    ap.add_argument("--dump-text", help="write body.innerText across the interaction matrix")
    ap.add_argument("--screenshot", help="full-page PNG after the matrix")
    ap.add_argument("--max-age-days", type=int, default=None, help="fail if LAST_REFRESH is older than this")
    args = ap.parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()
