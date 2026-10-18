"""
generate_data.py  (version 2)
Creates fake HR data for "Harbor City Public Schools", a fictional district.

Every name, ID and number is invented. Errors are planted on purpose so the
SQL has something to find. Uses only Python's standard library (nothing to install).

What it writes (all into the data/ folder):
  raw/       the "exports" from each system, the way they'd land on your desk
  reference/ the HR Audit message catalog and the known-exceptions list
  answer_key.csv   how many errors were planted, so you can prove the SQL works

The HR Audit is the post go-live Oracle Fusion HR Audit Report, one run every
Friday from 2/6/2026 to 7/31/2026. Each week has a small set of real errors that
come and go, plus "known exceptions" that show up every week no matter what.

Run from the project folder:
    python generate_data.py
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

# ============================================================== 1. SETTINGS
random.seed(42)                      # same "random" data every run, so results repeat
AS_OF = date(2026, 7, 31)            # the roster snapshot date (last Fusion audit run)
FUSION_RUNS = [date(2026, 2, 6) + timedelta(weeks=i) for i in range(26)]   # 2/6 to 7/31
OPEN_END = "4712-12-31"              # Oracle's "no end date"

HERE = Path(__file__).parent
RAW = HERE / "data" / "raw"
REF = HERE / "data" / "reference"
RAW.mkdir(parents=True, exist_ok=True)
REF.mkdir(parents=True, exist_ok=True)
for old in RAW.glob("*.csv"):        # clear last run's files (and any from version 1)
    old.unlink()

planted = {}        # answer key: check_id -> how many errors we planted


def plant(check_id, n=1):
    planted[check_id] = planted.get(check_id, 0) + n


def rand_date(start, end):
    return start + timedelta(days=random.randint(0, (end - start).days))


def write(folder, name, rows, cols):
    """Write a list of dicts to a CSV file and print the row count."""
    with open(folder / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"  {folder.name}/{name}.csv: {len(rows):,} rows")


# ============================================================== 2. NAMES, SCHOOLS, JOBS
FIRST = ["James", "Maria", "Robert", "Aisha", "Michael", "Keisha", "David", "Tanya", "Marcus", "Linda",
         "Andre", "Monique", "Kevin", "Erica", "Jamal", "Nicole", "Brian", "Shonda", "Terrence", "Angela",
         "Darnell", "Crystal", "Victor", "Renee", "Calvin", "Denise", "Tyrone", "Patricia", "Omar", "Latoya",
         "Jasmine", "Derrick", "Imani", "Gregory", "Tiana", "Russell", "Kendra", "Malik", "Yolanda", "Curtis"]
LAST = ["Walker", "Brooks", "Harris", "Coleman", "Price", "Bennett", "Hayes", "Ward", "Foster", "Graves",
        "Mitchell", "Barnes", "Holloway", "Carter", "Simmons", "Reed", "Jenkins", "Tucker", "Banks", "Owens",
        "Fields", "Gaines", "Wallace", "Lyons", "Porter", "Mack", "Dixon", "Pierce", "Hampton", "Rhodes",
        "Sutton", "Greer", "Chambers", "Nash", "Boyd", "Whitaker", "Spencer", "Gilliam", "Hollis", "Mayfield"]


def person_name():
    return f"{random.choice(LAST)}, {random.choice(FIRST)}"


# 175 fictional schools: a code and a made-up name
PLACES = ["Harbor View", "Eastside", "Northwood", "Riverside", "Lakeshore", "Westgate", "Pinecrest",
          "Cedar Hill", "Maple Park", "Oak Ridge", "Fairmount", "Brookfield", "Highland", "Southport",
          "Bayview", "Elm Street", "Greenspring", "Linden", "Mount Royal", "Patterson", "Liberty",
          "Franklin", "Douglass", "Tubman", "Carver", "Banneker", "Garrison", "Hampden", "Canton",
          "Belair", "Forest Park", "Glenmore", "Irvington", "Lakeland", "Morrell", "Norwood", "Parkside",
          "Roland", "Sandtown", "Waverly"]
TYPES = ["Elementary", "Elementary/Middle", "Middle", "High", "Academy"]
_names = set()
while len(_names) < 175:
    _names.add(f"{random.choice(PLACES)} {random.choice(TYPES)}")
_codes = random.sample(range(1, 460), 175)
SCHOOLS = [f"{c:04d} - {n}" for c, n in zip(sorted(_codes), sorted(_names))]
OFFICES = ["0601 - Human Capital Office", "0612 - Information Technology", "0679 - Secondary Programs",
           "0712 - Pupil Transportation", "0745 - Facilities Management", "0810 - Special Education Office"]
LEAVE_ORG = "2027 - Special Leaves Unpaid"
VACANCY_ORG = "2020 - Vacancy Factor"

# job_code: (job_name, person_type, union, payroll, pension, standard_hours, weight)
JOBS = {
    "101545": ("Teacher - Elementary",         "Employee", "TEA",     "10 Month Payroll", "S", 35.5, 34),
    "101590": ("Teacher - Special Education",  "Employee", "TEA",     "10 Month Payroll", "S", 35.5, 10),
    "101610": ("Teacher - High School",        "Employee", "TEA",     "10 Month Payroll", "S", 35.5, 9),
    "102831": ("Paraeducator",                 "Employee", "PARA",    "10 Month Payroll", "D", 35.5, 12),
    "110081": ("Educational Associate",        "Employee", "PARA",    "12 Month Payroll", "C", 40.0, 4),
    "102390": ("Custodial Worker I",           "Employee", "SUPPORT", "12 Month Payroll", "C", 40.0, 8),
    "104120": ("Bus Attendant",                "Employee", "SUPPORT", "10 Month Payroll", "C", 30.0, 3),
    "109065": ("Program Manager",              "Employee", "ADMIN",   "12 Month Payroll", "C", 40.0, 4),
    "109010": ("Principal",                    "Employee", "ADMIN",   "12 Month Payroll", "C", 40.0, 0),
    "100770": ("Teacher - Substitute",         "Substitute", "SUB",   "10 Month Payroll", "I", 0.0, 9),
    "103845": ("Temporary Professional I",     "Temporary Employee", "TEMP", "12 Month Payroll", "I", 40.0, 4),
    "103875": ("Temporary Support III",        "Temporary Employee", "TEMP", "12 Month Payroll", "I", 40.0, 3),
    "103890": ("Home & Hospital Teacher",      "Temporary Employee", "TEMP", "10 Month Payroll", "I", 20.0, 0),
    "900100": ("Contractor - Services",        "Contingent Worker", "NONE", "No Payroll", "I", 0.0, 5),
}
TEACHER_JOBS = {"101545", "101590", "101610"}
TEMP_JOBS = {"103845", "103875"}
SPECIALISTS = ["SPEC01", "SPEC02", "SPEC03", "SPEC04"]

# ============================================================== 3. ROSTER (~13,000 workers)
# One row per assignment, like the HR Active Assignments report.
workers = []
emp_num = 40000
cw_num = 906000
job_codes = [j for j in JOBS if JOBS[j][6] > 0]
weights = [JOBS[j][6] for j in job_codes]


def new_worker(job_code, org=None, status="Active - Payroll Eligible"):
    global emp_num, cw_num
    job_name, ptype, union, payroll, pension, hours, _ = JOBS[job_code]
    if ptype == "Contingent Worker":
        cw_num += random.randint(1, 3)
        num = str(cw_num)
        asg = f"C{num}"
        status = "Active - No Payroll"
    else:
        emp_num += random.randint(1, 6)
        num = str(emp_num)
        asg = f"E{num}"
    hire = rand_date(date(1999, 1, 1), date(2026, 6, 30))
    start = rand_date(max(hire, date(2025, 11, 19)), date(2026, 7, 15)) if random.random() < 0.3 \
        else max(hire, date(2025, 11, 19))                      # 11/19/2025 = Fusion conversion date
    w = {
        "employee_number": num, "assignment_number": asg, "full_name": person_name(),
        "person_type": ptype, "job_code": job_code, "job_name": job_name, "union_code": union,
        "organization": org or (random.choice(OFFICES) if job_code in ("109065",) or ptype == "Contingent Worker"
                                and random.random() < 0.3 else random.choice(SCHOOLS)),
        "payroll": payroll, "pension_code": pension, "assignment_status": status,
        "hire_date": hire.isoformat(), "assignment_start": start.isoformat(), "assignment_end": OPEN_END,
        "termination_date": "", "suspension_date": "",
        "fte": "0" if ptype in ("Contingent Worker", "Substitute") else "1.0",
        "standard_hours": hours,
        "position_number": "" if ptype == "Substitute" else str(random.randint(400000, 489999)),
        "supervisor_number": "", "visa_type": "",
    }
    if ptype == "Substitute":
        w["position_number"] = "400001"          # everyone shares the sub pool position
    workers.append(w)
    return w


for org in SCHOOLS:                               # one principal per school
    new_worker("109010", org=org)
for _ in range(12900):
    new_worker(random.choices(job_codes, weights=weights)[0])

# Home & Hospital teachers are Temporary Employee on purpose (not a mismatch)
for _ in range(6):
    new_worker("103890")

principals = {w["organization"]: w for w in workers if w["job_code"] == "109010"}
managers = [w for w in workers if w["job_code"] == "109065"]
for w in workers:                                 # schools roll up to the principal
    if w["job_code"] == "109010":
        w["supervisor_number"] = random.choice(managers)["employee_number"]
    elif w["organization"] in principals:
        w["supervisor_number"] = principals[w["organization"]]["employee_number"]
    else:
        w["supervisor_number"] = random.choice(managers)["employee_number"]

# Terminated workers (about 1,600 left the district in 2026)
for w in random.sample([w for w in workers if w["job_code"] not in ("109010", "109065")], 1600):
    w["assignment_status"] = "Terminated"
    w["termination_date"] = rand_date(date(2026, 1, 5), date(2026, 7, 24)).isoformat()

active = [w for w in workers if w["assignment_status"] != "Terminated"]
temps = [w for w in active if w["job_code"] in TEMP_JOBS]
subs = [w for w in active if w["person_type"] == "Substitute"]
cws = [w for w in active if w["person_type"] == "Contingent Worker"]
teachers = [w for w in active if w["job_code"] in TEACHER_JOBS]
regular = [w for w in active if w["person_type"] == "Employee" and w["job_code"] not in ("109010", "109065")]

# Temps: end date from P-STAR, suspension date = P-STAR end date + 1 day
for w in temps:
    end = rand_date(date(2026, 8, 15), date(2027, 6, 30))
    w["assignment_end"] = end.isoformat()
    w["suspension_date"] = (end + timedelta(days=1)).isoformat()
    w["pstar_end"] = end

# Known exceptions that show up on the HR Audit every week
special_leave = random.sample(regular, 7)                 # #31 and #9: same 7 people
for w in special_leave:
    w["organization"] = LEAVE_ORG
    w["assignment_status"] = "Active - No Payroll"
international = random.sample([w for w in teachers if w not in special_leave], 3)   # #5
for w in international:
    w["visa_type"] = "J-1"
for w in random.sample(teachers, 22):
    w["visa_type"] = w["visa_type"] or random.choice(["J-1", "H-1B"])

# ============================================================== 4. HCIS DATA POINT CHECKS (plants)
# These are Antonio's own checks, run with SQL against the roster.
used = set(id(w) for w in special_leave + international)


def pick(pool, n):
    """Pick n workers nobody else has planted on, so each check's count stays exact."""
    choices = [w for w in pool if id(w) not in used]
    chosen = random.sample(choices, n)
    used.update(id(w) for w in chosen)
    return chosen


