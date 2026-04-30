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

The site is deployed on Netlify. To deploy your own instance:

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Login and deploy
netlify login
netlify deploy --prod
```

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

## Statistics (April 2026)

| Metric | Ethereum (V1) | Gnosis (V1) | Arbitrum (V2) | Total |
|--------|---------------|-------------|---------------|-------|
| Total Disputes | 1,675 | 792 | 133 | **2,600** |
| Last 30d | — | 38 | 11 | +49 |
| Status | dormant (last case Feb 2026) | active | growing | — |

## Related Resources

- [Kleros Documentation](https://docs.kleros.io/)
- [Klerosboard](https://klerosboard.com/) - Official community dashboard
- [Kleros GitHub](https://github.com/kleros)
- [The Graph Explorer](https://thegraph.com/explorer)

## License

MIT
