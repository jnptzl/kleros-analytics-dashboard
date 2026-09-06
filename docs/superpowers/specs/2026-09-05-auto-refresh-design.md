# Auto-refresh for artisanal-klerosboard.netlify.app

Status: **proposed, awaiting Jean's approval** (written 5 Sep 2026, after the manual
5 Sep refresh). Nothing here is built yet. The scratch scripts that produced today's
numbers live in `kleros marketing tasks/video-generation/artisanal-dashboard-video/tools/refresh-seed-2026-09-05/`
and are the seed for `refresh.py` below.

## Why

The site went 82 days without a refresh (15 Jun → 5 Sep). In that gap 214 disputes
landed, two courts opened (Gnosis 19, Arbitrum 34) and every hand-bumped snapshot
drifted. A refresh today is ~40 edits across 14 structures in one 1,900-line HTML
file, so it only happens when someone sits down for two hours. The data model is
already month-bucketed and self-deriving; what is missing is a script that owns the
numbers and a scheduler that runs it.

## What today proved (all pure HTTP, no MCP, no wallet)

| Need | Source | Verified |
|---|---|---|
| New disputes, all chains | Gnosis RPC `eth_getLogs`; Eth Blockscout logs API; V2 Goldsky `disputes(orderBy:createdAt)` | 161 / 3 / 56 since Jun 1, totals match Klerosboard 2,867 |
| Per-court split | V1 `disputes(uint256)` batch `eth_call` (Gnosis 40/call, Eth publicnode 15/call); V2 `court{id}` from subgraph | caught new courts 19 and 34 |
| Per-arbitrable split | V1 log `topics[2]`; V2 `arbitrated{id}` | drives §05 apps |
| Arbitrable names | Gnosis/Eth Blockscout `implementations[0].name` | PoH, LightGTCR, PermanentGTCR, KlerosGovernor, Realitio |
| V2 stats + per-court jurors | Goldsky `counter(id:"0")`, `courts{numberStakedJurors stake}` | 197 / 38 / 664K |
| V1 jurors, fees, staked | Klerosboard 3.0 `/.netlify/functions/stats-active-jurors|stats-fees|stats-staked-percentage?chainId=N&freq=M` (JSON, no auth) | jurors 703 / 286, fees 407 Ξ / 45.8K xDAI |
| V1 per-court jurors, PNK redistributed | Klerosboard SPA `/N/courts` and `/N` tiles (needs a browser; the underlying gateway subgraph key sits in their JS bundle) | 25 Eth + 20 Gn courts |
| Prices | Klerosboard tile (ETH $2,507 · PNK $0.008) or CoinGecko | – |
| Deploy | `netlify deploy --prod` with the stored token; `git push` with the gh token | live in 4 s |
| Render gates | Playwright + system Chrome reading `Chart.getChart(...)` data and `metric-*` | 0 console errors across 4×4×4×2 toggles |

## Design

### 1. Split data from page

`index.html` keeps its markup, renderers and CSS. The 14 data constants
(`courtsData`, `monthlyDataByCourt`, `monthlyDataByArbitrable`, `applicationsData`,
`v2Stats`, `v2MonthlyData`, `v2*Categories`, `recentCases`, `yearlyData`,
`useCaseData`, `PRICES`, `LAST_REFRESH`, plus the static hero/V2/§13/§14 tile
numbers) move into one generated block between `/* DATA:BEGIN */` … `/* DATA:END */`
markers. The static tile numbers get `id`s and are filled at load, the way
`LAST_REFRESH` and the §08 price tiles already are. The README-facing meaning of
every field stays the same; only the authoring moves out of the HTML.

### 2. Three files replace hand memory

- `data/ledger.jsonl` — one line per dispute: `chain, id, court, arbitrable, ts`.
  Append-only, rebuilt from chain on `--full`. Backfill: Gnosis and Arbitrum in
  full (992 + 197 disputes, minutes). Ethereum keeps the existing monthly dict as a
  frozen `data/legacy-eth-monthly.json` (its creation-court split came from the old
  subgraph and cannot be re-derived from `disputes()`, which reports the *current*
  court after appeals) and only appends new ids. Every derived structure comes
  from the ledger: month buckets, per-court and per-arbitrable all-time, yearly,
  hero totals, V2 monthly/cumulative, recent cases, §14 tiles.
