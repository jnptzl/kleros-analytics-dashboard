# Kleros Analytics Dashboard

A comprehensive analytics dashboard for the Kleros decentralized arbitration protocol, visualizing dispute data across all chains (Ethereum, Gnosis, and Arbitrum V2).

**Live Demo:** https://artisanal-klerosboard.netlify.app

## Features

- **Multi-chain support**: View data from Ethereum Mainnet, Gnosis Chain, and Arbitrum (V2)
- **Real-time metrics**: Total disputes, active courts, staked jurors, fees paid, and PNK redistributed
- **Interactive timeline**: Monthly dispute activity by court with stacked/grouped views
- **Court analytics**: Activity rankings, dispute distribution, and detailed court information
- **Application tracking**: See which dApps generate the most disputes (PoH, Curate, Seer, etc.)
- **Time filtering**: View data for 30d, 90d, 1y, or all-time periods

## Data Sources

The dashboard aggregates data from on-chain logs (V1) and a public subgraph (V2):

| Chain | Source | Auth |
|-------|--------|------|
| Ethereum (V1) | Blockscout etherscan-compat API on `0x988b3a538b618c7a603e1c11ab82cd16dbe28069` | None (UA required, see notes) |
| Gnosis (V1) | Public Gnosis RPC `eth_getLogs` on `0x9C1dA9A04925bDfDedf0f6421bC7EEa8305F9002` | None |
| Arbitrum (V2) | Goldsky subgraph `kleros-v2-coreneo/v0.17.2/gn` | None |

> **Note**: the legacy Klerosboard subgraphs (`klerosboard-mainnet`, `klerosboard-gnosis`) are deprecated and return `"deployment does not exist"`. Don't fall back to them. See [`klerosboard-data-guide.md`](./klerosboard-data-guide.md) for verified data-pull recipes.

## Project Structure

```
artisanal-dashboard/
├── index.html                    # Single-page dashboard application
├── klerosboard-data-guide.md     # Comprehensive data extraction guide
├── README.md                     # This file
├── .claude/launch.json           # Local preview config (python http.server :8765)
└── .gitignore
```

## Local Development

This is a static site with no build step. Simply open `index.html` in a browser or serve it locally:

```bash
# Using Python
python -m http.server 8000

# Using Node.js
npx serve .

# Using PHP
php -S localhost:8000
```

## Deployment

The site is deployed on Netlify **via the CLI, not a GitHub webhook.**
⚠️ **`git push` alone does NOT update the live site.** Always run both:

```bash
git add index.html && git commit -m "..." && git push origin main   # version control
netlify deploy --prod --dir=.                                        # what actually goes live
```

First-time setup: `npm install -g netlify-cli && netlify login`.

## Weekly Refresh

The dashboard is hand-curated and updated **weekly**. The data model is
month-bucketed, so a weekly run just re-fetches the **current (partial) month**
and overwrites that bucket — `rolling-30`, `last-12m`, totals, and the timeline
all recompute from it. You only append a brand-new month bucket once a month.

1. **Pull the current month's data** with the reusable tool (lives in the sibling video project):
   ```bash
   python3 "../../kleros marketing tasks/video-generation/artisanal-dashboard-video/tools/refresh.py" --month YYYY-MM
   ```
   It does one wide `eth_getLogs` per chain, buckets by month, auto-resolves Gnosis arbitrable contract names, and prints every value keyed to where it goes. It also prints the Klerosboard V1 lookups + V2 MCP calls it can't do over pure RPC.
   - **Mid-week drift check** (no full re-pull): `get_court_stats(chainId=42161, courtId=N).totalDisputes` flags new V2 cases fast; confirm the headline count with the RPC max-dispute-id one-liner before bumping.
2. **Overwrite** the current month in `monthlyDataByCourt` (per chain) and `monthlyDataByArbitrable` in `index.html` (append a new key only when the month rolls over).
3. **Reconcile the summary figures** — these all silently drift from `monthlyDataByCourt` unless re-derived each cycle:
   - `yearlyData` current-year row = sum of that year's monthly entries (verify `Σ yearlyData ≈ hero total ± 1`)
   - hero `metric-*`, per-chain ledger, `v2Stats`, `applicationsData[].allTime`, `courtsData[].allTime`, `v2*Categories`, `recentCases`, use-case chart
   - cross-panel gates: apps-Arbitrum total **==** V2 total; consumer categories sum **==** the "§10 …N cases" header; timeline All-view Total line **==** stacked bars for the latest month
4. **Bump the date:** one line — `const LAST_REFRESH = 'DD Mon YYYY'` near `PRICES`. It fills both the hero attribution and footer colophon stamps on load. (The `// YTD through ...` comment in `yearlyData` is a code comment, optional.)
5. **Deploy** (the two-step flow above), then verify the live `timelineChart` / `yearlyChart` / `distributionChart` / `metric-*` and the cross-panel sums — don't trust the push.

## Data Extraction Guide

For detailed instructions on scraping Kleros data, including:
- GraphQL queries for disputes, courts, jurors, and votes
- Pagination strategies for large datasets
- Time-based filtering
- IPFS evidence retrieval
- V1 vs V2 differences

See **[klerosboard-data-guide.md](./klerosboard-data-guide.md)**

### Quick Start

**V2 (Arbitrum) — Goldsky subgraph, one query for the headline numbers:**

```javascript
const V2 = "https://api.goldsky.com/api/public/project_cmgx9all3003atlp2bqha1zif/subgraphs/kleros-v2-coreneo/v0.17.2/gn";

const res = await fetch(V2, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: `{
    counter(id: "0") {
      cases casesRuled casesVoting casesAppealing
      paidETH redistributedPNK activeJurors stakedPNK
    }
  }` })
});
const { data } = await res.json();
// Divide paidETH, stakedPNK, redistributedPNK by 1e18
```

**V1 (Eth + Gnosis) — fast-path, no pagination:**
The latest `DisputeCreation` log's `topics[1]` is the zero-indexed dispute ID, so `total = parseInt(topics[1], 16) + 1`. Pull from Blockscout (Eth) or `rpc.gnosischain.com` (Gnosis). Topic0: `0x141dfc18aa6a56fc816f44f0e9e2f1ebc92b15ab167770e17db5b084c10ed995`.

## Statistics (September 2026 · last refresh 5 Sep)

| Metric | Ethereum (V1) | Gnosis (V1) | Arbitrum (V2) | Total |
|--------|---------------|-------------|---------------|-------|
| Total Disputes | 1,678 | 992 | 197 | **2,867** |
| Rolling 30d | 0 | ~65 | ~42 | ~107 |
| Last 12 months | 7 | 328 | 137 | +472 |
| Status | dormant (Governor + Reality.eth one-offs) | very active (PoH surge in Humanity Court, new Hidden-Voting curation court 19) | growing (Agentic Commerce Court 34 opened 19 Aug, 46 test-docket cases) | — |

## Related Resources

- [Kleros Documentation](https://docs.kleros.io/)
- [Klerosboard](https://klerosboard.com/) - Official community dashboard
- [Kleros GitHub](https://github.com/kleros)
- [The Graph Explorer](https://thegraph.com/explorer)

## License

MIT
