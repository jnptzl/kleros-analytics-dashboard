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

## What Klerosboard 3.0 teaches (investigated 6 Sep 2026)

Repo `klerosboard/klerosboard` (MIT, Koki + kemuru), Vite + React 19 + MUI 9 + viem,
deployed by Netlify from the repo (no CLI), five TypeScript Netlify functions under
`netlify/functions/`, secrets as Netlify env vars. Findings that change this design:

1. **The Klerosboard Gnosis subgraph is public again.**
   `api.studio.thegraph.com/query/66145/klerosboard-gnosis/version/latest` answers
   without a key: `klerosCounter` (disputes, active jurors, fees, PNK redistributed,
   staked, court count), `courts{disputesNum activeJurors tokenStaked}` and the full
   `disputes{id subcourtID startTime arbitrable period ruled}` list, 992 rows in 0.9 s.
   → Gnosis needs no `eth_getLogs`, no `disputes()` batches, no Klerosboard scraping.
   The mainnet twin lives only on the Graph gateway
   (`ECENsJRf…`, needs a free API key). Until Jean creates one, mainnet court ids
   come from Klerosboard's `stats-fees-by-dispute?chainId=1` (1,621 of 1,678 disputes
   carry `courtId`, `arbitrableId`, `timestamp`; the 57 missing never paid fees) plus
   one `disputes()` call per missing id.
2. **V2 categories are in the data, not in our heads.** Every V2 dispute has a
   `templateId`; the DRT subgraph (`kleros-v2-drt/v0.12.0`) holds `templateData` JSON
   with a `category` string. Joining the two gives Junín 45 · Lemon 44 · Metlife 15 …
   for courts 29+32 and Agentic commerce 22 · Oracle 11 · Services 7 … for court 34.
   Our hand-kept §10 was off by up to 6 per category; corrected on 6 Sep from this
   source. `manual.json` loses the consumer rules entirely; only the display names,
   icons and the "Other" grouping remain manual.
3. **Arbitrable names come from Scout Address Tags** via the Envio HyperIndex
   (`indexer.hyperindex.xyz/1a2f51c/v1/graphql`, `LItem` where `key0 = eip155:<chain>:<addr>`,
   `key1` = name). Coverage is partial (Kleros Tokens yes; PoH V2, Governor, Reality
   no), so keep Blockscout `implementations[0].name` as the fallback, in that order.
4. **A ready-made address → category map.** `src/lib/arbitrableCategories.ts` tags
   ~100 V1 arbitrables (Curation, PoH, Prediction Markets, Governance, Linguo,
   Escrow, Finance, Other) and is regenerated from a CSV by a script. MIT; copy the
   map into `manual.json` as the seed for the §07 use-case chart instead of the
   per-court guesswork we do now.
5. **Their "active jurors" is replayed, not read.** `stats-active-jurors` fetches
   every `StakeSet` event and replays them month by month (juror active = latest
   `newTotalStake > 0`), with a 10-minute in-memory cache and
   `Cache-Control: public, s-maxage=86400, max-age=3600`. That is why their monthly
   series exists at all; the live tile is the subgraph counter. Reuse the endpoint,
   do not reimplement it.
6. **Deploy model.** Netlify builds from `master` on push; env vars carry the Graph
   key; functions are the API. For us the equivalent is linking the site to the
   repo so `git push` deploys, which removes the Netlify token from CI entirely
   (only the Graph key would remain, and only if we adopt the mainnet subgraph).

Net effect on the pipeline: fewer RPC calls (Gnosis: zero; Arbitrum: zero; Ethereum:
a handful per month), zero manual categorisation for V2, and three external
dependencies to watch (Goldsky, Graph Studio, Klerosboard functions), each with an
obvious fallback that already works today.

## Codex review (6 Sep 2026) and what it changes

Codex (gpt-5 class, xhigh reasoning) read the spec, the page, the seed scripts and the
Klerosboard source. Verdict: "do not implement as written". Accepted points, now part
of the design:

- **Full fetch, not incremental.** Under 3,000 disputes; Gnosis and Arbitrum are one
  cheap query each. Weekly full pull → normalize → validate → derive → generate. No
  ledger high-watermark, no reorg handling, no "rebucket the current month".
- **Snapshot, not append-only ledger.** `data/snapshot.json` (every dispute with
  `chain, id, court, arbitrable, ts, period, ruled, templateId, category, source,
  observedAt`) is rebuilt each run and atomically replaced. Courts, statuses and
  categories can change after the fact; append-only was the wrong model.
- **Generate a data file, not a marker block.** `data/dashboard-data.js` sets
  `window.DASHBOARD_DATA`; `index.html` loads it before the renderers. The page
  stops being edited by scripts at all.
- **Fail-closed means all-or-nothing.** Fetch into a temp dir, validate the complete
  snapshot, then swap. Never deploy fresh disputes next to stale juror tiles.
  Per-source `asOf` timestamps are stored and shown; `LAST_REFRESH` becomes the
  snapshot time, and a source older than the snapshot is labelled.
- **Real gates, with source checks.** The seed `verify.py` only prints; the real
  one asserts and exits non-zero. Beyond internal consistency add: cursor
  pagination with a terminal-count assertion on every list query (Gnosis is at
  992 of a 1,000 page), unique `(chain, id)`, no unexplained count decrease versus
  the previous snapshot, GraphQL `errors` and `_meta.block` freshness, counter
  versus list agreement, category coverage, and a post-deploy live smoke test.
- **Exact time windows.** With per-dispute timestamps, 30d/90d/1y become true
  windows from the snapshot time. Today's "30d" is two calendar months.
- **Escape external strings.** Court names and template categories come from
  IPFS and subgraphs; they must not reach `innerHTML` or inline `onclick`
  unescaped. Render with `textContent` and data attributes.
- **Deployment out of the script.** `refresh.py` fetches, derives, validates,
  writes. GitHub Actions commits the snapshot; Netlify deploys from the repo on
  push, so the Netlify token disappears from CI. One workflow, `workflow_dispatch`,
  failure notification, no local fallback cron (it would race CI).
- **Fix the copy with the change.** Footer "No cron, no subgraph — just a human and
  the chain", the README deploy section, and the hard-coded masthead month all
  become false the day this ships.
- **The estimate was optimistic.** The reusable part of the seed is the queries.
  Budget a proper session for schemas, tests, CI and atomic writes.

Rejected or qualified:

- *"Aggregate V2 applications by arbitrable, not court."* Every V2 dispute shares one
  `arbitrated` address (the DisputeResolver), so that collapses §05 into one row.
  For V2 the application dimension is the template `category`; courts stay a
  separate dimension. Codex is right for V1, where the arbitrable is the app.
- *"Represent the pre-2019-03 Ethereum dispute explicitly."* Agreed in principle;
  it becomes an explicit `unknown-month` row in the legacy baseline rather than a
  tolerated ±1.

Revised answers to the four decisions: (1) split, via `data/dashboard-data.js`;
(2) GitHub Actions only, Netlify linked to the repo, no Netlify token; (3) freeze
Ethereum history as a versioned baseline, do not attempt transaction-input
recovery; (4) no live overlay.

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
