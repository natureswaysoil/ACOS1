"""
Amazon Ads Automation — Google Cloud Function
============================================================
Runs on a schedule (Cloud Scheduler) and does 3 things:
  1. Pulls your Amazon Ads data (campaigns, spend, sales, ACOS)
  2. Auto-adjusts daily budgets based on your seasonal targets
  3. Sends email/SMS alerts when ACOS goes out of range
  4. Logs everything to Google Sheets + BigQuery

Deploy with:
  gcloud functions deploy amazon_ads_automation \
    --runtime python311 \
    --trigger-http \
    --region us-central1 \
    --env-vars-file .env.yaml \
    --memory 512MB \
    --timeout 300s
"""

import functions_framework
from datetime import datetime
from config.settings import Settings
from functions.amazon_ads import AmazonAdsClient
from functions.budget_optimizer import BudgetOptimizer
from functions.alert_system import AlertSystem
from functions.reporting import ReportingService


@functions_framework.http
def amazon_ads_automation(request):
    """Main entry point — triggered by Cloud Scheduler daily."""
    print(f"[{datetime.now()}] Starting Amazon Ads Automation run...")

    settings = Settings()
    results = {"timestamp": datetime.now().isoformat(), "actions": []}

    try:
        # 1. Connect to Amazon Ads
        ads_client = AmazonAdsClient(settings)
        campaign_data = ads_client.get_campaign_performance()
        print(f"  ✓ Pulled data for {len(campaign_data)} campaigns")

        # 2. Optimize budgets based on seasonal targets
        optimizer = BudgetOptimizer(settings)
        budget_actions = optimizer.optimize(campaign_data)
        applied = ads_client.apply_budget_changes(budget_actions)
        results["actions"].extend(applied)
        print(f"  ✓ Applied {len(applied)} budget adjustments")

        # 3. Check ACOS and send alerts if out of range
        alert_system = AlertSystem(settings)
        alerts_sent = alert_system.check_and_alert(campaign_data)
        results["alerts_sent"] = alerts_sent
        print(f"  ✓ Sent {len(alerts_sent)} alerts")

        # 4. Log everything to Sheets + BigQuery
        reporter = ReportingService(settings)
        reporter.log_to_sheets(campaign_data, budget_actions)
        reporter.log_to_bigquery(campaign_data, budget_actions)
        print(f"  ✓ Logged to Google Sheets and BigQuery")

        results["status"] = "success"
        return {"statusCode": 200, "body": results}

    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        results["status"] = "error"
        results["error"] = str(e)
        AlertSystem(settings).send_error_alert(str(e))
        return {"statusCode": 500, "body": results}
