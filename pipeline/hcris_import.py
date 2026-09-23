"""STORY-001: import CMS HCRIS Hospital cost reports (Form 2552-10) for
rural and Critical Access Hospitals in Oklahoma and Texas, and compute
operating margin, days cash on hand, and days in A/R per hospital per year.

Every worksheet/line/column reference below is cited against the CMS
"Hospital Provider Cost Report Data Dictionary" and confirmed empirically
against a real downloaded file (RPT_REC_NUM 795252, an Oklahoma hospital)
before this was written -- see PROGRESS.md for the verification record.
Nothing here is guessed.

File format (CMS HCRIS flat files, no header row):
  <name>_rpt.csv   one row per cost report:   RPT_REC_NUM, PRVDR_CTRL_TYPE_CD,
                   PRVDR_NUM, NPI, RPT_STUS_CD, FY_BGN_DT, FY_END_DT, PROC_DT,
                   INITL_RPT_SW, LAST_RPT_SW, TRNSMTL_NUM, FI_NUM, ADR_VNDR_CD,
                   FI_CREAT_DT, UTIL_CD, NPR_DT, SPEC_IND, FI_RCPT_DT
  <name>_nmrc.csv  numeric worksheet values:   RPT_REC_NUM, WKSHT_CD, LINE_NUM,
                   CLMN_NUM, ITM_VAL_NUM
  <name>_alpha.csv alphanumeric worksheet values, same 4 key columns + text

Usage: python3 hcris_import.py --fiscal-year 2024
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlretrieve

import duckdb
import psycopg2
import psycopg2.extras

from env import load_env
from pipeline_run_log import finish_pipeline_run, start_pipeline_run

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
DOWNLOAD_URL = "https://downloads.cms.gov/FILES/HCRIS/HOSP10FY{year}.ZIP"
DOWNLOAD_TIMEOUT_SECONDS = 120
DOWNLOAD_MAX_ATTEMPTS = 3

# CMS Certification Number state prefixes (Medicare State Code Listing).
# A CCN's first 2-3 characters identify the state; everything after that
# identifies the facility within the state. Multiple prefixes per state
# exist because the original 2-digit numeric codes ran out.
STATE_CCN_PREFIXES: dict[str, list[str]] = {
    "OK": ["37", "90"],
    "TX": ["45", "67", "74", "97", "A9"],
}

# Every worksheet/line/column this importer reads, in one place, each with
# where it came from. WKSHT_CD/LINE_NUM/CLMN_NUM follow the standard HCRIS
# convention (line number x100, column number x100, zero-padded to 5
# digits) confirmed against the real file's own values.
#
# Source: CMS Hospital Provider Cost Report Data Dictionary (data.cms.gov),
# cross-checked against RPT_REC_NUM 795252 (an Oklahoma rural hospital) in
# HOSP10_2024_nmrc.csv, which returned plausible, internally consistent
# values for every field below.
NUMERIC_FIELDS = {
    "cash_on_hand": ("G000000", "00100", "00100"),               # Worksheet G, Line 1, Col 1: Cash on Hand and in Banks
    "accounts_receivable": ("G000000", "00400", "00100"),        # Worksheet G, Line 4, Col 1: Accounts Receivable
    "ar_allowance": ("G000000", "00600", "00100"),                # Worksheet G, Line 6, Col 1: Allowance for uncollectibles (entered as negative)
    "net_patient_revenue": ("G300000", "00300", "00100"),        # Worksheet G-3, Line 3, Col 1: Net Patient Revenue
    "total_operating_expense": ("G300000", "00400", "00100"),    # Worksheet G-3, Line 4, Col 1: Total Operating Expense
    "net_income_from_patients": ("G300000", "00500", "00100"),   # Worksheet G-3, Line 5, Col 1: Net Income from Service to Patients
    "rural_or_urban": ("S200001", "02600", "00100"),              # Worksheet S-2 Part I, Line 26, Col 1: 1=urban, 2=rural
}
ALPHA_FIELDS = {
    "hospital_name": ("S200001", "00300", "00100"),               # Worksheet S-2 Part I, Line 3, Col 1: Hospital Name
}

# Maps each stored cost_report_years column to the NUMERIC_FIELDS key that
# is its provenance source. accounts_receivable_net is derived from two
# lines (accounts_receivable minus the allowance); the allowance being
# absent is treated as a legitimate zero (not every hospital reports one),
# so provenance for the net figure follows the primary line only.
PROVENANCE_FIELDS = {
    "cash_on_hand": "cash_on_hand",
    "accounts_receivable_net": "accounts_receivable",
    "net_patient_revenue": "net_patient_revenue",
    "total_operating_expense": "total_operating_expense",
    "net_income_from_patients": "net_income_from_patients",
}


class HcrisFormatError(Exception):
    """Raised when a downloaded HCRIS file doesn't have the structure this
    importer expects (STORY-001 failure path: data format mismatch)."""


class HcrisDownloadError(Exception):
    """Raised when the CMS file can't be fetched after all retries
    (STORY-001 failure path: network failure during import)."""


def state_for_ccn(ccn: str) -> str | None:
    for state, prefixes in STATE_CCN_PREFIXES.items():
        for p in prefixes:
            if ccn.startswith(p):
                return state
    return None


def download_hcris_zip(fiscal_year: int, dest_dir: Path = RAW_DIR) -> Path:
    """Download HOSP10FY{year}.ZIP, with a timeout and capped retries.
    Idempotent: if the file already exists at the expected path, skip the
    download and reuse it rather than re-fetching. Crash-safe resume: the
    download lands in a .part file first and is only renamed into the
    final path on success, so a process killed mid-download leaves a
    stale .part behind that the exists() check above never trusts -- a
    resumed run re-downloads cleanly instead of treating a partial file
    as complete."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / f"HOSP10FY{fiscal_year}.ZIP"
    if zip_path.exists() and zip_path.stat().st_size > 0:
        return zip_path

    url = DOWNLOAD_URL.format(year=fiscal_year)
    last_error: Exception | None = None
    for attempt in range(1, DOWNLOAD_MAX_ATTEMPTS + 1):
        try:
            tmp_path = zip_path.with_suffix(".part")
            urlretrieve(url, tmp_path)  # nosec B310 - fixed cms.gov URL, not user input
            tmp_path.rename(zip_path)
            return zip_path
        except (URLError, OSError, TimeoutError) as exc:
            last_error = exc
            if attempt < DOWNLOAD_MAX_ATTEMPTS:
                time.sleep(2**attempt)  # capped exponential backoff: 2s, 4s
    raise HcrisDownloadError(
        f"could not download {url} after {DOWNLOAD_MAX_ATTEMPTS} attempts: {last_error}"
    )