# DP01 False flip: a 10-month teacher moved onto 12 Month Payroll
flipped = pick(teachers, 9)
for w in flipped:
    w["payroll"] = "12 Month Payroll"
plant("DP01", 9)

# DP02 Temp suspension date doesn't equal P-STAR end date + 1
for w in pick(temps, 8):
    w["suspension_date"] = (w["pstar_end"] + timedelta(days=random.choice([-14, 0, 31]))).isoformat()
plant("DP02", 8)
# (temps with NO suspension date are left for the HR Audit, message #90)
no_susp = pick(temps, 4)
for w in no_susp:
    w["suspension_date"] = ""

# DP04 CW Manager Update: 6 terminated supervisors still over 22 active CWs (one has 17)
termed_sups = random.sample([m for m in managers], 6)
for m in termed_sups:
    m["assignment_status"] = "Terminated"
    m["termination_date"] = rand_date(date(2025, 5, 1), date(2026, 6, 1)).isoformat()
termed_sups[0]["termination_date"] = "2025-05-09"          # the one 14+ months gone
live_mgrs = [m for m in managers if m not in termed_sups]
for w in workers:                                          # nobody else reports to them
    if w["supervisor_number"] in {m["employee_number"] for m in termed_sups}:
        w["supervisor_number"] = random.choice(live_mgrs)["employee_number"]
