-- 01_load_raw.sql
-- Step 1: load every CSV into the "raw" schema exactly as exported.
-- Every column is text on purpose: raw = "what the system gave us", no cleanup yet.
-- Run from the project folder (run_all.bat does this for you):
--   psql -U postgres -d hr_portfolio -f sql/01_load_raw.sql

DROP SCHEMA IF EXISTS raw CASCADE;
CREATE SCHEMA raw;

-- HR roster: one row per assignment (like the HR Active Assignments report)
CREATE TABLE raw.active_assignments (
    employee_number text, assignment_number text, full_name text, person_type text,
    job_code text, job_name text, union_code text, organization text, payroll text,
    pension_code text, assignment_status text, hire_date text, assignment_start text,
    assignment_end text, termination_date text, suspension_date text, fte text,
    standard_hours text, position_number text, supervisor_number text, visa_type text
);
CREATE TABLE raw.assignment_changes (
    employee_number text, assignment_number text, change_type text, old_value text,
    new_value text, changed_by text, change_date text
);
CREATE TABLE raw.temp_approvals (          -- P-STAR
    pstar_txn_id text, employee_id text, position_number text, approved_end_date text,
    approval_status text, processed_by text
);
CREATE TABLE raw.ats_users (               -- PowerSchool ATS
    ats_user_id text, employee_number text, admin_access text
);
CREATE TABLE raw.new_hires (               -- pending workers
    pending_worker_id text, full_name text, proposed_worker_type text, job_name text,
    bargaining_unit text, organization text, planned_start_date text, personal_email text,
    primary_phone text, national_id_provided text, address_provided text
);
CREATE TABLE raw.journey_tasks (           -- Journey Tasks Status Report
    journey_id text, pending_worker_id text, journey_name text, task_seq text, task_name text,
    task_performer text, task_status text, assigned_date text, completed_date text,
    reopened_flag text, reopen_reason text
);
CREATE TABLE raw.cw_smartsheet (           -- CW request intake
    submission_id text, pending_worker_id text, cw_name text, request_type text,
    organization text, status text, submitted_date text
);
CREATE TABLE raw.pending_transactions (
    txn_id text, employee_number text, txn_type text, queue text, submitted_date text, status text
);
CREATE TABLE raw.partner_submissions (
    submission_id text, partner text, submission_type text, submitted_date text,
    status text, rejection_comment text, specialist text
);

-- Every weekly Fusion HR Audit Report (post go-live), stacked into one file
CREATE TABLE raw.hr_audit_fusion (
    employee_number text, legal_full_name text, assignment_number text, assignment_status text,
    position_number text, job_name text, organization_name text, supervisor_name text,
    responsible_team text, audit_message text, run_date text
);

-- Reference lists
CREATE TABLE raw.hr_audit_catalog (
    check_id text, msg_no text, check_name text, owner_team text,
    severity text, why_it_matters text, tracking text, hits_payroll text
);
CREATE TABLE raw.known_exceptions (check_id text, employee_number text, reason text);
CREATE TABLE raw.payroll_calendar (
    pay_period text, school_year text, hcis_submission_deadline text, hcis_processing_deadline text,
    credentials_date text, pay_period_start text, physical_start text, pay_period_end text,
    payroll_error_fix_by text, blackout_start text, blackout_end text, payroll_file_run text,
    ess_pay_slip text, check_date text, note text
);
CREATE TABLE raw.answer_key (check_id text, expected text);

\copy raw.active_assignments   FROM 'data/raw/active_assignments.csv'   WITH (FORMAT csv, HEADER true)
\copy raw.assignment_changes   FROM 'data/raw/assignment_changes.csv'   WITH (FORMAT csv, HEADER true)
\copy raw.temp_approvals       FROM 'data/raw/temp_approvals.csv'       WITH (FORMAT csv, HEADER true)
\copy raw.ats_users            FROM 'data/raw/ats_users.csv'            WITH (FORMAT csv, HEADER true)
\copy raw.new_hires            FROM 'data/raw/new_hires.csv'            WITH (FORMAT csv, HEADER true)
\copy raw.journey_tasks        FROM 'data/raw/journey_tasks.csv'        WITH (FORMAT csv, HEADER true)
\copy raw.cw_smartsheet        FROM 'data/raw/cw_smartsheet.csv'        WITH (FORMAT csv, HEADER true)
\copy raw.pending_transactions FROM 'data/raw/pending_transactions.csv' WITH (FORMAT csv, HEADER true)
\copy raw.partner_submissions  FROM 'data/raw/partner_submissions.csv'  WITH (FORMAT csv, HEADER true)
\copy raw.hr_audit_fusion      FROM 'data/raw/hr_audit_fusion.csv'      WITH (FORMAT csv, HEADER true)
\copy raw.hr_audit_catalog     FROM 'data/reference/hr_audit_catalog.csv' WITH (FORMAT csv, HEADER true)
\copy raw.known_exceptions     FROM 'data/reference/known_exceptions.csv' WITH (FORMAT csv, HEADER true)
\copy raw.payroll_calendar     FROM 'data/reference/payroll_calendar.csv' WITH (FORMAT csv, HEADER true)
\copy raw.answer_key           FROM 'data/answer_key.csv'               WITH (FORMAT csv, HEADER true)

-- quick check: rows loaded per table
SELECT 'active_assignments' AS table_name, count(*) FROM raw.active_assignments
UNION ALL SELECT 'hr_audit_fusion (26 weekly runs)', count(*) FROM raw.hr_audit_fusion
UNION ALL SELECT 'journey_tasks', count(*) FROM raw.journey_tasks
UNION ALL SELECT 'new_hires', count(*) FROM raw.new_hires
UNION ALL SELECT 'hr_audit_catalog', count(*) FROM raw.hr_audit_catalog
UNION ALL SELECT 'payroll_calendar', count(*) FROM raw.payroll_calendar;