def extract_source_files(zip_path: Path, fiscal_year: int) -> dict[str, Path]:
    import zipfile

    out_dir = zip_path.parent
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        zf.extractall(out_dir)

    files = {}
    for kind in ("rpt", "nmrc", "alpha"):
        matches = [n for n in names if n.lower().endswith(f"_{kind}.csv")]
        if not matches:
            raise HcrisFormatError(
                f"HOSP10FY{fiscal_year}.ZIP has no *_{kind}.csv file -- "
                f"CMS may have changed the file layout. Found: {names}"
            )
        files[kind] = out_dir / matches[0]
    return files


def fiscal_year_of(fy_end_dt: str | None, fallback: int) -> int:
    """The report's OWN fiscal year, from its fy_end_dt (MM/DD/YYYY) --
    NOT the CMS download bucket's year. CMS's HOSP10FY{year}.ZIP groups
    reports by when CMS processed them, not by each report's own period
    end; a report ending 06/30/2025 can show up inside the FY2024 file.
    Falls back to the download's year only if the date is missing/malformed."""
    if fy_end_dt:
        parts = fy_end_dt.split("/")
        if len(parts) == 3 and parts[2].isdigit():
            return int(parts[2])
    return fallback


@dataclass
class HospitalYear:
    provider_ccn: str
    state: str
    name: str | None
    rural_or_cah: bool | None
    fiscal_year: int
    fy_begin_date: str | None
    fy_end_date: str | None
    cash_on_hand: float | None
    accounts_receivable_net: float | None
    net_patient_revenue: float | None
    total_operating_expense: float | None
    net_income_from_patients: float | None
    source_rpt_rec_num: int
    source_file: str
    metric_provenance: dict = field(default_factory=dict)


