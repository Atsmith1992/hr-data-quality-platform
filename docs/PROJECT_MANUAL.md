# Project Manual: HR Data Quality & Operations Platform

Everything you need to run, rebuild, explain and extend this project on your own. Keep it open in VS Code (press **Ctrl+Shift+V** to see it formatted) or read it on GitHub.

- For a line-by-line walkthrough of the code, see `docs/HOW_IT_WORKS.md`.
- This manual covers everything around the code: setup, Power BI, GitHub, fixing problems, interview answers, and the skills you need to own.

---

## 1. What this project is

A weekly HR audit, rebuilt as a data pipeline for a fictional 13,091-worker school district, "Harbor City Public Schools."

```
generate_data.py  ->  data/raw/*.csv  ->  raw  ->  staging  ->  audit  ->  Power BI
  (fake exports)       (the files)      (load)    (clean)     (checks)   (dashboard)
```

**The 30-second version for interviews:**
> "I rebuilt the weekly HR audit I ran after our Oracle Fusion go-live as a pipeline. Python generates realistic exports for a 13,000-person district with errors planted on purpose. PostgreSQL loads and cleans them in raw, staging and audit layers. The audit layer separates known exceptions from real work, routes every error to the team that owns it, compares each week to the last, and runs my own cross-system checks. Every count reconciles to an answer key. Power BI shows leadership only what needs action, including how many payroll-blocking errors are open and how many days are left before Payroll's Monday-noon fix-by."

**Headline numbers (as of 7/31/2026):**

| What | Number |
| --- | --- |
| Open errors (action items + Data Point Checks) | 179 (55 + 124) |
| Critical = payroll-blocking | 46 |
| Days to the next payroll fix-by (Mon 8/10, check date 8/14) | 10 |
| Known exceptions, kept in their own log | 4,598 |
| Payroll-blocking errors that missed a check | 19 (PP17) down to 2 (PP28) |

---

## 2. What's real and what's simulated

This answers the worry "I'm building dashboards from data I didn't pull or clean myself."

| Part | Real job | This project | Is it a skill you need? |
| --- | --- | --- | --- |
| **Pulling** the data | Run the HR Audit Report or an OTBI / BI Publisher report in Oracle Fusion, download the CSV or Excel file | `generate_data.py` makes those files, because real HR data is confidential | **Yes, but it's a system skill, not a coding skill.** You've done it for years. In an interview: "In production this is a scheduled BI Publisher export; here a script stands in for it." |
| **Loading** the data | Paste into Excel, or import into a database | `sql/01_load_raw.sql` | **Yes.** Easy to learn (section 9). |
| **Cleaning** the data | Fix dates, IDs, spaces by hand or with formulas | `sql/02_staging.sql` | **Yes. This is a core skill.** Hiring managers test it. |
| **Checking** the data | Your audit checks, Data Point Checks, Monday vs. Friday comparison | `sql/03_audit_checks.sql` | **Yes. This is your strongest story.** The logic is yours; the SQL is the new part. |
| **Showing** the data | Excel summaries, emails to teams | Power BI | **Yes.** You built these pages yourself. |
| Writing a fake-data generator | Nobody does this at work | `generate_data.py` | **No.** Know what it does, not how to write it from scratch. |

**The honest gap:** you designed the checks, the rules and the dashboard, but Claude wrote most of the SQL. Section 9 is the plan to close that gap so you can write and defend every query yourself.

**The honest interview answer if asked "Did you write all of this?"**
> "I designed the checks and business rules from my real audit work and built the dashboards. I used AI to speed up the code, then went through every query until I could explain and change it myself. For example, here's how the week-over-week comparison works..."

That answer is true, common in 2026, and strong as long as you can back it up. Section 9 makes sure you can.

---

## 3. Folder map

```
hr-data-quality-platform/
├── generate_data.py        makes the fake exports + answer key
├── run_all.bat             runs everything in one click
├── README.md               the GitHub front page
├── data/
│   ├── raw/                the fake exports (CSV), rebuilt every run
│   ├── reference/          audit message catalog, known exceptions, payroll calendar
│   └── answer_key.csv      how many errors were planted
├── sql/
│   ├── 01_load_raw.sql     CSV -> raw tables (all text)
│   ├── 02_staging.sql      raw -> clean, typed tables
│   ├── 03_audit_checks.sql staging -> audit answers + proof
│   └── 04_pipeline.sql     staging -> hiring pipeline + proof
├── dashboards/
│   ├── dashboard_a.pbix    Power BI file (both pages)
│   ├── dashboard_a.png     Command Center screenshot
│   ├── payroll_risk.png    Payroll Risk screenshot
│   └── dashboard_a.pdf     both pages as a PDF
└── docs/
    ├── HOW_IT_WORKS.md     code walkthrough + practice
    └── PROJECT_MANUAL.md   this file
```

