from datetime import date, datetime

import pytest
import resend

from weekly_briefing_email import (
    ResendCallFailed,
    build_html,
    build_subject,
    send_email_with_retry,
    should_run_now,
    week_start_for,
)


# --- should_run_now / week_start_for: pure time logic --------------------


def test_should_run_now_true_on_monday_6am_central():
    assert should_run_now(datetime(2026, 9, 28, 6, 0)) is True  # a Monday


def test_should_run_now_false_on_a_different_day():
    assert should_run_now(datetime(2026, 9, 29, 6, 0)) is False  # a Tuesday


def test_should_run_now_false_at_a_different_hour():
    assert should_run_now(datetime(2026, 9, 28, 7, 0)) is False


def test_week_start_for_returns_the_monday_of_that_week():
    assert week_start_for(date(2026, 9, 24)) == date(2026, 9, 21)  # a Thursday -> that week's Monday
    assert week_start_for(date(2026, 9, 21)) == date(2026, 9, 21)  # already a Monday


# --- build_subject / build_html: pure formatting --------------------------


def test_build_subject_includes_the_date():
    assert "2026-09-28" in build_subject(date(2026, 9, 28))


def test_build_html_wraps_nonblank_lines_and_drops_blank_ones():
    html = build_html("Hospital A is at risk.\n\nHospital B is stable.")
    assert html == "<div><p>Hospital A is at risk.</p><p>Hospital B is stable.</p></div>"


# --- send_email_with_retry: retry / backoff / failure ---------------------


class FakeEmails:
    """Returns responses[i] on the i-th call, or raises if it's an Exception."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def send(self, params):
        outcome = self.responses[self.calls]
        self.calls += 1
        if isinstance(outcome, BaseException):
            raise outcome
        return {"id": outcome}


class FakeResendClient:
    def __init__(self, responses):
        self.Emails = FakeEmails(responses)


def _resend_error(code, message="error"):
    return resend.exceptions.ResendError(
        code=code, error_type="application_error", message=message, suggested_action="retry"
    )


def test_send_email_with_retry_succeeds_first_try():
    client = FakeResendClient(["msg_1"])
    message_id = send_email_with_retry(client, "ops@example.com", "subj", "<p>hi</p>", sleep=lambda s: None)
    assert message_id == "msg_1"
    assert client.Emails.calls == 1


def test_send_email_with_retry_retries_on_retryable_error_then_succeeds():
    sleeps = []
    client = FakeResendClient([_resend_error(429), _resend_error(500), "msg_2"])
    message_id = send_email_with_retry(client, "ops@example.com", "subj", "<p>hi</p>", sleep=sleeps.append)
    assert message_id == "msg_2"
    assert client.Emails.calls == 3
    assert sleeps == [1.0, 2.0]


def test_send_email_with_retry_retries_on_network_level_runtime_error():
    client = FakeResendClient([RuntimeError("Request failed: timed out"), "msg_3"])
    message_id = send_email_with_retry(client, "ops@example.com", "subj", "<p>hi</p>", sleep=lambda s: None)
    assert message_id == "msg_3"
    assert client.Emails.calls == 2


def test_send_email_with_retry_fails_fast_on_non_retryable_error():
    client = FakeResendClient([_resend_error(400, "bad request")])
    with pytest.raises(ResendCallFailed):
        send_email_with_retry(client, "ops@example.com", "subj", "<p>hi</p>", sleep=lambda s: None)
    assert client.Emails.calls == 1  # never retried


def test_send_email_with_retry_fails_after_exhausting_retries():
    client = FakeResendClient([_resend_error(503)] * 4)
    with pytest.raises(ResendCallFailed):
        send_email_with_retry(client, "ops@example.com", "subj", "<p>hi</p>", sleep=lambda s: None)
    assert client.Emails.calls == 4  # 1 initial + 3 retries, never more
