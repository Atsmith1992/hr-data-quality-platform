-- 03_audit_checks.sql
-- Step 3: build the audit layer the dashboards read.
--
--   Part A  the check catalog: HR Audit messages + Antonio's Data Point Checks
--   Part B  every HR Audit row from every weekly run, tagged with its check
--   Part C  week over week: New / Still Open / Resolved, plus the Known Exceptions log
--   Part D  history per error: first seen, last seen, resolved date
--   Part E  audit.exceptions = action items open on the latest run (Dashboard A reads this)
--   Part F  HCIS Data Point Checks, run with SQL against the roster
--   Part F2 payroll deadlines: days to the next fix-by, saved vs. missed per pay period
--   Part G  proof: found vs. planted

DROP SCHEMA IF EXISTS audit CASCADE;
CREATE SCHEMA audit;

-- =================================================================== PART A: catalog
CREATE TABLE audit.check_catalog (
    check_id       text PRIMARY KEY,
    check_name     text,
    severity       text,      -- Critical / High / Medium
    owner_team     text,      -- the one team that fixes it
    why_it_matters text,
    source         text,      -- HR Audit Report (AJ's) or HCIS Data Point Check (Antonio's)
    msg_no         int,       -- the AUDIT_MESSAGE number on the report (#6 etc.)
    tracking       text,      -- Action, or Known Exception (on the report every week, not worked)
    hits_payroll   boolean    -- true = Payroll comes back to HCIS on this one. Every Critical check, nothing else.
);

INSERT INTO audit.check_catalog
SELECT check_id, check_name, severity, owner_team, why_it_matters,
       'HR Audit Report', msg_no::int, tracking, hits_payroll = 'Y'
FROM raw.hr_audit_catalog;

INSERT INTO audit.check_catalog VALUES
('DP01', 'False flip: 10-month teacher on 12 Month Payroll', 'Critical', 'HCIS', '$17K-$27K overpayment risk per teacher', 'HCIS Data Point Check', NULL, 'Action', true),
('DP02', 'Temp suspension date is not P-STAR end date + 1',  'Critical',     'HCIS', 'Temp suspended early or paid past approval', 'HCIS Data Point Check', NULL, 'Action', true),
('DP03', 'Terminated staff still has ATS admin access',      'High',     'HCIS', 'Security gap in PowerSchool', 'HCIS Data Point Check', NULL, 'Action', false),
('DP04', 'Contingent worker reports to a terminated supervisor', 'High', 'HCIS', 'No one can approve the contractor', 'HCIS Data Point Check', NULL, 'Action', false),
('DP05', 'Person type does not match job',                    'Medium',   'HCIS', 'Wrong pay rules and reporting', 'HCIS Data Point Check', NULL, 'Action', false),
('DP06', 'Duplicate active assignment',                       'Medium',   'HCIS', 'Double pay or double headcount', 'HCIS Data Point Check', NULL, 'Action', false),
('DP07', 'Name formatting error',                             'Medium',   'HCIS', 'Breaks matching in other systems', 'HCIS Data Point Check', NULL, 'Action', false),
('DP08', 'Substitute with pension code R (should be I)',      'Medium',   'HCIS', 'Wrong retirement deductions', 'HCIS Data Point Check', NULL, 'Action', false),
('DP09', 'CW journey with no Smartsheet request',             'Medium',   'HCIS', 'Journey started outside the process', 'HCIS Data Point Check', NULL, 'Action', false),
('DP10', 'Legacy 300K position processed by HCIS',            'High',     'HCIS', 'Should be flagged to Systems, not processed', 'HCIS Data Point Check', NULL, 'Action', false),
('DP11', 'Pending worker with no journey',                    'High',     'HCIS', 'New hire never gets onboarded', 'HCIS Data Point Check', NULL, 'Action', false);

-- Known exceptions. A blank employee number means "every row of that message".
CREATE TABLE audit.known_exceptions AS
SELECT check_id, NULLIF(employee_number, '') AS employee_number, reason
FROM raw.known_exceptions;

-- =================================================================== PART B: every audit row, tagged
-- Match each row to its check on the message number, and flag the known exceptions.
-- error_key = what identifies one error across weeks: the assignment (or position) + the check.
CREATE TABLE audit.audit_rows AS
SELECT r.*, c.check_id,
       coalesce(r.responsible_team, c.owner_team) AS team,
       coalesce(r.assignment_number, r.position_number) || '|' || c.check_id AS error_key,
       EXISTS (SELECT 1 FROM audit.known_exceptions k
               WHERE k.check_id = c.check_id
                 AND (k.employee_number IS NULL OR k.employee_number = r.employee_number)) AS is_known
FROM staging.hr_audit_runs r
JOIN audit.check_catalog c ON c.msg_no = r.msg_no;

CREATE INDEX ON audit.audit_rows (error_key, run_date);

-- One row per weekly run, with the run before it
CREATE TABLE audit.run_calendar AS
SELECT run_date,
       LAG(run_date) OVER (ORDER BY run_date)   AS prev_run_date,
       run_date = MAX(run_date) OVER ()         AS is_latest
FROM (SELECT DISTINCT run_date FROM audit.audit_rows) d;

-- =================================================================== PART C: week over week
-- Same idea as comparing Monday's file to Friday's: match on the error key.
CREATE TABLE audit.weekly_status AS
SELECT a.run_date, a.error_key, a.check_id, a.team, a.employee_number,
       CASE WHEN p.error_key IS NULL THEN 'New' ELSE 'Still Open' END AS week_status
FROM audit.audit_rows a
JOIN audit.run_calendar rc USING (run_date)
LEFT JOIN audit.audit_rows p
       ON p.error_key = a.error_key AND p.run_date = rc.prev_run_date
WHERE NOT a.is_known
UNION ALL
-- Resolved = it was on last run's report and it's gone from this run
SELECT rc.run_date, p.error_key, p.check_id, p.team, p.employee_number, 'Resolved'
FROM audit.run_calendar rc
JOIN audit.audit_rows p
  ON p.run_date = rc.prev_run_date AND NOT p.is_known
LEFT JOIN audit.audit_rows a
  ON a.error_key = p.error_key AND a.run_date = rc.run_date
WHERE a.error_key IS NULL;

-- Action items per run, per check, per team (for trend charts)
CREATE TABLE audit.weekly_summary AS
SELECT run_date, check_id, team,
       count(*) FILTER (WHERE week_status <> 'Resolved')   AS on_report,
       count(*) FILTER (WHERE week_status = 'New')         AS new_items,
       count(*) FILTER (WHERE week_status = 'Still Open')  AS still_open,
       count(*) FILTER (WHERE week_status = 'Resolved')    AS resolved
FROM audit.weekly_status
GROUP BY run_date, check_id, team;

-- Known Exceptions log: counted every week, kept off the main charts
CREATE TABLE audit.known_exception_log AS
SELECT a.run_date, a.check_id, c.check_name, a.team, count(*) AS rows_on_report
FROM audit.audit_rows a
JOIN audit.check_catalog c USING (check_id)
WHERE a.is_known
GROUP BY a.run_date, a.check_id, c.check_name, a.team;

-- =================================================================== PART D: history per error
CREATE TABLE audit.error_history AS
WITH h AS (
    SELECT error_key, check_id, max(team) AS team, max(employee_number) AS employee_number,
           min(run_date) AS first_seen, max(run_date) AS last_seen, count(*) AS weeks_on_report
    FROM audit.audit_rows
    WHERE NOT is_known
    GROUP BY error_key, check_id
)
SELECT h.*,
       h.last_seen = latest.run_date                                   AS still_open,
       CASE WHEN h.last_seen <> latest.run_date THEN nxt.run_date END  AS resolved_date
FROM h
JOIN audit.run_calendar latest ON latest.is_latest
LEFT JOIN audit.run_calendar nxt ON nxt.prev_run_date = h.last_seen;

-- =================================================================== PART E: what's open now
-- Dashboard A reads this table: the action items on the latest run, plus the Data Point Checks.
-- Same columns as version 1, plus a few new ones at the end.
CREATE TABLE audit.exceptions (
    check_id          text REFERENCES audit.check_catalog(check_id),
    employee_number   text,
    assignment_number text,
    full_name         text,
    organization      text,
    detail            text,
    status            text DEFAULT 'Open',
    first_seen        date,
    run_date          date,
    source            text,
    week_status       text,      -- New / Still Open
    position_number   text,
    payroll_fix_by    date,      -- for payroll-blocking errors: the next Monday-noon fix-by
    days_to_fix_by    int
);

INSERT INTO audit.exceptions (check_id, employee_number, assignment_number, full_name, organization,
                              detail, first_seen, run_date, source, week_status, position_number)
SELECT a.check_id, a.employee_number, a.assignment_number, a.full_name, a.organization,
       concat_ws(' | ', a.job_name, a.assignment_status, 'Supervisor: ' || a.supervisor_name),
       h.first_seen, a.run_date, 'HR Audit Report', ws.week_status, a.position_number
FROM audit.audit_rows a
JOIN audit.run_calendar rc  ON rc.run_date = a.run_date AND rc.is_latest
JOIN audit.error_history h  ON h.error_key = a.error_key
JOIN audit.weekly_status ws ON ws.error_key = a.error_key AND ws.run_date = a.run_date
                           AND ws.week_status <> 'Resolved'
WHERE NOT a.is_known;

-- =================================================================== PART F: HCIS Data Point Checks
-- Antonio's own checks. They run against the roster as of 7/31/2026 (the last audit run).
CREATE VIEW audit.active AS
SELECT * FROM staging.assignments WHERE is_active;

-- DP01 False flip: teacher moved to 12 Month Payroll, with the latest payroll change as proof
WITH payroll_changes AS (
    SELECT employee_number, old_value, new_value, changed_by, change_date,
           ROW_NUMBER() OVER (PARTITION BY employee_number ORDER BY change_date DESC) AS rn
    FROM staging.assignment_changes
    WHERE change_type = 'Change Assignment - Payroll'
)
INSERT INTO audit.exceptions (check_id, employee_number, assignment_number, full_name, organization, detail, position_number)
SELECT 'DP01', a.employee_number, a.assignment_number, a.full_name, a.organization,
       'Changed ' || coalesce(pc.old_value, '?') || ' -> ' || a.payroll ||
       coalesce(' by ' || pc.changed_by || ' on ' || pc.change_date, ''), a.position_number
FROM audit.active a
LEFT JOIN payroll_changes pc ON pc.employee_number = a.employee_number AND pc.rn = 1
WHERE a.job_code IN ('101545', '101590', '101610')
  AND a.payroll = '12 Month Payroll';

-- DP02 Temp suspension date must equal P-STAR end date + 1 day
-- (a blank suspension date is skipped: the HR Audit already catches that as #90)
INSERT INTO audit.exceptions (check_id, employee_number, assignment_number, full_name, organization, detail, position_number)
SELECT 'DP02', a.employee_number, a.assignment_number, a.full_name, a.organization,
       'Suspension ' || a.suspension_date || ', should be ' || (t.approved_end_date + 1) ||
       ' (P-STAR end ' || t.approved_end_date || ')', a.position_number
FROM audit.active a
JOIN staging.temp_approvals t ON t.employee_number = a.employee_number
WHERE a.suspension_date IS NOT NULL
  AND a.suspension_date <> t.approved_end_date + 1;

-- DP03 Terminated staff who still have PowerSchool ATS admin access
INSERT INTO audit.exceptions (check_id, employee_number, assignment_number, full_name, organization, detail, position_number)
SELECT DISTINCT ON (a.employee_number)
       'DP03', a.employee_number, a.assignment_number, a.full_name, a.organization,
       'Terminated ' || a.termination_date || ', ATS admin still active', a.position_number
FROM staging.assignments a
JOIN staging.ats_users u ON u.employee_number = a.employee_number AND u.admin_access
WHERE a.assignment_status = 'Terminated'
ORDER BY a.employee_number;

-- DP04 CW Manager Update: active contingent workers whose supervisor has left
INSERT INTO audit.exceptions (check_id, employee_number, assignment_number, full_name, organization, detail, position_number)
SELECT 'DP04', a.employee_number, a.assignment_number, a.full_name, a.organization,
       'Supervisor ' || s.full_name || ' terminated ' || s.termination_date ||
       ' (' || (DATE '2026-07-31' - s.termination_date) || ' days ago)', a.position_number
FROM audit.active a
JOIN staging.assignments s ON s.employee_number = a.supervisor_number
WHERE a.person_type = 'Contingent Worker'
  AND s.assignment_status = 'Terminated';

-- DP05 Person type doesn't match the job (Home & Hospital teachers are Temporary on purpose)
INSERT INTO audit.exceptions (check_id, employee_number, assignment_number, full_name, organization, detail, position_number)
SELECT 'DP05', employee_number, assignment_number, full_name, organization,
       'Person type ' || person_type || ' on job ' || job_name, position_number
FROM audit.active
WHERE (person_type = 'Temporary Employee' AND job_code NOT IN ('103845', '103875', '103890'))
   OR (person_type = 'Employee'           AND job_code IN ('103845', '103875'))
   OR (person_type = 'Substitute'         AND job_code <> '100770')
   OR (person_type = 'Contingent Worker'  AND job_code <> '900100');

-- DP06 Duplicate assignment: same person, same job, same school, more than one active row
WITH dupes AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY employee_number, job_code, organization
                                 ORDER BY assignment_start) AS rn,
              COUNT(*)     OVER (PARTITION BY employee_number, job_code, organization) AS copies
    FROM audit.active
)
INSERT INTO audit.exceptions (check_id, employee_number, assignment_number, full_name, organization, detail, position_number)
SELECT 'DP06', employee_number, assignment_number, full_name, organization,
       copies || ' active assignments for ' || job_name || '; this one starts ' || assignment_start, position_number
