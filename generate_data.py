"""
generate_data.py
Creates fake HR exports for "Harbor City Public Schools", a fictional district.

Every name, ID and number is invented. Errors are planted on purpose so the
SQL audit checks have something to find. Uses only Python's standard library,
so there is nothing to install.

Run from the project folder:
    python generate_data.py
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)                      # same data every run, so results are repeatable
AS_OF = date(2026, 10, 15)           # the "today" the audit runs against
OPEN_END = "4712-12-31"              # Oracle-style open-ended end date
OUT = Path(__file__).parent / "data" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

FIRST = ["James", "Maria", "Robert", "Aisha", "Michael", "Keisha", "David", "Tanya", "Marcus", "Linda",
         "Andre", "Monique", "Kevin", "Erica", "Jamal", "Nicole", "Brian", "Shonda", "Terrence", "Angela",
         "Darnell", "Crystal", "Victor", "Renee", "Calvin", "Denise", "Tyrone", "Patricia", "Omar", "Latoya"]
LAST = ["Walker", "Brooks", "Harris", "Coleman", "Price", "Bennett", "Hayes", "Ward", "Foster", "Graves",
        "Mitchell", "Barnes", "Holloway", "Carter", "Simmons", "Reed", "Jenkins", "Tucker", "Banks", "Owens",
        "Fields", "Gaines", "Wallace", "Lyons", "Porter", "Mack", "Dixon", "Pierce", "Hampton", "Rhodes"]
SCHOOLS = ["0101 - Harbor View Elementary", "0102 - Eastside Middle", "0103 - Northwood High",
           "0104 - Riverside Elementary", "0105 - Lakeshore Academy", "0106 - Westgate Middle",
           "0107 - Pinecrest Elementary", "0108 - Central High", "0201 - District Office",
           "0202 - Transportation", "0203 - Facilities"]
# job_code: (job_name, union, payroll, pension_code, person_type, base_salary)
JOBS = {
    "101545": ("Teacher - Elementary", "TEA", "10 Month Payroll", "S", "Employee", 62000),
    "101590": ("Teacher - Special Education", "TEA", "10 Month Payroll", "S", "Employee", 65000),
    "102831": ("Paraeducator", "PARA", "10 Month Payroll", "D", "Employee", 34000),
    "110081": ("Educational Associate", "PARA", "12 Month Payroll", "C", "Employee", 41000),
    "102390": ("Custodial Worker I", "SUPPORT", "12 Month Payroll", "C", "Employee", 36000),
    "109065": ("Program Manager", "ADMIN", "12 Month Payroll", "C", "Employee", 88000),
    "100770": ("Substitute Teacher", "SUB", "10 Month Payroll", "I", "Employee", 0),
    "103845": ("Temporary Professional I", "TEMP", "12 Month Payroll", "I", "Temp", 0),
    "103875": ("Temporary Support III", "TEMP", "12 Month Payroll", "I", "Temp", 0),
    "900100": ("Contractor - IT Services", "NONE", "No Payroll", "I", "Contingent Worker", 0),
}
TEACHER_JOBS = {"101545", "101590"}
PARTNERS = ["Partner A", "Partner B", "Partner C", "Partner D", "Partner E", "Partner F", "Partner G"]
SPECIALISTS = ["SPEC01", "SPEC02", "SPEC03", "SPEC04"]
REJECT_REASONS = ["Missing position number", "Blocked position", "Incorrect position",
                  "Effective date in the past", "Missing salary information", "Duplicate submission"]

planted = {}   # answer key: check name -> how many errors were planted


def plant(name, n=1):
    planted[name] = planted.get(name, 0) + n


def rand_date(start, end):
    return start + timedelta(days=random.randint(0, (end - start).days))


def write(name, rows, cols):
    with open(OUT / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"  {name}.csv: {len(rows):,} rows")


# ---------------------------------------------------------------- roster
workers = []
emp_num = 40000
job_weights = [30, 10, 14, 6, 8, 5, 8, 6, 5, 3]
for i in range(1800):
    emp_num += random.randint(1, 4)
    job_code = random.choices(list(JOBS), weights=job_weights)[0]
    job_name, union, payroll, pension, person_type, base = JOBS[job_code]
    hire = rand_date(date(1998, 1, 1), date(2026, 8, 1))
    start = rand_date(max(hire, date(2024, 7, 1)), date(2026, 9, 1))
    end = OPEN_END
    if person_type == "Temp":
        end = rand_date(date(2026, 11, 1), date(2027, 6, 30)).isoformat()
    workers.append({
        "employee_number": str(emp_num),
        "assignment_number": f"{emp_num}-{random.randint(1, 6)}",
        "full_name": f"{random.choice(LAST)}, {random.choice(FIRST)}",
        "person_type": person_type,
        "job_code": job_code,
        "job_name": job_name,
        "union_code": union,
        "organization": random.choice(SCHOOLS),
        "payroll": payroll,
        "pension_code": pension,
        "assignment_status": "Active Assignment",
        "hire_date": hire.isoformat(),
        "assignment_start": start.isoformat(),
        "assignment_end": end,
        "termination_date": "",
        "fte": "0" if person_type == "Contingent Worker" else "1.0",
        "position_number": str(300000 + i),
        "supervisor_number": "",
        "visa_type": "",
        "base_salary": base,
    })

# supervisors: give everyone a supervisor from the Program Manager pool
managers = [w for w in workers if w["job_code"] == "109065"]
for w in workers:
    w["supervisor_number"] = random.choice(managers)["employee_number"]

# a small group of terminated workers (needed for "supervisor is ex-employee")
for w in random.sample([w for w in workers if w["job_code"] != "109065"], 60):
    w["assignment_status"] = "Terminated"
    w["termination_date"] = rand_date(date(2025, 6, 1), date(2026, 9, 30)).isoformat()

# PLANT: supervisor is an ex-employee (point to a terminated manager)
termed_mgrs = random.sample(managers, 3)
for m in termed_mgrs:
    m["assignment_status"] = "Terminated"
    m["termination_date"] = rand_date(date(2025, 3, 1), date(2026, 3, 1)).isoformat()
active = [w for w in workers if w["assignment_status"] == "Active Assignment"]

# PLANT: still active after termination date
for w in random.sample(active, 14):
    w["termination_date"] = rand_date(date(2026, 6, 1), date(2026, 10, 1)).isoformat()
    plant("C03 Still active after termination date")

# PLANT: future-dated assignment start (typo year 2027)
for w in random.sample(active, 11):
    w["assignment_start"] = rand_date(date(2027, 6, 1), date(2027, 12, 31)).isoformat()
    plant("H05 Future-dated assignment start")

# PLANT: name formatting errors (all caps, lowercase, double spaces, trailing space)
for w in random.sample(active, 17):
    style = random.choice(["upper", "lower", "double", "trail"])
    if style == "upper":
        w["full_name"] = w["full_name"].upper()
    elif style == "lower":
        w["full_name"] = w["full_name"].lower()
    elif style == "double":
        w["full_name"] = w["full_name"].replace(", ", ",  ")
    else:
        w["full_name"] = w["full_name"] + " "
    plant("M07 Name formatting error")

reports_of_termed = [w for w in workers if w["supervisor_number"] in {m["employee_number"] for m in termed_mgrs}
                     and w["assignment_status"] == "Active Assignment"]
plant("H06 Supervisor is an ex-employee", len(reports_of_termed))


# PLANT: substitutes carrying pension code R (should be I)
subs = [w for w in active if w["job_code"] == "100770"]
for w in random.sample(subs, 6):
    w["pension_code"] = "R"
    plant("M08 Substitute with wrong pension code")

# PLANT: false flip - teacher moved onto 12 Month Payroll
active_teachers = [w for w in active if w["job_code"] in TEACHER_JOBS]
flipped = random.sample(active_teachers, 9)
for w in flipped:
    w["payroll"] = "12 Month Payroll"
    plant("C02 False flip: teacher on 12 Month Payroll")

# international teachers with visa type (used in later weeks)
for w in random.sample(active_teachers, 25):
    w["visa_type"] = random.choice(["J-1", "H-1B"])

roster_cols = [c for c in workers[0] if c != "base_salary"]
write("active_assignments", [{k: w[k] for k in roster_cols} for w in workers], roster_cols)

# ---------------------------------------------------------------- salary
salary_rows = []
paid_workers = [w for w in workers if w["base_salary"] > 0]
missing_salary = set(w["employee_number"] for w in random.sample(
    [w for w in paid_workers if w["assignment_status"] == "Active Assignment"], 12))
plant("C01 Active assignment with no salary record", len(missing_salary))
for w in paid_workers:
    if w["employee_number"] in missing_salary:
        continue
    salary_rows.append({
        "employee_number": w["employee_number"],
        "assignment_number": w["assignment_number"],
        "annual_salary": round(w["base_salary"] * random.uniform(0.9, 1.35), 2),
        "salary_basis": "Annual " + w["payroll"].replace(" Payroll", ""),
        "effective_date": w["assignment_start"],
    })
write("salary", salary_rows, list(salary_rows[0]))

# ---------------------------------------------------------------- change log (Oracle-style dates)
def oracle_date(d):
    return d.strftime("%d-%b-%Y").upper()

change_rows = []
for w in random.sample(active, 700):
    ctype = random.choice(["Assignment Flip - Position", "Assignment Flip - Supervisor",
                           "Assignment Flip - Job", "Assignment Flip - Asg Status"])
    change_rows.append({
        "employee_number": w["employee_number"], "assignment_number": w["assignment_number"],
        "change_type": ctype, "old_value": "previous value", "new_value": "new value",
        "changed_by": random.choice(SPECIALISTS),
        "change_date": oracle_date(rand_date(date(2026, 7, 1), date(2026, 10, 14))),
    })
for w in flipped:
    change_rows.append({
        "employee_number": w["employee_number"], "assignment_number": w["assignment_number"],
        "change_type": "Assignment Flip - Payroll", "old_value": "10 Month Payroll",
        "new_value": "12 Month Payroll", "changed_by": random.choice(SPECIALISTS),
        "change_date": oracle_date(rand_date(date(2026, 8, 1), date(2026, 10, 10))),
    })
random.shuffle(change_rows)
write("assignment_changes", change_rows, list(change_rows[0]))

# ---------------------------------------------------------------- PSTAR temp approvals (messy IDs + US dates)
temps = [w for w in active if w["person_type"] == "Temp"]
pstar_rows = []
mismatch = set(w["employee_number"] for w in random.sample(temps, 8))
plant("H04 Temp end date differs from PSTAR approval", len(mismatch))
for w in temps:
    hr_end = date.fromisoformat(w["assignment_end"])
    approved = hr_end + timedelta(days=random.choice([14, 30, 45])) if w["employee_number"] in mismatch else hr_end
    pstar_rows.append({
        "pstar_txn_id": f"PS{random.randint(100000, 999999)}",
        "employee_id": w["employee_number"].zfill(8),          # 8-character, zero-padded
        "approved_end_date": approved.strftime("%m/%d/%Y"),
        "approval_status": "Approved",
    })
write("temp_approvals", pstar_rows, list(pstar_rows[0]))

# ---------------------------------------------------------------- journey tasks (onboarding, for Dashboard B)
TASKS = [("Personal Information", "New Hire"), ("Background Check", "Pre-Employment"),
         ("Position Assignment", "HC Partner"), ("Salary Verification", "Compensation"),
         ("System Access", "IT"), ("Final Approval", "HCIS")]
journey_rows = []
hire_rows = []
for n in range(320):                                   # upcoming new hires (pending workers)
    pw = f"P{70000 + n}"
    start_day = rand_date(date(2026, 8, 15), date(2026, 11, 30))
    hire_rows.append({"pending_worker_id": pw, "full_name": f"{random.choice(LAST)}, {random.choice(FIRST)}",
                      "organization": random.choice(SCHOOLS), "planned_start_date": start_day.isoformat(),
                      "job_name": random.choice([JOBS[j][0] for j in JOBS])})
    jstart = start_day - timedelta(days=random.randint(20, 75))
    if jstart > AS_OF or random.random() < 0.08:
        continue                                       # journey not started (or never kicked off)
    stall_at = random.choices([None, 0, 1, 2, 3, 4, 5], weights=[35, 12, 10, 12, 14, 9, 8])[0]
    for k, (task, owner) in enumerate(TASKS):
        assigned = jstart + timedelta(days=k * 3)
        if assigned > AS_OF:
            break
        if stall_at is None or k < stall_at:
            status, done = "Completed", (assigned + timedelta(days=random.randint(0, 3))).isoformat()
        elif k == stall_at:
            status, done = "Assigned", ""
        else:
            break
        journey_rows.append({
            "journey_id": f"J{pw}", "pending_worker_id": pw,
            "task_name": task, "owner_team": owner, "assigned_date": assigned.isoformat(),
            "status": status, "completed_date": done,
            "reopened_flag": "Y" if random.random() < 0.04 else "N",
            "missing_data_flag": "Y" if (status == "Assigned" and random.random() < 0.35) else "N",
        })
write("new_hires", hire_rows, list(hire_rows[0]))
write("journey_tasks", journey_rows, list(journey_rows[0]))

# ---------------------------------------------------------------- pending workflow (queue aging)
queues = ["Compensation", "HC Partner", "HCIS", "Talent Management"]
txn_types = ["Change Assignment", "Termination", "Personal Info Change", "Rehire", "Salary Change"]
pending_rows = []
for n in range(420):
    w = random.choice(active)
    q = random.choices(queues, weights=[3, 4, 2, 2])[0]
    age = random.randint(0, 20) if q != "Compensation" else random.randint(0, 110)
    submitted = AS_OF - timedelta(days=age)
    pending_rows.append({
        "txn_id": f"TX{500000 + n}", "employee_number": w["employee_number"],
        "txn_type": random.choice(txn_types), "queue": q,
        "submitted_date": submitted.isoformat(),
        "status": "Pending" if random.random() < 0.55 else "Approved",
    })
write("pending_transactions", pending_rows, list(pending_rows[0]))

# ---------------------------------------------------------------- partner submissions (Smartsheet intake)
sub_rows = []
weak = {"Partner B": 0.30, "Partner D": 0.26, "Partner F": 0.33}
for n in range(640):
    p = random.choice(PARTNERS)
    rejected = random.random() < weak.get(p, 0.10)
    sub_rows.append({
        "submission_id": f"SS{80000 + n}", "partner": p,
        "submission_type": random.choice(["New Hire", "Transfer", "Termination", "Temp Extension", "CW Request"]),
        "submitted_date": rand_date(date(2026, 7, 1), date(2026, 10, 14)).isoformat(),
        "status": "Rejected" if rejected else random.choices(["Complete", "In Progress"], weights=[9, 1])[0],
        "rejection_comment": random.choice(REJECT_REASONS) if rejected else "",
        "specialist": random.choice(SPECIALISTS),
    })
write("partner_submissions", sub_rows, list(sub_rows[0]))

# ---------------------------------------------------------------- ATS users (for later access-revoke check)
ats_rows = []
termed = [w for w in workers if w["assignment_status"] == "Terminated"]
still_access = set(w["employee_number"] for w in random.sample(termed, 9))
plant("M15 Terminated user still holds ATS admin access", len(still_access))
for w in random.sample(active, 150) + termed:
    has = "Y" if (w in termed and w["employee_number"] in still_access) or (w not in termed and random.random() < 0.5) else "N"
    ats_rows.append({"ats_user_id": f"U{w['employee_number']}", "employee_number": w["employee_number"],
                     "admin_access": has})
write("ats_users", ats_rows, list(ats_rows[0]))

# ---------------------------------------------------------------- answer key
with open(OUT.parent / "answer_key.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["check", "errors_planted"])
    for k in sorted(planted):
        w.writerow([k, planted[k]])

print("\nPlanted errors (your SQL checks should find these):")
for k in sorted(planted):
    print(f"  {k}: {planted[k]}")
print(f"\nDone. Files are in {OUT}")
