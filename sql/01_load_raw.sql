-- 01_load_raw.sql
-- Creates the "raw" schema and loads every CSV exactly as exported (all text).
-- Run from the project folder with psql (see the build guide, Step 3):
--   psql -U postgres -d hr_portfolio -f sql/01_load_raw.sql

DROP SCHEMA IF EXISTS raw CASCADE;
CREATE SCHEMA raw;

CREATE TABLE raw.active_assignments (
    employee_number text, assignment_number text, full_name text, person_type text,
    job_code text, job_name text, union_code text, organization text, payroll text,
    pension_code text, assignment_status text, hire_date text, assignment_start text,
    assignment_end text, termination_date text, fte text, position_number text,
    supervisor_number text, visa_type text
);
CREATE TABLE raw.salary (
    employee_number text, assignment_number text, annual_salary text,
    salary_basis text, effective_date text
);
CREATE TABLE raw.assignment_changes (
    employee_number text, assignment_number text, change_type text, old_value text,
    new_value text, changed_by text, change_date text
);
CREATE TABLE raw.temp_approvals (
    pstar_txn_id text, employee_id text, approved_end_date text, approval_status text
);
CREATE TABLE raw.new_hires (
    pending_worker_id text, full_name text, organization text,
    planned_start_date text, job_name text
);
CREATE TABLE raw.journey_tasks (
    journey_id text, pending_worker_id text, task_name text, owner_team text,
    assigned_date text, status text, completed_date text, reopened_flag text,
    missing_data_flag text
);
CREATE TABLE raw.pending_transactions (
    txn_id text, employee_number text, txn_type text, queue text,
    submitted_date text, status text
);
CREATE TABLE raw.partner_submissions (
    submission_id text, partner text, submission_type text, submitted_date text,
    status text, rejection_comment text, specialist text
);
CREATE TABLE raw.ats_users (
    ats_user_id text, employee_number text, admin_access text
);

\copy raw.active_assignments   FROM 'data/raw/active_assignments.csv'   WITH (FORMAT csv, HEADER true)
\copy raw.salary               FROM 'data/raw/salary.csv'               WITH (FORMAT csv, HEADER true)
\copy raw.assignment_changes   FROM 'data/raw/assignment_changes.csv'   WITH (FORMAT csv, HEADER true)
\copy raw.temp_approvals       FROM 'data/raw/temp_approvals.csv'       WITH (FORMAT csv, HEADER true)
\copy raw.new_hires            FROM 'data/raw/new_hires.csv'            WITH (FORMAT csv, HEADER true)
\copy raw.journey_tasks        FROM 'data/raw/journey_tasks.csv'        WITH (FORMAT csv, HEADER true)
\copy raw.pending_transactions FROM 'data/raw/pending_transactions.csv' WITH (FORMAT csv, HEADER true)
\copy raw.partner_submissions  FROM 'data/raw/partner_submissions.csv'  WITH (FORMAT csv, HEADER true)
\copy raw.ats_users            FROM 'data/raw/ats_users.csv'            WITH (FORMAT csv, HEADER true)

-- quick check: row counts per table
SELECT 'active_assignments' AS table_name, count(*) FROM raw.active_assignments
UNION ALL SELECT 'salary', count(*) FROM raw.salary
UNION ALL SELECT 'assignment_changes', count(*) FROM raw.assignment_changes
UNION ALL SELECT 'temp_approvals', count(*) FROM raw.temp_approvals
UNION ALL SELECT 'new_hires', count(*) FROM raw.new_hires
UNION ALL SELECT 'journey_tasks', count(*) FROM raw.journey_tasks
UNION ALL SELECT 'pending_transactions', count(*) FROM raw.pending_transactions
UNION ALL SELECT 'partner_submissions', count(*) FROM raw.partner_submissions
UNION ALL SELECT 'ats_users', count(*) FROM raw.ats_users;
