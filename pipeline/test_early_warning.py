from early_warning import YearMetrics, evaluate_early_warning_flags


def criterion(evaluation, name):
    return next(c for c in evaluation.criteria if c.name == name)


# --- Happy path: each criterion can genuinely trigger -----------------

def test_negative_operating_margin_flags_the_hospital():
    years = [YearMetrics(2025, operating_margin_pct=-5.0, days_cash_on_hand=100, days_in_ar=40)]
    result = evaluate_early_warning_flags("123456", years)
    assert result.status == "flagged"
    c = criterion(result, "operating_margin_negative")
    assert c.status == "triggered"
    assert c.values["operating_margin_pct"] == -5.0


def test_low_days_cash_on_hand_flags_the_hospital():
    years = [YearMetrics(2025, operating_margin_pct=5.0, days_cash_on_hand=10, days_in_ar=40)]
    result = evaluate_early_warning_flags("123456", years)
    assert result.status == "flagged"
    c = criterion(result, "days_cash_on_hand_low")
    assert c.status == "triggered"
    assert c.values["days_cash_on_hand"] == 10


def test_days_in_ar_rising_two_years_in_a_row_flags_the_hospital():
    years = [
        YearMetrics(2023, 5.0, 100, 30),
        YearMetrics(2024, 5.0, 100, 35),
        YearMetrics(2025, 5.0, 100, 41),
    ]
    result = evaluate_early_warning_flags("123456", years)
    assert result.status == "flagged"
    c = criterion(result, "days_in_ar_rising_two_years")
    assert c.status == "triggered"
    assert c.values["days_in_ar"] == [30, 35, 41]


def test_healthy_hospital_with_full_data_is_not_flagged():
    years = [
        YearMetrics(2023, 3.0, 60, 40),
        YearMetrics(2024, 2.0, 55, 38),  # days_in_ar actually falling
        YearMetrics(2025, 4.0, 50, 36),
    ]
    result = evaluate_early_warning_flags("123456", years)
    assert result.status == "not_flagged"
    assert all(c.status == "not_triggered" for c in result.criteria)


# --- Missing data: never silently cleared ------------------------------

def test_missing_metrics_mark_the_hospital_not_assessable_not_healthy():
    years = [YearMetrics(2025, operating_margin_pct=None, days_cash_on_hand=None, days_in_ar=None)]
    result = evaluate_early_warning_flags("123456", years)
    assert result.status == "not_assessable"
    assert criterion(result, "operating_margin_negative").status == "not_assessable"
    assert criterion(result, "days_cash_on_hand_low").status == "not_assessable"


def test_no_cost_report_data_at_all_is_not_assessable():
    result = evaluate_early_warning_flags("123456", [])
    assert result.status == "not_assessable"
    assert result.as_of_fiscal_year is None
    assert all(c.status == "not_assessable" for c in result.criteria)


def test_a_real_trigger_wins_over_a_missing_metric_elsewhere():
    # operating margin is missing, but days cash on hand alone is enough
    # to flag -- a genuine problem must not be hidden by an unrelated gap.
    years = [YearMetrics(2025, operating_margin_pct=None, days_cash_on_hand=5, days_in_ar=40)]
    result = evaluate_early_warning_flags("123456", years)
    assert result.status == "flagged"
    assert criterion(result, "operating_margin_negative").status == "not_assessable"
    assert criterion(result, "days_cash_on_hand_low").status == "triggered"


# --- Days-in-AR trend: the real gap-year edge case ---------------------

def test_fewer_than_three_years_cannot_assess_the_rising_ar_trend():
    years = [
        YearMetrics(2024, 5.0, 100, 92),
        YearMetrics(2025, 5.0, 100, 141),
    ]
    result = evaluate_early_warning_flags("670781", years)
    c = criterion(result, "days_in_ar_rising_two_years")
    assert c.status == "not_assessable"
    # the other two criteria are still assessable with just the latest year
    assert criterion(result, "operating_margin_negative").status == "not_triggered"


def test_a_real_reporting_gap_is_not_assessable_not_silently_compared():
    # FY2023 is missing (a real pattern in this dataset) -- comparing
    # FY2022 and FY2024 across the gap as if adjacent would be dishonest.
    years = [
        YearMetrics(2022, 5.0, 100, 30),
        YearMetrics(2024, 5.0, 100, 90),
        YearMetrics(2025, 5.0, 100, 95),
    ]
    result = evaluate_early_warning_flags("123456", years)
    c = criterion(result, "days_in_ar_rising_two_years")
    assert c.status == "not_assessable"
    assert c.values["reason"] == "fiscal years are not consecutive"


def test_days_in_ar_falling_is_not_triggered_not_missing():
    years = [
        YearMetrics(2023, 5.0, 100, 50),
        YearMetrics(2024, 5.0, 100, 45),
        YearMetrics(2025, 5.0, 100, 40),
    ]
    result = evaluate_early_warning_flags("123456", years)
    c = criterion(result, "days_in_ar_rising_two_years")
    assert c.status == "not_triggered"
