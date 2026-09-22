-- HosPulse: public HCRIS data schema (STORY-001 / STORY-002).
--
-- These two tables hold ONLY public CMS cost report data -- no patient
-- data, no customer data. They are meant to be read by anyone via the
-- free Health Snapshot, so the RLS policies below explicitly allow public
-- SELECT (this project's "Enable automatic RLS" trigger turns RLS on for
-- every new table with zero policies, which fails closed by design --
-- these policies are what open read access back up, on purpose, for
-- exactly these two public-data tables).
--
-- Idempotent: safe to run this file more than once (IF NOT EXISTS / DROP
-- POLICY IF EXISTS before CREATE).

CREATE TABLE IF NOT EXISTS hospitals (
    provider_ccn        text PRIMARY KEY,        -- 6-char CMS Certification Number
    state                text NOT NULL,            -- 2-letter, derived from the CCN's state prefix
    name                 text,                     -- from Worksheet S-2 Part I, Line 3, Column 1 (alpha file); NULL if not yet resolved
    rural_or_cah         boolean,                  -- Worksheet S-2 Part I, Line 26, Column 1 (1=urban, 2=rural); NULL if unknown
    created_at           timestamptz NOT NULL DEFAULT now(),
    updated_at           timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cost_report_years (
    id                       bigserial PRIMARY KEY,
    provider_ccn             text NOT NULL REFERENCES hospitals(provider_ccn),
    fiscal_year              int NOT NULL,             -- calendar year of FY_END_DT
    fy_begin_date            date,
    fy_end_date              date,

    cash_on_hand             numeric,                  -- Worksheet G, Line 1, Column 1
    accounts_receivable_net  numeric,                  -- Worksheet G, Line 4 + Line 6 (allowance, stored negative), Column 1
    net_patient_revenue      numeric,                  -- Worksheet G-3, Line 3, Column 1
    total_operating_expense  numeric,                  -- Worksheet G-3, Line 4, Column 1
    net_income_from_patients numeric,                  -- Worksheet G-3, Line 5, Column 1

    -- Generated, not stored input: derived only from the raw values above,
    -- so a re-derivation always matches. NULL whenever an input is NULL
    -- (missing data is missing, never treated as zero -- REQ-005's
    -- "not assessable" rule).
    operating_margin_pct     numeric GENERATED ALWAYS AS (
        CASE WHEN net_patient_revenue IS NULL OR net_patient_revenue = 0 THEN NULL
             ELSE round(100 * net_income_from_patients / net_patient_revenue, 2) END
    ) STORED,
    days_cash_on_hand        numeric GENERATED ALWAYS AS (
        CASE WHEN total_operating_expense IS NULL OR total_operating_expense = 0 THEN NULL
             ELSE round(cash_on_hand / (total_operating_expense / 365.0), 1) END
    ) STORED,
    days_in_ar                numeric GENERATED ALWAYS AS (
        CASE WHEN net_patient_revenue IS NULL OR net_patient_revenue = 0 THEN NULL
             ELSE round(accounts_receivable_net / (net_patient_revenue / 365.0), 1) END
    ) STORED,

    -- Traceability (REQ-013 / STORY-001's Trust criterion): the exact
    -- source report and file this row was computed from. The specific
    -- WKSHT_CD/LINE_NUM/CLMN_NUM per field is fixed and documented in
    -- pipeline/hcris_import.py's METRICS dict, not duplicated per row.
    source_rpt_rec_num       bigint NOT NULL,
    source_file              text NOT NULL,            -- e.g. "HOSP10_2024"
    imported_at              timestamptz NOT NULL DEFAULT now(),

    UNIQUE (provider_ccn, fiscal_year)
);

CREATE INDEX IF NOT EXISTS idx_cost_report_years_provider ON cost_report_years(provider_ccn);

ALTER TABLE hospitals ENABLE ROW LEVEL SECURITY;
ALTER TABLE cost_report_years ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "public read" ON hospitals;
CREATE POLICY "public read" ON hospitals FOR SELECT USING (true);

DROP POLICY IF EXISTS "public read" ON cost_report_years;
CREATE POLICY "public read" ON cost_report_years FOR SELECT USING (true);