def extract_metrics(files: dict[str, Path], fiscal_year: int) -> list[HospitalYear]:
    """Read the raw flat files with DuckDB, filter to OK/TX rural and CAH
    hospitals, and compute the metric set for each. Every value defaults
    to None (never a guessed 0) unless the source line was actually
    present in the file. Malformed numeric strings TRY_CAST to NULL rather
    than raising, since one bad row must not fail the whole import."""
    con = duckdb.connect()

    def read_kv(path: Path, value_type: str):
        return con.sql(
            f"""
            SELECT rpt_rec_num, wksht_cd, line_num, clmn_num, item_val
            FROM read_csv(
                '{path.as_posix()}', header=false, delim=',',
                columns={{'rpt_rec_num':'BIGINT','wksht_cd':'VARCHAR','line_num':'VARCHAR',
                          'clmn_num':'VARCHAR','item_val':'{value_type}'}}
            )
            """
        )

    nmrc = read_kv(files["nmrc"], "VARCHAR")  # VARCHAR first: TRY_CAST below, never a hard failure on a bad row
    alpha = read_kv(files["alpha"], "VARCHAR")

    rpt = con.sql(
        f"""
        SELECT rpt_rec_num, prvdr_num, fy_bgn_dt, fy_end_dt
        FROM read_csv(
            '{files["rpt"].as_posix()}', header=false, delim=',',
            columns={{'rpt_rec_num':'BIGINT','prvdr_ctrl_type_cd':'VARCHAR','prvdr_num':'VARCHAR',
                      'npi':'VARCHAR','rpt_stus_cd':'VARCHAR','fy_bgn_dt':'VARCHAR','fy_end_dt':'VARCHAR',
                      'proc_dt':'VARCHAR','initl_rpt_sw':'VARCHAR','last_rpt_sw':'VARCHAR',
                      'trnsmtl_num':'VARCHAR','fi_num':'VARCHAR','adr_vndr_cd':'VARCHAR',
                      'fi_creat_dt':'VARCHAR','util_cd':'VARCHAR','npr_dt':'VARCHAR',
                      'spec_ind':'VARCHAR','fi_rcpt_dt':'VARCHAR'}}
        )
        """
    )

    def pivot(view_name: str, out_table: str, fields: dict[str, tuple[str, str, str]], numeric: bool):
        cast = "TRY_CAST(item_val AS DOUBLE)" if numeric else "item_val"
        parts = []
        for name, (w, l, c) in fields.items():
            when = f"wksht_cd='{w}' AND line_num='{l}' AND clmn_num='{c}'"
            parts.append(f"MAX(CASE WHEN {when} THEN {cast} END) AS {name}")
            if numeric:
                # Distinguishes "line absent from this report" from "line
                # present but failed to parse" -- both look like NULL in
                # the value column above, but they're different situations
                # (metric_provenance's status field needs to tell them apart).
                parts.append(f"MAX(CASE WHEN {when} THEN 1 ELSE 0 END) AS {name}__found")
        selects = ", ".join(parts)
        # CREATE TABLE AS forces immediate execution into a real DuckDB
        # table, not a lazy relation. A lazy relation built against a
        # registered Python-object view resolves that view's name at
        # EXECUTION time, not when the relation is built -- re-registering
        # the same name for a second pivot silently made an earlier,
        # not-yet-fetched query read the wrong source. This sidesteps that
        # entirely, with no extra dependency (no pyarrow/pandas needed).
        con.execute(f"CREATE OR REPLACE TEMP TABLE {out_table} AS "
                    f"SELECT rpt_rec_num, {selects} FROM {view_name} GROUP BY rpt_rec_num")

    con.register("nmrc_kv", nmrc)
    con.register("alpha_kv", alpha)
    pivot("nmrc_kv", "numeric_pivot", NUMERIC_FIELDS, numeric=True)
    pivot("alpha_kv", "alpha_pivot", ALPHA_FIELDS, numeric=False)

    con.register("rpt_view", rpt)
    found_cols = ", ".join(f"n.{name}__found" for name in NUMERIC_FIELDS)
    joined = con.sql(
        f"""
        SELECT r.rpt_rec_num, r.prvdr_num, r.fy_bgn_dt, r.fy_end_dt,
               n.cash_on_hand, n.accounts_receivable, n.ar_allowance,
               n.net_patient_revenue, n.total_operating_expense,
               n.net_income_from_patients, n.rural_or_urban,
               a.hospital_name, {found_cols}
        FROM rpt_view r
        JOIN numeric_pivot n USING (rpt_rec_num)
        LEFT JOIN alpha_pivot a USING (rpt_rec_num)
        """
    ).fetchall()
    found_index = {name: 12 + i for i, name in enumerate(NUMERIC_FIELDS)}  # column order matches found_cols above

    results: list[HospitalYear] = []
    for row in joined:
        rec, ccn, fy_bgn, fy_end, cash, ar, ar_allow, npr, toe, nifp, rural, name = row[:12]
        state = state_for_ccn(ccn)
        if state is None:
            continue  # not OK/TX, out of scope for this importer
        if rural != 2:
            continue  # not rural (S-2 Part I Line 26 Col 1: 1=urban, 2=rural); CAHs are rural by definition

        ar_net = None
        if ar is not None:
            ar_net = ar + (ar_allow or 0)  # allowance is stored as a negative value on Worksheet G

        values = {
            "cash_on_hand": cash, "accounts_receivable_net": ar,  # provenance status follows the raw line, not the derived net
            "net_patient_revenue": npr, "total_operating_expense": toe, "net_income_from_patients": nifp,
        }
        provenance = {}
        for db_column, source_key in PROVENANCE_FIELDS.items():
            wksht, line, clmn = NUMERIC_FIELDS[source_key]
            found = row[found_index[source_key]]
            value = values[db_column]
            status = "ok" if value is not None else ("not_reported" if not found else "unparseable")
            provenance[db_column] = {"wksht_cd": wksht, "line_num": line, "clmn_num": clmn, "status": status}

        results.append(
            HospitalYear(
                provider_ccn=ccn,
                state=state,
                name=name,
                rural_or_cah=True,
                fiscal_year=fiscal_year_of(fy_end, fallback=fiscal_year),
                fy_begin_date=fy_bgn,
                fy_end_date=fy_end,
                cash_on_hand=cash,
                accounts_receivable_net=ar_net,
                net_patient_revenue=npr,
                total_operating_expense=toe,
                net_income_from_patients=nifp,
                source_rpt_rec_num=rec,
                source_file=f"HOSP10_{fiscal_year}",
                metric_provenance=provenance,
            )
        )
    return dedupe_by_provider_year(results)