---

## 4. Setup on a new computer (one time)

1. **Install:**
   - Python 3 (check "Add to PATH" during install)
   - PostgreSQL 18 (remember the password you set for the user `postgres`)
   - VS Code
   - Power BI Desktop
   - GitHub Desktop
2. **Get the repo:** GitHub Desktop → File → Clone repository → `Atsmith1992/hr-data-quality-platform`.
3. **Open it in VS Code:** File → Open Folder → pick the repo folder. Open the terminal with **Ctrl+`**.
4. **Create the database** (one time). In the VS Code terminal:
   ```
   & "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "CREATE DATABASE hr_portfolio;"
   ```
   Type your Postgres password when asked.

---

## 5. Run the pipeline

In the VS Code terminal:
```
.\run_all.bat
```
It asks for your Postgres password, then runs 5 steps:

| Step | What happens |
| --- | --- |
| 1/5 | Python writes the CSVs and prints the planted counts |
| 2/5 | Loads the CSVs into `raw` |
| 3/5 | Cleans them into `staging` |
| 4/5 | Builds `audit` (Dashboard A) and prints its proof table |
| 5/5 | Builds `pipeline` (Dashboard B) and prints its proof table and the start-date countdown |

**What success looks like:** both proof tables have a `result` column, and **every row says MATCH**. Then it says "Done."

**If something fails:** scroll up to the first line that says `ERROR`. Section 8 lists the usual causes.

Run it again any time. It wipes and rebuilds everything, and because of `random.seed(42)` you get the same numbers every time.

---

## 6. Power BI

### Connect (first time only)
1. Home → **Get data** → **More...** → search **PostgreSQL database** → Connect. ("Recent sources" may be empty; that's fine.)
2. Server: `localhost`. Database: `hr_portfolio`. Mode: **Import**.
3. Sign in with **Database** credentials: user `postgres` plus your password.
4. Check these tables, then **Load**:
   - `audit.exceptions`
   - `audit.check_catalog`
   - `audit.payroll_status`
   - `audit.payroll_impact`
   - `audit.weekly_summary`
   - `audit.known_exception_log`
   - for Dashboard B: `pipeline.hires`, `pipeline.intervention_list`, `pipeline.status`
5. **Model view** (left side, third icon): make sure there's a line from `exceptions.check_id` to `check_catalog.check_id`. If not, drag one onto the other.

### After you rerun the pipeline
Home → **Refresh**. That's it. You never rebuild visuals because the data changed.

### Page 1: Command Center

| Visual | Fields | Notes |
| --- | --- | --- |
| Card: **Open Errors** | Count of `exceptions.check_id` | Shows 179 |
| Card: **Critical (payroll-blocking)** | Count of `exceptions.check_id`, visual filter `check_catalog.hits_payroll` = True | Shows 46. Red number. |
| Card: **Days to Fix Before Payroll** | `payroll_status.days_to_fix_by` (Sum is fine, it's one row) | Shows 10. Navy number. |
| Bar chart: **Errors by Check** | Y = `check_catalog.check_name`, X = Count of `exceptions.check_id` | Sort by count, descending |
| Stacked bar: **Errors by Owner Team** | Y = `check_catalog.owner_team`, X = Count of `check_id`, Legend = `check_catalog.source` | HR Audit = navy `#2C3E50`, Data Point Check = gray `#95A5A6` |
| Table | check name, owner team, employee, location, detail, week status | Rename columns with **Rename for this visual** |

### Page 2: Payroll Risk

