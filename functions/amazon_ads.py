"""
Amazon Ads API Client
Handles authentication (OAuth2) and all API calls.
Docs: https://advertising.amazon.com/API/docs
"""

import requests
from datetime import datetime, timedelta
from typing import List, Dict


class AmazonAdsClient:

    TOKEN_URL = "https://api.amazon.com/auth/o2/token"

    # API endpoints differ by region
    API_ENDPOINTS = {
        "NA": "https://advertising-api.amazon.com",
        "EU": "https://advertising-api-eu.amazon.com",
        "FE": "https://advertising-api-fe.amazon.com",
    }

    def __init__(self, settings):
        self.settings = settings
        self.base_url = self.API_ENDPOINTS[settings.amazon_ads_region]
        self.access_token = self._get_access_token()
        self.headers = {
            "Authorization":      f"Bearer {self.access_token}",
            "Amazon-Advertising-API-ClientId": settings.amazon_client_id,
            "Amazon-Advertising-API-Scope":    settings.amazon_profile_id,
            "Content-Type": "application/json",
        }

    # ── Authentication ──────────────────────────────────────────────────────

    def _get_access_token(self) -> str:
        """Exchange refresh token for a fresh access token."""
        resp = requests.post(self.TOKEN_URL, data={
            "grant_type":    "refresh_token",
            "refresh_token": self.settings.amazon_refresh_token,
            "client_id":     self.settings.amazon_client_id,
            "client_secret": self.settings.amazon_client_secret,
        })
        resp.raise_for_status()
        return resp.json()["access_token"]

    # ── Data Retrieval ──────────────────────────────────────────────────────

    def get_campaign_performance(self) -> List[Dict]:
        """
        Pull last 30 days of campaign performance.
        Returns list of campaigns with spend, sales, ACOS, units, etc.
        """
        end_date   = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

        # Request a Sponsored Products report
        report_resp = requests.post(
            f"{self.base_url}/v2/sp/campaigns/report",
            headers=self.headers,
            json={
                "reportDate": end_date,
                "metrics": "campaignName,campaignId,campaignStatus,campaignBudget,"
                           "impressions,clicks,cost,attributedSales30d,"
                           "attributedUnitsOrdered30d,acos30d",
                "startDate": start_date,
                "endDate":   end_date,
            }
        )
        report_resp.raise_for_status()
        report_id = report_resp.json()["reportId"]

        # Poll until ready (usually 30–60 sec)
        return self._poll_and_download_report(report_id)

    def _poll_and_download_report(self, report_id: str) -> List[Dict]:
        """Poll the report endpoint until ready, then download and parse."""
        import time, gzip, json

        for attempt in range(20):
            status_resp = requests.get(
                f"{self.base_url}/v2/reports/{report_id}",
                headers=self.headers
            )
            status_resp.raise_for_status()
            data = status_resp.json()

            if data["status"] == "SUCCESS":
                # Download the gzipped report
                dl = requests.get(data["location"], headers=self.headers)
                rows = json.loads(gzip.decompress(dl.content))
                return self._enrich_campaigns(rows)

            elif data["status"] == "FAILURE":
                raise Exception(f"Amazon report failed: {data}")

            time.sleep(10)

        raise TimeoutError("Amazon report timed out after 200 seconds")

    def _enrich_campaigns(self, rows: List[Dict]) -> List[Dict]:
        """Add computed fields (ACOS, recommended budget) to each campaign row."""
        enriched = []
        for row in rows:
            cost  = float(row.get("cost", 0))
            sales = float(row.get("attributedSales30d", 0))
            acos  = (cost / sales) if sales > 0 else None
            enriched.append({
                "campaign_id":     row.get("campaignId"),
                "campaign_name":   row.get("campaignName"),
                "status":          row.get("campaignStatus"),
                "current_budget":  float(row.get("campaignBudget", 0)),
                "spend_30d":       cost,
                "sales_30d":       sales,
                "units_30d":       int(row.get("attributedUnitsOrdered30d", 0)),
                "acos_30d":        acos,
                "clicks":          int(row.get("clicks", 0)),
                "impressions":     int(row.get("impressions", 0)),
                "pulled_at":       datetime.now().isoformat(),
            })
        return enriched

    # ── Budget Updates ──────────────────────────────────────────────────────

    def apply_budget_changes(self, budget_actions: List[Dict]) -> List[Dict]:
        """
        Apply recommended budget changes to Amazon Ads campaigns.
        Only updates campaigns that need a change > $1.
        """
        applied = []
        for action in budget_actions:
            if not action.get("should_update"):
                continue

            resp = requests.put(
                f"{self.base_url}/v2/sp/campaigns",
                headers=self.headers,
                json=[{
                    "campaignId":    action["campaign_id"],
                    "dailyBudget":   action["new_budget"],
                }]
            )

            if resp.status_code == 207:   # Amazon returns 207 Multi-Status
                result = resp.json()
                action["api_response"] = result
                action["applied_at"]   = datetime.now().isoformat()
                applied.append(action)
                print(f"    Budget updated: {action['campaign_name']} "
                      f"${action['old_budget']:.2f} → ${action['new_budget']:.2f}")
            else:
                print(f"    WARNING: Budget update failed for {action['campaign_name']}: {resp.text}")

        return applied