FROM dupes
WHERE rn = 2;

-- DP07 Name formatting: extra spaces, leading/trailing space, or ALL CAPS
INSERT INTO audit.exceptions (check_id, employee_number, assignment_number, full_name, organization, detail, position_number)
SELECT 'DP07', employee_number, assignment_number, full_name, organization,
       'Stored as "' || full_name_raw || '"', position_number
FROM audit.active
WHERE full_name_raw <> trim(full_name_raw)
   OR full_name_raw ~ '\s{2,}'
   OR full_name_raw = upper(full_name_raw);

-- DP08 Substitutes must carry pension code I (Ineligible), not R (Retired Rehire)
INSERT INTO audit.exceptions (check_id, employee_number, assignment_number, full_name, organization, detail, position_number)
SELECT 'DP08', employee_number, assignment_number, full_name, organization,
       'Pension code ' || pension_code || ', should be I', position_number
FROM audit.active
WHERE person_type = 'Substitute' AND pension_code = 'R';

-- DP09 CW journey started with no Smartsheet request behind it
INSERT INTO audit.exceptions (check_id, employee_number, full_name, organization, detail)
SELECT DISTINCT 'DP09', h.pending_worker_id, h.full_name, h.organization,
       'On ' || j.journey_name || ' with no Smartsheet request'
