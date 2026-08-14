# EIA STEO Analysis

Pulling and analyzing the U.S. Energy Information Administration's Short-Term Energy Outlook via the EIA API. This project focuses on crude oil production and supply projections.

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

## Data Sources
[EIA Short-Term Energy Outlook](https://www.eia.gov/outlooks/steo/) —
monthly-updated 18-month-ahead forecasts covering production,
consumption, imports, and inventories across US energy categories.