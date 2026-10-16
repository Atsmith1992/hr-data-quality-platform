# HR Data Quality & Operations Platform

An end-to-end HR data pipeline for a fictional 1,800-employee school district: messy exports from eight HR systems go in, every data error comes out in one exceptions table, routed to the team that owns the fix, and shown on Power BI dashboards.

Modeled on the audit and routing work I ran as HRIS Supervisor for a 13,000-employee school district. **All data is synthetic.** No real people or records are used.

## The problem

HR data lives in several systems that don't agree: the HR system of record, a temp approval system, a change log, onboarding journeys, intake forms. Errors such as a teacher moved onto the wrong payroll or a temp whose end date doesn't match the approval reach payroll unless someone catches them first.

## What it does

1. `generate_data.py` creates the fake exports, with errors planted on purpose and an answer key.
2. `sql/01_load_raw.sql` loads the exports into PostgreSQL exactly as received.
3. `sql/02_staging.sql` cleans them: three date formats, zero-padded IDs, stray spaces, Oracle open end dates.
4. `sql/03_audit_checks.sql` runs the audit checks and writes every finding to `audit.exceptions` with a severity and an owner team.
5. Power BI reads the exceptions table for the dashboards.

## Results (first run)

| Check | Severity | Owner | Found |
| --- | --- | --- | --- |
| Active assignment with no salary record | Critical | Compensation | 12 |
| False flip: teacher on 12 Month Payroll | Critical | HCIS | 9 |
| Still active after termination date | Critical | HCIS | 14 |
| Temp end date differs from PSTAR approval | High | HCIS | 8 |
| Future-dated assignment start | High | HCIS | 11 |
| Supervisor is an ex-employee | High | Talent Management | 56 |
| Name formatting error | Medium | HCIS | 17 |
| Substitute with wrong pension code | Medium | HCIS | 6 |

Every check matches the planted answer key in `data/answer_key.csv`.

## Dashboard

   ![Data Quality Command Center](dashboards/dashboard_a.png)

## How to run it

Requires Python 3 and PostgreSQL. No Python packages needed.

```
python generate_data.py
psql -U postgres -c "CREATE DATABASE hr_portfolio;"
psql -U postgres -d hr_portfolio -f sql/01_load_raw.sql
psql -U postgres -d hr_portfolio -f sql/02_staging.sql
psql -U postgres -d hr_portfolio -f sql/03_audit_checks.sql
```

## Tech

Python (standard library) · PostgreSQL · SQL (CTEs, window functions, regex) · Power BI

## Next

- Hiring pipeline dashboard: stalled onboarding tasks, missing data, queue aging
- Team operations dashboard: partner submission quality, transactions by specialist
- AI-drafted escalation notes for each exception, with human approval
