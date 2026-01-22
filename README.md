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

The dashboard aggregates data from multiple public GraphQL endpoints:

| Chain | Endpoint | Auth |
|-------|----------|------|
| Ethereum | `api.studio.thegraph.com/query/66145/klerosboard-mainnet/version/latest` | None |
| Gnosis | `api.studio.thegraph.com/query/66145/klerosboard-gnosis/version/latest` | None |
| Arbitrum V2 | `api.goldsky.com/.../kleros-v2-coreneo/v0.17.2/gn` | None |

All endpoints are publicly accessible and require no authentication.

## Project Structure

```
artisanal-dashboard/
├── index.html                    # Single-page dashboard application
├── klerosboard-data-guide.md     # Comprehensive data extraction guide
├── README.md                     # This file
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

### Quick Start: Fetching All Disputes

```javascript
const ENDPOINTS = {
  mainnet: "https://api.studio.thegraph.com/query/66145/klerosboard-mainnet/version/latest",
  gnosis: "https://api.studio.thegraph.com/query/66145/klerosboard-gnosis/version/latest",
  v2: "https://api.goldsky.com/api/public/project_cmgx9all3003atlp2bqha1zif/subgraphs/kleros-v2-coreneo/v0.17.2/gn"
};

async function fetchDisputes(endpoint) {
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: `{
        disputes(first: 1000, orderBy: id, orderDirection: desc) {
          id
          subcourtID { id }
          period
          startTime
          ruled
        }
      }`
    })
  });
  return (await response.json()).data.disputes;
}
```

## Statistics (January 2026)

| Metric | V1 (ETH+Gnosis) | V2 (Arbitrum) | Total |
|--------|-----------------|---------------|-------|
| Total Disputes | 2,375 | 118 | **2,493** |
| Active Courts | 44 | 5 | 49 |
| Chain Activity | Gnosis 94% | - | - |

## Related Resources

- [Kleros Documentation](https://docs.kleros.io/)
- [Klerosboard](https://klerosboard.com/) - Official community dashboard
- [Kleros GitHub](https://github.com/kleros)
- [The Graph Explorer](https://thegraph.com/explorer)

## License

MIT