FROM staging.journey_tasks j
JOIN staging.new_hires h USING (pending_worker_id)
LEFT JOIN staging.cw_smartsheet s USING (pending_worker_id)
WHERE j.journey_name = 'Pre-boarding - Contingent Worker Role'
  AND s.submission_id IS NULL;

-- DP10 Legacy 300K (EBS) positions should be flagged to Systems, not processed by HCIS
INSERT INTO audit.exceptions (check_id, employee_number, assignment_number, full_name, organization, detail, position_number)
SELECT 'DP10', a.employee_number, a.assignment_number, a.full_name, a.organization,
       'P-STAR ' || t.pstar_txn_id || ' on legacy position ' || t.position_number || ' processed by HCIS',
       t.position_number
FROM staging.temp_approvals t
JOIN audit.active a ON a.employee_number = t.employee_number
WHERE t.position_number LIKE '3%' AND t.processed_by = 'HCIS';

-- DP11 Pending worker created with no journey (the go-live auto-journey bug)
INSERT INTO audit.exceptions (check_id, employee_number, full_name, organization, detail)
SELECT 'DP11', h.pending_worker_id, h.full_name, h.organization,
       h.proposed_worker_type || ', starts ' || h.planned_start_date || ', no journey assigned'
FROM staging.new_hires h
WHERE NOT EXISTS (SELECT 1 FROM staging.journey_tasks j WHERE j.pending_worker_id = h.pending_worker_id);