| Visual | Fields | Notes |
| --- | --- | --- |
| Title + the Critical and Days cards | Copy them from page 1 (Ctrl+C / Ctrl+V) | Title text: **Payroll Risk** |
| **Stacked column chart** (not 100%) | X = `payroll_impact.check_date` (the field itself, not Date Hierarchy). Y = Sum of `saved`, Sum of `missed` | Format → Visual → X-axis → Type = **Categorical**. Rename to Saved / Missed. Saved navy, Missed red. Subtitle off. Short date format via Column tools. |
| Table: **Fix before Monday noon** | `check_name`, `owner_team`, `full_name`, `organization`, `payroll_fix_by`, `days_to_fix_by` | Visual filter `hits_payroll` = True (46 rows). Days column: **Don't summarize**. Totals off. Rename to Check, Team, Employee, Location, Fix by, Days left. |

**How to read page 2:** every pay period, the errors still on the report the Friday timecards close are "at risk." If they're off the report by check day, they were **saved**. If they're still there, they **missed** the check.

### Reusable Power BI moves
- **Rename for this visual:** right-click a field in the field wells.
- **Filter one visual:** drag a field into **Filters on this visual**.
- **Copy formatting:** select the formatted visual → **Format painter** → click the other visual.
- **Date showing Year/Quarter/Month:** click the arrow on the field in the well and pick the plain field name instead of Date Hierarchy.
- **Unwanted totals:** Format → Totals → Off.

---

## 7. Updating GitHub

Every time you change something:

1. **Save:** Ctrl+S in Power BI and in VS Code.
2. **New screenshot (if a page changed):** snip it and save it into `dashboards/`, using the same file name to replace the old one.
3. **README (if you added an image):** add a line like `![Payroll Risk](dashboards/payroll_risk.png)` inside README.md. This goes in the file, **not** the terminal.
4. **GitHub Desktop:** check the Changes list, type a short Summary (e.g. `Add Payroll Risk page`), then **Commit to main** → **Push origin**.
5. **Check:** open the repo page and press **Ctrl+Shift+R** to skip the browser's cached copy.

**PDF export:** Power BI → File → Export → Export to PDF. It opens in your default PDF app (now Edge). Press Ctrl+S in Edge and save to `dashboards/dashboard_a.pdf`.

**Don't** click Power BI's **Publish** button. That's the online Power BI service and needs a work account. GitHub is how this project is shared.

**Can people open the .pbix?** Only if they download it and have Power BI Desktop. Even then, Refresh won't work without your database. They'll see the data as of your last save. That's why the PNGs and the PDF matter.

---

## 8. Troubleshooting

| Problem | Cause | Fix |
| --- | --- | --- |
| `psql is not recognized` | psql isn't on PATH | Use the full path: `& "C:\Program Files\PostgreSQL\18\bin\psql.exe"`. `run_all.bat` already does this. |
| `password authentication failed` | Wrong Postgres password | Retype it. It's the one you chose when installing PostgreSQL. |
| `database "hr_portfolio" does not exist` | Database never created | Run the CREATE DATABASE line in section 4. |
| `could not open file "data/raw/...csv"` | psql ran from the wrong folder | Run `run_all.bat` from the repo folder. It switches to its own folder automatically. |
| Proof table shows **CHECK THIS** | A query or a planted count changed | Compare `found` vs. `expected` for that check. If you added a check on purpose (like DP12), CHECK THIS is expected because it isn't in the answer key. |
| Red error after pasting into the terminal | Pasted file text into the terminal | Paste into the file in the editor instead. Type `cls` to clear the terminal. |
| Power BI "Recent sources" is empty | Normal on first use | Get data → More → PostgreSQL database. |
| Chart shows percentages | 100% stacked chart | Switch to the plain stacked chart. |
| Axis shows months, not each date | Continuous axis | Format → Visual → X-axis → Type → Categorical. |
| Table total says something like "460 days" | Numbers are summed by default | Set the field to Don't summarize, or turn Totals off. |
| Gray bar next to a text box | Text box is too small (scrollbar) | Drag the box bigger. |
| GitHub still shows the old picture | Browser cache | Ctrl+Shift+R. |
| Export to PDF opens Word | Word is the default PDF app | Settings → Default apps → `.pdf` → Microsoft Edge. |
| Commit made but not on GitHub | Not pushed yet | GitHub Desktop → Push origin. |

---

## 9. Owning the skills: your training plan

Do these in order. Each level has a **self-test**: you pass when you can do it with a blank file and no help. Use `docs/HOW_IT_WORKS.md` as the textbook.

