# How It Works (and how to do it yourself)

This guide walks through every file in plain English, so you can explain it in an interview and change it without help. Read it with the file open next to it in VS Code.

## The big picture

```
generate_data.py  ->  data/raw/*.csv  ->  raw schema  ->  staging schema  ->  audit + pipeline  ->  Power BI
   (Python)            (the exports)     (01 load)       (02 clean)        (03 and 04)        (dashboards)
```

Same flow as the real job: a system exports a file, you load it, clean it, check it, and report on it.

- **raw** = exactly what the system gave you. Every column is text. Never edit it.
- **staging** = cleaned copies: real dates, trimmed names, matching IDs.
- **audit** = the answers: errors found, who owns them, what changed since last week.

Keeping the three layers separate means that when a number looks wrong, you can trace it back step by step.

## Part 1: generate_data.py (Python)

It makes the fake data. Open it and follow the numbered section headers.

| Section | What it does | Python ideas used |
| --- | --- | --- |
| 1. Settings | Dates, folders, `random.seed(42)` | Variables, `Path`, `date`, `timedelta` |
| 2. Names, schools, jobs | Lists of names, 175 schools, a `JOBS` dictionary | Lists, dictionaries, tuples |
| 3. Roster | Builds about 13,000 workers with `new_worker()` | Functions, `for` loops, `random.choices` with weights |
| 4. Data Point Checks | Plants your checks' errors on purpose, with exact counts | `pick()` so no worker gets planted twice |
| 5. Other exports | Change log, P-STAR, PowerSchool ATS | Date formatting (`strftime`) |
| 5b. Payroll calendar | Every pay period's deadlines, all as offsets from the Saturday start | `timedelta(days=16)` = Monday fix-by |
| 6. Journeys | The 4 real pre-boarding templates and their task names, start dates, district office hires | Nested lists, building task rows step by step, `sorted(..., key=...)` |
| 7. Queues | Pending transactions and partner submissions (for Dashboard C) | Same patterns again |
| 8. Catalog | Every audit message: team, severity, Action or Known Exception | Dictionaries of tuples |
| 9. Weekly audit files | 26 Friday runs of the HR Audit Report | `random.random() < chance` decides if an error shows up that week |
| 10. Answer key | Writes what was planted | `csv.writer` |

Ideas worth knowing:

- **`random.seed(42)`** makes the "random" data the same every run. Same input, same output, so your SQL results can be checked.
- **Dictionaries** (`{"key": value}`) are how each worker is stored. `w["job_name"]` reads one field.
- **`csv.DictWriter`** turns a list of dictionaries into a CSV file. That's the `write()` function.
- **Planting with an answer key** is how you prove a check works: you know the right answer before the SQL runs.

