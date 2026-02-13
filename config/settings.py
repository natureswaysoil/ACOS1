"""
Settings — pulls all secrets from GCP Secret Manager.
Project: amazon-ppc-474902
Token refresh is handled automatically by GCP.
"""

from google.cloud import secretmanager


class Settings:
    def __init__(self):
        self.project_id = "amazon-ppc-474902"
        self.region     = "us-central1"

        sm = secretmanager.SecretManagerServiceClient()

        def get_secret(name, fallback=None):
            try:
                path = f"projects/{self.project_id}/secrets/{name}/versions/latest"
                return sm.access_secret_version(name=path).payload.data.decode("UTF-8")
            except Exception as e:
                if fallback is not None:
                    return fallback
                raise Exception(f"Secret '{name}' not found in {self.project_id}: {e}")

        # ── Amazon Ads ──────────────────────────────────────────
        self.amazon_client_id      = get_secret("AMAZON_CLIENT_ID")
        self.amazon_client_secret  = get_secret("AMAZON_CLIENT_SECRET")
        self.amazon_refresh_token  = get_secret("AMAZON_REFRESH_TOKEN")
        self.amazon_profile_id     = get_secret("AMAZON_PROFILE_ID")
        self.amazon_ads_region     = get_secret("AMAZON_REGION", fallback="NA")

        # ── Google Sheets ───────────────────────────────────────
        self.google_sheet_id  = "1TIs6baaTbkaKH4zwR1JPxvjqD7ioKCqGT9yjfrO7O6I"
        self.sheet_tab_daily  = "Daily Performance"
        self.sheet_tab_budget = "Budget Changes"
        self.sheet_tab_alerts = "Alerts"

        # ── BigQuery ────────────────────────────────────────────
        self.bq_dataset = "amazon_ads"
        self.bq_table   = "daily_performance"

        # ── Alerts ──────────────────────────────────────────────
        self.sendgrid_api_key   = get_secret("SENDGRID_API_KEY")
        self.alert_email_to     = get_secret("ALERT_EMAIL_TO")
        self.alert_email_from   = get_secret("ALERT_EMAIL_FROM")
        self.twilio_sid         = get_secret("TWILIO_SID",        fallback="")
        self.twilio_auth_token  = get_secret("TWILIO_AUTH_TOKEN", fallback="")
        self.twilio_from_number = get_secret("TWILIO_FROM",       fallback="")
        self.alert_sms_to       = get_secret("ALERT_SMS_TO",      fallback="")

        # ── Business Rules ──────────────────────────────────────
        self.target_acos           = float(get_secret("TARGET_ACOS",    fallback="0.20"))
        self.acos_upper_warn       = float(get_secret("ACOS_WARN_HIGH", fallback="0.30"))
        self.acos_lower_warn       = float(get_secret("ACOS_WARN_LOW",  fallback="0.10"))
        self.yoy_growth_rate       = float(get_secret("YOY_GROWTH",     fallback="0.37"))
        self.max_budget_change_pct = float(get_secret("MAX_CHANGE",     fallback="0.25"))

        # ── Seasonal Daily Budget Targets ($) ───────────────────
        self.seasonal_budgets = {
            1:  35,   # January
            2:  18,   # February
            3:  65,   # March
            4:  68,   # April
            5:  68,   # May
            6:  87,   # June
            7:  110,  # July — PEAK
            8:  88,   # August
            9:  70,   # September
            10: 45,   # October
            11: 20,   # November
            12: 19,   # December
        }