-- Data point checks all ran as of 7/31/2026
UPDATE audit.exceptions
SET first_seen = DATE '2026-07-31', run_date = DATE '2026-07-31',
    source = 'HCIS Data Point Check', week_status = 'New'
WHERE source IS NULL;

-- =================================================================== PART F2: payroll deadlines
-- "Today" is the latest audit run. The next deadline is the next Monday-noon error fix-by.
CREATE TABLE audit.payroll_status AS
WITH asof AS (SELECT run_date AS as_of FROM audit.run_calendar WHERE is_latest),
nxt AS (
    SELECT pc.* FROM staging.payroll_calendar pc, asof
    WHERE pc.payroll_error_fix_by > asof.as_of
    ORDER BY pc.payroll_error_fix_by LIMIT 1
)
SELECT asof.as_of,
       nxt.pay_period                          AS next_pay_period,
       nxt.pay_period_end                      AS timecards_close,
       nxt.payroll_error_fix_by                AS fix_by,
       nxt.payroll_file_run,
       nxt.check_date                          AS next_check_date,
       nxt.payroll_error_fix_by - asof.as_of   AS days_to_fix_by,
       (SELECT count(*) FROM audit.exceptions e
        JOIN audit.check_catalog c USING (check_id) WHERE c.hits_payroll) AS payroll_blocking_open