orphaned = pick(cws, 22)
for i, w in enumerate(orphaned):
    w["supervisor_number"] = termed_sups[0 if i < 17 else i - 16]["employee_number"]
plant("DP04", 22)

# DP05 Person type doesn't fit the job (Home & Hospital temps are the allowed exception)
for w in pick(regular, 7):
    w["person_type"] = "Temporary Employee"
for w in pick(temps, 5):
    w["person_type"] = "Employee"
plant("DP05", 12)

# DP06 Duplicate assignment: same person, same job, same school, two active rows
dupes = pick(regular, 10)
for w in dupes:
    twin = dict(w)
    twin["assignment_number"] = w["assignment_number"] + "-2"
    twin["assignment_start"] = (date.fromisoformat(w["assignment_start"]) + timedelta(days=random.randint(1, 40))).isoformat()
    workers.append(twin)
plant("DP06", 10)

# DP07 Name formatting: 1 all caps, 16 with extra spaces
fmt = pick(active, 17)
fmt[0]["full_name"] = fmt[0]["full_name"].upper()
for w in fmt[1:]:
    w["full_name"] = random.choice([w["full_name"].replace(", ", ",  "), w["full_name"] + " ",
                                    " " + w["full_name"]])
plant("DP07", 17)

# DP08 Substitute carrying pension code R (Retired Rehire) instead of I (Ineligible)
for w in pick(subs, 5):
    w["pension_code"] = "R"
plant("DP08", 5)

roster_cols = ["employee_number", "assignment_number", "full_name", "person_type", "job_code", "job_name",
               "union_code", "organization", "payroll", "pension_code", "assignment_status", "hire_date",
               "assignment_start", "assignment_end", "termination_date", "suspension_date", "fte",
               "standard_hours", "position_number", "supervisor_number", "visa_type"]
write(RAW, "active_assignments", [{k: w[k] for k in roster_cols} for w in workers], roster_cols)
by_num = {w["employee_number"]: w for w in workers}

# ============================================================== 5. OTHER SYSTEM EXPORTS


def oracle_date(d):
    return d.strftime("%d-%b-%Y").upper()            # 23-JUL-2026


# Change log: proof of who flipped each teacher's payroll
changes = []
for w in random.sample(active, 900):
    changes.append({"employee_number": w["employee_number"], "assignment_number": w["assignment_number"],
                    "change_type": random.choice(["Change Assignment - Position", "Change Assignment - Manager",
                                                  "Change Assignment - Job", "Change Assignment - Status"]),
                    "old_value": "previous value", "new_value": "new value",
                    "changed_by": random.choice(SPECIALISTS),
                    "change_date": oracle_date(rand_date(date(2026, 2, 1), date(2026, 7, 30)))})
for w in flipped:
    changes.append({"employee_number": w["employee_number"], "assignment_number": w["assignment_number"],
                    "change_type": "Change Assignment - Payroll", "old_value": "10 Month Payroll",
                    "new_value": "12 Month Payroll", "changed_by": random.choice(SPECIALISTS),
                    "change_date": oracle_date(rand_date(date(2026, 4, 1), date(2026, 7, 28)))})
random.shuffle(changes)
write(RAW, "assignment_changes", changes, list(changes[0]))

# P-STAR temp approvals: 8-character zero-padded IDs, US-style dates
pstar = []
for w in temps:
    pstar.append({"pstar_txn_id": f"4{random.randint(1000000, 9999999)}",
                  "employee_id": w["employee_number"].zfill(8),
                  "position_number": w["position_number"],
                  "approved_end_date": w["pstar_end"].strftime("%m/%d/%Y"),
                  "approval_status": "Approved", "processed_by": "HCIS"})
# DP10 legacy 300K positions: should be flagged to Systems, never processed by HCIS
legacy = random.sample(temps, 16)
for i, w in enumerate(legacy):
    row = next(r for r in pstar if r["employee_id"] == w["employee_number"].zfill(8))
    row["position_number"] = str(random.randint(300000, 389999))
    row["processed_by"] = "HCIS" if i < 6 else "Flagged to Systems"
plant("DP10", 6)
write(RAW, "temp_approvals", pstar, list(pstar[0]))

# PowerSchool ATS users: terminated staff should have no admin access
termed = [w for w in workers if w["assignment_status"] == "Terminated"]
still_admin = set(w["employee_number"] for w in random.sample(termed, 27))
ats = []
for w in random.sample(active, 2500) + termed:
    admin = "Y" if w["employee_number"] in still_admin else ("N" if w in termed else random.choice("YN"))
    ats.append({"ats_user_id": f"U{w['employee_number']}", "employee_number": w["employee_number"],
                "admin_access": admin})
plant("DP03", 27)
write(RAW, "ats_users", ats, list(ats[0]))

