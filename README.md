# 🪙 CryptoPulse — Automated Crypto Market Tracker & Alert System

CryptoPulse is a Python automation pipeline that **fetches** live cryptocurrency
prices, **stores** them in a database, **analyzes** trends, **visualizes** them in
an interactive dashboard, and **alerts** you by email — all on an automatic
schedule, completely unattended.

> This project is a hands-on tour of real-world Python automation: API
> consumption, databases, data analysis, visualization, notifications, and
> scheduling — the exact pattern behind countless automation jobs.

## ✨ Features

- 🔄 **Automated data collection** from the free CoinGecko API (no key required)
- 🗄️ **Historical storage** in SQLite so trends build up over time
- 📊 **Analysis** with pandas (price changes, moving averages, top movers)
- 📈 **Interactive HTML dashboard** with live charts
- 📧 **Email alerts** when a coin crosses a price threshold
- ⏰ **Scheduling** to run hands-free
- 🔐 **Secret-safe**: all credentials live in a git-ignored `.env`

## 🚀 Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create your config from the template
cp .env.example .env        # then edit .env with your settings

# 3. Run a single collection + dashboard cycle
python -m cryptopulse run-once

# 4. Or run it continuously on a schedule (every 10 min by default)
python -m cryptopulse run --interval 10

# 5. Check what's been collected so far
python -m cryptopulse status
```

## 🧱 Project structure

```
cryptopulse/
├── __init__.py
├── __main__.py        # CLI entry point + scheduler (run-once / run / status)
├── config.py          # loads settings & secrets from .env
├── logging_setup.py   # console + rotating-file logging
├── api_client.py      # fetches live prices from the CoinGecko API
├── storage.py         # saves & queries price history in SQLite
├── analysis.py        # trend, moving-average & top-mover analysis (pandas)
├── dashboard.py       # builds an interactive HTML dashboard (Plotly)
├── alerts.py          # evaluates price rules & sends email alerts (SMTP)
└── pipeline.py        # orchestrates one full fetch→store→analyze→alert cycle
```

Try the API client on its own (live data, no setup required):

```bash
python -m cryptopulse.api_client
```

Fetch live prices and store a snapshot (run it twice to watch history grow):

```bash
python -m cryptopulse.storage
```

Analyze the stored history (trends, moving averages, top movers):

```bash
python -m cryptopulse.analysis
```

Build the interactive dashboard (writes `reports/dashboard.html`):

```bash
python -m cryptopulse.dashboard
```

Test the alert rule engine with safe demo data (no email sent):

```bash
python -m cryptopulse.alerts
```

## 🛣️ Build roadmap

- [x] **Step 1** — Project foundation (structure, config, logging, tooling)
- [x] **Step 2** — CoinGecko API client
- [x] **Step 3** — SQLite storage layer
- [x] **Step 4** — Market analysis with pandas
- [x] **Step 5** — Interactive dashboard
- [x] **Step 6** — Email alerts
- [x] **Step 7** — Scheduler & CLI
- [ ] Step 8 — Docs & demo assets

## 📝 License

MIT
