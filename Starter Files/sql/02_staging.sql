-- 02_staging.sql
-- Cleans the raw exports into typed, standardized tables in the "staging" schema.
-- What cleaning happens here:
--   * trim stray spaces and collapse double spaces in names
--   * convert text dates to real dates (three different date formats come in)
--   * strip leading zeros from PSTAR's 8-character IDs so they match HR IDs
--   * turn Oracle's 4712-12-31 "open end date" into NULL
-- You can run this in pgAdmin's Query Tool (open file, then F5) or with psql.

DROP SCHEMA IF EXISTS staging CASCADE;
CREATE SCHEMA staging;

-- Roster: one row per assignment
CREATE TABLE staging.assignments AS
SELECT
    trim(employee_number)                                   AS employee_number,
    trim(assignment_number)                                 AS assignment_number,
    full_name                                               AS full_name_raw,      -- kept for the name check
    initcap(regexp_replace(trim(full_name), '\s+', ' ', 'g')) AS full_name,
    person_type,
    job_code,
    job_name,
    union_code,
    organization,
    payroll,
    pension_code,
    assignment_status,
    hire_date::date                                         AS hire_date,
    assignment_start::date                                  AS assignment_start,
    NULLIF(assignment_end, '4712-12-31')::date              AS assignment_end,
    NULLIF(termination_date, '')::date                      AS termination_date,
    NULLIF(fte, '')::numeric                                AS fte,
    position_number,
    NULLIF(supervisor_number, '')                           AS supervisor_number,
    NULLIF(visa_type, '')                                   AS visa_type
FROM raw.active_assignments;

CREATE TABLE staging.salary AS
SELECT trim(employee_number) AS employee_number,
       trim(assignment_number) AS assignment_number,
       annual_salary::numeric AS annual_salary,
       salary_basis,
       effective_date::date AS effective_date
FROM raw.salary;

-- Change log uses Oracle-style dates like 23-JUL-2026
CREATE TABLE staging.assignment_changes AS
SELECT trim(employee_number) AS employee_number,
       trim(assignment_number) AS assignment_number,
       change_type, old_value, new_value, changed_by,
       to_date(change_date, 'DD-MON-YYYY') AS change_date
FROM raw.assignment_changes;

-- PSTAR uses 8-character zero-padded IDs and MM/DD/YYYY dates
CREATE TABLE staging.temp_approvals AS
SELECT pstar_txn_id,
       ltrim(employee_id, '0')                      AS employee_number,
       to_date(approved_end_date, 'MM/DD/YYYY')     AS approved_end_date,
       approval_status
FROM raw.temp_approvals;

CREATE TABLE staging.new_hires AS
SELECT pending_worker_id, full_name, organization,
       planned_start_date::date AS planned_start_date, job_name
FROM raw.new_hires;

CREATE TABLE staging.journey_tasks AS
SELECT journey_id, pending_worker_id, task_name, owner_team,
       assigned_date::date AS assigned_date, status,
       NULLIF(completed_date, '')::date AS completed_date,
       reopened_flag = 'Y' AS reopened,
       missing_data_flag = 'Y' AS missing_data
FROM raw.journey_tasks;

CREATE TABLE staging.pending_transactions AS
SELECT txn_id, trim(employee_number) AS employee_number, txn_type, queue,
       submitted_date::date AS submitted_date, status
FROM raw.pending_transactions;

CREATE TABLE staging.partner_submissions AS
SELECT submission_id, partner, submission_type, submitted_date::date AS submitted_date,
       status, NULLIF(rejection_comment, '') AS rejection_comment, specialist
FROM raw.partner_submissions;

CREATE TABLE staging.ats_users AS
SELECT ats_user_id, trim(employee_number) AS employee_number, admin_access = 'Y' AS admin_access
FROM raw.ats_users;

-- quick check
SELECT 'assignments' AS table_name, count(*) FROM staging.assignments
UNION ALL SELECT 'temp_approvals (IDs matched to roster)', count(*)
FROM staging.temp_approvals t JOIN staging.assignments a USING (employee_number);