# ============================================================== 5b. PAYROLL CALENDAR (SY25-26 Fusion era)
# Biweekly. Every date is an offset from the Pay Period Start (a Saturday).
# Rhythm: Tue submit -> Thu HCIS process -> Sat start -> (2 weeks) -> Fri timecards
#         -> Mon noon error fix-by -> Tue payroll run -> Thu pay stub -> Fri paid
# From PP27 (FY27) HCIS deadlines moved to Monday submit / Wednesday process.
PP_NOTES = {
    13: "Fusion live; no HCIS deadlines (cutover)",
    17: "IBM bug mass-suspends temps ~2/27",
    18: "First Fusion punch-to-pay run; 71 temps at risk",
    19: "Sub Cert escalation to Recruitment sent 3/27",
    20: "IBM fix to production 3/21",
    25: "Payroll's noon deadline 6/15: 4 subs missing Sub Cert, fixed same day",
    27: "FY27 deadlines move to Monday submit / Wednesday process",
    28: "Last SY25-26 check",
    30: "First pay of SY26-27; 10-month effective date 8/8",
}
payroll_calendar = []
for pp in range(13, 34):
    start = date(2025, 12, 13) + timedelta(weeks=2 * (pp - 13))
    submit = start - timedelta(days=5 if pp >= 27 else 4)
    process = start - timedelta(days=3 if pp >= 27 else 2)
    check = start + timedelta(days=20)
    payroll_calendar.append({
        "pay_period": pp,
        "school_year": "SY25-26" if check <= date(2026, 7, 31) else "SY26-27",
        "hcis_submission_deadline": "" if pp == 13 else submit.isoformat(),
        "hcis_processing_deadline": "" if pp == 13 else process.isoformat(),
        "credentials_date": (start - timedelta(days=1)).isoformat(),
        "pay_period_start": start.isoformat(),
        "physical_start": (start + timedelta(days=2)).isoformat(),
        "pay_period_end": (start + timedelta(days=13)).isoformat(),      # timecards approved by 6pm
        "payroll_error_fix_by": (start + timedelta(days=16)).isoformat(),  # Monday noon
        "blackout_start": (start + timedelta(days=16)).isoformat(),
        "blackout_end": (start + timedelta(days=17)).isoformat(),
        "payroll_file_run": (start + timedelta(days=17)).isoformat(),
        "ess_pay_slip": (start + timedelta(days=19)).isoformat(),
        "check_date": check.isoformat(),
        "note": PP_NOTES.get(pp, ""),
    })
write(REF, "payroll_calendar", payroll_calendar, list(payroll_calendar[0]))
PP_STARTS_AHEAD = [date.fromisoformat(r["pay_period_start"]) for r in payroll_calendar
                   if date(2026, 8, 1) <= date.fromisoformat(r["pay_period_start"]) <= date(2026, 9, 30)]

# ============================================================== 6. JOURNEYS (real templates)
JOURNEYS = {
    "Pre-boarding - Certified Role": [
        ("Verify and Update your Personal Information", "Employee"),
        ("Verify and Update your Contact Information", "Employee"),
        ("Verify and Update your U.S. Visa Information, if applicable", "Employee"),
        ("Fill out the I-9 Online Link", "Employee"),
        ("Upload your I-9 Supporting Documents", "Employee"),
        ("Complete Criminal Background and Medical Clearance agreement", "Employee"),
        ("Schedule your Background Check", "Employee"),
        ("Sign the Reasonable Assurance Notification for 10-month employees", "Employee"),
        ("Complete Retirement Questions", "Employee"),
        ("Verify and Update your Education Information", "Employee"),
        ("Register your educator certification account with the MSDE TEACH portal", "Employee"),
        ("Submit Official Transcripts", "Employee"),
        ("Verified Employee submission of HB486 and send out forms to former employers", "Pre-Employment"),
        ("Review I-9 Supporting Documents", "Pre-Employment"),
        ("Review Background Check Results", "Pre-Employment"),
        ("Complete Certification Review", "Certification"),
        ("Review retirement questions and update pension codes as required", "Retirement"),
        ("Confirm Reasonable Assurance for 10-month employees was appropriately signed", "Employee Engagement"),
        ("Confirm Position Number employee is being hired into", "HC Partner"),
        ("Confirm final salary and select official start date", "Compensation"),
        ("Complete HCIS Audit and flip Pending Worker to Employee", "HCIS")],
    "Pre-boarding - Non-Certified Role": [
        ("Verify and Update your Personal Information", "Employee"),
        ("Verify and Update your Contact Information", "Employee"),
        ("Verify and Update your U.S. Visa Information, if applicable", "Employee"),
        ("Fill out the I-9 Online Link", "Employee"),
        ("Upload your I-9 Supporting Documents", "Employee"),
        ("Complete Criminal Background and Medical Clearance agreement", "Employee"),
        ("Schedule your Background Check", "Employee"),
        ("Sign the Reasonable Assurance Notification for 10-month employees", "Employee"),
        ("Complete Retirement Questions", "Employee"),
        ("Verify and Update your Education Information", "Employee"),
        ("Submit Unofficial Transcripts", "Employee"),
        ("Verified Employee submission of HB486 and send out forms to former employers", "Pre-Employment"),
        ("Review I-9 Supporting Documents", "Pre-Employment"),
        ("Review Background Check Results", "Pre-Employment"),
        ("Verify education information submitted is aligned with submitted transcript", "HC Partner"),
        ("Review retirement questions and update pension codes as required", "Retirement"),
        ("Confirm Reasonable Assurance for 10-month employees was appropriately signed", "Employee Engagement"),
        ("Confirm Position Number employee is being hired into", "HC Partner"),
        ("Confirm final salary and select official start date", "Compensation"),
        ("Complete HCIS Audit and flip Pending Worker to Employee", "HCIS")],
    "Pre-boarding - Contingent Worker Role": [
        ("Verify and Update your Personal Information", "Worker"),
        ("Verify and Update your Contact Information", "Worker"),
        ("Schedule your Background Check", "Worker"),
        ("Review Background Check Results", "Pre-Employment"),
        ("Confirm Department Contractor is being hired into", "HC Partner"),
        ("Complete HCIS Audit and flip Pending Worker to Contingent Worker", "HCIS")],
    "Pre-boarding - Temporary Role": [
        ("Verify and Update your Personal Information", "Employee"),
        ("Verify and Update your Contact Information", "Employee"),
        ("Fill out the I-9 Online Form", "Employee"),
        ("Upload your I-9 Supporting Documents", "Employee"),
        ("Complete Criminal Background and Medical Clearance Agreement", "Employee"),
        ("Schedule your Background Check", "Employee"),
        ("Review I-9 Supporting Documents", "Pre-Employment"),
        ("Review Background Check Results", "Pre-Employment"),
        ("Confirm Position Number employee is being hired into", "HC Partner"),
        ("Complete HCIS Audit and flip Pending Worker to Employee", "HCIS")],
}
CANDIDATE = {"Employee", "Worker"}            # tasks that sit with the new hire
REOPEN_REASONS = ["Missing SSN", "Missing address", "Missing marital status", "Missing gender",
                  "Missing date of birth", "Missing phone number"]

