-- 04_pipeline.sql
-- Step 4: the hiring pipeline (Dashboard B).
-- Pending workers moving through their pre-boarding journeys before their first day.
-- Modeled on Laura's hiring intervention dashboard and the daily tracker built from it.
--
--   Part A  pipeline.hires              one row per pending worker: where they're stuck, who it's waiting on
--   Part B  pipeline.intervention_list  Laura's four tabs, one row per hire per tab (909 rows)
--   Part C  pipeline.status             the cards: counts plus the countdown to the next HCIS deadline
--   Part D  proof: counts vs. the answer key
--
-- "Today" is 7/31/2026, the same as-of date as Dashboard A (the last audit run).

DROP SCHEMA IF EXISTS pipeline CASCADE;
CREATE SCHEMA pipeline;

-- =================================================================== PART A: one row per hire
CREATE TABLE pipeline.hires AS
WITH asof AS (
    SELECT max(run_date) AS as_of FROM staging.hr_audit_runs          -- 7/31/2026
),
current_task AS (
    -- Journeys move one task at a time. The current task is the one Initiated or In Progress.
    SELECT DISTINCT ON (pending_worker_id)
           pending_worker_id, journey_name, task_seq, task_name, task_performer,
           assigned_date, reopened, reopen_reason
    FROM staging.journey_tasks
    WHERE task_status IN ('Initiated', 'In Progress')
    ORDER BY pending_worker_id, task_seq
),
task_counts AS (
    SELECT pending_worker_id, count(*) AS total_tasks
    FROM staging.journey_tasks
    GROUP BY pending_worker_id
),
base AS (
    SELECT
        h.pending_worker_id,
        h.full_name,
        h.proposed_worker_type                                    AS worker_type,
        h.job_name,
        h.bargaining_unit,
        h.organization,
        -- District offices use org codes 0600 and up; schools are below 0600
        CASE WHEN split_part(h.organization, ' - ', 1)::int >= 600
             THEN 'District Office' ELSE 'School' END             AS location_type,
        h.planned_start_date,
        h.personal_email,
        h.primary_phone,

        -- The journey this worker type SHOULD be on
        CASE
            WHEN h.proposed_worker_type = 'Contingent Worker'  THEN 'Pre-boarding - Contingent Worker Role'
            WHEN h.proposed_worker_type = 'Temporary Employee' THEN 'Pre-boarding - Temporary Role'
            WHEN h.proposed_worker_type = 'Employee' AND h.job_name LIKE 'Teacher -%'
                                                                THEN 'Pre-boarding - Certified Role'
            ELSE 'Pre-boarding - Non-Certified Role'           -- non-cert staff, subs, district office
        END                                                       AS expected_journey,
        ct.journey_name,

        ct.task_seq                                               AS current_task_no,
        tc.total_tasks,
        tc.total_tasks - ct.task_seq + 1                          AS tasks_left,
        ct.task_name                                              AS current_task,
        ct.task_performer,
        ct.assigned_date                                          AS task_assigned,
        asof.as_of - ct.assigned_date                             AS days_waiting,
        coalesce(ct.reopened, false)                              AS reopened,
        ct.reopen_reason,

        -- What's missing that will block them later
        NULLIF(concat_ws(', ',
            CASE WHEN h.personal_email IS NULL   THEN 'Personal email' END,
            CASE WHEN h.primary_phone IS NULL    THEN 'Phone' END,
            CASE WHEN NOT h.national_id_provided THEN 'SSN' END,
            CASE WHEN NOT h.address_provided     THEN 'Address' END), '')  AS missing_data,

        asof.as_of
    FROM staging.new_hires h
    CROSS JOIN asof
    LEFT JOIN current_task ct USING (pending_worker_id)
    LEFT JOIN task_counts  tc USING (pending_worker_id)
)
SELECT
    b.*,
    -- short labels for charts
    replace(replace(coalesce(b.journey_name, 'No journey'), 'Pre-boarding - ', ''), ' Role', '') AS journey,
    b.journey_name IS NOT NULL AND b.journey_name <> b.expected_journey               AS wrong_journey,

    -- Who it's waiting on
    CASE WHEN b.journey_name IS NULL                      THEN 'HCIS (no journey)'
         WHEN b.task_performer IN ('Employee', 'Worker')  THEN 'New hire'
         ELSE 'HC staff' END                                                          AS waiting_on,
    CASE WHEN b.task_performer IN ('Employee', 'Worker') THEN 'New hire'
         ELSE coalesce(b.task_performer, 'HCIS') END                                  AS waiting_on_team,

    -- Stalled = the same task has sat 3+ days (Laura's rule)
    coalesce(b.days_waiting >= 3, false)                                              AS stalled,

    -- Pay period and HCIS deadlines for the planned start date
    pc.pay_period                                                                     AS start_pay_period,
    pc.hcis_submission_deadline,
    pc.hcis_processing_deadline,
    pc.hcis_processing_deadline - b.as_of                                             AS days_to_hcis_deadline,
    b.planned_start_date + 14                                                         AS start_if_missed
FROM base b
LEFT JOIN staging.payroll_calendar pc ON pc.pay_period_start = b.planned_start_date;

-- One status per hire, in priority order (the first problem that applies), and the start-date risk.
ALTER TABLE pipeline.hires ADD COLUMN pipeline_status text, ADD COLUMN start_risk text;

UPDATE pipeline.hires SET pipeline_status = CASE
    WHEN journey_name IS NULL                         THEN 'Blocked: no journey'
    WHEN wrong_journey                                THEN 'Blocked: wrong journey'
    WHEN missing_data IS NOT NULL                     THEN 'Blocked: missing data'
    WHEN reopened                                     THEN 'Reopened'
    WHEN stalled AND waiting_on = 'New hire'          THEN 'Stalled with new hire'
    WHEN stalled                                      THEN 'Stalled with HC staff'
    WHEN task_performer = 'HCIS'                      THEN 'Ready for HCIS flip'
    ELSE 'Moving' END;

-- Start-date risk. Missing the HCIS processing deadline moves the start to the next pay period.
--   On track        = moving, or ready for the HCIS flip
--   At risk         = blocked, reopened or stalled, with the HCIS deadline 14 days away or less: act now
--   Needs follow-up = blocked, reopened or stalled, with more time (worth a nudge, not urgent yet)
UPDATE pipeline.hires SET start_risk = CASE
    WHEN pipeline_status IN ('Moving', 'Ready for HCIS flip') THEN 'On track'
    WHEN days_to_hcis_deadline <= 14                         THEN 'At risk'
    ELSE 'Needs follow-up' END;

-- =================================================================== PART B: Laura's four tabs
-- One hire can sit on more than one tab (stalled AND missing data), so this has 909 rows for ~800 hires,
-- the same way Laura's export did. The daily tracker works from this list.
CREATE TABLE pipeline.intervention_list AS
SELECT 'Stalled Hires' AS tab, 1 AS tab_order, h.* FROM pipeline.hires h
WHERE h.stalled AND h.waiting_on = 'New hire'
UNION ALL
SELECT 'HC Staff Tasks', 2, h.* FROM pipeline.hires h
WHERE h.stalled AND h.waiting_on = 'HC staff'
UNION ALL
SELECT 'Reopened Tasks', 3, h.* FROM pipeline.hires h
WHERE h.reopened
UNION ALL
SELECT 'Missing Data', 4, h.* FROM pipeline.hires h
WHERE h.missing_data IS NOT NULL AND h.journey_name IS NOT NULL;

-- =================================================================== PART C: the cards
CREATE TABLE pipeline.status AS
WITH nxt AS (
    -- the next start date after today, and its HCIS deadlines
    SELECT h.planned_start_date, h.start_pay_period, h.hcis_submission_deadline,
           h.hcis_processing_deadline, h.days_to_hcis_deadline, h.start_if_missed
    FROM pipeline.hires h
    WHERE h.planned_start_date > h.as_of
    ORDER BY h.planned_start_date
    LIMIT 1
)
SELECT
    (SELECT max(as_of) FROM pipeline.hires)                                       AS as_of,
    (SELECT count(*) FROM pipeline.hires)                                         AS pending_hires,
    (SELECT count(*) FROM pipeline.intervention_list WHERE tab = 'Stalled Hires')  AS stalled_with_hire,
    (SELECT count(*) FROM pipeline.intervention_list WHERE tab = 'HC Staff Tasks') AS stalled_with_hc_staff,
    (SELECT count(*) FROM pipeline.intervention_list WHERE tab = 'Reopened Tasks') AS reopened_tasks,
    (SELECT count(*) FROM pipeline.intervention_list WHERE tab = 'Missing Data')   AS missing_data,
    (SELECT count(*) FROM pipeline.intervention_list)                             AS intervention_rows,
    (SELECT count(*) FROM pipeline.hires WHERE wrong_journey)                     AS wrong_journey,
    (SELECT count(*) FROM pipeline.hires WHERE journey_name IS NULL)              AS no_journey,
    (SELECT count(*) FROM pipeline.hires WHERE location_type = 'District Office') AS district_office_hires,
    nxt.planned_start_date                                                        AS next_start_date,
    nxt.start_pay_period                                                          AS next_start_pay_period,
    nxt.hcis_submission_deadline,
    nxt.hcis_processing_deadline,
    nxt.days_to_hcis_deadline,
    nxt.start_if_missed,
    (SELECT count(*) FROM pipeline.hires h
      WHERE h.planned_start_date = nxt.planned_start_date)                        AS starting_next,
    (SELECT count(*) FROM pipeline.hires h
      WHERE h.planned_start_date = nxt.planned_start_date AND h.start_risk = 'At risk') AS at_risk_next
FROM nxt;

-- =================================================================== PART D: proof
-- Every row should say MATCH.
WITH found AS (
    SELECT 'LAURA_STALLED_HIRES' AS check_id, stalled_with_hire AS n FROM pipeline.status
    UNION ALL SELECT 'LAURA_HC_STAFF_TASKS', stalled_with_hc_staff FROM pipeline.status
    UNION ALL SELECT 'LAURA_REOPENED_TASKS', reopened_tasks FROM pipeline.status
    UNION ALL SELECT 'LAURA_MISSING_DATA', missing_data FROM pipeline.status
    UNION ALL SELECT 'PIPELINE_WRONG_JOURNEY', wrong_journey FROM pipeline.status
    UNION ALL SELECT 'PIPELINE_DISTRICT_OFFICE_HIRES', district_office_hires FROM pipeline.status
    UNION ALL SELECT 'DP11', no_journey FROM pipeline.status
)
SELECT f.check_id, f.n AS found, k.expected::int AS expected,
       CASE WHEN f.n = k.expected::int THEN 'MATCH' ELSE 'CHECK THIS' END AS result
FROM found f
LEFT JOIN raw.answer_key k USING (check_id)
ORDER BY 1;

-- and the countdown
SELECT next_start_date, next_start_pay_period, hcis_processing_deadline, days_to_hcis_deadline,
       starting_next, at_risk_next, start_if_missed
FROM pipeline.status;
