# Startup Comparable Company Screener

Screens and ranks growth-stage startups on financial and operating metrics. Built for VC analysts evaluating deal flow or strategy teams benchmarking against competitors.

## What it does

- Calculates derived metrics: runway, revenue multiples, burn multiples, magic number, efficiency score
- Ranks companies on a weighted composite score (growth, margins, retention, efficiency, runway, payback)
- Benchmarks by sector and funding stage
- Flags outliers — fastest growing, most efficient, highest retention, fastest payback

## Quick start

```bash
pip install -r requirements.txt
python comp_screener.py
```

## Scoring methodology

The composite score uses percentile ranks with weights that reflect a growth-stage VC evaluation:

| Factor | Weight | Why |
|--------|--------|-----|
| Revenue growth | 25% | Top-line momentum is the primary signal |
| Net revenue retention | 20% | Existing customer expansion = durable growth |
| Efficiency score | 20% | Revenue × margin / burn — are they building efficiently? |
| Gross margin | 15% | Unit economics sustainability |
| Runway | 10% | Survival buffer |
| Payback period | 10% | How fast they recoup CAC (inverted — lower is better) |

## Data

Sample dataset in `/data/companies.csv` includes 15 notable growth-stage companies across AI, fintech, devtools, cybersecurity, and defense tech. Metrics are approximate and based on publicly reported figures as of early 2025.

## Tech

- **Python** — pandas for derived metrics and scoring
- **SQL** (SQLite) — sector and stage benchmarking queries

## Other projects

- [b2b-pipeline-analyzer](https://github.com/anecdotal-trout/b2b-pipeline-analyzer) — Marketing spend → pipeline ROI
- [influencer-marketing-report](https://github.com/anecdotal-trout/influencer-marketing-report) — Influencer campaign analysis
- [saas-growth-dashboard](https://github.com/anecdotal-trout/saas-growth-dashboard) — SaaS growth metrics tracker
