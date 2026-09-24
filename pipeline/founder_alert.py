"""Best-effort email alert to the founder when a pipeline run fails.

Wired into pipeline_run_log.finish_pipeline_run(), so every process that
already uses start_pipeline_run/finish_pipeline_run (early_warning,
cost_report_copilot, and any future one) gets paging for free, not just
the one that motivated this module.

Deliberately never raises, same reasoning as supabase_storage.py's
upload_export_file(): this alert is a secondary notification about a
failure pipeline_runs.error_message has already recorded. If sending the
alert itself fails (missing config, Resend down), the original failure
must still propagate to the caller untouched, not get replaced by a
config error about alerting. A missing FOUNDER_ALERT_EMAIL or
RESEND_API_KEY is logged to stderr as "not configured yet," not a crash.
No retry -- a retry would delay the caller for a nice-to-have; a missed
alert is recoverable by looking at pipeline_runs directly.
"""
from __future__ import annotations

import os
import sys
from typing import Any

import resend
from resend.http_client_requests import RequestsClient

FROM_ADDRESS = "onboarding@resend.dev"
REQUEST_TIMEOUT_SECONDS = 10.0


def send_founder_alert(subject: str, body: str, resend_client: Any = None) -> None:
    """Best-effort only. Never raises -- see module docstring.
    resend_client is injectable for tests (same pattern as
    weekly_briefing_email.send_email_with_retry's FakeResendClient);
    defaults to the real, configured resend module."""
    resend_api_key = os.environ.get("RESEND_API_KEY")
    founder_email = os.environ.get("FOUNDER_ALERT_EMAIL")
    if not resend_api_key or not founder_email:
        print(
            f"warning: founder alert not sent (RESEND_API_KEY or FOUNDER_ALERT_EMAIL not set): {subject}",
            file=sys.stderr,
        )
        return

    if resend_client is None:
        resend.api_key = resend_api_key
        resend.default_http_client = RequestsClient(timeout=int(REQUEST_TIMEOUT_SECONDS))
        resend_client = resend

    try:
        resend_client.Emails.send(
            {"from": FROM_ADDRESS, "to": [founder_email], "subject": subject, "html": f"<p>{body}</p>"}
        )
    except resend.exceptions.ResendError as exc:
        print(f"warning: founder alert failed to send (Resend error): {exc!r}", file=sys.stderr)
    except RuntimeError as exc:
        # resend wraps a network-level failure (timeout, connection error)
        # from `requests` as a plain RuntimeError, same as weekly_briefing_email.py.
        print(f"warning: founder alert failed to send (network error): {exc!r}", file=sys.stderr)
