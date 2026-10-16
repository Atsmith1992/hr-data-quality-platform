-- 03_audit_checks.sql
-- Runs the first 8 audit checks and writes every finding to ONE table: audit.exceptions.
-- Each check has a severity and an owner team, like a real HR audit program.
-- The audit "as of" date is fixed at 2026-10-15 so results match the answer key.

DROP SCHEMA IF EXISTS audit CASCADE;
CREATE SCHEMA audit;

-- The list of checks: what each one is, how serious, and who fixes it
CREATE TABLE audit.check_catalog (
    check_id    text PRIMARY KEY,
    check_name  text,
    severity    text,      -- Critical / High / Medium
    owner_team  text,
    why_it_matters text
);

INSERT INTO audit.check_catalog VALUES
('C01', 'Active assignment with no salary record', 'Critical', 'Compensation', 'Worker will not be paid correctly'),
('C02', 'False flip: teacher on 12 Month Payroll',  'Critical', 'HCIS',         'Overpayment risk of $17K+ per teacher'),
('C03', 'Still active after termination date',      'Critical', 'HCIS',         'Paying someone who has left'),
('H04', 'Temp end date differs from PSTAR approval','High',     'HCIS',         'Temp suspended early or paid past approval'),
('H05', 'Future-dated assignment start',            'High',     'HCIS',         'Typo year blocks pay and timekeeping'),
('H06', 'Supervisor is an ex-employee',             'High',     'Talent Management', 'No one can approve time or tasks'),
('M07', 'Name formatting error',                    'Medium',   'HCIS',         'Breaks matching in downstream systems'),
('M08', 'Substitute with wrong pension code',       'Medium',   'HCIS',         'Wrong retirement deductions');

CREATE TABLE audit.exceptions (
    check_id         text REFERENCES audit.check_catalog(check_id),
    employee_number  text,
    assignment_number text,
    full_name        text,
    organization     text,
    detail           text,
    status           text DEFAULT 'Open',     -- Open / In Progress / Complete / NAR
    first_seen       date DEFAULT DATE '2026-10-15',
    run_date         date DEFAULT DATE '2026-10-15'
);

-- Only look at active assignments for most checks
CREATE VIEW audit.active AS
SELECT * FROM staging.assignments WHERE assignment_status = 'Active Assignment';

-- C01: active, paid job, but no salary row
INSERT INTO audit.exceptions (check_id, employee_number, assignment_number, full_name, organization, detail)
SELECT 'C01', a.employee_number, a.assignment_number, a.full_name, a.organization,
       a.job_name || ' has no salary record'
FROM audit.active a
LEFT JOIN staging.salary s ON s.employee_number = a.employee_number
WHERE s.employee_number IS NULL
  AND a.person_type = 'Employee'
  AND a.job_code <> '100770';          -- substitutes are paid daily, no salary row expected

-- C02: teacher on 12 Month Payroll, with the latest payroll change shown as proof
WITH payroll_changes AS (
    SELECT employee_number, old_value, new_value, changed_by, change_date,
           ROW_NUMBER() OVER (PARTITION BY employee_number ORDER BY change_date DESC) AS rn
    FROM staging.assignment_changes
    WHERE change_type = 'Assignment Flip - Payroll'
)
INSERT INTO audit.exceptions (check_id, employee_number, assignment_number, full_name, organization, detail)
SELECT 'C02', a.employee_number, a.assignment_number, a.full_name, a.organization,
       'Changed ' || coalesce(pc.old_value, '?') || ' -> ' || a.payroll ||
       coalesce(' by ' || pc.changed_by || ' on ' || pc.change_date, '')
FROM audit.active a
LEFT JOIN payroll_changes pc ON pc.employee_number = a.employee_number AND pc.rn = 1
WHERE a.job_code IN ('101545', '101590')
  AND a.payroll = '12 Month Payroll';

-- C03: still active, but termination date has already passed
INSERT INTO audit.exceptions (check_id, employee_number, assignment_number, full_name, organization, detail)
SELECT 'C03', employee_number, assignment_number, full_name, organization,
       'Termination date ' || termination_date || ' but assignment is still active'
FROM audit.active
WHERE termination_date IS NOT NULL
  AND termination_date <= DATE '2026-10-15';

-- H04: temp end date in HR does not match PSTAR approved end date
INSERT INTO audit.exceptions (check_id, employee_number, assignment_number, full_name, organization, detail)
SELECT 'H04', a.employee_number, a.assignment_number, a.full_name, a.organization,
       'HR end ' || a.assignment_end || ' vs PSTAR approved ' || t.approved_end_date ||
       ' (' || (t.approved_end_date - a.assignment_end) || ' days apart)'
FROM audit.active a
JOIN staging.temp_approvals t ON t.employee_number = a.employee_number
WHERE a.person_type = 'Temp'
  AND a.assignment_end IS DISTINCT FROM t.approved_end_date;

-- H05: assignment starts more than 6 months in the future (usually a typo year)
INSERT INTO audit.exceptions (check_id, employee_number, assignment_number, full_name, organization, detail)
SELECT 'H05', employee_number, assignment_number, full_name, organization,
       'Assignment start ' || assignment_start
FROM audit.active
WHERE assignment_start > DATE '2026-10-15' + INTERVAL '6 months';

-- H06: supervisor is terminated (or not on the roster at all)
WITH supervisors AS (
    SELECT employee_number, full_name, assignment_status, termination_date
    FROM staging.assignments
)
INSERT INTO audit.exceptions (check_id, employee_number, assignment_number, full_name, organization, detail)
SELECT 'H06', a.employee_number, a.assignment_number, a.full_name, a.organization,
       'Supervisor ' || a.supervisor_number || ' ' ||
       coalesce(s.full_name || ' terminated ' || s.termination_date, 'not found on roster')
FROM audit.active a
LEFT JOIN supervisors s ON s.employee_number = a.supervisor_number
WHERE s.employee_number IS NULL
   OR s.assignment_status = 'Terminated';

-- M07: name has extra spaces, trailing space, or is all upper / all lower case
INSERT INTO audit.exceptions (check_id, employee_number, assignment_number, full_name, organization, detail)
SELECT 'M07', employee_number, assignment_number, full_name, organization,
       'Stored as "' || full_name_raw || '"'
FROM audit.active
WHERE full_name_raw <> trim(full_name_raw)
   OR full_name_raw ~ '\s{2,}'
   OR full_name_raw = upper(full_name_raw)
   OR full_name_raw = lower(full_name_raw);

-- M08: substitutes must carry pension code I (Ineligible)
INSERT INTO audit.exceptions (check_id, employee_number, assignment_number, full_name, organization, detail)
SELECT 'M08', employee_number, assignment_number, full_name, organization,
       'Pension code ' || pension_code || ', should be I'
FROM audit.active
WHERE job_code = '100770'
  AND pension_code <> 'I';

-- Summary: compare these counts to data/answer_key.csv
SELECT c.check_id, c.check_name, c.severity, c.owner_team, count(e.*) AS errors_found
FROM audit.check_catalog c
LEFT JOIN audit.exceptions e USING (check_id)
GROUP BY c.check_id, c.check_name, c.severity, c.owner_team
ORDER BY c.check_id;
