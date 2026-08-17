# EIA STEO Analysis

Pulling and analyzing the U.S. Energy Information Administration's Short-Term Energy Outlook via the EIA API. This project focuses on crude oil production and supply projections from the Permian and Eagle Ford basins, the two major Texas shale plays.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install requests pandas python-dotenv matplotlib
```

Create a `.env` file:
```
EIA_TOKEN=your_key_here
```

## Usage
```bash
python steo_analysis.py
```

## Project Structure

- `steo_analysis.py` — exploratory script including iterations and documentation
- `eia_steo_pipeline.py` — refactored and reusable pipeline version of the same analysis, organized into discrete functions (extract, clean, reshape, compute metrics, compute correlation, generate graph, and export results)

## Findings
![Crude production volume chart](images/volGraph.png)

## Output

Cleaned data exports available in [`output/`](output/):
- `texas_production_and_share.csv` — yearly production, growth rates, and % share of US total
- `texas_production_price_correlation.csv` — production merged with lagged crude price data

## Data Sources
[EIA Short-Term Energy Outlook](https://www.eia.gov/outlooks/steo/) —
monthly-updated 18-month-ahead forecasts covering production,
consumption, imports, and inventories across US energy categories.
