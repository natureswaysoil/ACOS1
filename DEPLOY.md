# 🚀 Amazon Ads Automation — Deployment Guide
## Google Cloud Function + Cloud Scheduler

---

## WHAT THIS DOES
Runs every day at 7am and automatically:
1. Pulls your Amazon Ads campaign data (spend, sales, ACOS, units)
2. Adjusts daily budgets up/down based on seasonal targets
3. Emails + texts you if ACOS goes out of range
4. Logs everything to Google Sheets + BigQuery

---

## STEP 1 — Get Your Amazon Ads API Credentials
1. Go to: https://advertising.amazon.com → Account → Manage API Access
2. Create a new app → copy your **Client ID** and **Client Secret**
3. Authorize via OAuth2 to get your **Refresh Token**
   - Use the Login with Amazon flow or tools like Postman
   - Scope needed: `advertising::campaign_management`
4. Find your **Profile ID**: call GET /v2/profiles after auth — use the one matching your seller account

---

## STEP 2 — Set Up Google Cloud Project
```bash
# Install gcloud CLI: https://cloud.google.com/sdk/docs/install
gcloud auth login
gcloud projects create YOUR-PROJECT-ID --name="Amazon Ads Bot"
gcloud config set project YOUR-PROJECT-ID

# Enable required APIs
gcloud services enable \
  cloudfunctions.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  bigquery.googleapis.com \
  sheets.googleapis.com
```

---

## STEP 3 — Store Secrets in Secret Manager
```bash
# Never put credentials in code. Store them here:

echo -n "YOUR_AMAZON_CLIENT_ID" | \
  gcloud secrets create AMAZON_CLIENT_ID --data-file=-

echo -n "YOUR_AMAZON_CLIENT_SECRET" | \
  gcloud secrets create AMAZON_CLIENT_SECRET --data-file=-

echo -n "YOUR_AMAZON_REFRESH_TOKEN" | \
  gcloud secrets create AMAZON_REFRESH_TOKEN --data-file=-

echo -n "YOUR_AMAZON_PROFILE_ID" | \
  gcloud secrets create AMAZON_PROFILE_ID --data-file=-

echo -n "YOUR_SENDGRID_API_KEY" | \
  gcloud secrets create SENDGRID_API_KEY --data-file=-

echo -n "YOUR_TWILIO_SID" | \
  gcloud secrets create TWILIO_SID --data-file=-

echo -n "YOUR_TWILIO_AUTH_TOKEN" | \
  gcloud secrets create TWILIO_AUTH_TOKEN --data-file=-
```

---

## STEP 4 — Set Up Google Sheet
1. Create a new Google Sheet at sheets.google.com
2. Add 3 tabs: "Daily Performance", "Budget Changes", "Alerts"
3. Copy the Sheet ID from the URL:
   https://docs.google.com/spreadsheets/d/**THIS-PART**/edit
4. Paste into .env.yaml → GOOGLE_SHEET_ID

---

## STEP 5 — Set Up BigQuery
```bash
# Create the dataset
bq mk --dataset YOUR-PROJECT-ID:amazon_ads

# Create the table (run this Python script once)
python3 -c "
from functions.reporting import ReportingService
ReportingService.create_bq_table_schema()
"
```

---

## STEP 6 — Fill in .env.yaml
Edit `.env.yaml` and fill in all your values (project ID, email, phone, sheet ID)

---

## STEP 7 — Deploy the Cloud Function
```bash
cd amazon-ads-automation

gcloud functions deploy amazon_ads_automation \
  --gen2 \
  --runtime python311 \
  --trigger-http \
  --entry-point amazon_ads_automation \
  --region us-central1 \
  --env-vars-file .env.yaml \
  --memory 512MB \
  --timeout 300s \
  --no-allow-unauthenticated

# Note the HTTPS URL that gets printed after deploy — you'll need it next
```

---

## STEP 8 — Schedule It to Run Daily
```bash
# Create a service account for the scheduler
gcloud iam service-accounts create ads-scheduler \
  --display-name "Ads Scheduler"

# Grant it permission to invoke the function
gcloud functions add-iam-policy-binding amazon_ads_automation \
  --region us-central1 \
  --member serviceAccount:ads-scheduler@YOUR-PROJECT-ID.iam.gserviceaccount.com \
  --role roles/cloudfunctions.invoker

# Create the daily schedule (runs at 7am US Eastern every day)
gcloud scheduler jobs create http amazon-ads-daily \
  --schedule "0 7 * * *" \
  --time-zone "America/New_York" \
  --uri "YOUR-FUNCTION-URL" \
  --oidc-service-account-email ads-scheduler@YOUR-PROJECT-ID.iam.gserviceaccount.com \
  --http-method POST
```

---

## STEP 9 — Test It
```bash
# Trigger a manual run
gcloud scheduler jobs run amazon-ads-daily --location us-central1

# Check the logs
gcloud functions logs read amazon_ads_automation --region us-central1 --limit 50
```

---

## ESTIMATED MONTHLY COST ON GCP
| Service          | Usage                    | Cost      |
|------------------|--------------------------|-----------|
| Cloud Functions  | 30 runs/month, 5 min each| ~$0.00    |  ← free tier
| Cloud Scheduler  | 1 job                    | ~$0.10    |
| Secret Manager   | 7 secrets                | ~$0.21    |
| BigQuery         | <1GB storage             | ~$0.02    |
| **Total**        |                          | **~$0.33/month** |

---

## UPDATING YOUR SEASONAL BUDGETS
Edit `config/settings.py` → `seasonal_budgets` dict, then redeploy:
```bash
gcloud functions deploy amazon_ads_automation \
  --gen2 --runtime python311 --trigger-http \
  --entry-point amazon_ads_automation \
  --region us-central1 --env-vars-file .env.yaml
```

---

## FILE STRUCTURE
```
amazon-ads-automation/
├── main.py                    ← Cloud Function entry point
├── requirements.txt           ← Python dependencies
├── .env.yaml                  ← Environment variables (fill this in)
├── config/
│   └── settings.py            ← All config + seasonal budget targets
└── functions/
    ├── amazon_ads.py          ← Amazon Ads API client
    ├── budget_optimizer.py    ← Budget change logic
    ├── alert_system.py        ← Email + SMS alerts
    └── reporting.py           ← Google Sheets + BigQuery logging
```
