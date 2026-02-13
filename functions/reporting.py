"""
Reporting Service
Logs all campaign data and budget changes to:
  1. Google Sheets — human-readable dashboard
  2. BigQuery — queryable history for trend analysis
"""

from datetime import datetime
from typing import List, Dict
from google.cloud import bigquery
from googleapiclient.discovery import build
from google.auth import default


class ReportingService:

    def __init__(self, settings):
        self.settings = settings
        self.bq        = bigquery.Client(project=settings.project_id)
        creds, _       = default(scopes=["https://www.googleapis.com/auth/spreadsheets"])
        self.sheets    = build("sheets", "v4", credentials=creds).spreadsheets()

    # ── Google Sheets ───────────────────────────────────────────────────────

    def log_to_sheets(self, campaigns: List[Dict], budget_actions: List[Dict]):
        """Append today's data to the Google Sheet dashboard."""
        today = datetime.now().strftime("%Y-%m-%d")

        # Tab 1: Daily Performance
        perf_rows = [[
            today,
            c["campaign_name"],
            c["status"],
            c["current_budget"],
            c["spend_30d"],
            c["sales_30d"],
            c["units_30d"],
            f"{c['acos_30d']*100:.1f}%" if c["acos_30d"] else "N/A",
            c["clicks"],
            c["impressions"],
        ] for c in campaigns]

        if perf_rows:
            self._append_rows(self.settings.sheet_tab_daily, perf_rows)

        # Tab 2: Budget Changes
        budget_rows = [[
            today,
            a["campaign_name"],
            a["old_budget"],
            a["new_budget"],
            a["delta"],
            a["direction"].upper(),
            a["reason"],
        ] for a in budget_actions if a.get("should_update")]

        if budget_rows:
            self._append_rows(self.settings.sheet_tab_budget, budget_rows)

    def _append_rows(self, tab_name: str, rows: List[List]):
        """Append rows to a specific tab. Creates header if sheet is empty."""
        # Check if header exists
        result = self.sheets.values().get(
            spreadsheetId=self.settings.google_sheet_id,
            range=f"{tab_name}!A1:A1"
        ).execute()

        if not result.get("values"):
            self._write_headers(tab_name)

        self.sheets.values().append(
            spreadsheetId=self.settings.google_sheet_id,
            range=f"{tab_name}!A:Z",
            valueInputOption="USER_ENTERED",
            body={"values": rows}
        ).execute()

    def _write_headers(self, tab_name: str):
        headers = {
            self.settings.sheet_tab_daily: [[
                "Date","Campaign","Status","Daily Budget ($)","Spend 30d ($)",
                "Sales 30d ($)","Units 30d","ACOS 30d","Clicks","Impressions"
            ]],
            self.settings.sheet_tab_budget: [[
                "Date","Campaign","Old Budget ($)","New Budget ($)","Change ($)","Direction","Reason"
            ]],
        }
        if tab_name in headers:
            self.sheets.values().update(
                spreadsheetId=self.settings.google_sheet_id,
                range=f"{tab_name}!A1",
                valueInputOption="USER_ENTERED",
                body={"values": headers[tab_name]}
            ).execute()

    # ── BigQuery ─────────────────────────────────────────────────────────────

    def log_to_bigquery(self, campaigns: List[Dict], budget_actions: List[Dict]):
        """Insert campaign rows into BigQuery for long-term trend analysis."""
        table_ref = f"{self.settings.project_id}.{self.settings.bq_dataset}.{self.settings.bq_table}"

        rows_to_insert = [{
            "date":            datetime.now().strftime("%Y-%m-%d"),
            "campaign_id":     c["campaign_id"],
            "campaign_name":   c["campaign_name"],
            "status":          c["status"],
            "daily_budget":    c["current_budget"],
            "spend_30d":       c["spend_30d"],
            "sales_30d":       c["sales_30d"],
            "units_30d":       c["units_30d"],
            "acos_30d":        c["acos_30d"],
            "clicks":          c["clicks"],
            "impressions":     c["impressions"],
            "inserted_at":     datetime.utcnow().isoformat(),
        } for c in campaigns]

        errors = self.bq.insert_rows_json(table_ref, rows_to_insert)
        if errors:
            raise Exception(f"BigQuery insert errors: {errors}")

    @staticmethod
    def create_bq_table_schema():
        """
        Run this ONCE to create the BigQuery table.
        Usage: ReportingService.create_bq_table_schema()
        """
        from google.cloud import bigquery
        client = bigquery.Client()
        schema = [
            bigquery.SchemaField("date",          "DATE"),
            bigquery.SchemaField("campaign_id",   "STRING"),
            bigquery.SchemaField("campaign_name", "STRING"),
            bigquery.SchemaField("status",        "STRING"),
            bigquery.SchemaField("daily_budget",  "FLOAT"),
            bigquery.SchemaField("spend_30d",     "FLOAT"),
            bigquery.SchemaField("sales_30d",     "FLOAT"),
            bigquery.SchemaField("units_30d",     "INTEGER"),
            bigquery.SchemaField("acos_30d",      "FLOAT"),
            bigquery.SchemaField("clicks",        "INTEGER"),
            bigquery.SchemaField("impressions",   "INTEGER"),
            bigquery.SchemaField("inserted_at",   "TIMESTAMP"),
        ]
        table = bigquery.Table("YOUR_PROJECT.amazon_ads.daily_performance", schema=schema)
        table.time_partitioning = bigquery.TimePartitioning(field="date")
        client.create_table(table)
        print("BigQuery table created.")