# 1,060 pending workers. proposed type -> normal journey
mix = (["Employee-Certified"] * 360 + ["Employee-Non-Certified"] * 180 + ["Substitute"] * 120
       + ["Contingent Worker"] * 200 + ["Temporary Employee"] * 200)
random.shuffle(mix)
NORMAL = {"Employee-Certified": "Pre-boarding - Certified Role",
          "Employee-Non-Certified": "Pre-boarding - Non-Certified Role",
          "Substitute": "Pre-boarding - Non-Certified Role",
          "Contingent Worker": "Pre-boarding - Contingent Worker Role",
          "Temporary Employee": "Pre-boarding - Temporary Role"}
JOB_FOR = {"Employee-Certified": "101545", "Employee-Non-Certified": "102831", "Substitute": "100770",
           "Contingent Worker": "900100", "Temporary Employee": "103845"}

hires = []
for n, kind in enumerate(mix):
    job = JOB_FOR[kind]
    hires.append({"pending_worker_id": f"AP{70000 + n}", "full_name": person_name(),
                  "proposed_worker_type": "Employee" if kind.startswith("Employee") else kind,
                  "job_name": JOBS[job][0], "bargaining_unit": JOBS[job][2],
                  "organization": random.choice(SCHOOLS),
                  "planned_start_date": random.choice(PP_STARTS_AHEAD).isoformat(),   # starts land on a pay period Saturday
                  "personal_email": f"hire{70000 + n}@example.com",
                  "primary_phone": f"555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
                  "national_id_provided": "Y", "address_provided": "Y",
                  "journey_name": NORMAL[kind], "kind": kind})

# Misrouted stragglers still found after the 2/5 and ~2/20 cutovers
for h in random.sample([h for h in hires if h["kind"] == "Contingent Worker"], 8):
    h["journey_name"] = "Pre-boarding - Non-Certified Role"
for h in random.sample([h for h in hires if h["kind"] == "Temporary Employee"], 3):
    h["journey_name"] = "Pre-boarding - Non-Certified Role"
for h in random.sample([h for h in hires if h["kind"] == "Employee-Non-Certified"], 15):
    h["journey_name"] = "Pre-boarding - Temporary Role"

# DP11 Pending worker created with no journey (the go-live auto-journey bug)
no_journey = random.sample([h for h in hires if h["kind"] in ("Employee-Certified", "Employee-Non-Certified")], 5)
for h in no_journey:
    h["journey_name"] = ""
plant("DP11", 5)

# Laura's dashboard buckets: 307 stalled with the hire, 321 stalled with HC staff, the rest fresh
with_journey = [h for h in hires if h["journey_name"]]
random.shuffle(with_journey)
buckets = ["stalled_candidate"] * 307 + ["stalled_staff"] * 321
buckets += ["fresh"] * (len(with_journey) - len(buckets))
reopened = set()
fresh = [h for h, b in zip(with_journey, buckets) if b == "fresh"]
for h in random.sample(fresh, 34):
    reopened.add(h["pending_worker_id"])
missing = random.sample(with_journey, 247)
for h in missing:
    field = random.choice(["personal_email", "primary_phone", "national_id_provided", "address_provided"])
    h[field] = "N" if field.endswith("provided") else ""

tasks = []
for h, bucket in zip(with_journey, buckets):
    steps = JOURNEYS[h["journey_name"]]
    if bucket == "stalled_candidate" or h["pending_worker_id"] in reopened:
        options = [i for i, s in enumerate(steps) if s[1] in CANDIDATE]
    elif bucket == "stalled_staff":
        options = [i for i, s in enumerate(steps) if s[1] not in CANDIDATE]
    else:
        options = list(range(len(steps)))
    cur = random.choice(options)
    age = random.randint(3, 45) if bucket.startswith("stalled") else random.randint(0, 2)
    cur_assigned = AS_OF - timedelta(days=age)
    # walk backwards to give completed tasks believable dates
    day = cur_assigned
    dates = {}
    for i in range(cur - 1, -1, -1):
        dates[i] = day - timedelta(days=random.randint(0, 3))
        day = dates[i]
    for i, (task, performer) in enumerate(steps):
        if i < cur:
            status, assigned, done = "Completed", dates[i], dates[i] + timedelta(days=random.randint(0, 2))
            done = min(done, cur_assigned)
        elif i == cur:
            status, assigned, done = random.choice(["Initiated", "In Progress"]), cur_assigned, None
        else:
            status, assigned, done = "Dependent", None, None
        is_reopen = i == cur and h["pending_worker_id"] in reopened
        tasks.append({"journey_id": f"J{h['pending_worker_id'][2:]}", "pending_worker_id": h["pending_worker_id"],
                      "journey_name": h["journey_name"], "task_seq": i + 1, "task_name": task,
                      "task_performer": performer, "task_status": status,
                      "assigned_date": assigned.isoformat() if assigned else "",
                      "completed_date": done.isoformat() if done else "",
                      "reopened_flag": "Y" if is_reopen else "N",
                      "reopen_reason": random.choice(REOPEN_REASONS) if is_reopen else ""})
