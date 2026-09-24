import resend

from founder_alert import send_founder_alert


class FakeEmails:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def send(self, params):
        self.calls.append(params)
        outcome = self.responses[len(self.calls) - 1]
        if isinstance(outcome, BaseException):
            raise outcome
        return {"id": outcome}


class FakeResendClient:
    def __init__(self, responses):
        self.Emails = FakeEmails(responses)


def _resend_error(code=500, message="error"):
    return resend.exceptions.ResendError(
        code=code, error_type="application_error", message=message, suggested_action="retry"
    )


def test_sends_to_the_configured_founder_email(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "key")
    monkeypatch.setenv("FOUNDER_ALERT_EMAIL", "founder@example.com")
    client = FakeResendClient(["msg_1"])

    send_founder_alert("subject", "body", resend_client=client)

    assert len(client.Emails.calls) == 1
    assert client.Emails.calls[0]["to"] == ["founder@example.com"]
    assert client.Emails.calls[0]["subject"] == "subject"


def test_does_not_send_and_does_not_raise_when_founder_email_unset(monkeypatch, capsys):
    monkeypatch.setenv("RESEND_API_KEY", "key")
    monkeypatch.delenv("FOUNDER_ALERT_EMAIL", raising=False)
    client = FakeResendClient(["msg_1"])

    send_founder_alert("subject", "body", resend_client=client)

    assert len(client.Emails.calls) == 0
    assert "not sent" in capsys.readouterr().err


def test_does_not_send_and_does_not_raise_when_resend_key_unset(monkeypatch, capsys):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.setenv("FOUNDER_ALERT_EMAIL", "founder@example.com")
    client = FakeResendClient(["msg_1"])

    send_founder_alert("subject", "body", resend_client=client)

    assert len(client.Emails.calls) == 0
    assert "not sent" in capsys.readouterr().err


def test_a_resend_failure_is_logged_and_never_raised(monkeypatch, capsys):
    monkeypatch.setenv("RESEND_API_KEY", "key")
    monkeypatch.setenv("FOUNDER_ALERT_EMAIL", "founder@example.com")
    client = FakeResendClient([_resend_error(500, "boom")])

    send_founder_alert("subject", "body", resend_client=client)  # must not raise

    assert "failed to send" in capsys.readouterr().err


def test_a_network_failure_is_logged_and_never_raised(monkeypatch, capsys):
    monkeypatch.setenv("RESEND_API_KEY", "key")
    monkeypatch.setenv("FOUNDER_ALERT_EMAIL", "founder@example.com")
    client = FakeResendClient([RuntimeError("Request failed: timed out")])

    send_founder_alert("subject", "body", resend_client=client)  # must not raise

    assert "failed to send" in capsys.readouterr().err