### Level 1: Run and explain (you're here)
- [ ] Run `run_all.bat` from a fresh terminal and read the proof table.
- [ ] Explain raw → staging → audit in one sentence each.
- [ ] Rebuild Page 2 from section 6 without looking at the existing one.
- **Self-test:** explain the project out loud in 60 seconds, then answer "how do you know your checks are right?" (Answer: the answer key, the MATCH table.)

### Level 2: Read and change the SQL
- [ ] Do practice exercises 1, 3 and 4 in `HOW_IT_WORKS.md` (change a count, change a frequency, move the fix-by).
- [ ] Open pgAdmin, or psql in the terminal, and run `SELECT * FROM audit.exceptions LIMIT 20;`. Then filter it: `WHERE owner_team = 'HCIS'` (join `check_catalog` to get the team).
- [ ] Write 5 queries of your own against `audit.exceptions`: count by team, count by check, only Critical, only New this week, top 10 locations.
- **Self-test:** someone says "how many HCIS errors are New this week?" and you write the query in under 5 minutes.

### Level 3: Write checks from scratch
- [ ] Practice exercise 2 in `HOW_IT_WORKS.md`: write DP12 (temps whose P-STAR approval ends in 30 days). It should find 40.
- [ ] Delete the DP04 block in a **copy** of `03_audit_checks.sql` and rewrite it from memory. Run it and get MATCH.
- [ ] Rewrite the week-over-week logic (New / Still Open / Resolved) on paper first, then in SQL.
- **Self-test:** given any one of your real audit checks in plain English, you can write the SQL.

### Level 4: Load and clean data you didn't make
This is the part your concern is about, and the next project should cover it:
- [ ] **Project 2 idea:** take a real, public, messy HR dataset (for example, a city government's open employee salary data, which many cities publish) and do the whole pipeline yourself: download it, write `01_load_raw.sql`, find and fix its real problems in `02_staging.sql`, then build a dashboard. Claude coaches and reviews; you write.
- [ ] Learn the basics of Python **pandas** for cleaning (reading CSV, fixing dates, removing duplicates). It's the other tool hiring managers expect.
- **Self-test:** someone hands you a CSV you've never seen and you load it, list its data problems, and clean them.

---

## 10. Interview questions you should be ready for

**"Why fake data?"**
Real HR data is confidential. I built a generator that copies the structure and the problems of the real exports: Oracle date formats, zero-padded IDs, the 4712-12-31 end date, known exceptions. In production the input would be a scheduled Fusion report.

**"How do you know your checks are right?"**
The generator plants errors on purpose and writes an answer key. The last step of the SQL compares what each check found to what was planted, and every row says MATCH.

**"What's a known exception and why separate it?"**
Rows that show up on the report every week no matter what, like mass items waiting on a bulk update or the same people on special leave. They were about 4,600 rows a week and buried the 20 to 70 real errors. Keeping them in their own log means leadership sees only what needs action.

**"How do you track an error week to week?"**
Each error gets a key: assignment number plus check. If the key was on last week's run, it's Still Open; if not, it's New; if it was on last week's run and isn't now, it's Resolved. In SQL that's a LAG to find the previous run and a LEFT JOIN to compare.

**"What does Critical mean on your dashboard?"**
Critical means payroll-blocking: Payroll comes back to us if it isn't fixed by the Monday-noon fix-by before the check date. One definition, so leadership never has to ask what the difference is.

**"What's the payroll chart telling me?"**
For each pay period, how many payroll-blocking errors were fixed before the check (saved) and how many weren't (missed). Misses fell from 19 in pay period 17 to 2 by pay period 28.

**"What would you do differently with real data?"**
Schedule the report export, load it automatically every Friday, and have the dashboard refresh on its own. Then add outreach: a drafted note to each owner team listing their errors, reviewed by a person before it's sent.

---

## 11. What's next

- **Dashboard B, hiring pipeline:** in progress. The SQL is `sql/04_pipeline.sql` (walkthrough in `HOW_IT_WORKS.md` Part 5). This section gets its Power BI build steps once the pages are done.
- **Dashboard C, team operations:** partner submission quality and queue aging.
- **AI layer:** drafted outreach notes per error, approved by a person.
- **Project 2:** real public HR data in a new repo, walked through step by step, where you do the downloading.
- **Project 3:** you write the SQL with coaching (Levels 3 and 4).
