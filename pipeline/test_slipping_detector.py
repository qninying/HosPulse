from slipping_detector import MonthMetrics, evaluate_slipping


def criterion(evaluation, name):
    return next(c for c in evaluation.criteria if c.name == name)


# --- Happy path: each criterion can genuinely trigger -------------------

def test_declining_cash_on_hand_flags_the_hospital_as_slipping():
    months = [
        MonthMetrics("2026-07-01", cash_on_hand=200000, denial_rate_pct=5.0, ar_balance=300000),
        MonthMetrics("2026-08-01", cash_on_hand=150000, denial_rate_pct=5.0, ar_balance=300000),
    ]
    result = evaluate_slipping("370178", months)
    assert result.status == "slipping"
    c = criterion(result, "cash_on_hand_declining")
    assert c.status == "triggered"
    assert c.values["cash_on_hand"] == [200000, 150000]


def test_rising_denial_rate_flags_the_hospital_as_slipping():
    months = [
        MonthMetrics("2026-07-01", cash_on_hand=200000, denial_rate_pct=5.0, ar_balance=300000),
        MonthMetrics("2026-08-01", cash_on_hand=200000, denial_rate_pct=9.0, ar_balance=300000),
    ]
    result = evaluate_slipping("370178", months)
    assert result.status == "slipping"
    c = criterion(result, "denial_rate_rising")
    assert c.status == "triggered"
    assert c.values["denial_rate_pct"] == [5.0, 9.0]


def test_rising_ar_balance_flags_the_hospital_as_slipping():
    months = [
        MonthMetrics("2026-07-01", cash_on_hand=200000, denial_rate_pct=5.0, ar_balance=300000),
        MonthMetrics("2026-08-01", cash_on_hand=200000, denial_rate_pct=5.0, ar_balance=340000),
    ]
    result = evaluate_slipping("370178", months)
    assert result.status == "slipping"
    c = criterion(result, "ar_balance_rising")
    assert c.status == "triggered"
    assert c.values["ar_balance"] == [300000, 340000]


def test_healthy_hospital_with_full_data_is_not_slipping():
    months = [
        MonthMetrics("2026-07-01", cash_on_hand=200000, denial_rate_pct=6.0, ar_balance=310000),
        MonthMetrics("2026-08-01", cash_on_hand=210000, denial_rate_pct=5.0, ar_balance=300000),
    ]
    result = evaluate_slipping("370178", months)
    assert result.status == "not_slipping"
    assert all(c.status == "not_triggered" for c in result.criteria)
    assert result.as_of_month == "2026-08-01"


# --- Missing data: never silently cleared --------------------------------

def test_no_monthly_data_at_all_is_not_assessable():
    result = evaluate_slipping("370178", [])
    assert result.status == "not_assessable"
    assert result.as_of_month is None
    assert all(c.status == "not_assessable" for c in result.criteria)


def test_a_single_month_cannot_assess_any_trend_but_still_sets_as_of_month():
    months = [MonthMetrics("2026-08-01", cash_on_hand=200000, denial_rate_pct=5.0, ar_balance=300000)]
    result = evaluate_slipping("370178", months)
    assert result.status == "not_assessable"
    assert result.as_of_month == "2026-08-01"
    assert all(c.status == "not_assessable" for c in result.criteria)


def test_a_missing_value_in_either_month_is_not_assessable_not_a_false_pass():
    months = [
        MonthMetrics("2026-07-01", cash_on_hand=None, denial_rate_pct=5.0, ar_balance=300000),
        MonthMetrics("2026-08-01", cash_on_hand=150000, denial_rate_pct=5.0, ar_balance=300000),
    ]
    result = evaluate_slipping("370178", months)
    assert criterion(result, "cash_on_hand_declining").status == "not_assessable"


def test_a_real_trigger_wins_over_an_unrelated_missing_metric():
    months = [
        MonthMetrics("2026-07-01", cash_on_hand=None, denial_rate_pct=5.0, ar_balance=300000),
        MonthMetrics("2026-08-01", cash_on_hand=150000, denial_rate_pct=9.0, ar_balance=300000),
    ]
    result = evaluate_slipping("370178", months)
    assert result.status == "slipping"
    assert criterion(result, "cash_on_hand_declining").status == "not_assessable"
    assert criterion(result, "denial_rate_rising").status == "triggered"


# --- Consecutive-months guard: the real gap edge case --------------------

def test_a_gap_between_the_two_latest_months_is_not_assessable_not_silently_compared():
    # June is missing -- comparing May and July across the gap as if
    # adjacent would be dishonest, same reasoning as STORY-004's fiscal
    # year gap guard.
    months = [
        MonthMetrics("2026-05-01", cash_on_hand=250000, denial_rate_pct=5.0, ar_balance=300000),
        MonthMetrics("2026-07-01", cash_on_hand=150000, denial_rate_pct=9.0, ar_balance=340000),
    ]
    result = evaluate_slipping("370178", months)
    assert result.status == "not_assessable"
    c = criterion(result, "cash_on_hand_declining")
    assert c.status == "not_assessable"
    assert c.values["reason"] == "the two latest months are not consecutive calendar months"


def test_consecutive_months_across_a_year_boundary_are_assessable():
    months = [
        MonthMetrics("2026-12-01", cash_on_hand=200000, denial_rate_pct=5.0, ar_balance=300000),
        MonthMetrics("2027-01-01", cash_on_hand=150000, denial_rate_pct=5.0, ar_balance=300000),
    ]
    result = evaluate_slipping("370178", months)
    assert result.status == "slipping"
    assert criterion(result, "cash_on_hand_declining").status == "triggered"


def test_only_the_two_latest_months_are_compared_even_with_longer_history():
    months = [
        MonthMetrics("2026-06-01", cash_on_hand=100000, denial_rate_pct=5.0, ar_balance=300000),
        MonthMetrics("2026-07-01", cash_on_hand=200000, denial_rate_pct=5.0, ar_balance=300000),
        MonthMetrics("2026-08-01", cash_on_hand=150000, denial_rate_pct=5.0, ar_balance=300000),
    ]
    result = evaluate_slipping("370178", months)
    assert result.status == "slipping"
    c = criterion(result, "cash_on_hand_declining")
    assert c.values["cash_on_hand"] == [200000, 150000]


def test_no_change_between_months_is_not_triggered_not_slipping():
    months = [
        MonthMetrics("2026-07-01", cash_on_hand=200000, denial_rate_pct=5.0, ar_balance=300000),
        MonthMetrics("2026-08-01", cash_on_hand=200000, denial_rate_pct=5.0, ar_balance=300000),
    ]
    result = evaluate_slipping("370178", months)
    assert result.status == "not_slipping"
