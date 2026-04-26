# Klerosboard Data Extraction Guide

A comprehensive guide to extracting data from Klerosboard, including API endpoints, GraphQL queries, and scraping strategies.

## Table of Contents

1. [Overview](#overview)
2. [Data Sources](#data-sources)
3. [GraphQL/Subgraph APIs](#graphqlsubgraph-apis)
4. [Built-in Export Features](#built-in-export-features)
5. [IPFS & Evidence Data](#ipfs--evidence-data)
6. [URL Structure](#url-structure)
7. [Data Models](#data-models)
8. [Scraping Strategy](#scraping-strategy)
9. [Example Queries](#example-queries)

---

## Overview

Klerosboard is a community-built analytics dashboard for Kleros, the decentralized arbitration protocol. It provides data visualization and statistics for:

- **Disputes/Cases**: All arbitration cases with voting history
- **Courts**: Court structure, stakes, and parameters
- **Jurors**: Juror statistics, stakes, and rewards
- **Arbitrables**: Contracts using Kleros arbitration

**Supported Chains:**
- Ethereum Mainnet (Chain ID: 1)
- Gnosis Chain (Chain ID: 100)

**GitHub Repository:** https://github.com/klerosboard/klerosboard

---

## Data Sources

### Primary Data Sources

| Source | Type | Description |
|--------|------|-------------|
| The Graph Subgraphs | GraphQL API | Main data source for on-chain data |
| Kleros Stats API | REST API | Additional statistics |
| IPFS (cdn.kleros.link) | File Storage | Evidence, policies, and metadata |
| RPC Endpoints | JSON-RPC | Direct blockchain queries |

### Endpoints Summary

```
# The Graph - Ethereum Mainnet (PUBLIC - no auth required)
https://api.studio.thegraph.com/query/66145/klerosboard-mainnet/version/latest

# The Graph - Gnosis Chain (PUBLIC - no auth required) ⭐ RECOMMENDED
https://api.studio.thegraph.com/query/66145/klerosboard-gnosis/version/latest

# The Graph - Gnosis Chain (Gateway - requires auth token)
https://gateway.thegraph.com/api/subgraphs/id/Ck26N16xgimEuuuNSJqYVWBKcWSwPmkk36BWZGtfx1ox

# Curate Subgraphs (for registry data)
https://api.studio.thegraph.com/query/61738/legacy-curate-xdai/version/latest
https://api.studio.thegraph.com/query/61738/legacy-curate-mainnet/version/latest

# Kleros Stats API
https://kleros-stats.onrender.com/

# IPFS Gateway
https://cdn.kleros.link

# RPC Endpoints
Gnosis: https://rpc.gnosischain.com/
Mainnet: https://eth.llamarpc.com/
```

### Quick Reference: Which Endpoint to Use

| Chain | Endpoint | Auth Required | Notes |
|-------|----------|---------------|-------|
| Ethereum | Studio API | No | Recommended for mainnet data |
| Gnosis | Studio API | No | ⭐ Recommended for Gnosis data |
| Gnosis | Gateway | Yes (Bearer token) | Alternative, requires API key |

---

## GraphQL/Subgraph APIs

### Authentication

**Good news: Both chains have public endpoints that require NO authentication!**

| Endpoint | Authentication |
|----------|----------------|
| Mainnet Studio API | None required ✅ |
| Gnosis Studio API | None required ✅ |
| Gnosis Gateway API | Requires Bearer token |

For the Gnosis Gateway endpoint (if needed), use:
```
Authorization: Bearer <GRAPHQL_TOKEN>
```

**Recommendation:** Use the Studio API endpoints for both chains - they're publicly accessible and don't require any API keys.

### Available Entities

#### KlerosCounter (Global Statistics)
```graphql
{
  klerosCounters {
    id
    courtsCount
    disputesCount
    openDisputes
    closedDisputes
    evidencePhaseDisputes
    commitPhaseDisputes
    votingPhaseDisputes
    appealPhaseDisputes
    activeJurors
    inactiveJurors
    drawnJurors
    numberOfArbitrables
    tokenStaked
    totalETHFees
    totalTokenRedistributed
    totalUSDthroughContract
  }
}
```

#### Disputes
```graphql
{
  disputes(first: 100, orderBy: id, orderDirection: desc) {
    id
    subcourtID {
      id
      policy { policy }
      timePeriods
      hiddenVotes
    }
    arbitrable { id }
    creator { id }
    currentRulling
    period
    lastPeriodChange
    startTime
    ruled
    txid
    rounds {
      votes(first: 1000) {
        id
        address { id }
        choice
        voted
        commit
        timestamp
      }
    }
  }
}
```

#### Courts
```graphql
{
  courts(first: 100) {
    id
    subcourtID
    disputesOngoing
    disputesClosed
    disputesAppealed
    disputesNum
    evidencePhaseDisputes
    commitPhaseDisputes
    votingPhaseDisputes
    appealPhaseDisputes
    childs { id }
    parent { id }
    policy { policy }
    tokenStaked
    activeJurors
    hiddenVotes
    minStake
    alpha
    feeForJuror
    jurorsForCourtJump
    timePeriods
    totalETHFees
    totalTokenRedistributed
    coherency
    appealPercentage
  }
}
```

#### Jurors
```graphql
{
  jurors(first: 100, orderBy: totalStaked, orderDirection: desc) {
    id
    totalStaked
    numberOfDisputesAsJuror
    numberOfDisputesCreated
    ethRewards
    tokenRewards
    coherency
    numberOfCoherentVotes
    numberOfVotes
    totalGasCost
  }
}
```

#### Votes
```graphql
{
  votes(first: 1000, where: { dispute: "123" }) {
    id
    dispute {
      id
      currentRulling
      period
      subcourtID { id }
      arbitrable { id }
    }
    round { id }
    voteID
    address { id }
    choice
    voted
    salt
    timestamp
    commit
    commitGasUsed
    commitGasPrice
    commitGasCost
    castGasUsed
    castGasPrice
    castGasCost
    totalGasCost
  }
}
```

#### Arbitrables
```graphql
{
  arbitrables(first: 100) {
    id
    disputesCount
    openDisputes
    closedDisputes
    evidencePhaseDisputes
    commitPhaseDisputes
    votingPhaseDisputes
    appealPhaseDisputes
    ethFees
  }
}
```

#### Stakes
```graphql
{
  stakeSets(first: 100, orderBy: timestamp, orderDirection: desc) {
    id
    address { id }
    subcourtID
    stake
    newTotalStake
    timestamp
    gasCost
  }
}
```

---

## Built-in Export Features

Klerosboard has built-in CSV export for several pages:

### CSV Downloads Available

| Page | URL | Data Included |
|------|-----|---------------|
| Cases | `/[chainId]/cases` | Case #, Court, Ruling, Period, Last Period Change |
| Courts | `/[chainId]/courts` | Court ID, Name, Stakes, Jurors, Fees, Disputes |

### JSON Downloads

Individual case pages have a "Download JSON file" button that exports:
- Case metadata
- All rounds and votes
- Timeline information

**URL Pattern:** `https://klerosboard.com/[chainId]/cases/[caseId]`

---

## IPFS & Evidence Data

### Evidence Gateway

All evidence and policy files are stored on IPFS and accessible via:
```
https://cdn.kleros.link/ipfs/[hash]
```

### Fetching Evidence

Evidence is retrieved using the Archon library. The process:

1. Get dispute from KlerosLiquid contract
2. Fetch MetaEvidence using arbitrable contract
3. Retrieve evidence files from IPFS

**KlerosLiquid Contracts:**
- Mainnet: `0x988b3A538b618C7A603e1c11Ab82Cd16dbE28069`
- Gnosis: `0x9C1dA9A04925bDfDedf0f6421bC7EEa8305F9002`

### Court Policies

Court policies are stored as JSON on IPFS. Get the policy path from the subgraph:
```graphql
{
  court(id: "0") {
    policy { policy }
  }
}
```

Then fetch: `https://cdn.kleros.link[policy_path]`

---

## URL Structure

### Klerosboard URLs

```
# Dashboard
https://klerosboard.com/[chainId]

# Cases List
https://klerosboard.com/[chainId]/cases

# Individual Case
https://klerosboard.com/[chainId]/cases/[caseId]

# Courts List
https://klerosboard.com/[chainId]/courts

# Individual Court
https://klerosboard.com/[chainId]/courts/[courtId]

# Charts
https://klerosboard.com/[chainId]/charts

# Aggregated Charts (both chains)
https://klerosboard.com/charts

# Juror Profile
https://klerosboard.com/[chainId]/profile/[address]

# Arbitrable Details
https://klerosboard.com/[chainId]/arbitrable/[address]
```

**Chain IDs:**
- `1` = Ethereum Mainnet
- `100` = Gnosis Chain

---

## Data Models

### Dispute Periods

| Period | Value | Description |
|--------|-------|-------------|
| evidence | 0 | Evidence submission |
| commit | 1 | Vote commitment (hidden votes) |
| vote | 2 | Vote casting |
| appeal | 3 | Appeal period |
| execution | 4 | Final execution |

### Vote Choices

| Choice | Meaning |
|--------|---------|
| 0 | Refuse to Arbitrate |
| 1+ | Corresponds to ruling options (usually Yes/No) |

---

## Scraping Strategy

### Recommended Approach

1. **Use GraphQL APIs** (Primary)
   - Most efficient for bulk data
   - Supports pagination with `first` and `skip`
   - Real-time data

2. **Use Built-in CSV Exports** (Quick exports)
   - Good for one-time downloads
   - Limited to visible columns

3. **Browser Automation** (Last resort)
   - For data not in APIs
   - Use for evidence that requires JS rendering

### GraphQL Pagination Example

```javascript
// Endpoints - both are PUBLIC and require no authentication
const ENDPOINTS = {
  mainnet: "https://api.studio.thegraph.com/query/66145/klerosboard-mainnet/version/latest",
  gnosis: "https://api.studio.thegraph.com/query/66145/klerosboard-gnosis/version/latest"
};

async function getAllDisputes(chainId) {
  const endpoint = chainId === "100" || chainId === 100
    ? ENDPOINTS.gnosis
    : ENDPOINTS.mainnet;

  let allDisputes = [];
  let skip = 0;
  const first = 1000;

  while (true) {
    const query = `{
      disputes(first: ${first}, skip: ${skip}, orderBy: id) {
        id
        subcourtID { id }
        currentRulling
        period
        startTime
        lastPeriodChange
        ruled
      }
    }`;

    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query })
    });

    const data = await response.json();
    const disputes = data.data.disputes;

    if (disputes.length === 0) break;

    allDisputes = allDisputes.concat(disputes);
    skip += first;

    if (disputes.length < first) break;
  }

  return allDisputes;
}

// Fetch from both chains
async function getAllDisputesBothChains() {
  const [mainnetDisputes, gnosisDisputes] = await Promise.all([
    getAllDisputes(1),
    getAllDisputes(100)
  ]);

  return {
    mainnet: mainnetDisputes,
    gnosis: gnosisDisputes,
    total: mainnetDisputes.length + gnosisDisputes.length
  };
}
```

### Fetching Evidence for a Case

```javascript
async function getEvidence(chainId, disputeId, arbitrableAddress) {
  const Archon = require('@kleros/archon');
  const archon = new Archon(
    chainId === "100" ? "https://rpc.gnosischain.com/" : "https://eth.llamarpc.com/",
    "https://cdn.kleros.link"
  );

  const KL = chainId === "100"
    ? "0x9C1dA9A04925bDfDedf0f6421bC7EEa8305F9002"
    : "0x988b3A538b618C7A603e1c11Ab82Cd16dbE28069";

  const dispute = await archon.arbitrable.getDispute(arbitrableAddress, KL, disputeId);
  const metaEvidence = await archon.arbitrable.getMetaEvidence(
    arbitrableAddress,
    dispute.metaEvidenceID
  );

  return metaEvidence;
}
```

---

## Example Queries

### Get All Cases with Court Names (Gnosis)

```graphql
query GetAllCases {
  disputes(first: 1000, orderBy: startTime, orderDirection: desc) {
    id
    subcourtID {
      id
      policy { policy }
    }
    arbitrable { id }
    creator { id }
    currentRulling
    period
    startTime
    lastPeriodChange
    ruled
  }
}
```

### Get Court Statistics

```graphql
query GetCourtStats {
  courts {
    id
    subcourtID
    disputesNum
    disputesOngoing
    disputesClosed
    activeJurors
    tokenStaked
    feeForJuror
    minStake
  }
}
```

### Get Detailed Court Information (with hierarchy)

```graphql
query GetDetailedCourtInfo {
  courts(first: 100, orderBy: disputesNum, orderDirection: desc) {
    id
    subcourtID
    disputesNum
    disputesOngoing
    disputesClosed
    disputesAppealed
    activeJurors
    tokenStaked
    minStake
    feeForJuror
    hiddenVotes
    alpha
    jurorsForCourtJump
    timePeriods
    totalETHFees
    totalTokenRedistributed
    policy {
      policy
    }
    parent {
      id
    }
    childs {
      id
    }
  }
}
```

### Get Specific Court by ID

```graphql
query GetCourtById($courtId: ID!) {
  court(id: $courtId) {
    id
    subcourtID
    disputesNum
    disputesOngoing
    disputesClosed
    disputesAppealed
    activeJurors
    tokenStaked
    minStake
    feeForJuror
    hiddenVotes
    alpha
    timePeriods
    policy {
      policy
    }
    parent {
      id
    }
    childs {
      id
    }
  }
}
```

### Get Court Policy from IPFS

After getting the policy path from the court, fetch the full policy details:

```javascript
async function getCourtPolicy(policyPath) {
  const response = await fetch("https://cdn.kleros.link" + policyPath);
  const policy = await response.json();
  return {
    name: policy.name,
    description: policy.description,
    summary: policy.summary,
    requiredSkills: policy.requiredSkills
  };
}

// Example: Get policy for Gnosis General Court
const policy = await getCourtPolicy("/ipfs/QmTsPLwhozEqjWnYKsnamZiJW47LFT7LzkQhKw5ygQxqyH/xDai-General-Court-Policy.json");
```

### Get Juror Voting History

```graphql
query GetJurorVotes($jurorAddress: String!) {
  votes(where: { address: $jurorAddress }, first: 1000) {
    id
    dispute { id }
    choice
    voted
    timestamp
  }
}
```

### Get Recent Stakes

```graphql
query GetRecentStakes {
  stakeSets(first: 100, orderBy: timestamp, orderDirection: desc) {
    id
    address { id }
    subcourtID
    stake
    newTotalStake
    timestamp
  }
}
```

### Get Arbitrables (Applications Using Kleros)

```graphql
query GetArbitrables {
  arbitrables(first: 50, orderBy: disputesCount, orderDirection: desc) {
    id
    disputesCount
    openDisputes
    closedDisputes
    ethFees
  }
}
```

### Get Recent Disputes with Arbitrable Info

```graphql
query GetRecentDisputes {
  disputes(first: 50, orderBy: startTime, orderDirection: desc) {
    id
    subcourtID { id }
    arbitrable { id }
    startTime
    lastPeriodChange
    period
    currentRulling
    ruled
  }
}
```

---

## Arbitrable Reference (Applications Using Kleros)

### Known Arbitrable Contracts

| Application | Chain | Contract | Disputes | Description |
|-------------|-------|----------|----------|-------------|
| Proof of Humanity | Mainnet | 0xC5E9...7b19 | 1,023 | Sybil-resistant identity verification |
| Tokens Registry (TCR) | Mainnet | 0xeBcd...3E96 | 304 | Curated token listings |
| Linguo | Mainnet | Various | 168+ | Translation work escrows |
| Curate | Gnosis | 0x99a3...8d97 | 515+ | Generic curated registries |
| Reality.eth | Both | Various | 9+ | Oracle dispute resolution |
| Omen | Gnosis | 0xA3Bf...d9e0 | 67 | Prediction market disputes |
| Tags Registry | Mainnet | 0xCa8c...E612 | 4 | Contract metadata tags |

### Fetching Arbitrable Details

The arbitrable contract address can be used to:
1. Look up the application name in the known contracts list above
2. Query the contract on-chain for its name/metadata
3. Fetch MetaEvidence from IPFS via Archon

```javascript
// Example: Get all disputes from a specific arbitrable
const query = `{
  disputes(
    where: { arbitrable: "0x99a3...8d97" }
    orderBy: startTime
    orderDirection: desc
  ) {
    id
    startTime
    period
    currentRulling
  }
}`;
```

---

## Additional Resources

- **Kleros Documentation:** https://docs.kleros.io/
- **Kleros GitHub:** https://github.com/kleros
- **Archon Library:** https://github.com/kleros/archon
- **The Graph Explorer:** https://thegraph.com/explorer

---

## Notes

- **Both Mainnet and Gnosis Studio APIs are publicly accessible** (no authentication required)
- The Gnosis Gateway subgraph requires authentication, but the Studio API is recommended instead
- Evidence data requires the Archon library or direct IPFS access
- Court policies are JSON files on IPFS containing name, description, and rules
- Some arbitrables are whitelisted in the codebase for special handling

---

## Chain Statistics (as of April 2026)

| Metric | Ethereum Mainnet | Gnosis Chain | Total |
|--------|------------------|--------------|-------|
| Total Disputes | 1,675 | 792 | 2,467 |
| Active Courts | 25 | 19 | 44 |
| Peak Year | 2021 (531 cases) | 2025 (~345 cases) | - |

**Use-case eras:** The Kleros caseload has gone through three functional phases, each dominated by a different class of dispute:

1. **Identity era (Mainnet, 2021)** — Proof of Humanity v1 accounts for 1,012 of 1,675 mainnet disputes (60%). The 2021 PoH launch drove Kleros's largest single dispute spike (531 cases that year).
2. **Curation era (Gnosis, 2023–present)** — the Curation Court alone handles 613 of 792 Gnosis disputes (77%). Curate lists back Omen, Seer, Reality.eth and the token registry; the court rarely falls below 20 disputes/month.
3. **Consumer arbitration era (Arbitrum V2, 2025–present)** — the Consumer Disputes Court ("Corte de Disputas de Consumo y Vecindad") is 80 of 133 V2 cases (60%), driven by Lemon (fintech) and Argentine municipal ombudsmen. Court 32 "Defensores del Cliente" went from 4 → 15 disputes in April 2026 alone.

Mainnet V1 is effectively frozen (last dispute ID 1674 on 2026-02-12). New dispute flow is split between Gnosis V1 (curation) and Arbitrum V2 (consumer) — two distinct product lines, not one "migrating" user base.

---

## Court Reference

### Gnosis Chain Courts (19 total)

| ID | Court Name | Disputes | Jurors | Parent | Hidden Votes |
|----|-----------|----------|--------|--------|--------------|
| 0 | General Court | 66 | 97 | - | ✅ |
| 1 | Curation Court | 515 | 47 | 0 | ❌ |
| 2 | English Language | 0 | 7 | 0 | ❌ |
| 3 | Spanish-English Translation | 8 | 2 | 2 | ❌ |
| 4 | French-English Translation | 3 | 2 | 2 | ❌ |
| 11 | Chinese-English Translation | 10 | 1 | 2 | ❌ |
| 12 | Development Court | 1 | 11 | 0 | ❌ |
| 13 | Solidity Court | 3 | 2 | 12 | ❌ |
| 14 | JavaScript Court | 13 | 6 | 12 | ❌ |
| 15 | Spanish General Court | 0 | 25 | 0 | ✅ |
| 17 | Blockchain Non-Technical (ES) | 73 | 22 | 15 | ❌ |
| 18 | Oracle Court | 9 | 2 | 0 | ❌ |

**Top Gnosis Courts by Activity:**
1. Curation Court (515 disputes) - Token registry challenges
2. Blockchain Non-Technical ES (73 disputes) - Spanish community
3. General Court (66 disputes) - Appeals and complex cases

### Ethereum Mainnet Courts (25 total)

| ID | Court Name | Disputes | Jurors | Parent | Hidden Votes |
|----|-----------|----------|--------|--------|--------------|
| 0 | General Court | 56 | 714 | - | ❌ |
| 2 | Non-Technical Court | 363 | 40 | 1 | ❌ |
| 3 | Token Listing Court | 15 | 5 | 2 | ❌ |
| 4 | Technical Court | 30 | 13 | 1 | ❌ |
| 8 | French-English Translation | 63 | 231 | 0 | ❌ |
| 9 | Portuguese-English Translation | 105 | 31 | 0 | ❌ |
| 22 | Kleros Scout | 0 | 33 | 0 | ✅ |
| 23 | Humanity Court | 1023 | 114 | 0 | ❌ |
| 24 | Tags Registry | 4 | 11 | 0 | ❌ |

**Top Mainnet Courts by Activity:**
1. Humanity Court (1023 disputes) - Proof of Humanity challenges
2. Non-Technical Court (363 disputes) - General disputes
3. Portuguese-English Translation (105 disputes) - Translation work

### Court Parameter Definitions

| Parameter | Description |
|-----------|-------------|
| `subcourtID` | Numeric identifier for the court |
| `disputesNum` | Total number of disputes ever handled |
| `activeJurors` | Number of jurors currently staked |
| `tokenStaked` | Total PNK tokens staked in this court |
| `minStake` | Minimum PNK required to be a juror |
| `feeForJuror` | Fee paid to each juror per vote (in wei) |
| `hiddenVotes` | Whether votes use commit-reveal scheme |
| `alpha` | Coherence reward multiplier (basis points) |
| `jurorsForCourtJump` | Jurors needed to appeal to parent court |
| `timePeriods` | Array of [evidence, commit, vote, appeal] durations in seconds |

### Fetching Court Names from Policy Files

Court names are stored in IPFS policy files. Example paths:

```
# Gnosis Chain
/ipfs/QmTsPLwhozEqjWnYKsnamZiJW47LFT7LzkQhKw5ygQxqyH/xDai-General-Court-Policy.json
/ipfs/QmWQDgtUWALrnCgakAAoFWdX1P7iDGmr5imZLZzyYtPqcE/xDai-Curation-Court-Policy.json
/ipfs/QmPLD9Zj8aZj5sVH9WcsHXbARR3RfRnEwHRrVeDM8AbPLt/xDai-English-Language-Court-Policy.json

# Access via
https://cdn.kleros.link/ipfs/[hash]/[filename].json
```

---

## Verified Applications Data & Scraping Methodology

This section documents the verified arbitrable contracts (applications) and the methodology used to scrape and validate dispute data.

### Data Verification Process

The following steps were used to verify dispute counts and application data:

1. **Query all disputes from both chains** via The Graph subgraph endpoints
2. **Extract unique arbitrable addresses** from dispute records
3. **Calculate time-based activity** using the `startTime` field (Unix timestamp)
4. **Cross-reference with known applications** to identify each arbitrable

### GraphQL Queries for Time-Based Analysis

```graphql
# Get disputes with time filtering (Gnosis example)
query GetRecentDisputes($since: BigInt!) {
  disputes(
    first: 1000
    where: { startTime_gte: $since }
    orderBy: startTime
    orderDirection: desc
  ) {
    id
    arbitrable { id }
    startTime
    subcourtID { id }
    period
  }
}
```

**Time calculation for filtering:**
```javascript
const now = Math.floor(Date.now() / 1000); // Current Unix timestamp
const last30d = now - (30 * 24 * 60 * 60);  // 30 days ago
const last90d = now - (90 * 24 * 60 * 60);  // 90 days ago
const lastYear = now - (365 * 24 * 60 * 60); // 1 year ago
```

### Verified Arbitrable Contracts (January 2026)

#### Ethereum Mainnet (1,672 total disputes)

| Application | Contract Address | All-Time | Last 30d | Last 90d | Last Year |
|-------------|------------------|----------|----------|----------|-----------|
| Proof of Humanity v1 | 0xc5e9ddeb... | 1,012 | 0 | 0 | 0 |
| Tokens Registry (TCR) | 0xebcf3bca... | 304 | 0 | 0 | 0 |
| Linguo | 0x99a0f0e0... | 39 | 0 | 0 | 0 |
| Escrow | 0xe0e1bc8c... | 21 | 0 | 0 | 0 |
| Proof of Humanity v2 | 0xbe983409... | 11 | 1 | 3 | 8 |
| Tags Registry | 0x... | 4 | 0 | 1 | 4 |
| *Other/Legacy* | Various | ~281 | 0 | 0 | 0 |

#### Gnosis Chain (703 total disputes)

| Application | Contract Address | All-Time | Last 30d | Last 90d | Last Year |
|-------------|------------------|----------|----------|----------|-----------|
| Curate Registry v1 | 0xee1502e2... | 187 | 2 | 5 | 97 |
| Curate Lists v2 | 0x66260c69... | 135 | 2 | 25 | 73 |
| Omen Markets | 0xc7add3c9... | 85 | 0 | 0 | 5 |
| Reality.eth | 0x957a53a9... | 83 | 0 | 1 | 5 |
| Seer Markets | 0x5aaf9e23... | 67 | 5 | 18 | 60 |
| Legacy Curate | 0x76944a26... | 34 | 0 | 0 | 0 |
| Misc Arbitrables | Various | ~112 | 2 | 2 | 7 |

### Complete Scraping Script

```javascript
// Full script to scrape and verify all Kleros dispute data

const ENDPOINTS = {
  mainnet: "https://api.studio.thegraph.com/query/66145/klerosboard-mainnet/version/latest",
  gnosis: "https://api.studio.thegraph.com/query/66145/klerosboard-gnosis/version/latest"
};

async function fetchAllDisputes(chain) {
  const endpoint = ENDPOINTS[chain];
  let allDisputes = [];
  let skip = 0;
  const first = 1000;

  while (true) {
    const query = `{
      disputes(first: ${first}, skip: ${skip}, orderBy: id, orderDirection: asc) {
        id
        arbitrable { id }
        subcourtID { id }
        startTime
        period
        currentRulling
        ruled
      }
    }`;

    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query })
    });

    const data = await response.json();
    const disputes = data.data?.disputes || [];

    if (disputes.length === 0) break;
    allDisputes = allDisputes.concat(disputes);
    skip += first;

    console.log(`${chain}: Fetched ${allDisputes.length} disputes...`);
    if (disputes.length < first) break;
  }

  return allDisputes;
}

function analyzeByArbitrable(disputes) {
  const now = Math.floor(Date.now() / 1000);
  const cutoffs = {
    last30d: now - (30 * 24 * 60 * 60),
    last90d: now - (90 * 24 * 60 * 60),
    lastYear: now - (365 * 24 * 60 * 60)
  };

  const arbitrables = {};

  disputes.forEach(d => {
    const arbId = d.arbitrable?.id?.toLowerCase().slice(0, 10) || 'unknown';
    const startTime = parseInt(d.startTime);

    if (!arbitrables[arbId]) {
      arbitrables[arbId] = {
        allTime: 0,
        last30d: 0,
        last90d: 0,
        lastYear: 0,
        courts: {}
      };
    }

    arbitrables[arbId].allTime++;
    if (startTime >= cutoffs.last30d) arbitrables[arbId].last30d++;
    if (startTime >= cutoffs.last90d) arbitrables[arbId].last90d++;
    if (startTime >= cutoffs.lastYear) arbitrables[arbId].lastYear++;

    const courtId = d.subcourtID?.id || '0';
    arbitrables[arbId].courts[courtId] = (arbitrables[arbId].courts[courtId] || 0) + 1;
  });

  return arbitrables;
}

function analyzeByMonth(disputes, chain) {
  const monthly = {};

  disputes.forEach(d => {
    const startTime = parseInt(d.startTime) * 1000;
    const date = new Date(startTime);
    const month = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
    const courtId = d.subcourtID?.id || '0';

    if (!monthly[month]) monthly[month] = {};
    monthly[month][courtId] = (monthly[month][courtId] || 0) + 1;
  });

  return monthly;
}

// Main execution
async function main() {
  console.log("Fetching data from both chains...\n");

  const [mainnetDisputes, gnosisDisputes] = await Promise.all([
    fetchAllDisputes('mainnet'),
    fetchAllDisputes('gnosis')
  ]);

  console.log(`\n=== SUMMARY ===`);
  console.log(`Mainnet: ${mainnetDisputes.length} disputes`);
  console.log(`Gnosis: ${gnosisDisputes.length} disputes`);
  console.log(`Total: ${mainnetDisputes.length + gnosisDisputes.length}\n`);

  // Analyze by arbitrable
  console.log("=== MAINNET ARBITRABLES ===");
  const mainnetArbs = analyzeByArbitrable(mainnetDisputes);
  Object.entries(mainnetArbs)
    .sort((a, b) => b[1].allTime - a[1].allTime)
    .slice(0, 10)
    .forEach(([id, data]) => {
      console.log(`${id}: ${data.allTime} total | 30d: ${data.last30d} | 90d: ${data.last90d} | 1y: ${data.lastYear}`);
    });

  console.log("\n=== GNOSIS ARBITRABLES ===");
  const gnosisArbs = analyzeByArbitrable(gnosisDisputes);
  Object.entries(gnosisArbs)
    .sort((a, b) => b[1].allTime - a[1].allTime)
    .slice(0, 10)
    .forEach(([id, data]) => {
      console.log(`${id}: ${data.allTime} total | 30d: ${data.last30d} | 90d: ${data.last90d} | 1y: ${data.lastYear}`);
    });

  // Monthly breakdown
  console.log("\n=== MONTHLY DATA BY COURT ===");
  const mainnetMonthly = analyzeByMonth(mainnetDisputes, 'mainnet');
  const gnosisMonthly = analyzeByMonth(gnosisDisputes, 'gnosis');

  return {
    mainnet: {
      disputes: mainnetDisputes,
      arbitrables: mainnetArbs,
      monthly: mainnetMonthly
    },
    gnosis: {
      disputes: gnosisDisputes,
      arbitrables: gnosisArbs,
      monthly: gnosisMonthly
    }
  };
}

main().catch(console.error);
```

### Application Identification

The arbitrable contract addresses can be mapped to known applications:

```javascript
const KNOWN_ARBITRABLES = {
  // Mainnet
  '0xc5e9ddeb': { name: 'Proof of Humanity v1', url: 'https://proofofhumanity.id' },
  '0xebcf3bca': { name: 'Tokens Registry', url: 'https://tokens.kleros.io' },
  '0x99a0f0e0': { name: 'Linguo', url: 'https://linguo.kleros.io' },
  '0xe0e1bc8c': { name: 'Escrow', url: 'https://escrow.kleros.io' },
  '0xbe983409': { name: 'Proof of Humanity v2', url: 'https://proofofhumanity.id' },

  // Gnosis
  '0xee1502e2': { name: 'Curate Registry v1', url: 'https://curate.kleros.io' },
  '0x66260c69': { name: 'Curate Lists v2', url: 'https://curate.kleros.io' },
  '0xc7add3c9': { name: 'Omen Markets', url: 'https://omen.eth.link' },
  '0x957a53a9': { name: 'Reality.eth', url: 'https://reality.eth.link' },
  '0x5aaf9e23': { name: 'Seer Markets Curate List', url: 'https://seer.pm' },
  '0x76944a26': { name: 'Legacy Curate', url: 'https://curate.kleros.io' }
};
```

### Key Findings

1. **Most active current applications** (last 30 days):
   - Seer Markets Curate List (Gnosis): 5 disputes
   - Curate Registry v1 (Gnosis): 2 disputes
   - Curate Lists v2 (Gnosis): 2 disputes
   - PoH v2 (Mainnet): 1 dispute

2. **Historical dominance:**
   - Proof of Humanity v1 dominated Mainnet (1,012 of 1,672 disputes)
   - Curate Registry dominates Gnosis (187 + 135 = 322 of 703 disputes)

3. **Chain migration:**
   - Mainnet activity has largely ceased (only PoH v2 active)
   - Gnosis is now the primary chain for new disputes
   - Seer Markets is the most active new application

4. **Data freshness:**
   - Subgraph data updates within minutes of on-chain transactions
   - Use `startTime` field for time-based filtering
   - Court ID mapping available via subgraph court entities

---

## Important: Understanding Arbitrable Contracts vs Applications

### Arbitrable ≠ Application Contract

A key insight when analyzing Kleros data: **arbitrable contracts are not always the application's main contracts**. Many applications use Kleros through **Kleros Curate lists** rather than direct integration.

#### Example: Seer Markets

Seer (https://seer.pm) is a prediction marketplace. When you see disputes related to Seer:

- **The arbitrable contract** `0x5aaf9e23a11440f8c1ad6d2e2e5109c7e52cc672` is NOT a Seer contract
- It's a **Kleros Curate list** specifically for verifying Seer markets
- Case descriptions read: "Add a market to Seer Markets: Does the market comply with the required criteria?"

**Seer's actual deployed contracts** (from their documentation):
```
Gnosis Chain:
- GnosisRouter: 0xeC9048b59b3467415b1a38F63416407eA0c70fB8
- Market: 0x8F76bC35F8C72E5e2Ec55ebED785da5efaa9636a
- MarketFactory: 0x83183DA839Ce8228E31Ae41222EaD9EDBb5cDcf1
- RealityProxy: 0xc260ADfAC11f97c001dC143d2a4F45b98e0f2D6C
```

None of these match the arbitrable address - because Seer uses Curate as an intermediary.

### Types of Kleros Integration

1. **Direct Integration** - Application contracts call Kleros directly
   - Example: Proof of Humanity (`0xc5e9ddeb...`) - PoH contract is the arbitrable

2. **Curate-Mediated** - Application uses a Curate list for verification
   - Example: Seer Markets (`0x5aaf9e23...`) - Curate list is the arbitrable
   - Example: Omen Markets - Uses Curate for market verification

3. **Oracle Integration** - Application uses Reality.eth which uses Kleros
   - Example: Many prediction markets use Reality.eth (`0x957a53a9...`)

### Verification Methodology

To identify what application an arbitrable serves:

1. **Query recent disputes** for that arbitrable
2. **Look at case descriptions** on Klerosboard (e.g., `klerosboard.com/100/cases/702`)
3. **Check the MetaEvidence** which describes the dispute type
4. **Cross-reference** with known application documentation

```javascript
// Get case description via subgraph dispute lookup
// Then check klerosboard.com/{chainId}/cases/{disputeId} for full details
async function identifyArbitrable(arbitrableAddress) {
  const response = await fetch(ENDPOINTS.gnosis, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: `{
        disputes(
          first: 5
          where: { arbitrable: "${arbitrableAddress}" }
          orderBy: startTime
          orderDirection: desc
        ) {
          id
          subcourtID { id }
        }
      }`
    })
  });
  const data = await response.json();
  // Then visit klerosboard.com to see case descriptions
  return data.data.disputes.map(d => d.id);
}
```

---

## Full Arbitrable Address Reference

### Gnosis Chain - Complete Verified List

| Address | Disputes | Application | Type | Description |
|---------|----------|-------------|------|-------------|
| `0xee1502e29795ef6c2d60f8d7120596abe3bad990` | 187 | Curate Registry v1 | Generic Curate | General-purpose curation |
| `0x66260c69d03837016d88c9877e61e08ef74c59f2` | 135 | Curate Lists v2 | Generic Curate | Updated curate contracts |
| `0xc7add3c961f7935cb4914e37da991d2f1cd7986c` | 85 | Omen Markets | Curate List | Prediction market verification |
| `0x957a53a994860be4750810131d9c876b2f52d6e1` | 83 | Reality.eth | Oracle | Dispute resolution oracle |
| `0x5aaf9e23a11440f8c1ad6d2e2e5109c7e52cc672` | 67 | Seer Markets | Curate List | Seer market verification |
| `0x76944a2678a0954a610096ee78e8ceb8d46d5922` | 34 | Legacy Curate | Deprecated | Old curate contracts |
| `0xae6aaed5434244be3699c56e7ebc828194f26dc3` | 11 | Misc Integrations | Various | Other arbitrables |
| `0xd5994f15be9987104d9821aa99d1c97227c7c08c` | 10 | Unknown | TBD | Requires investigation |
| `0x70533554fe5c17caf77fe530f77eab933b92af60` | 10 | Unknown | TBD | Requires investigation |
| `0x0b928165a67df8254412483ae8c3b8cc7f2b4d36` | 10 | Unknown | TBD | Requires investigation |

### Ethereum Mainnet - Complete Verified List

| Address | Disputes | Application | Type | Description |
|---------|----------|-------------|------|-------------|
| `0xc5e9dDebb09Cd64DfaCab4011A0D5cEDaf7c9BDb` | 1,012 | Proof of Humanity v1 | Direct | Identity verification |
| `0xebcf3bca271B26ae4B162Ba560e243055Af0E679` | 304 | Tokens Registry | Curate List | Token curation |
| Various | 168+ | Linguo | Direct | Translation escrows |
| `0xe0e1bc8c1c7a5c6b5f5b4e4d8c7c4f1f7b8a9e0d` | 21 | Escrow | Direct | Generic escrow |
| `0xbe9834094b9ad08B0e77Df7d62Ab67Bf02d24CD9` | 11 | Proof of Humanity v2 | Direct | PoH updated version |

---

## Data Gathering Best Practices

### 1. Always Verify Dispute Counts

Don't trust application-provided numbers. Query the subgraph directly:

```javascript
// Get authoritative dispute count for any arbitrable
async function getDisputeCount(chain, arbitrableAddress) {
  const response = await fetch(ENDPOINTS[chain], {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: `{
        arbitrable(id: "${arbitrableAddress.toLowerCase()}") {
          disputesCount
        }
      }`
    })
  });
  const data = await response.json();
  return parseInt(data.data?.arbitrable?.disputesCount || 0);
}
```

### 2. Time-Based Filtering

Always use `startTime` for historical analysis:

```javascript
// Get disputes within a time range
async function getDisputesInRange(chain, startTimestamp, endTimestamp) {
  const response = await fetch(ENDPOINTS[chain], {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: `{
        disputes(
          first: 1000
          where: {
            startTime_gte: "${startTimestamp}"
            startTime_lt: "${endTimestamp}"
          }
          orderBy: startTime
        ) {
          id
          arbitrable { id }
          subcourtID { id }
          startTime
        }
      }`
    })
  });
  return (await response.json()).data.disputes;
}
```

### 3. Handling Pagination

The subgraph limits queries to 1000 results. Always paginate:

```javascript
async function getAllEntities(chain, entityName, fields) {
  let all = [];
  let skip = 0;
  const first = 1000;

  while (true) {
    const query = `{
      ${entityName}(first: ${first}, skip: ${skip}, orderBy: id) {
        ${fields}
      }
    }`;

    const response = await fetch(ENDPOINTS[chain], {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query })
    });

    const data = await response.json();
    const entities = data.data?.[entityName] || [];

    if (entities.length === 0) break;
    all = all.concat(entities);
    skip += first;

    if (entities.length < first) break;
  }

  return all;
}
```

### 4. Identifying Unknown Arbitrables

For arbitrables you can't identify:

1. **Check Gnosisscan/Etherscan** for contract code and verification
2. **Look at transaction history** - function names reveal purpose
3. **Query recent disputes** and check Klerosboard case pages
4. **Search GitHub** for the contract address

```bash
# Quick identification via Gnosisscan
https://gnosisscan.io/address/{ADDRESS}#code

# Klerosboard arbitrable page (may show "Not Found" for some)
https://klerosboard.com/{chainId}/arbitrable/{ADDRESS}
```

### 5. Court to Application Mapping

Most applications use specific courts:

| Court (Gnosis) | Primary Applications |
|----------------|---------------------|
| Court 1 (Curation) | Curate lists, Seer, Omen |
| Court 18 (Oracle) | Reality.eth |
| Court 0 (General) | Appeals, complex cases |

| Court (Mainnet) | Primary Applications |
|-----------------|---------------------|
| Court 23 (Humanity) | Proof of Humanity |
| Court 2 (Non-Technical) | Token Registry, general disputes |

---

## Kleros V2 (Arbitrum) Data Guide

Kleros v2 is the next generation of the Kleros protocol, deployed on **Arbitrum One**. It features improved court mechanics, new dispute resolution features, and operates independently from v1.

### V2 Subgraph Endpoint

The primary Kleros v2 subgraph is hosted on Goldsky:

```
https://api.goldsky.com/api/public/project_cmgx9all3003atlp2bqha1zif/subgraphs/kleros-v2-coreneo/v0.17.2/gn
```

**Alternative endpoints:**
- The Graph Explorer: `https://thegraph.com/explorer/subgraphs/3U95wXKP8fBpkMNn8mbroVkUTuh6KtHGa456pTixx9B2`
- Requires API key for production use

### V2 Key Statistics (April 2026)

| Metric | Value |
|--------|-------|
| Total Cases | 133 |
| Cases Ruled | 131 |
| Active Jurors | 41 |
| Staked PNK | 774,964 PNK (~$8,525) |
| ETH Paid | 3.53 ETH (~$7,244) |
| PNK Redistributed | 189,304 PNK (~$2,082) |
| First Dispute | November 14, 2024 |
| Chain | Arbitrum One |

### V2 Courts with Disputes

| Court ID | Court Name | Disputes | Parent Court |
|----------|------------|----------|--------------|
| 29 | Corte de Disputas de Consumo y Vecindad | 80 | Corte General en Español |
| 31 | Automated Curation | 21 | Curation |
| 3 | Non-Technical | 8 | Blockchain |
| 1 | General Court | 6 | Root |
| 24 | Humanity | 3 | General Court |

### V2 Time-Based Activity

| Period | Disputes |
|--------|----------|
| Last 30 days | 1 |
| Last 90 days | 10 |
| Last Year | 107 |
| All Time | 118 |

### V2 Arbitrable Contracts

Currently, all v2 disputes go through a single arbitrable contract:

| Address | Disputes | Description |
|---------|----------|-------------|
| `0xb5526d022962a1fff6ed32c93e8b714c901f4323` | 118 | Dispute Template Registry |

This is the universal arbitrable for v2 - applications create dispute templates rather than deploying separate arbitrable contracts.

### V2 GraphQL Queries

#### Get All Disputes
```javascript
const V2_ENDPOINT = "https://api.goldsky.com/api/public/project_cmgx9all3003atlp2bqha1zif/subgraphs/kleros-v2-coreneo/v0.17.2/gn";

async function getV2Disputes() {
  const response = await fetch(V2_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: `{
        disputes(first: 1000, orderBy: createdAt, orderDirection: desc) {
          id
          disputeID
          createdAt
          period
          ruled
          currentRuling
          court { id name }
          arbitrated { id }
        }
      }`
    })
  });
  return (await response.json()).data.disputes;
}
```

#### Get Counter Statistics
```javascript
async function getV2Stats() {
  const response = await fetch(V2_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: `{
        counter(id: "0") {
          cases
          casesRuled
          casesVoting
          casesAppealing
          paidETH
          redistributedPNK
          activeJurors
          stakedPNK
        }
      }`
    })
  });
  return (await response.json()).data.counter;
}
```

#### Get Courts
```javascript
async function getV2Courts() {
  const response = await fetch(V2_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: `{
        courts(first: 100, orderBy: numberDisputes, orderDirection: desc) {
          id
          name
          parent { id name }
          numberDisputes
          numberClosedDisputes
          stakedJurors
          stake
          minStake
          feeForJuror
        }
      }`
    })
  });
  return (await response.json()).data.courts;
}
```

#### Time-Based Filtering
```javascript
async function getV2DisputesByTime() {
  const now = Math.floor(Date.now() / 1000);
  const cutoffs = {
    last30d: now - (30 * 24 * 60 * 60),
    last90d: now - (90 * 24 * 60 * 60),
    lastYear: now - (365 * 24 * 60 * 60)
  };

  const response = await fetch(V2_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: `{
        disputes(first: 1000, orderBy: createdAt, orderDirection: asc) {
          id
          createdAt
          court { id name }
        }
      }`
    })
  });

  const disputes = (await response.json()).data.disputes;

  return {
    last30d: disputes.filter(d => parseInt(d.createdAt) >= cutoffs.last30d).length,
    last90d: disputes.filter(d => parseInt(d.createdAt) >= cutoffs.last90d).length,
    lastYear: disputes.filter(d => parseInt(d.createdAt) >= cutoffs.lastYear).length,
    total: disputes.length
  };
}
```

### V2 Schema - Key Entities

| Entity | Description | Key Fields |
|--------|-------------|------------|
| `Dispute` | A case in arbitration | id, disputeID, createdAt, period, court, arbitrated, ruled |
| `Court` | A specialized court | id, name, parent, numberDisputes, stake, feeForJuror |
| `Counter` | Global statistics | cases, casesRuled, paidETH, activeJurors, stakedPNK |
| `Arbitrable` | Contract creating disputes | id, totalDisputes |
| `Round` | Voting round in a dispute | id, dispute, drawnJurors |
| `Draw` | Juror selection | id, round, juror |

### V2 vs V1 Differences

| Feature | V1 (Ethereum/Gnosis) | V2 (Arbitrum) |
|---------|---------------------|---------------|
| Chain | Ethereum Mainnet, Gnosis | Arbitrum One |
| Total Disputes | ~2,375 | 118 |
| Arbitrable Model | Per-application contracts | Universal template registry |
| Primary Use Case | PoH, Curate, Reality.eth | Consumer disputes (Lemon), Curation |
| Subgraph Host | The Graph Studio | Goldsky |
| Timestamp Field | `startTime` | `createdAt` |
| Court Rewards | ETH/xDAI | ETH (Arbitrum) |

### Complete V2 Scraping Script

```javascript
// Full script to scrape Kleros V2 data

const V2_ENDPOINT = "https://api.goldsky.com/api/public/project_cmgx9all3003atlp2bqha1zif/subgraphs/kleros-v2-coreneo/v0.17.2/gn";

async function scrapeKlerosV2() {
  // Get global stats
  const statsResponse = await fetch(V2_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: `{
        counter(id: "0") {
          cases
          casesRuled
          casesVoting
          paidETH
          redistributedPNK
          activeJurors
          stakedPNK
        }
      }`
    })
  });
  const stats = (await statsResponse.json()).data.counter;

  // Get all disputes with timestamps
  const disputesResponse = await fetch(V2_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: `{
        disputes(first: 1000, orderBy: createdAt, orderDirection: asc) {
          id
          createdAt
          period
          ruled
          court { id name }
          arbitrated { id }
        }
      }`
    })
  });
  const disputes = (await disputesResponse.json()).data.disputes;

  // Get courts
  const courtsResponse = await fetch(V2_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: `{
        courts(first: 100) {
          id
          name
          parent { id name }
          numberDisputes
          numberClosedDisputes
          stake
          minStake
          feeForJuror
        }
      }`
    })
  });
  const courts = (await courtsResponse.json()).data.courts;

  // Time-based analysis
  const now = Math.floor(Date.now() / 1000);
  const cutoffs = {
    last30d: now - (30 * 24 * 60 * 60),
    last90d: now - (90 * 24 * 60 * 60),
    lastYear: now - (365 * 24 * 60 * 60)
  };

  const courtStats = {};
  disputes.forEach(d => {
    const courtId = d.court?.id || '0';
    const courtName = d.court?.name || 'Unknown';
    const createdAt = parseInt(d.createdAt);

    if (!courtStats[courtId]) {
      courtStats[courtId] = { name: courtName, allTime: 0, last30d: 0, last90d: 0, lastYear: 0 };
    }
    courtStats[courtId].allTime++;
    if (createdAt >= cutoffs.last30d) courtStats[courtId].last30d++;
    if (createdAt >= cutoffs.last90d) courtStats[courtId].last90d++;
    if (createdAt >= cutoffs.lastYear) courtStats[courtId].lastYear++;
  });

  return {
    stats: {
      totalCases: stats.cases,
      casesRuled: stats.casesRuled,
      activeJurors: stats.activeJurors,
      stakedPNK: (parseInt(stats.stakedPNK) / 1e18).toFixed(0),
      paidETH: (parseInt(stats.paidETH) / 1e18).toFixed(4),
      redistributedPNK: (parseInt(stats.redistributedPNK) / 1e18).toFixed(0)
    },
    disputes: disputes,
    courts: courts.filter(c => parseInt(c.numberDisputes) > 0),
    courtStats: courtStats
  };
}

scrapeKlerosV2().then(console.log).catch(console.error);
```

### V2 Key Findings

1. **Primary Application**: The "Corte de Disputas de Consumo y Vecindad" (Consumer Disputes Court) handles 68% of all v2 cases (80/118), primarily from the Lemon marketplace integration in Argentina.

2. **Spanish Language Courts**: V2 has significant Spanish-language activity, reflecting Kleros's expansion in Latin America.

3. **Automated Curation**: 21 disputes (18%) are from automated curation, likely from Curate v2 integrations.

4. **Low Recent Activity**: Only 1 dispute in the last 30 days, 10 in last 90 days - indicating the beta is still ramping up.

5. **Single Arbitrable Model**: Unlike v1 where each application deploys its own arbitrable contract, v2 uses a universal Dispute Template Registry (`0xb5526d02...`).

---

## Combined Data: Kleros v1 + v2 Summary

### Total Protocol Statistics (April 2026)

| Metric | V1 (ETH+Gnosis) | V2 (Arbitrum) | Total |
|--------|-----------------|---------------|-------|
| Total Disputes | 2,467 | 133 | **2,600** |
| Active Disputes | ~6 | 2 | ~8 |
| Chains | 2 | 1 | 3 |

### All Endpoints Reference

```javascript
const KLEROS_ENDPOINTS = {
  // V1 - Klerosboard Subgraphs
  v1_mainnet: "https://api.studio.thegraph.com/query/66145/klerosboard-mainnet/version/latest",
  v1_gnosis: "https://api.studio.thegraph.com/query/66145/klerosboard-gnosis/version/latest",

  // V2 - Arbitrum (Goldsky)
  v2_arbitrum: "https://api.goldsky.com/api/public/project_cmgx9all3003atlp2bqha1zif/subgraphs/kleros-v2-coreneo/v0.17.2/gn"
};
```

---

## V2 Category Data Retrieval

### Important: Categories Are NOT in the Subgraph

**Critical limitation**: The V2 subgraph does NOT contain dispute category information. Categories (like "Lemon", "Metlife", "Junín", etc.) are:

1. Stored in the **Dispute Template Registry** on-chain
2. Only visible on the **v2.kleros.builders** web interface
3. NOT queryable via GraphQL

This means you must use web scraping to get category breakdowns.

### V2 Category Data Source

**Web Interface**: https://v2.kleros.builders/

The case listing at v2.kleros.builders displays each case with its category badge, which comes from the dispute template metadata.

### Web Scraping Methodology

Since the subgraph doesn't expose category data, you must scrape the web interface:

1. **Navigate to the cases list**: `https://v2.kleros.builders/`
2. **Paginate through all pages**: Cases are displayed 10 per page
3. **Extract case ID and category** from each case card
4. **Compile the complete mapping**

#### Example: Scraping with Browser Automation

```javascript
// Example scraping approach using browser automation or fetch
// Navigate through paginated case list at v2.kleros.builders

async function scrapeV2Categories() {
  const caseCategories = {};
  let page = 1;
  let hasMore = true;

  while (hasMore) {
    // Navigate to page: https://v2.kleros.builders/?page={page}
    // Extract case cards with their category badges
    // Each card shows: Case #{id} | {Category} | {Court}

    // Parse categories from DOM elements
    // Categories appear as text labels on case cards

    page++;
    hasMore = /* check if more pages exist */;
  }

  return caseCategories;
}
```

### V2 Category Reference Tables (Verified January 2026)

The following tables were compiled by manually scraping all 118 V2 cases from v2.kleros.builders:

#### Consumer Disputes Court (Court 29) - 74 Cases

| Category | Count | Description |
|----------|-------|-------------|
| Lemon | 35 | Fintech - e-commerce disputes |
| Junín | 17 | Municipality (Buenos Aires province) |
| Metlife | 14 | Insurance company disputes |
| Mendoza | 2 | Mendoza province (incl. Lavalle) |
| Gov. Entities | 1 | Government entity disputes |
| CABA | 1 | Buenos Aires City |
| El Dorado | 1 | El Dorado municipality |
| Maldo | 1 | Maldo consumer office |
| Insurance | 1 | Generic insurance |
| General | 1 | Uncategorized consumer disputes |

#### Automated Curation Court (Court 31) - 21 Cases

| Category | Count | Description |
|----------|-------|-------------|
| Sports | 13 | Controversial sports calls curation |
| IP | 6 | Image similarity assessment |
| Fake News | 2 | Fact-checking curation |

#### General Court (Court 1) - 6 Cases

| Category | Count | Description |
|----------|-------|-------------|
| General | 3 | Uncategorized general disputes |
| GiftCard | 2 | Gift card disputes |
| Residential lease | 1 | Lease agreement dispute |

#### Humanity Court (Court 24) - 3 Cases

| Category | Count | Description |
|----------|-------|-------------|
| Identity | 3 | Proof of Humanity v2 identity challenges |

#### Non-Technical Court (Court 3) - 8 Cases

| Category | Count | Description |
|----------|-------|-------------|
| Gov. Entities | 7 | Government entity related disputes |
| Unknown | 1 | Unclassified |

### Complete Case-by-Category Reference

Here is the complete verified mapping of V2 cases to their categories (as of January 2026):

#### Consumer Court (Court 29) - Complete List

```
Lemon (35 cases): 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 22, 23, 24, 25, 26, 27, 28, 29, 36, 38, 39, 40, 41, 46, 47, 48, 49

Junín (17 cases): 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 73, 74, 101, 102, 103, 104

Metlife (14 cases): 44, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 77, 78, 79

Mendoza (2 cases): 80, 81

Gov. Entities (1 case): 99

CABA (1 case): 100

El Dorado (1 case): 105

Maldo (1 case): 106

Insurance (1 case): 107

General (1 case): 37
```

#### Automated Curation Court (Court 31) - Complete List

```
Sports (13 cases): 82, 83, 84, 85, 86, 87, 88, 89, 91, 96, 97, 108, 109

IP (6 cases): 90, 92, 93, 94, 95, 98

Fake News (2 cases): 110, 111
```

#### General Court (Court 1) - Complete List

```
General (3 cases): 9, 42, 43

GiftCard (2 cases): 32, 33

Residential lease (1 case): 31
```

#### Humanity Court (Court 24) - Complete List

```
Identity (3 cases): 112, 113, 118
```

#### Non-Technical Court (Court 3) - Complete List

```
Gov. Entities (7 cases): 34, 35, 71, 72, 75, 76, 114

Unknown (1 case): 30
```

### Why Categories Aren't in the Subgraph

V2's architecture uses a **Dispute Template Registry** pattern:

1. **On-chain**: The `DisputeKitClassic` contract stores dispute metadata
2. **Template model**: Instead of each app deploying an arbitrable, they register dispute templates
3. **Category in template**: Categories are part of the template JSON, not indexed separately
4. **Subgraph limitation**: The Goldsky subgraph indexes on-chain events but doesn't parse template JSON content

### Alternative: Direct Contract Query (Advanced)

For programmatic access to categories, you could:

1. **Query the Dispute Template Registry contract** on Arbitrum
2. **Parse the template JSON** for each dispute
3. **Extract the category field** from the template

```solidity
// Contract: 0xb5526d022962a1fff6ed32c93e8b714c901f4323 (Arbitrum)
// Function: getDisputeTemplate(uint256 disputeId)
// Returns JSON with category information
```

However, this requires blockchain RPC calls and JSON parsing, making web scraping simpler for most use cases.

### Recommended Workflow for Category Analysis

1. **Use the subgraph** for dispute counts, timing, and court data
2. **Use web scraping** (v2.kleros.builders) for category breakdowns
3. **Cache the category data** since it changes infrequently
4. **Update periodically** when new cases are created

```javascript
// Hybrid approach: Subgraph + Web scraping
async function getV2DataWithCategories() {
  // Step 1: Get dispute data from subgraph
  const disputes = await fetchV2SubgraphDisputes();

  // Step 2: Scrape categories from web interface
  const categories = await scrapeV2Categories();

  // Step 3: Merge the data
  return disputes.map(d => ({
    ...d,
    category: categories[d.id] || 'Unknown'
  }));
}
```

---

*Document generated from Klerosboard source code analysis and live API data*
*Last updated: April 2026*