def dedupe_by_provider_year(results: list[HospitalYear]) -> list[HospitalYear]:
    """A provider can legitimately file two reports whose OWN fiscal years
    still coincide (e.g. an original plus an amended resubmission covering
    the same period, or two short transitional periods both ending in the
    same calendar year). Deterministic tie-break so a re-run always makes
    the same choice: a higher RPT_REC_NUM was received later by CMS, so
    prefer it. This must be deterministic -- "no duplicates" alone isn't
    enough for idempotency if which row survives could vary between runs."""
    best_by_key: dict[tuple[str, int], HospitalYear] = {}
    for row in results:
        key = (row.provider_ccn, row.fiscal_year)
        current = best_by_key.get(key)
        if current is None or row.source_rpt_rec_num > current.source_rpt_rec_num:
            best_by_key[key] = row
    return list(best_by_key.values())




def _dedupe_by_provider(rows: list[HospitalYear]) -> list[HospitalYear]:
    """The `hospitals` table is keyed on provider_ccn alone, unlike
    `cost_report_years` (provider_ccn + fiscal_year), so a batch that
    legitimately has one hospital across two real fiscal years still needs
    exactly one row per hospital here. Prefers the highest fiscal_year,
    tie-broken by the highest source_rpt_rec_num -- the most current
    identity (name, rural status) available in this batch."""
    best: dict[str, HospitalYear] = {}
    for row in rows:
        current = best.get(row.provider_ccn)
        if current is None or (row.fiscal_year, row.source_rpt_rec_num) > (current.fiscal_year, current.source_rpt_rec_num):
            best[row.provider_ccn] = row
    return list(best.values())


