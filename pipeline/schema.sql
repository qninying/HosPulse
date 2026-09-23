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
    -- source report this row was computed from.
    source_rpt_rec_num       bigint NOT NULL,
    source_file              text NOT NULL,            -- e.g. "HOSP10_2024"
    imported_at              timestamptz NOT NULL DEFAULT now(),

    -- Per-metric provenance: for each of the 5 raw metrics above, the
    -- exact {wksht_cd, line_num, clmn_num} it was read from and a status
    -- of "ok" | "not_reported" (the line wasn't in this report) |
    -- "unparseable" (present but not a valid number). Makes every row
    -- self-describing without needing to trust code elsewhere hasn't
    -- drifted, and turns a bare NULL into a specific, checkable reason.
    metric_provenance        jsonb NOT NULL DEFAULT '{}'::jsonb,

    UNIQUE (provider_ccn, fiscal_year)
);

-- Migration for a table that may already exist from before this column
-- was added (idempotent: a no-op if it's already there).
ALTER TABLE cost_report_years ADD COLUMN IF NOT EXISTS metric_provenance jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_cost_report_years_provider ON cost_report_years(provider_ccn);

ALTER TABLE hospitals ENABLE ROW LEVEL SECURITY;
ALTER TABLE cost_report_years ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "public read" ON hospitals;
CREATE POLICY "public read" ON hospitals FOR SELECT USING (true);

DROP POLICY IF EXISTS "public read" ON cost_report_years;
CREATE POLICY "public read" ON cost_report_years FOR SELECT USING (true);

-- STORY-004: early warning flags, computed from cost_report_years (REQ-004
-- / REQ-005). One row per hospital, replaced (not appended to) each time
-- the evaluator runs -- this is a current-state table, not a history log.
-- Public read, same as the two tables above: this is derived entirely from
-- public CMS data with no management-company-specific scoping yet (that
-- arrives with STORY-006's row-level security, once operator-uploaded data
-- exists to scope).
CREATE TABLE IF NOT EXISTS early_warning_flags (
    provider_ccn      text PRIMARY KEY REFERENCES hospitals(provider_ccn),
    as_of_fiscal_year int,              -- latest fiscal year evaluated; NULL if the hospital has no cost report data at all
    status            text NOT NULL,    -- 'flagged' | 'not_flagged' | 'not_assessable'
    -- Per-criterion results, each with the exact values that produced it
    -- (REQ-005's trust requirement) -- see pipeline/early_warning.py's
    -- CriterionResult.to_json() for the exact shape.
    criteria          jsonb NOT NULL DEFAULT '[]'::jsonb,
    evaluated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_early_warning_flags_status ON early_warning_flags(status);

ALTER TABLE early_warning_flags ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "public read" ON early_warning_flags;
CREATE POLICY "public read" ON early_warning_flags FOR SELECT USING (true);

-- STORY-003: grounded hospitals-at-risk briefings written by Claude Sonnet
-- 5 from early_warning_flags' own output (REQ-006). One row per
-- generation run; UNIQUE(as_of_date) makes re-running the same day
-- idempotent (replaces that day's briefing) instead of accumulating
-- duplicates. facts and provider_ccns are stored alongside body so a
-- saved briefing's grounding can be re-verified later without re-calling
-- Claude. Derived entirely from public CMS-sourced flags, same public-read
-- treatment as early_warning_flags above.
CREATE TABLE IF NOT EXISTS briefings (
    id             bigserial PRIMARY KEY,
    as_of_date     date NOT NULL,
    provider_ccns  jsonb NOT NULL,   -- flagged hospitals this briefing covers
    facts          jsonb NOT NULL,   -- exact engine values Claude was given (REQ-004 audit trail)
    body           text NOT NULL,
    model          text NOT NULL,
    generated_at   timestamptz NOT NULL DEFAULT now(),
    UNIQUE (as_of_date)
);

CREATE INDEX IF NOT EXISTS idx_briefings_as_of_date ON briefings(as_of_date);

ALTER TABLE briefings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "public read" ON briefings;
CREATE POLICY "public read" ON briefings FOR SELECT USING (true);

-- STORY-011: normalize operator-uploaded hospital-system exports (Epic,
-- Cerner, etc.) into standard monthly metrics. Unlike the public CMS
-- tables above, this is a management company's own data -- no upload
-- path exists yet (STORY-005) and no per-company scoping exists yet
-- (STORY-006), so these two tables get RLS enabled with ZERO policies
-- on purpose. This project's "Enable automatic RLS" trigger fails
-- closed for any table with no policies; that's exactly what we want
-- here until STORY-006 adds real per-management-company policies --
-- unlike the CMS tables, there is no "public read" default to restore.

-- One row per file processed -- the Trust criterion's audit entry
-- linking an export to the metrics it produced. Written on every
-- outcome (ok / needs_mapping / failed), never skipped, so "audit
-- entry missing for conversion" can't happen by construction.
CREATE TABLE IF NOT EXISTS export_conversions (
    id                 bigserial PRIMARY KEY,
    source_file        text NOT NULL,
    source_file_hash   text NOT NULL,        -- idempotency key: reprocessing the same file is a no-op
    source_system      text,                 -- NULL when status = 'needs_mapping' (format was never identified)
    status             text NOT NULL,        -- 'ok' | 'needs_mapping' | 'failed'
    metrics_count      int NOT NULL DEFAULT 0,
    error_message      text,                 -- populated only when status = 'failed'
    processed_at       timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source_file_hash)
);

-- One row per (hospital, month, metric). UNIQUE constraint is what makes
-- normalization idempotent: re-running on the same export upserts the
-- same values instead of duplicating rows.
CREATE TABLE IF NOT EXISTS hospital_monthly_metrics (
    id              bigserial PRIMARY KEY,
    provider_ccn    text NOT NULL REFERENCES hospitals(provider_ccn),
    month           date NOT NULL,            -- first-of-month
    metric_name     text NOT NULL,
    metric_value    numeric,
    source_file     text NOT NULL,
    source_row      int,                      -- row index within source_file; NULL if not row-derived
    source_system   text NOT NULL,
    conversion_id   bigint NOT NULL REFERENCES export_conversions(id),
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (provider_ccn, month, metric_name)
);

CREATE INDEX IF NOT EXISTS idx_hospital_monthly_metrics_provider ON hospital_monthly_metrics(provider_ccn);
CREATE INDEX IF NOT EXISTS idx_hospital_monthly_metrics_conversion ON hospital_monthly_metrics(conversion_id);

ALTER TABLE export_conversions ENABLE ROW LEVEL SECURITY;
ALTER TABLE hospital_monthly_metrics ENABLE ROW LEVEL SECURITY;
-- No policies added: fails closed until STORY-006 scopes access by management company.

-- STORY-012: surface slipping hospitals from operator-uploaded monthly
-- metrics (hospital_monthly_metrics, STORY-011), ahead of an operator's
-- own monthly review cycle. Same private-data treatment as STORY-011's
-- tables above, NOT early_warning_flags' public-read policy -- this is
-- derived from private management-company data, not public CMS data.
CREATE TABLE IF NOT EXISTS slipping_hospital_alerts (
    provider_ccn   text PRIMARY KEY REFERENCES hospitals(provider_ccn),
    as_of_month    date,              -- latest month evaluated; NULL if no monthly data exists at all
    status         text NOT NULL,     -- 'slipping' | 'not_slipping' | 'not_assessable'
    -- Per-criterion results, mirroring early_warning_flags.criteria's
    -- shape (REQ-016's "provide details on performance decline" / Trust
    -- criterion) -- see pipeline/slipping_detector.py's
    -- CriterionResult.to_json() for the exact shape.
    criteria       jsonb NOT NULL DEFAULT '[]'::jsonb,
    analyzed_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_slipping_hospital_alerts_status ON slipping_hospital_alerts(status);

ALTER TABLE slipping_hospital_alerts ENABLE ROW LEVEL SECURITY;
-- No policy added: fails closed until STORY-006 scopes access by management company.

-- STORY-006: real per-management-company row-level security. Replaces
-- the fail-closed placeholders above (export_conversions,
-- hospital_monthly_metrics, slipping_hospital_alerts had zero policies)
-- with actual scoping, now that a company/membership/hospital-assignment
-- model exists to scope by.
--
-- anon and authenticated already hold blanket ALL-privilege grants on
-- every table in this schema (Supabase's schema-level default) -- RLS is
-- the only thing restricting them. A FOR SELECT policy below opens reads
-- for a company's own data; INSERT/UPDATE/DELETE remain denied by RLS's
-- default (no policy for a command = deny), so the trusted Python
-- pipeline (which connects as the table owner and bypasses RLS entirely,
-- confirmed live: `postgres` has rolbypassrls=true) stays the only write
-- path -- no change needed there.
--
-- company_members.user_id is a bare uuid, not foreign-keyed to
-- auth.users(id): no real sign-up/sign-in flow exists yet in this repo
-- (deliberately out of this story's scope, confirmed with the user), so
-- there are no real Supabase Auth users to reference yet. Added once a
-- real auth flow creates them.

CREATE TABLE IF NOT EXISTS companies (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name        text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS company_members (
    company_id  uuid NOT NULL REFERENCES companies(id),
    user_id     uuid NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (company_id, user_id)
);

-- Which hospitals a management company manages -- a subset of the
-- public `hospitals` table, not a copy of it. A hospital's public CMS
-- data (hospitals, cost_report_years, early_warning_flags) stays
-- public-read regardless of this table; this only scopes the private
-- operator-uploaded data (below).
CREATE TABLE IF NOT EXISTS company_hospitals (
    company_id    uuid NOT NULL REFERENCES companies(id),
    provider_ccn  text NOT NULL REFERENCES hospitals(provider_ccn),
    created_at    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (company_id, provider_ccn)
);

CREATE INDEX IF NOT EXISTS idx_company_members_user ON company_members(user_id);
CREATE INDEX IF NOT EXISTS idx_company_hospitals_ccn ON company_hospitals(provider_ccn);

ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_hospitals ENABLE ROW LEVEL SECURITY;

-- Self-contained: no dependency on another table's RLS, so this always
-- resolves regardless of policy evaluation order.
DROP POLICY IF EXISTS "see own membership" ON company_members;
CREATE POLICY "see own membership" ON company_members
    FOR SELECT USING (user_id = auth.uid());

-- Depends on company_members' own policy above being evaluable for the
-- querying user -- RLS subqueries run under the querying role's own
-- privileges, so without that policy this would always find zero rows.
DROP POLICY IF EXISTS "see own company" ON companies;
CREATE POLICY "see own company" ON companies
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM company_members cm
            WHERE cm.company_id = companies.id AND cm.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "see own companys hospitals" ON company_hospitals;
CREATE POLICY "see own companys hospitals" ON company_hospitals
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM company_members cm
            WHERE cm.company_id = company_hospitals.company_id AND cm.user_id = auth.uid()
        )
    );

-- export_conversions had no hospital reference at all until now -- an
-- audit row for a 'needs_mapping' file genuinely can't be attributed to
-- a hospital (the format was never even identified), so this stays
-- NULL in that case rather than guessing; export_normalizer.py populates
-- it from the first successfully-mapped row when status = 'ok'.
ALTER TABLE export_conversions ADD COLUMN IF NOT EXISTS provider_ccn text REFERENCES hospitals(provider_ccn);
CREATE INDEX IF NOT EXISTS idx_export_conversions_provider ON export_conversions(provider_ccn);

DROP POLICY IF EXISTS "company scoped read" ON export_conversions;
CREATE POLICY "company scoped read" ON export_conversions
    FOR SELECT USING (
        provider_ccn IS NOT NULL AND EXISTS (
            SELECT 1 FROM company_hospitals ch
            JOIN company_members cm ON cm.company_id = ch.company_id
            WHERE ch.provider_ccn = export_conversions.provider_ccn
              AND cm.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "company scoped read" ON hospital_monthly_metrics;
CREATE POLICY "company scoped read" ON hospital_monthly_metrics
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM company_hospitals ch
            JOIN company_members cm ON cm.company_id = ch.company_id
            WHERE ch.provider_ccn = hospital_monthly_metrics.provider_ccn
              AND cm.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "company scoped read" ON slipping_hospital_alerts;
CREATE POLICY "company scoped read" ON slipping_hospital_alerts
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM company_hospitals ch
            JOIN company_members cm ON cm.company_id = ch.company_id
            WHERE ch.provider_ccn = slipping_hospital_alerts.provider_ccn
              AND cm.user_id = auth.uid()
        )
    );