- `data/manual.json` — the only hand-edited file. Court names and colours,
  arbitrable registry (`arbId → name, icon, desc, url, chain`), court → use-case
  map, V2 consumer categorisation rules (`court 32 → Junín`, `court 29 → Lemon`
  unless overridden per id), the V2 curation/general/humanity/non-tech category
  lists, and the §14 court-34 parameters. Anything the rules do not cover falls
  into an "Other / unclassified" bucket, so the §10 header always equals the sum.
- `data/klerosboard.json` — the V1 tiles the script cannot get from chain:
  per-chain active jurors, fees, PNK redistributed, per-court jurors. Refreshed
  by the same run via the Klerosboard functions plus a Playwright read of the two
  courts pages; if Klerosboard is down the previous file is kept and the page
  shows "jurors as of <date>" instead of failing.

### 3. `refresh.py` — one command, fail-closed

```
python3 refresh.py            # incremental: new ids since ledger max, current month rebucketed
python3 refresh.py --full     # rebuild ledger from chain
python3 refresh.py --no-deploy
```

Steps: pull → append ledger → derive → render data block into `index.html` →
run the gates → commit → `netlify deploy --prod`. Gates (from today's `verify.py`,
run headless): Σ yearly = hero ± 1; donut sum = hero; timeline All bars = total
line; apps-Arbitrum = V2 court ledger = subgraph counter; consumer categories =
§10 header; per-court jurors present for every V2 court; zero console errors
across every chain × period × range × view. Any gate failure exits 2 and leaves
the deployed site untouched. Today's numbers become the first regression fixture.

### 4. Scheduler

**Recommended: GitHub Actions**, weekly (Mon 06:00 UTC) plus `workflow_dispatch`.
The repo is already `jnptzl/kleros-analytics-dashboard`; Playwright and Python
install cleanly in CI; it runs while the Mac sleeps. Needs two repo secrets:
`NETLIFY_AUTH_TOKEN` (create a fresh Personal Access Token at
app.netlify.com/user/applications rather than reusing the CLI token) and
`NETLIFY_SITE_ID` (`5f84ff38-3937-4fa1-80b5-6bbaae874f37`, not secret). The job
commits the ledger and the regenerated `index.html` back to `main` with the
Actions token, so git history doubles as the audit log.

Fallback trigger: a Claude scheduled task (like `marketing-data-daily`) that just
runs `refresh.py` locally on Wednesday morning before the community call, so the
call recap always has fresh numbers even if CI is broken. It should not do the
data work itself.

### 5. Small live overlay (optional, cheap)

Goldsky allows cross-origin requests, so the page can fetch `counter(id:"0")` on
load and, if it is ahead of the snapshot, show "+N since <LAST_REFRESH>" next to
the hero. Everything else stays static. No RPC or Klerosboard calls from
visitors' browsers.

## Alternatives considered

- **Fully client-side live page.** Always fresh, no pipeline. Rejected: 1,000+
  `eth_call`s per visitor for court splits, public RPC rate limits, Klerosboard
  CORS is unknown, and the curated names/categories still need a store.
- **Keep the video project's `refresh.py` and extend it.** It only counts; it
  never learned court splits, and its output is a checklist for a human. Retire
  it once this ships; the video can read `data/` from this repo.
- **Netlify build from GitHub instead of CLI deploy.** Would make `git push` the
  only step, but linking the site to the repo needs the Netlify UI. Worth doing
  at the same time if Jean is in the UI creating the token anyway; then the
  Action needs no Netlify secret at all.

## Effort

About 400 lines of Python, most already written as today's seed scripts
(`probe.py` + `courts.py` = pull, `compute.py` = derive, `patch.py` = render,
`verify.py` = gates). Estimate: one focused session to fold them together and
backfill the ledger, plus the one-off GitHub secret setup on Jean's side.

## Decisions needed from Jean

1. Go ahead with the split (data block + `data/` files) or keep everything inline?
2. GitHub Actions weekly (needs the two secrets) or local scheduled task only?
3. Keep the Ethereum monthly history frozen as legacy (recommended) or spend a
   one-off ~1,700 `eth_getTransactionByHash` calls to rebuild creation courts?
4. Live V2 overlay on the hero: yes or no?