def upsert(rows: list[HospitalYear], database_url: str) -> None:
    """Idempotent load: ON CONFLICT DO UPDATE on the same natural keys
    used by the table's constraints, so importing the same file twice
    leaves the same data with no duplicates (REQ-007 / REQ-015)."""
    if not rows:
        return
    conn = psycopg2.connect(database_url, connect_timeout=10)
    try:
        with conn, conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO hospitals (provider_ccn, state, name, rural_or_cah)
                VALUES %s
                ON CONFLICT (provider_ccn) DO UPDATE SET
                    state = EXCLUDED.state,
                    name = COALESCE(EXCLUDED.name, hospitals.name),
                    rural_or_cah = EXCLUDED.rural_or_cah,
                    updated_at = now()
                """,
                # `rows` is deduped per (provider, fiscal_year), not per
                # provider alone -- the same hospital legitimately appears
                # twice in one batch when it has two real fiscal years in
                # this file (the split-year pattern found earlier). A
                # single INSERT...ON CONFLICT statement can't target the
                # same conflict key twice, so dedupe again here, keyed on
                # provider_ccn only, preferring the most recent fiscal year.
                [
                    (r.provider_ccn, r.state, r.name, r.rural_or_cah)
                    for r in _dedupe_by_provider(rows)
                ],
            )
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO cost_report_years (
                    provider_ccn, fiscal_year, fy_begin_date, fy_end_date,
                    cash_on_hand, accounts_receivable_net, net_patient_revenue,
                    total_operating_expense, net_income_from_patients,
                    source_rpt_rec_num, source_file, metric_provenance
                ) VALUES %s
                ON CONFLICT (provider_ccn, fiscal_year) DO UPDATE SET
                    fy_begin_date = EXCLUDED.fy_begin_date,
                    fy_end_date = EXCLUDED.fy_end_date,
                    cash_on_hand = EXCLUDED.cash_on_hand,
                    accounts_receivable_net = EXCLUDED.accounts_receivable_net,
                    net_patient_revenue = EXCLUDED.net_patient_revenue,
                    total_operating_expense = EXCLUDED.total_operating_expense,
                    net_income_from_patients = EXCLUDED.net_income_from_patients,
                    source_rpt_rec_num = EXCLUDED.source_rpt_rec_num,
                    source_file = EXCLUDED.source_file,
                    metric_provenance = EXCLUDED.metric_provenance,
                    imported_at = now()
                -- Order-independent across separate runs, not just within
                -- one: dedupe_by_provider_year() only protects duplicates
                -- found inside a single run's own batch. Without this
                -- guard, re-running an older fiscal-year file after a
                -- newer one already supplied a better record for the same
                -- (provider, year) would silently regress that row back
                -- to the older report. A higher RPT_REC_NUM was always
                -- received later by CMS, so only ever move forward.
                WHERE EXCLUDED.source_rpt_rec_num >= cost_report_years.source_rpt_rec_num
                """,
                [
                    (
                        r.provider_ccn, r.fiscal_year, r.fy_begin_date, r.fy_end_date,
                        r.cash_on_hand, r.accounts_receivable_net, r.net_patient_revenue,
                        r.total_operating_expense, r.net_income_from_patients,
                        r.source_rpt_rec_num, r.source_file,
                        psycopg2.extras.Json(r.metric_provenance),
                    )
                    for r in rows
                ],
            )
    finally:
        conn.close()


def run(fiscal_year: int) -> list[HospitalYear]:
    load_env(ROOT / ".env")
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set -- check .env")

    run_id = start_pipeline_run("hcris_import", database_url, run_key=str(fiscal_year))
    try:
        zip_path = download_hcris_zip(fiscal_year)
        files = extract_source_files(zip_path, fiscal_year)
        rows = extract_metrics(files, fiscal_year)
        upsert(rows, database_url)
    except Exception as exc:
        finish_pipeline_run(run_id, "failed", database_url, error_message=str(exc))
        raise
    finish_pipeline_run(run_id, "succeeded", database_url, rows_affected=len(rows))
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fiscal-year", type=int, required=True)
    args = parser.parse_args()
    try:
        imported = run(args.fiscal_year)
    except (HcrisDownloadError, HcrisFormatError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"imported {len(imported)} OK/TX rural or Critical Access Hospital cost reports for FY{args.fiscal_year}")