FROM asof, nxt;

UPDATE audit.exceptions e
SET payroll_fix_by = ps.fix_by, days_to_fix_by = ps.days_to_fix_by
FROM audit.payroll_status ps, audit.check_catalog c
WHERE c.check_id = e.check_id AND c.hits_payroll;

-- Saved vs. missed, per pay period:
--   at risk = payroll-blocking error on the report the Friday timecards closed
--   missed  = still on the report on check day (not fixed by the Monday fix-by)
--   saved   = gone by check day
CREATE TABLE audit.payroll_impact AS
WITH at_risk AS (
    SELECT pc.pay_period, pc.pay_period_end, pc.payroll_error_fix_by, pc.check_date,
           a.error_key, a.check_id, a.team
    FROM staging.payroll_calendar pc
    JOIN audit.audit_rows a     ON a.run_date = pc.pay_period_end AND NOT a.is_known
    JOIN audit.check_catalog c  ON c.check_id = a.check_id AND c.hits_payroll
)
SELECT r.pay_period, r.pay_period_end AS timecards_close, r.payroll_error_fix_by AS fix_by,
       r.check_date, r.check_id, r.team,
       count(*)                                          AS at_risk,
       count(*) FILTER (WHERE nxt.error_key IS NULL)     AS saved,
       count(*) FILTER (WHERE nxt.error_key IS NOT NULL) AS missed
FROM at_risk r
LEFT JOIN audit.audit_rows nxt ON nxt.error_key = r.error_key AND nxt.run_date = r.check_date
GROUP BY r.pay_period, r.pay_period_end, r.payroll_error_fix_by, r.check_date, r.check_id, r.team;

-- =================================================================== PART G: proof
-- Every row should say MATCH. Known Exception messages should find 0 on the action list.
SELECT c.source, c.tracking, c.check_id, c.check_name,
       count(e.check_id)   AS found,
       k.expected::int     AS expected,
       CASE WHEN count(e.check_id) = k.expected::int THEN 'MATCH' ELSE 'CHECK THIS' END AS result
FROM audit.check_catalog c
LEFT JOIN audit.exceptions e USING (check_id)
LEFT JOIN raw.answer_key k USING (check_id)
GROUP BY c.source, c.tracking, c.check_id, c.check_name, k.expected
UNION ALL
SELECT 'HR Audit Report', 'Known Exception', 'LOG', 'Known exceptions on the latest run (own log)',
       sum(l.rows_on_report)::int, max(k.expected)::int,
       CASE WHEN sum(l.rows_on_report) = max(k.expected)::int THEN 'MATCH' ELSE 'CHECK THIS' END
FROM audit.known_exception_log l
JOIN audit.run_calendar rc ON rc.run_date = l.run_date AND rc.is_latest
CROSS JOIN (SELECT expected FROM raw.answer_key WHERE check_id = 'KNOWN_EXCEPTIONS_LATEST') k
UNION ALL
SELECT 'HR Audit Report', '', 'UNMATCHED', 'Audit rows with no matching check', count(*)::int, 0,
       CASE WHEN count(*) = 0 THEN 'MATCH' ELSE 'CHECK THIS' END
FROM staging.hr_audit_runs r
WHERE NOT EXISTS (SELECT 1 FROM audit.check_catalog c WHERE c.msg_no = r.msg_no)
ORDER BY 1 DESC, 2, 3;
