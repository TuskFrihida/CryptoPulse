# CryptoPulse Architecture

CryptoPulse is built as a **linear pipeline** of small, single-responsibility
modules. Data flows in one direction; each stage hands a clean, typed object to
the next. This is the same shape behind most real-world automation jobs.

## The data flow

```
                ┌─────────────┐
   CoinGecko ──▶│ api_client  │  fetch  → list[PriceRecord]
   (REST API)   └──────┬──────┘
                       ▼
                ┌─────────────┐
                │  storage    │  store  → SQLite (data/cryptopulse.db)
                └──────┬──────┘
                       ▼
                ┌─────────────┐
                │  analysis   │  analyze → list[CoinSummary] (pandas)
                └──────┬──────┘
            ┌──────────┴──────────┐
            ▼                     ▼
     ┌─────────────┐       ┌─────────────┐
     │ dashboard   │       │   alerts    │
     │ (Plotly →   │       │ (rules →    │
     │  HTML file) │       │  SMTP email)│
     └─────────────┘       └─────────────┘

   pipeline.run_cycle() orchestrates all of the above.
   __main__.py (CLI + scheduler) calls run_cycle on demand or on a timer.
```

## Module responsibilities

| Module             | Stage      | Responsibility                                              |
|--------------------|------------|-------------------------------------------------------------|
| `config.py`        | foundation | Load settings/secrets from `.env`; define paths & rules.    |
| `logging_setup.py` | foundation | Console + rotating-file logging for unattended runs.        |
| `api_client.py`    | fetch      | Call CoinGecko with timeout + retries; return `PriceRecord`.|
| `storage.py`       | store      | Persist & query history in SQLite (parameterised SQL).      |
| `analysis.py`      | analyze    | Moving averages, trend, top movers via pandas.              |
| `dashboard.py`     | visualize  | Render an interactive standalone HTML report (Plotly).      |
| `alerts.py`        | act        | Evaluate price rules; send MIME email over SMTP+TLS.        |
| `pipeline.py`      | orchestrate| Run one full cycle; isolate failures.                       |
| `__main__.py`      | automate   | CLI subcommands + `schedule`-based repeating runner.        |

## Design principles applied

- **Single responsibility** — every module does one job, so changes stay local.
- **Typed boundaries** — stages exchange dataclasses (`PriceRecord`,
  `CoinSummary`, `TriggeredAlert`), never raw dicts or JSON.
- **Config over code** — coins, currency, and alert rules live in `.env`; no
  secrets or environment-specific values are ever committed.
- **Fail safe** — network and email errors are logged and skipped so one bad
  cycle never stops the scheduler.
- **Idempotent setup** — directories and the database schema are created
  on demand, so the app is safe to run any number of times.
- **Portable artifacts** — the dashboard is a single HTML file anyone can open.

## Extending it

Because the network layer is isolated, swapping CoinGecko for another data
source means changing only `api_client.py`. Adding a new output (e.g. a Slack
or Telegram notifier) means adding one module and calling it from
`pipeline.run_cycle`. The same skeleton works for stock prices, weather,
server metrics, or any "collect → analyze → notify" automation.