How the weekly runs work (section 9). Each **Action** message has a chance of showing up each week and a size range. Sub Cert (#6) is `.95, (5, 14)`: it shows up 95% of weeks with 5 to 14 people. When a message shows up again, about half of last week's people are still on it and new ones join. That's what makes New, Still Open and Resolved meaningful. **Known Exception** messages show up every week at a steady, large size, the way #88 did.

## Part 2: 01_load_raw.sql (loading)

- `CREATE SCHEMA raw;` makes a folder for tables.
- `CREATE TABLE ... (col text, ...)` makes an empty table.
- `\copy table FROM 'file.csv' WITH (FORMAT csv, HEADER true)` loads the CSV. `\copy` is a psql command that reads the file from your computer.

## Part 3: 02_staging.sql (cleaning)

Each block is `CREATE TABLE staging.x AS SELECT ... FROM raw.x`. That means "make a new table from this query."

| Cleaning | SQL that does it |
| --- | --- |
| Extra spaces in names | `regexp_replace(trim(full_name), '\s+', ' ', 'g')` |
| Text to a real date | `'2026-07-31'::date` |
| Oracle date 23-JUL-2026 | `to_date(change_date, 'DD-MON-YYYY')` |
| US date 07/31/2026 | `to_date(x, 'MM/DD/YYYY')` |
| 00045123 to 45123 | `ltrim(employee_id, '0')` |
| 4712-12-31 means "no end date" | `NULLIF(assignment_end, '4712-12-31')` |
| Blank means NULL | `NULLIF(x, '')` |
| "6. Substitute Certification..." to the number 6 | `split_part(audit_message, '.', 1)::int` |

## Part 4: 03_audit_checks.sql (the audit layer)

**Part A, catalog.** One row per check, with its severity, team and `tracking` (Action or Known Exception). Dashboards slice on these.

**Part B, tagging.** A `JOIN` attaches each audit row to its check by message number. `EXISTS` flags known exceptions: a whole message (like #88), or specific people (the 7 on special leave). The `error_key` (assignment + check) is how the same error is recognized from week to week.

**Part C, week over week.** This is your Monday-vs-Friday comparison, written in SQL.
- `LAG(run_date)` gets the run before each run.
- `LEFT JOIN` last week's rows: no match means the error is **New**, a match means **Still Open**.
- The reverse, last week's rows with no match this week, means **Resolved**. (This is an "anti-join": `LEFT JOIN ... WHERE a.error_key IS NULL`.)
- Known exceptions skip all of that and go to `audit.known_exception_log` as weekly counts.

**Part D, history.** `min(run_date)` = first seen, `max(run_date)` = last seen. If last seen isn't the latest run, the resolved date is the next run after it.

**Part E, exceptions.** The action items open on the latest run. Dashboard A reads this table. It keeps all of version 1's columns, so your Power BI visuals still work.

**Part F, Data Point Checks.** Your own checks, one `INSERT ... SELECT` each. Read them like sentences:

```sql
-- DP04: active contingent workers whose supervisor is terminated
SELECT ...
FROM audit.active a
JOIN staging.assignments s ON s.employee_number = a.supervisor_number   -- look up the supervisor
WHERE a.person_type = 'Contingent Worker'
  AND s.assignment_status = 'Terminated';
```

- **CTE** (`WITH name AS (...)`) = a named sub-query you use right after. DP01 and DP06 use one.
- **`ROW_NUMBER() OVER (PARTITION BY ...)`** numbers rows inside each group. DP01 uses it to grab the latest payroll change. DP06 uses it to find the second copy of a duplicate.
- **`DISTINCT ON`** keeps one row per employee (DP03).
- **`NOT EXISTS`** finds pending workers with no journey at all (DP11).

**Part F2, payroll deadlines.**
- `audit.payroll_status` finds the next Monday-noon fix-by after the latest run and subtracts dates: `fix_by - as_of` = days left. In PostgreSQL, date minus date gives a number of days.
- Every payroll-blocking error in `audit.exceptions` gets that deadline stamped on it.
- `audit.payroll_impact` looks at each pay period: errors on the report the Friday timecards closed are **at risk**. If they're gone by check day they were **saved**, and if they're still there they **missed** the check.

**Part G, proof.** Compares every check to the answer key. Every row should say MATCH.

## Part 5: 04_pipeline.sql (the hiring pipeline)

New hires sit in pre-boarding journeys before their first day. Journeys move one task at a time, so the question is always: **which task is each hire stuck on, and who is it waiting on?**

**Part A, one row per hire (`pipeline.hires`).**
- `DISTINCT ON (pending_worker_id) ... ORDER BY pending_worker_id, task_seq` keeps the first open task per hire: the one Initiated or In Progress.
- `waiting_on` asks whether the task performer is the hire (Employee or Worker) or HC staff (Pre-Employment, HC Partner, HCIS and so on).
- `days_waiting` = 7/31/2026 minus the date the task was assigned. **Stalled** = 3+ days, the same rule Laura's dashboard used.
- `expected_journey` is a `CASE` that says which journey the worker type *should* be on. When it differs from the actual journey, `wrong_journey` is true (a CW sitting on the Non-Certified journey, say).
- `missing_data` uses `concat_ws` to list what's missing (email, phone, SSN, address). `NULLIF(..., '')` turns "nothing missing" into NULL.
- The `LEFT JOIN` to `staging.payroll_calendar` on the start date pulls that pay period's HCIS deadlines.
- Two `UPDATE`s then set one `pipeline_status` per hire (the first problem that applies) and a `start_risk`: **On track**, **At risk** (a problem with the HCIS deadline 14 days away or less), or **Needs follow-up** (a problem, but more time).

**Part B, Laura's four tabs (`pipeline.intervention_list`).** Four `SELECT`s glued together with `UNION ALL`, one per tab. A hire can be on two tabs (stalled *and* missing data), which is why there are 909 rows for fewer hires, just like her export.

**Part C, the cards (`pipeline.status`).** One row of counts plus the next start date and its deadline. Each number is a small `(SELECT count(*) ...)` sub-query. `ORDER BY planned_start_date LIMIT 1` finds the next start date.

**Part D, proof.** Same idea as Part G of file 03: every count against the answer key.

Why start dates aren't random: in `generate_data.py`, hires are ranked by how far along their journey they are, and the most-ready group gets the nearest start date. That's how it works in real life, since the people starting soonest were hired first.

## Do it yourself: practice

1. **Change a count.** In `generate_data.py`, find `plant("DP08", 5)` and the `pick(subs, 5)` line above it. Change both 5s to 8, run `run_all.bat`, and watch DP08 show 8 and MATCH.
2. **Add a check.** Write DP12: "Temp's P-STAR approval ends in the next 30 days" (so the partner can extend it before the temp gets suspended).
   - Copy the DP02 block in `03_audit_checks.sql` and change `'DP02'` to `'DP12'`.
   - Change the `WHERE` to `t.approved_end_date <= DATE '2026-07-31' + 30`.
   - Add a DP12 row to the catalog `INSERT` at the top.
   - Run it. It should find 40 temps (it shows "CHECK THIS" because DP12 isn't in the answer key, which is expected).
3. **Make an error show up more often.** In section 8, change #95's chance from `.55` to `.95`. Run it and check `audit.weekly_summary`: #95 now appears almost every week.
4. **Move a deadline.** Payroll's error fix-by is `timedelta(days=16)` (Monday) in section 5b. Change it to 17 (Tuesday), rerun, and see `days_to_fix_by` go up by one.
5. **Query it yourself.** In pgAdmin or psql, try:
   ```sql
   SELECT run_date, sum(on_report) AS open_items, sum(new_items) AS new, sum(resolved) AS resolved
   FROM audit.weekly_summary GROUP BY run_date ORDER BY run_date;
   ```
   That's the weekly trend line for a dashboard.

## Interview version (30 seconds)

"I rebuilt my weekly HR audit as a pipeline. Python generates realistic exports for a 13,000-person district with errors planted on purpose. PostgreSQL loads and cleans them in raw, staging and audit layers. The audit layer separates known exceptions from real work, tags every error with its owner team, compares each week to the last to flag new, still open and resolved items, and runs my own cross-system checks. Every count reconciles to an answer key, and Power BI shows leadership only what needs action."
