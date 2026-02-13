# 🛒 Amazon Ads Automation

Auto-manages your Amazon Ads daily budgets based on seasonal targets, monitors ACOS, and sends alerts — runs on Google Cloud for ~$0.33/month.

## What it does
- **Pulls** campaign performance data from Amazon Ads API daily
- **Adjusts** daily budgets up/down based on your seasonal targets (peak in Jul/Aug, low in Nov–Feb)
- **Alerts** you by email + SMS if ACOS goes out of range
- **Logs** everything to Google Sheets + BigQuery

## How to deploy
See [DEPLOY.md](DEPLOY.md) for the full step-by-step guide.

## GitHub Secrets needed
Before pushing, add these in your repo → **Settings → Secrets → Actions**:

| Secret | Where to get it |
|--------|----------------|
| `GCP_SA_KEY` | GCP Console → IAM → Service Accounts → Create Key (JSON) |
| `GCP_PROJECT_ID` | Your GCP project ID |
| `GOOGLE_SHEET_ID` | From your Google Sheet URL |
| `ALERT_EMAIL_TO` | Your email address |
| `ALERT_EMAIL_FROM` | Verified SendGrid sender email |
| `ALERT_SMS_TO` | Your phone number (+1xxxxxxxxxx) |
| `TWILIO_FROM` | Your Twilio phone number |

## Workflow
```
Push to main → GitHub Actions runs tests → deploys to GCP → runs daily at 7am
```

## Seasonal Budget Targets
Edit `config/settings.py` → `seasonal_budgets` to update your monthly targets.
Current targets based on 20% ACOS analysis of 2025 sales data:

| Month | Daily Budget | Season |
|-------|-------------|--------|
| Jul   | $110        | 🔥 Peak |
| Jun   | $87         | 📈 High |
| Aug   | $88         | 📈 High |
| Mar–May | $65–68   | ➡️ Normal |
| Feb   | $18         | 🐌 Slow |
| Nov–Dec | $19–20   | 🐌 Slow |
