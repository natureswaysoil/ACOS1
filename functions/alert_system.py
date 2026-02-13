"""
Alert System
Sends email (SendGrid) and/or SMS (Twilio) when:
  - ACOS exceeds your upper warning threshold (default 30%)
  - ACOS drops below your lower threshold (default 10% — may mean ads aren't running)
  - A budget change of $10+ is made
  - Any automation error occurs
"""

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from twilio.rest import Client as TwilioClient
from datetime import datetime
from typing import List, Dict


class AlertSystem:

    def __init__(self, settings):
        self.settings = settings
        self.sg        = SendGridAPIClient(settings.sendgrid_api_key)
        self.twilio    = TwilioClient(settings.twilio_sid, settings.twilio_auth_token) \
                         if settings.twilio_sid else None

    def check_and_alert(self, campaigns: List[Dict]) -> List[str]:
        """Check every campaign for ACOS issues and fire alerts."""
        alerts_sent = []
        issues = []

        for c in campaigns:
            acos = c.get("acos_30d")
            if acos is None:
                continue

            name = c["campaign_name"]

            if acos > self.settings.acos_upper_warn:
                issues.append({
                    "level":   "⚠️ HIGH ACOS",
                    "message": f"{name}: ACOS is {acos*100:.1f}% — above your {self.settings.acos_upper_warn*100:.0f}% threshold",
                    "color":   "red",
                })
            elif acos < self.settings.acos_lower_warn:
                issues.append({
                    "level":   "ℹ️ LOW ACOS",
                    "message": f"{name}: ACOS is {acos*100:.1f}% — below {self.settings.acos_lower_warn*100:.0f}% (ads may not be spending)",
                    "color":   "orange",
                })

        if issues:
            subject = f"Amazon Ads Alert — {len(issues)} issue(s) — {datetime.now().strftime('%b %d')}"
            body    = self._build_email_body(issues)
            self._send_email(subject, body)
            alerts_sent.append("email")

            if self.twilio and self.settings.alert_sms_to:
                sms_text = f"Amazon Ads: {len(issues)} ACOS alert(s). Check email for details."
                self._send_sms(sms_text)
                alerts_sent.append("sms")

        return alerts_sent

    def send_error_alert(self, error_message: str):
        """Send an urgent alert when the automation itself fails."""
        subject = f"🚨 Amazon Ads Automation ERROR — {datetime.now().strftime('%b %d %H:%M')}"
        body    = f"""
        <h2 style='color:red'>Automation Error</h2>
        <p>The Amazon Ads automation encountered an error and did not complete.</p>
        <pre style='background:#f5f5f5;padding:12px'>{error_message}</pre>
        <p>Please check the Cloud Function logs in GCP Console.</p>
        """
        self._send_email(subject, body)
        if self.twilio and self.settings.alert_sms_to:
            self._send_sms(f"🚨 Amazon Ads automation FAILED. Check email.")

    # ── Private Helpers ─────────────────────────────────────────────────────

    def _build_email_body(self, issues: List[Dict]) -> str:
        rows = "".join(
            f"<tr><td style='padding:8px;color:{i['color']}'><b>{i['level']}</b></td>"
            f"<td style='padding:8px'>{i['message']}</td></tr>"
            for i in issues
        )
        return f"""
        <html><body style='font-family:Arial,sans-serif'>
        <h2>Amazon Ads Daily Report — {datetime.now().strftime('%B %d, %Y')}</h2>
        <p>{len(issues)} issue(s) detected today:</p>
        <table border='1' cellpadding='0' cellspacing='0' style='border-collapse:collapse;width:100%'>
          <thead>
            <tr style='background:#1F3864;color:white'>
              <th style='padding:8px'>Level</th>
              <th style='padding:8px'>Detail</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
        <p style='color:#666;font-size:12px'>Automated by your GCP Amazon Ads Bot</p>
        </body></html>
        """

    def _send_email(self, subject: str, html_body: str):
        message = Mail(
            from_email=self.settings.alert_email_from,
            to_emails=self.settings.alert_email_to,
            subject=subject,
            html_content=html_body,
        )
        self.sg.send(message)

    def _send_sms(self, text: str):
        self.twilio.messages.create(
            body=text,
            from_=self.settings.twilio_from_number,
            to=self.settings.alert_sms_to,
        )
