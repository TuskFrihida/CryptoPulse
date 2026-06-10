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

# 3. Run a single collection + dashboard cycle (added in later steps)
python -m cryptopulse run-once
```

## 🧱 Project structure

```
cryptopulse/
├── __init__.py
├── config.py          # loads settings & secrets from .env
└── logging_setup.py   # console + rotating-file logging
```

## 🛣️ Build roadmap

- [x] **Step 1** — Project foundation (structure, config, logging, tooling)
- [ ] Step 2 — CoinGecko API client
- [ ] Step 3 — SQLite storage layer
- [ ] Step 4 — Market analysis with pandas
- [ ] Step 5 — Interactive dashboard
- [ ] Step 6 — Email alerts
- [ ] Step 7 — Scheduler & CLI
- [ ] Step 8 — Docs & demo assets

## 📝 License

MIT
