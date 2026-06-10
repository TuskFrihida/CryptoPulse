# CryptoPulse — Demo & Recording Guide

A step-by-step script for a clean screenshot or screen recording for your
Upwork / LinkedIn / GitHub portfolio. Total run time: ~2 minutes.

## Before you record

```bash
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env
```

Edit `.env` and (optionally) set the coins you want and a couple of alert
rules with thresholds you know will fire, so an alert visibly triggers on
camera. Email is optional — the rule firing shows in the console either way.

> Tip: pick alert thresholds just inside the current price (e.g. an "above"
> threshold slightly below the live price) so the alert triggers during the demo.

## Suggested recording flow

1. **Show the problem (10s).** Say: "Manually checking crypto prices and
   spotting trends is tedious. CryptoPulse automates the whole loop."

2. **Show the structure (10s).** Open the repo tree and the README roadmap —
   eight clean, committed steps.

3. **Run one cycle (20s).**
   ```bash
   python -m cryptopulse run-once
   ```
   Narrate the log lines as they scroll: fetch → store → dashboard → alert.

4. **Open the dashboard (20s).** Open `reports/dashboard.html` in a browser.
   Hover over the lines to show interactive tooltips; point out the price line
   vs. the dashed moving-average trend line and the summary table.

5. **Show an alert firing (15s).** With a threshold set to trigger, point to
   the `🚨` alert line in the console (and the email in your inbox if SMTP is
   configured).

6. **Start the scheduler (20s).**
   ```bash
   python -m cryptopulse run --interval 1
   ```
   Let it complete two cycles so viewers see it repeat automatically, then
   press Ctrl+C. Say: "Now it runs unattended — on a server it would feed a
   live dashboard and alert you 24/7."

7. **Show status (10s).**
   ```bash
   python -m cryptopulse status
   ```
   Highlights how many snapshots have accumulated.

## What to capture as stills

- The README with all 8 roadmap steps checked.
- The dark-themed interactive dashboard with multiple coins.
- The console showing a `🚨` alert line.
- The git commit history (one clean, descriptive commit per step).

## One-line pitch for your portfolio

> CryptoPulse — a Python automation pipeline that fetches live crypto prices,
> stores them in SQLite, analyzes trends with pandas, renders an interactive
> Plotly dashboard, and emails threshold alerts, all on an unattended schedule.