plant("LAURA_STALLED_HIRES", 307)
plant("LAURA_HC_STAFF_TASKS", 321)
plant("LAURA_REOPENED_TASKS", 34)
plant("LAURA_MISSING_DATA", 247)

hire_cols = ["pending_worker_id", "full_name", "proposed_worker_type", "job_name", "bargaining_unit",
             "organization", "planned_start_date", "personal_email", "primary_phone",
             "national_id_provided", "address_provided"]
write(RAW, "new_hires", [{k: h[k] for k in hire_cols} for h in hires], hire_cols)
write(RAW, "journey_tasks", tasks, list(tasks[0]))

# CW Smartsheet: every CW pending worker should have a request... except 3 (DP09)
cw_hires = [h for h in hires if h["kind"] == "Contingent Worker" and h["journey_name"]]
no_request = set(h["pending_worker_id"] for h in random.sample(
    [h for h in cw_hires if h["journey_name"] == "Pre-boarding - Contingent Worker Role"], 3))
plant("DP09", 3)
sheet = []
for i, h in enumerate(cw_hires):
    if h["pending_worker_id"] in no_request:
        continue
    sheet.append({"submission_id": 2400 + i, "pending_worker_id": h["pending_worker_id"],
                  "cw_name": h["full_name"], "request_type": "Request Access (for a new contingent worker)",
                  "organization": h["organization"], "status": "Journey Initiated",
                  "submitted_date": rand_date(date(2026, 5, 1), date(2026, 7, 20)).isoformat()})
for i, w in enumerate(random.sample(cws, 150)):           # older, already processed requests
    sheet.append({"submission_id": 1800 + i, "pending_worker_id": "", "cw_name": w["full_name"],
                  "request_type": random.choice(["Request Access (for a new contingent worker)",
                                                 "Extend Access (for a current contingent worker)"]),
                  "organization": w["organization"], "status": "Processed",
                  "submitted_date": rand_date(date(2026, 2, 5), date(2026, 6, 30)).isoformat()})
write(RAW, "cw_smartsheet", sheet, list(sheet[0]))

# ============================================================== 7. QUEUES AND PARTNER SUBMISSIONS (Dashboard C)
pending_rows = []
for n in range(420):
    w = random.choice(active)
    q = random.choices(["Compensation", "HC Partner", "HCIS", "Talent Management"], weights=[3, 4, 2, 2])[0]
    age = random.randint(0, 110) if q == "Compensation" else random.randint(0, 20)
    pending_rows.append({"txn_id": f"TX{500000 + n}", "employee_number": w["employee_number"],
                         "txn_type": random.choice(["Change Assignment", "Termination", "Personal Info Change",
                                                    "Rehire", "Salary Change"]),
                         "queue": q, "submitted_date": (AS_OF - timedelta(days=age)).isoformat(),
                         "status": "Pending" if random.random() < 0.55 else "Approved"})
write(RAW, "pending_transactions", pending_rows, list(pending_rows[0]))

PARTNERS = ["Partner A", "Partner B", "Partner C", "Partner D", "Partner E", "Partner F", "Partner G"]
REJECT = ["Missing position number", "Blocked position", "Incorrect position",
          "Effective date in the past", "Missing salary information", "Duplicate submission"]
weak = {"Partner B": 0.30, "Partner D": 0.26, "Partner F": 0.33, "Partner G": 0.24}
subs_rows = []
for n in range(640):
    p = random.choice(PARTNERS)
    rej = random.random() < weak.get(p, 0.10)
    subs_rows.append({"submission_id": f"SS{80000 + n}", "partner": p,
                      "submission_type": random.choice(["New Hire", "Transfer", "Termination",
                                                        "Temp Extension", "CW Request"]),
                      "submitted_date": rand_date(date(2026, 3, 1), date(2026, 7, 31)).isoformat(),
                      "status": "Rejected" if rej else random.choices(["Complete", "In Progress"], [9, 1])[0],
                      "rejection_comment": random.choice(REJECT) if rej else "",
                      "specialist": random.choice(SPECIALISTS)})
write(RAW, "partner_submissions", subs_rows, list(subs_rows[0]))

# ============================================================== 8. HR AUDIT CATALOG (Fusion, post go-live)
# Two kinds of messages, the way the audit actually worked:
#   ACTION           real errors a team had to fix that week (small counts, come and go)
#   KNOWN EXCEPTION  showed up every week no matter what (mass volume, or the same people)
#                    -> kept in their own log so they don't drown out the real work
D = date

