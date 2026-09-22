"""Tests for pipeline/hcris_import.py's pure logic (no network, no database).

Run: cd HosPulse && ./.venv/bin/python -m pytest pipeline/test_hcris_import.py -v
"""

import zipfile

import pytest

from hcris_import import (
    HcrisFormatError,
    HospitalYear,
    _dedupe_by_provider,
    dedupe_by_provider_year,
    extract_source_files,
    fiscal_year_of,
    state_for_ccn,
)


def make(ccn="370245", fiscal_year=2024, rpt=1, fy_end="06/30/2024"):
    return HospitalYear(
        provider_ccn=ccn, state="OK", name="Test Hospital", rural_or_cah=True,
        fiscal_year=fiscal_year, fy_begin_date="07/01/2023", fy_end_date=fy_end,
        cash_on_hand=100.0, accounts_receivable_net=200.0, net_patient_revenue=1000.0,
        total_operating_expense=900.0, net_income_from_patients=100.0,
        source_rpt_rec_num=rpt, source_file="HOSP10_2024",
    )


# -- state_for_ccn: this is the entire OK/TX filter, so every prefix
# claimed in STATE_CCN_PREFIXES must actually be tested, not assumed.

def test_every_oklahoma_prefix_resolves_to_ok():
    for ccn in ("370001", "900001"):
        assert state_for_ccn(ccn) == "OK"


def test_every_texas_prefix_resolves_to_tx():
    for ccn in ("450001", "670001", "740001", "970001", "A90001"):
        assert state_for_ccn(ccn) == "TX"


def test_a_different_states_prefix_is_not_misclassified():
    assert state_for_ccn("050001") is None  # California
    assert state_for_ccn("140001") is None  # Illinois


# -- fiscal_year_of: this is what fixed the real bug (a report ending in
# 2025 was being mislabeled 2024 because that's the CMS download bucket).

def test_fiscal_year_comes_from_the_reports_own_end_date_not_the_download_bucket():
    assert fiscal_year_of("06/30/2025", fallback=2024) == 2025


def test_fiscal_year_falls_back_when_date_is_missing():
    assert fiscal_year_of(None, fallback=2024) == 2024


def test_fiscal_year_falls_back_when_date_is_malformed():
    assert fiscal_year_of("not-a-date", fallback=2024) == 2024
    assert fiscal_year_of("06/30", fallback=2024) == 2024


# -- dedupe_by_provider_year: the deterministic tie-break that replaced
# the original bug (an unordered upsert batch picking an arbitrary row).

def test_two_reports_with_different_real_fiscal_years_are_both_kept():
    # This is the actual real-world case found in FY2024's file: a short
    # transition-period report ending in 2024, and a full-year report for
    # the same hospital ending in 2025 -- both real, both belong.
    rows = [make(fiscal_year=2024, rpt=795252, fy_end="06/30/2024"),
            make(fiscal_year=2025, rpt=829825, fy_end="06/30/2025")]
    result = dedupe_by_provider_year(rows)
    assert {(r.fiscal_year, r.source_rpt_rec_num) for r in result} == {(2024, 795252), (2025, 829825)}


def test_two_reports_for_the_same_real_fiscal_year_keep_only_the_higher_rpt_rec_num():
    rows = [make(fiscal_year=2024, rpt=100), make(fiscal_year=2024, rpt=200)]
    result = dedupe_by_provider_year(rows)
    assert len(result) == 1
    assert result[0].source_rpt_rec_num == 200


def test_tie_break_choice_does_not_depend_on_input_order():
    forward = dedupe_by_provider_year([make(fiscal_year=2024, rpt=100), make(fiscal_year=2024, rpt=200)])
    backward = dedupe_by_provider_year([make(fiscal_year=2024, rpt=200), make(fiscal_year=2024, rpt=100)])
    assert forward[0].source_rpt_rec_num == backward[0].source_rpt_rec_num == 200


def test_different_hospitals_never_collide_with_each_other():
    rows = [make(ccn="370245", fiscal_year=2024, rpt=1), make(ccn="450001", fiscal_year=2024, rpt=2)]
    result = dedupe_by_provider_year(rows)
    assert len(result) == 2


# -- STORY-001's explicit failure-path acceptance criterion: "Given invalid
# data format, When the import process runs, Then the data is rejected
# with an error message." A zip missing the expected *_rpt/_nmrc/_alpha
# files (CMS changed the layout, or the file is corrupt) is exactly that.

def test_a_zip_missing_the_expected_files_is_rejected_with_a_clear_error(tmp_path):
    bad_zip = tmp_path / "HOSP10FY2099.ZIP"
    with zipfile.ZipFile(bad_zip, "w") as zf:
        zf.writestr("some_unexpected_file.txt", "not a cost report")

    with pytest.raises(HcrisFormatError, match="_rpt.csv"):
        extract_source_files(bad_zip, fiscal_year=2099)


# -- _dedupe_by_provider: the hospitals table is keyed on provider_ccn
# alone, so a batch containing the same hospital across two real fiscal
# years (a real, already-verified scenario) must still collapse to one
# row per hospital here, or a single-statement upsert crashes with a
# Postgres "ON CONFLICT DO UPDATE command cannot affect row a second time"
# error -- this is exactly the real bug that surfaced when importing FY2025.

def test_same_hospital_across_two_fiscal_years_collapses_to_one_row():
    rows = [make(fiscal_year=2024, rpt=1), make(fiscal_year=2025, rpt=2)]
    result = _dedupe_by_provider(rows)
    assert len(result) == 1
    assert result[0].fiscal_year == 2025  # the more recent year wins


def test_dedupe_by_provider_is_a_true_no_op_for_already_unique_providers():
    rows = [make(ccn="370245", fiscal_year=2024, rpt=1), make(ccn="450001", fiscal_year=2024, rpt=2)]
    result = _dedupe_by_provider(rows)
    assert len(result) == 2


def test_a_well_formed_zip_is_accepted(tmp_path):
    good_zip = tmp_path / "HOSP10FY2099.ZIP"
    with zipfile.ZipFile(good_zip, "w") as zf:
        zf.writestr("HOSP10_2099_RPT.csv", "1,2,3\n")
        zf.writestr("HOSP10_2099_NMRC.csv", "1,A000000,00100,00100,500\n")
        zf.writestr("HOSP10_2099_ALPHA.csv", "1,S200001,00300,00100,TEST\n")

    files = extract_source_files(good_zip, fiscal_year=2099)
    assert files["rpt"].exists() and files["nmrc"].exists() and files["alpha"].exists()
