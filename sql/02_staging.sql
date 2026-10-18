-- 02_staging.sql
-- Step 2: clean the raw exports into typed, standardized tables in the "staging" schema.
-- What gets cleaned here:
--   * stray and double spaces in names; real dates instead of text
--   * three date formats: ISO (2026-07-31), Oracle (23-JUL-2026), US (07/31/2026)
--   * P-STAR's 8-character zero-padded IDs -> match HR employee numbers
--   * Oracle's 4712-12-31 "no end date" -> NULL
--   * Fusion audit messages like "6. Substitute Certification is Missing" -> number + text

DROP SCHEMA IF EXISTS staging CASCADE;
CREATE SCHEMA staging;

-- ---------------------------------------------------------------- roster
CREATE TABLE staging.assignments AS
SELECT
    trim(employee_number)                                      AS employee_number,
    trim(assignment_number)                                    AS assignment_number,
    full_name                                                  AS full_name_raw,   -- kept for the name check
    initcap(regexp_replace(trim(full_name), '\s+', ' ', 'g'))  AS full_name,
    person_type, job_code, job_name, union_code, organization, payroll, pension_code,
    assignment_status,
    assignment_status <> 'Terminated'                          AS is_active,
    hire_date::date                                            AS hire_date,
    assignment_start::date                                     AS assignment_start,
    NULLIF(assignment_end, '4712-12-31')::date                 AS assignment_end,
    NULLIF(termination_date, '')::date                         AS termination_date,
    NULLIF(suspension_date, '')::date                          AS suspension_date,
    fte::numeric                                               AS fte,
    standard_hours::numeric                                    AS standard_hours,
    NULLIF(position_number, '')                                AS position_number,
    NULLIF(supervisor_number, '')                              AS supervisor_number,
    NULLIF(visa_type, '')                                      AS visa_type
FROM raw.active_assignments;

-- Oracle-style dates like 23-JUL-2026
CREATE TABLE staging.assignment_changes AS
SELECT trim(employee_number) AS employee_number, trim(assignment_number) AS assignment_number,
       change_type, old_value, new_value, changed_by,
       to_date(change_date, 'DD-MON-YYYY') AS change_date
FROM raw.assignment_changes;

-- P-STAR: 8-character zero-padded IDs and MM/DD/YYYY dates
CREATE TABLE staging.temp_approvals AS
SELECT pstar_txn_id,
       ltrim(employee_id, '0')                     AS employee_number,
       position_number,
       to_date(approved_end_date, 'MM/DD/YYYY')    AS approved_end_date,
       approval_status, processed_by
FROM raw.temp_approvals;

CREATE TABLE staging.ats_users AS
SELECT ats_user_id, trim(employee_number) AS employee_number, admin_access = 'Y' AS admin_access
FROM raw.ats_users;

-- ---------------------------------------------------------------- hiring pipeline
CREATE TABLE staging.new_hires AS
SELECT pending_worker_id, full_name, proposed_worker_type, job_name, bargaining_unit, organization,
       planned_start_date::date AS planned_start_date,
       NULLIF(personal_email, '') AS personal_email,
       NULLIF(primary_phone, '')  AS primary_phone,
       national_id_provided = 'Y' AS national_id_provided,
       address_provided = 'Y'     AS address_provided
FROM raw.new_hires;

CREATE TABLE staging.journey_tasks AS
SELECT journey_id, pending_worker_id, journey_name, task_seq::int AS task_seq, task_name,
       task_performer, task_status,
       NULLIF(assigned_date, '')::date  AS assigned_date,
       NULLIF(completed_date, '')::date AS completed_date,
       reopened_flag = 'Y'              AS reopened,
       NULLIF(reopen_reason, '')        AS reopen_reason
FROM raw.journey_tasks;

CREATE TABLE staging.cw_smartsheet AS
SELECT submission_id::int AS submission_id, NULLIF(pending_worker_id, '') AS pending_worker_id,
       cw_name, request_type, organization, status, submitted_date::date AS submitted_date
FROM raw.cw_smartsheet;

CREATE TABLE staging.pending_transactions AS
SELECT txn_id, trim(employee_number) AS employee_number, txn_type, queue,
       submitted_date::date AS submitted_date, status
FROM raw.pending_transactions;

CREATE TABLE staging.partner_submissions AS
SELECT submission_id, partner, submission_type, submitted_date::date AS submitted_date,
       status, NULLIF(rejection_comment, '') AS rejection_comment, specialist
FROM raw.partner_submissions;

-- ---------------------------------------------------------------- payroll calendar (biweekly)
CREATE TABLE staging.payroll_calendar AS
SELECT pay_period::int                                   AS pay_period,
       school_year,
       NULLIF(hcis_submission_deadline, '')::date        AS hcis_submission_deadline,
       NULLIF(hcis_processing_deadline, '')::date        AS hcis_processing_deadline,
       credentials_date::date                            AS credentials_date,
       pay_period_start::date                            AS pay_period_start,
       physical_start::date                              AS physical_start,
       pay_period_end::date                              AS pay_period_end,       -- timecards close
       payroll_error_fix_by::date                        AS payroll_error_fix_by, -- Monday noon
       blackout_start::date                              AS blackout_start,
       blackout_end::date                                AS blackout_end,
       payroll_file_run::date                            AS payroll_file_run,
       ess_pay_slip::date                                AS ess_pay_slip,
       check_date::date                                  AS check_date,
       NULLIF(note, '')                                  AS note
FROM raw.payroll_calendar;

-- ---------------------------------------------------------------- the weekly HR Audit Reports
-- "6. Substitute Certification is Missing"  ->  msg_no 6  +  "Substitute Certification is Missing"
CREATE TABLE staging.hr_audit_runs AS
SELECT
    to_date(run_date, 'MM/DD/YYYY')                                 AS run_date,
    NULLIF(employee_number, '')                                     AS employee_number,
    NULLIF(assignment_number, '')                                   AS assignment_number,
    NULLIF(position_number, '')                                     AS position_number,
    NULLIF(legal_full_name, '')                                     AS full_name,
    NULLIF(job_name, '')                                            AS job_name,
    organization_name                                               AS organization,
    NULLIF(assignment_status, '')                                   AS assignment_status,
    NULLIF(supervisor_name, '')                                     AS supervisor_name,
    responsible_team,
    split_part(audit_message, '.', 1)::int                          AS msg_no,
    trim(substring(audit_message FROM position('.' IN audit_message) + 1)) AS audit_message
FROM raw.hr_audit_fusion;

-- quick check
SELECT count(*) AS audit_rows, count(DISTINCT run_date) AS weekly_runs,
       min(run_date) AS first_run, max(run_date) AS last_run
FROM staging.hr_audit_runs;