# msg_no -> (message, team, severity, level, chance it shows up in a week, (min, max) when it does, why)
ACTION = {
    2:  ("Employee Gender is Missing", "Pre-Employment", "High", "emp", .6, (2, 6),
         "Required for state and federal reporting"),
    3:  ("Supervisor is blank", "Talent Management", "Medium", "emp", .65, (2, 7),
         "No one can approve time or tasks"),
    5:  ("Social Security Number is invalid", "Pre-Employment", "High", "emp", .35, (1, 3),
         "Tax reporting fails"),
    6:  ("Substitute Certification is Missing", "Recruitment", "Critical", "emp", .95, (5, 14),
         "Subs can't be paid without the cert flag"),
    9:  ("Salary record is Missing", "Compensation", "Critical", "emp", .4, (1, 4),
         "Employee won't be paid"),
    10: ("Active Assignment associated with an inactive position", "Talent Management", "Medium", "emp", .95, (8, 18),
         "Mostly temps with no P-STAR submitted"),
    16: ("Position is missing from Assignment", "HCIS", "High", "emp", .4, (1, 4),
         "Can't cost or budget the assignment"),
    17: ("Position Costing does not equal 100%", "Talent Management", "Critical", "pos", .7, (3, 9),
         "Pay charged to the wrong budget"),
    23: ("Position Costing contains duplicate records", "HCIS", "Medium", "pos", .4, (1, 4),
         "Costing double counts"),
    76: ("Employee Assignment FTE is Overallocated", "Talent Management", "Critical", "emp", .7, (2, 6),
         "Person is paid over 1.0 FTE"),
    77: ("Employee has multiple Active Work Relationships", "HCIS", "Critical", "emp", .4, (1, 3),
         "Duplicate pay risk"),
    83: ("Employee has multiple active assignments in different job titles", "HCIS", "Medium", "emp", .5, (2, 5),
         "Possible duplicate assignment"),
    90: ("Temporary employee without future suspension date", "HCIS", "Critical", "emp", .9, (3, 9),
         "Temp keeps getting paid past approval"),
    91: ("Active Job missing Budgeted and/or Fringe Amount", "Compensation", "Medium", "pos", .5, (2, 5),
         "Budget planning gap"),
    93: ("Position EIT and Position Costing does not match", "HCIS", "Medium", "pos", .35, (1, 3),
         "Two costing sources disagree"),
    95: ("Contingent Worker missing Department", "HCIS", "Medium", "emp", .55, (2, 6),
         "Can't route the contractor"),
}

# msg_no -> (message, team, severity, level, curve [(date, count)], why it's a known exception)
KNOWN = {
    18: ("Position Costing is Missing", "Talent Management", "High", "pos",
         [(D(2026, 2, 6), 126), (D(2026, 4, 3), 60), (D(2026, 7, 31), 35)], "Recurring mass item"),
    19: ("Employee hours do not match Job standard Hours", "HCIS", "Medium", "emp",
         [(D(2026, 2, 6), 187), (D(2026, 7, 31), 183)], "Recurring mass item (split assignments)"),
    22: ("Missing Final Close Date", "Payroll", "High", "emp",
         [(D(2026, 2, 6), 488), (D(2026, 7, 31), 777)], "Recurring mass item, Payroll close dates"),
    26: ("Position costing is end dated", "Talent Management", "High", "pos",
         [(D(2026, 2, 6), 124), (D(2026, 4, 3), 70), (D(2026, 7, 31), 48)], "Recurring mass item"),
    31: ("Employee Assigned to Leave Org and status is not Leave with or without pay", "HCIS", "Medium", "emp",
         [(D(2026, 2, 6), 7), (D(2026, 7, 31), 7)], "Same 7 special-leave employees"),
    85: ("Employee has multiple active Education records", "Talent Management", "Medium", "emp",
         [(D(2026, 2, 6), 575), (D(2026, 7, 31), 540)], "Recurring mass item"),
    88: ("Missing Vacant Position Costing", "HCIS", "Medium", "pos",
         [(D(2026, 2, 6), 560), (D(2026, 3, 27), 1615), (D(2026, 5, 15), 1799), (D(2026, 7, 31), 1799)],
         "Recurring mass item, fixed by mass update"),
    89: ("Active Position Missing Parent Position", "Talent Management", "Medium", "pos",
         [(D(2026, 2, 6), 1074), (D(2026, 7, 31), 936)], "Recurring mass item"),
    94: ("Contingent Worker missing Supervisor", "HCIS", "Medium", "emp",
         [(D(2026, 2, 6), 313), (D(2026, 4, 10), 313), (D(2026, 4, 17), 263), (D(2026, 7, 31), 263)],
         "Recurring mass item, fixed by mass update"),
}

# Messages Payroll actually came back to HCIS about (they block someone's pay).
# Rule: if Payroll would come back on it, it's Critical. So Critical = payroll-blocking.
PAYROLL_HITS = {no for no, v in ACTION.items() if v[2] == "Critical"}

catalog = []
for no in sorted(set(ACTION) | set(KNOWN)):
    if no in ACTION:
        msg, team, sev, level, chance, size, why = ACTION[no]
        tracking = "Action"
    else:
        msg, team, sev, level, curve, why = KNOWN[no]
        tracking = "Known Exception"
    catalog.append({"check_id": f"F{no:03d}", "msg_no": no, "check_name": msg, "owner_team": team,
                    "severity": sev, "why_it_matters": why, "tracking": tracking,
                    "hits_payroll": "Y" if no in PAYROLL_HITS else "N"})
write(REF, "hr_audit_catalog", catalog, list(catalog[0]))

# Known exceptions list. A blank employee_number means "every row of this message".
known = ([{"check_id": f"F{no:03d}", "employee_number": "", "reason": KNOWN[no][5]} for no in KNOWN if no != 31]
         + [{"check_id": "F031", "employee_number": w["employee_number"], "reason": "Special leave, unpaid"}
            for w in special_leave]
         + [{"check_id": "F009", "employee_number": w["employee_number"], "reason": "Special leave, unpaid"}
            for w in special_leave]
         + [{"check_id": "F005", "employee_number": w["employee_number"], "reason": "International worker"}
            for w in international])
write(REF, "known_exceptions", known, list(known[0]))

# ============================================================== 9. FUSION HR AUDIT FILES (one per Friday)


def count_on(curve, day):
    """Read the target count for a day off a curve of (date, count) points."""
    if day <= curve[0][0]:
        return curve[0][1]
    for (d1, c1), (d2, c2) in zip(curve, curve[1:]):
        if d1 <= day <= d2:
            return round(c1 + (c2 - c1) * (day - d1).days / (d2 - d1).days)
    return curve[-1][1]


vacant_positions = [str(p) for p in random.sample(range(490000, 499999), 2600)]
filled_positions = list({w["position_number"] for w in active if w["position_number"] not in ("", "400001")})
everyday = [w for w in regular if w not in special_leave and w not in international]
pools = {   # who each message can land on
    2: everyday, 3: everyday, 5: everyday, 6: subs, 9: temps + everyday[:400], 10: temps + everyday[:300],
    16: everyday, 19: everyday, 22: [w for w in workers if w["assignment_status"] == "Terminated"],
    76: everyday, 77: everyday, 83: everyday, 85: everyday, 90: temps, 94: cws, 95: cws,
}
pos_pools = {17: filled_positions, 18: filled_positions, 23: filled_positions, 26: filled_positions,
             88: vacant_positions, 89: vacant_positions + filled_positions, 91: filled_positions,
             93: filled_positions}
