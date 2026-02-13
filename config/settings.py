"""
Settings — pulled from Google Cloud Secret Manager (never hardcoded).
All secrets are stored in GCP Secret Manager and injected at runtime.
"""

import os
from google.cloud import secretmanager


class Settings:
    def __init__(self):
        self.project_id = os.environ["GCP_PROJECT_ID"]          # e.g. "my-project-123"
        self.region     = os.environ.get("REGION", "us-central1")

        # Load secrets from GCP Secret Manager
        sm = secretmanager.SecretManagerServiceClient()

        def get_secret(name):
            path = f"projects/{self.project_id}/secrets/{name}/versions/latest"
            return sm.access_secret_version(name=path).payload.data.decode("UTF-8")

        # ── Amazon Ads credentials ──────────────────────────────
        # Get these from: advertising.amazon.com → Manage API access
        self.amazon_client_id      = get_secret("AMAZON_CLIENT_ID")
        self.amazon_client_secret  = get_secret("AMAZON_CLIENT_SECRET")
        self.amazon_refresh_token  = get_secret("AMAZON_REFRESH_TOKEN")
        self.amazon_profile_id     = get_secret("AMAZON_PROFILE_ID")   # your seller profile ID
        self.amazon_ads_region     = os.environ.get("AMAZON_REGION", "NA")  # NA, EU, FE

        # ── Google Sheets ───────────────────────────────────────
        # Create a sheet and paste its ID from the URL
        self.google_sheet_id  = os.environ["GOOGLE_SHEET_ID"]
        self.sheet_tab_daily  = "Daily Performance"
        self.sheet_tab_budget = "Budget Changes"
        self.sheet_tab_alerts = "Alerts"

        # ── BigQuery ────────────────────────────────────────────
        self.bq_dataset  = os.environ.get("BQ_DATASET", "amazon_ads")
        self.bq_table    = os.environ.get("BQ_TABLE",   "daily_performance")

        # ── Alerts (SendGrid email + Twilio SMS) ────────────────
        self.sendgrid_api_key   = get_secret("SENDGRID_API_KEY")
        self.alert_email_to     = os.environ["ALERT_EMAIL_TO"]    # your email
        self.alert_email_from   = os.environ["ALERT_EMAIL_FROM"]  # verified sender
        self.twilio_sid         = get_secret("TWILIO_SID")
        self.twilio_auth_token  = get_secret("TWILIO_AUTH_TOKEN")
        self.twilio_from_number = os.environ.get("TWILIO_FROM", "")  # leave blank to skip SMS
        self.alert_sms_to       = os.environ.get("ALERT_SMS_TO", "")

        # ── Business Rules ──────────────────────────────────────
        self.target_acos     = float(os.environ.get("TARGET_ACOS", "0.20"))    # 20%
        self.acos_upper_warn = float(os.environ.get("ACOS_WARN_HIGH", "0.30")) # alert at 30%
        self.acos_lower_warn = float(os.environ.get("ACOS_WARN_LOW", "0.10"))  # alert at 10%
        self.yoy_growth_rate = float(os.environ.get("YOY_GROWTH", "0.37"))     # 37%
        self.max_budget_change_pct = float(os.environ.get("MAX_CHANGE", "0.25"))  # max 25% change/day

        # ── Seasonal Daily Budget Targets ($ per day) ───────────
        # Based on your 20% ACOS analysis — update anytime
        self.seasonal_budgets = {
            1:  35,   # January   — recovering
            2:  18,   # February  — slow
            3:  65,   # March     — ramp up
            4:  68,   # April     — building
            5:  68,   # May       — pre-peak
            6:  87,   # June      — peak approaching
            7:  110,  # July      — PEAK
            8:  88,   # August    — still peak
            9:  70,   # September — strong
            10: 45,   # October   — slowing
            11: 20,   # November  — slow
            12: 19,   # December  — slowest
        }
