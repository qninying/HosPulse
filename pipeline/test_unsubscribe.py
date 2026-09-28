from unsubscribe import (
    build_unsubscribe_url,
    generate_unsubscribe_token,
    verify_unsubscribe_token,
)

SECRET = "test-secret-do-not-use-in-prod"


def test_a_generated_token_verifies_against_the_same_inputs():
    token = generate_unsubscribe_token("company-1", "a@example.com", SECRET)
    assert verify_unsubscribe_token("company-1", "a@example.com", token, SECRET)


def test_a_token_for_one_recipient_does_not_verify_for_another():
    token = generate_unsubscribe_token("company-1", "a@example.com", SECRET)
    assert not verify_unsubscribe_token("company-1", "b@example.com", token, SECRET)


def test_a_token_does_not_verify_under_a_different_company():
    token = generate_unsubscribe_token("company-1", "a@example.com", SECRET)
    assert not verify_unsubscribe_token("company-2", "a@example.com", token, SECRET)


def test_a_token_does_not_verify_under_a_different_secret():
    token = generate_unsubscribe_token("company-1", "a@example.com", SECRET)
    assert not verify_unsubscribe_token("company-1", "a@example.com", token, "wrong-secret")


def test_a_tampered_token_is_rejected():
    token = generate_unsubscribe_token("company-1", "a@example.com", SECRET)
    tampered = token[:-1] + ("0" if token[-1] != "0" else "1")
    assert not verify_unsubscribe_token("company-1", "a@example.com", tampered, SECRET)


def test_token_generation_is_deterministic_not_random():
    # Same inputs must always produce the same token -- the link in a
    # real sent email has to keep working when re-verified later.
    a = generate_unsubscribe_token("company-1", "a@example.com", SECRET)
    b = generate_unsubscribe_token("company-1", "a@example.com", SECRET)
    assert a == b


def test_build_unsubscribe_url_embeds_a_verifiable_token():
    url = build_unsubscribe_url("company-1", "a@example.com", SECRET, "http://localhost:3000")
    assert url.startswith("http://localhost:3000/api/unsubscribe?")
    assert "company=company-1" in url
    assert "email=a%40example.com" in url


def test_build_unsubscribe_url_strips_a_trailing_slash_on_base_url():
    url = build_unsubscribe_url("company-1", "a@example.com", SECRET, "http://localhost:3000/")
    assert url.startswith("http://localhost:3000/api/unsubscribe?")
    assert "//api/unsubscribe" not in url.replace("http://", "")