always_on = {5: international, 9: special_leave, 31: special_leave}   # the same people, every week


def audit_row(x, no, msg, team, level, run):
    if level == "pos":
        row = {"EMPLOYEE_NUMBER": "", "LEGAL_FULL_NAME": "", "ASSIGNMENT_NUMBER": "",
               "ASSIGNMENT_STATUS": "", "POSITION_NUMBER": x, "JOB_NAME": "",
               "ORGANIZATION_NAME": random.Random(x).choice(SCHOOLS + OFFICES), "SUPERVISOR_NAME": ""}
    else:
        sup = "" if no in (3, 94) else by_num.get(x["supervisor_number"], {}).get("full_name", "")
        row = {"EMPLOYEE_NUMBER": x["employee_number"], "LEGAL_FULL_NAME": x["full_name"].strip(),
               "ASSIGNMENT_NUMBER": x["assignment_number"],
               "ASSIGNMENT_STATUS": "Inactive - Payroll Eligible" if no == 22 else x["assignment_status"],
               "POSITION_NUMBER": x["position_number"], "JOB_NAME": x["job_name"],
               "ORGANIZATION_NAME": x["organization"], "SUPERVISOR_NAME": sup}
    row.update({"RESPONSIBLE_TEAM": team, "AUDIT_MESSAGE": f"{no}. {msg}", "RUN_DATE": run.strftime("%m/%d/%Y")})
    return row


def top_up(items, target, pool, level):
    """Add new, not-already-open items until the list reaches the target."""
    have = set(items) if level == "pos" else set(id(x) for x in items)
    while len(items) < target:
        x = random.choice(pool)
        key = x if level == "pos" else id(x)
        if key not in have:
            items.append(x)
            have.add(key)


fusion_rows = []
open_items = {no: [] for no in list(ACTION) + list(KNOWN)}
for week, run in enumerate(FUSION_RUNS):
    progress = week / (len(FUSION_RUNS) - 1)                                 # 0 in February, 1 by July
    # ACTION messages: some weeks it shows up, some weeks it doesn't.
    # When it does, some of last week's items are still open and new ones join them.
    # Payroll-blocking ones get fixed faster as the team settles in after go-live.
    for no, (msg, team, sev, level, chance, (lo, hi), why) in ACTION.items():
        items = open_items[no]
        keep = 0.6 - 0.45 * progress if no in PAYROLL_HITS else 0.5          # share still open
        if random.random() < chance:
            items[:] = [x for x in items if random.random() < keep]
            target = random.randint(lo, hi)
            items[:] = items[:target]
            top_up(items, target, pos_pools.get(no) or pools[no], level)
        else:
            items.clear()                                                   # clean week for this one
        if run == FUSION_RUNS[-1] and no == 90:                              # last run matches the roster
            items[:] = list(no_susp)
        for x in items:
            fusion_rows.append(audit_row(x, no, msg, team, level, run))
        for x in always_on.get(no, []):                                     # #5 and #9 known people
            fusion_rows.append(audit_row(x, no, msg, team, level, run))
    # KNOWN EXCEPTION messages: on every report, big and steady
    for no, (msg, team, sev, level, curve, why) in KNOWN.items():
        items = open_items[no]
        if no in always_on:
            items[:] = list(always_on[no])
        else:
            items[:] = [x for x in items if random.random() > 0.02]
            target = count_on(curve, run)
            while len(items) > target:
                items.pop(random.randrange(len(items)))
            top_up(items, target, pos_pools.get(no) or pools[no], level)
        for x in items:
            fusion_rows.append(audit_row(x, no, msg, team, level, run))
write(RAW, "hr_audit_fusion", fusion_rows, list(fusion_rows[0]))

# Expected counts on the latest run, for the answer key
last = FUSION_RUNS[-1].strftime("%m/%d/%Y")
known_people = {(k["check_id"], k["employee_number"]) for k in known if k["employee_number"]}
latest_known = 0
for no in list(ACTION) + list(KNOWN):
    rows = [r for r in fusion_rows if r["RUN_DATE"] == last and r["AUDIT_MESSAGE"].startswith(f"{no}. ")]
    if no in KNOWN:
        latest_known += len(rows)
        planted[f"F{no:03d}"] = 0                       # never on the action list
    else:
        real = [r for r in rows if (f"F{no:03d}", r["EMPLOYEE_NUMBER"]) not in known_people]
        planted[f"F{no:03d}"] = len(real)
        latest_known += len(rows) - len(real)
planted["KNOWN_EXCEPTIONS_LATEST"] = latest_known

# ============================================================== 10. ANSWER KEY
with open(HERE / "data" / "answer_key.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["check_id", "expected"])
    for k in sorted(planted):
        w.writerow([k, planted[k]])

weekly = {}
for r in fusion_rows:
    no = int(r["AUDIT_MESSAGE"].split(".")[0])
    if no in ACTION and (f"F{no:03d}", r["EMPLOYEE_NUMBER"]) not in known_people:
        weekly[r["RUN_DATE"]] = weekly.get(r["RUN_DATE"], 0) + 1
print("\nPlanted errors (your SQL should find exactly these):")
for k in sorted(planted):
    if k.startswith(("DP", "LAURA")):
        print(f"  {k}: {planted[k]}")
print(f"  HR Audit action items per week: {min(weekly.values())} to {max(weekly.values())}")
print(f"  HR Audit action items on the latest run (7/31/2026): {sum(planted[f'F{n:03d}'] for n in ACTION)}")
print(f"  Known exceptions on the latest run (kept in their own log): {latest_known:,}")
print("\nDone. Files are in the data folder.")
