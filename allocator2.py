import pandas as pd

# ===============================
# INPUTS
# ===============================

# 1. Pull the google sheet data into Python
df = pd.read_csv("F25 ECON 1750 Final Project Preferences (Responses) - Form Responses 1.csv")
df2 = pd.read_csv("Roster - Sheet2.csv")

# Map email -> "First Last"
email_map = {
    row["Email"]: f"{row['First Name']} {row['Last Name']}"
    for _, row in df2.iterrows()
}

emails = df["Email Address"].tolist()

# ===============================
# BUILD master_map
# master_map[n]: project -> [list of emails who ranked that project at preference n]
# where n = 1..5 corresponds to df columns 2..6
# ===============================

master_map: dict[int, dict[str, list[str]]] = {}

for n in range(2, 7):  # columns 2,3,4,5,6 in df are pref1..pref5
    for i in range(len(emails)):
        pref = df.iat[i, n]       # the project this student ranked at that pref slot
        email = emails[i]
        if (n - 1) not in master_map:
            master_map[n - 1] = {}
        if pref not in master_map[n - 1]:
            master_map[n - 1][pref] = [email]
        else:
            master_map[n - 1][pref].append(email)

# ===============================
# PROJECT LIST
# We'll infer projects from the first-pref column (col 2)
# ===============================

projs = set(df.iloc[:, 2].tolist())

# ===============================
# NEW LOGIC STARTS HERE
# ===============================

# We will build a NEW assignment that respects quant preferences,
# with custom capacities, and then produce analytics + Excel output.

# -------------------------------
# (A) Quant preference info
# -------------------------------

# 1. Define which projects are considered quant projects
quant_projects = {
    "Fama French Regressions",
    "PCA (ML in Finance)"
    # <-- change these strings if your actual column values differ
}

# Capacity rules: raise headcount for quant to 14, others default to 10
capacity_map = {
    "Fama French Regressions": 14,
    "PCA (ML in Finance)": 14
}
DEFAULT_CAPACITY = 10

# 2. Build email -> quant preference string map from df
# Assumes survey had a column "Would you be willing to do a quant project?"
quant_pref_map = {
    row["Email Address"]: row["Would you be willing to do a quant project?"]
    for _, row in df.iterrows()
}

# 3. Helper to bucketize preference
def quant_bucket(pref_str: str) -> str:
    # "Yes, I would strictly prefer it"
    if isinstance(pref_str, str) and "strictly prefer" in pref_str:
        return "STRICT"
    # "I can do it if unavoidable"
    if isinstance(pref_str, str) and "unavoidable" in pref_str:
        return "CAN_DO"
    # "Never, please."
    return "NEVER"

# -------------------------------
# (B) Build a fresh assignment map that respects quant logic
# We'll call it constrained_output_map
# -------------------------------

constrained_output_map: dict[str, set[str]] = {}

# initialize constrained_output_map with all observed projects
for proj in projs:
    constrained_output_map[proj] = set()

# start unmatched list fresh
unmatched_constrained = list(emails)

# ---- STRICT QUANT PREASSIGNMENT ----
# Give priority to people who STRICTLY prefer quant,
# but only for quant projects they actually ranked (at any pref 1..5),
# and only up to that project's capacity.
for n in range(1, 6):  # preference ranks 1..5
    input_map = master_map[n]      # project -> [emails that chose it at rank n]
    for proj, people in input_map.items():
        if proj not in quant_projects:
            continue  # only care about quant projects in this pre-pass
        for person in people:
            if person in unmatched_constrained:
                pref_type = quant_bucket(quant_pref_map[person])
                if pref_type == "STRICT":
                    limit = capacity_map.get(proj, DEFAULT_CAPACITY)
                    if len(constrained_output_map[proj]) < limit:
                        name = email_map.get(person, person)  # fallback to email if missing from roster
                        constrained_output_map[proj].add(name)
                        unmatched_constrained.remove(person)

# ---- MAIN GREEDY ALLOCATION WITH QUANT RULES ----
# Now walk prefs 1..5 again and fill remaining seats for everyone else,
# respecting "NEVER" for quant projects and capacity limits.
for n in range(1, 6):
    input_map = master_map[n]
    for proj, people in input_map.items():
        for person in people:

            # already matched somewhere?
            if person not in unmatched_constrained:
                continue

            pref_type = quant_bucket(quant_pref_map[person])

            # If proj is quant and they said "NEVER", skip
            if proj in quant_projects and pref_type == "NEVER":
                continue

            # capacity check
            limit = capacity_map.get(proj, DEFAULT_CAPACITY)
            if len(constrained_output_map[proj]) < limit:
                name = email_map.get(person, person)
                constrained_output_map[proj].add(name)
                unmatched_constrained.remove(person)

    print(f"[Constrained] After Round {n} there are {len(unmatched_constrained)} unmatched.")

print("[Constrained] Unmatched emails:", unmatched_constrained)

for proj in constrained_output_map:
    print(f"[Constrained] {proj} has {len(constrained_output_map[proj])} people")

# -------------------------------
# (C) Export to Excel in 8 columns
# -------------------------------

# Decide the Excel column order
all_projects = [
    "Fama French Regressions",
    "Passive Investing",
    "Pension Fund (LDI Crisis)",
    "International Finance",
    "PCA (ML in Finance)",
    "Employee Stock Options",
    "Ashanti (Gold Hedging)",
    "LTCM"
]

# Make sure every project exists in constrained_output_map even if empty
for proj in all_projects:
    constrained_output_map.setdefault(proj, set())

# Convert each project's assigned set of names into a sorted list
project_to_lists = {
    proj: sorted(list(constrained_output_map[proj]))
    for proj in all_projects
}

# Compute the max number of rows we'll need
max_len = max(len(names) for names in project_to_lists.values()) if len(project_to_lists) > 0 else 0

# Pad shorter columns with "" so DataFrame lines up
for proj in project_to_lists:
    lst = project_to_lists[proj]
    if len(lst) < max_len:
        lst += [""] * (max_len - len(lst))
    project_to_lists[proj] = lst

# Build final DataFrame with 8 columns
final_df = pd.DataFrame(project_to_lists)

# Write Excel file (requires: pip install openpyxl)
final_df.to_excel("Allocation 2.xlsx", index=False)

print("Wrote final_groups_constrained.xlsx")

# -------------------------------
# (D) STATS: STRICT quant placement
# -------------------------------

strict_pref = set()
got_quant = set()

for email in emails:
    if "strictly prefer" in quant_pref_map[email]:
        strict_pref.add(email)

for proj in quant_projects:
    assigned_names = constrained_output_map.get(proj, set())
    # Map back each assigned name to its email if possible
    for email, name in email_map.items():
        if name in assigned_names:
            got_quant.add(email)

strict_not_matched = strict_pref - got_quant

print(f"Total who strictly preferred quant: {len(strict_pref)}")
print(f"Got a quant project: {len(got_quant & strict_pref)}")
print(f"Did NOT get a quant project: {len(strict_not_matched)}")

print("\nPeople who strictly preferred quant but didn't get a quant project:")
for email in strict_not_matched:
    print("  ", email_map.get(email, email))

# -------------------------------
# (E) STATS: people in quant projects who are NOT strict-pref quant
# -------------------------------

non_strict_in_quant = []

for proj in quant_projects:
    assigned_names = constrained_output_map.get(proj, set())

    for email, name in email_map.items():
        if name in assigned_names:
            pref_type = quant_bucket(quant_pref_map[email])
            if pref_type != "STRICT":
                non_strict_in_quant.append({
                    "Project": proj,
                    "Name": name,
                    "Email": email,
                    "Quant Preference Bucket": pref_type,
                    "Raw Preference Answer": quant_pref_map[email],
                })

print("\nPeople in quant projects who are NOT strict-pref quant:")
for person in non_strict_in_quant:
    print(
        f"{person['Name']} ({person['Email']}) "
        f"in {person['Project']} "
        f"- pref_type={person['Quant Preference Bucket']} "
        f"- raw='{person['Raw Preference Answer']}'"
    )

print(f"\nTotal non-strict in quant projects: {len(non_strict_in_quant)}")

# -------------------------------
# (F) STATS: PCA #1, Fama #2, assigned to PCA
# -------------------------------

target_students = []

for i in range(len(df)):
    email = df.at[i, "Email Address"]
    first_pref = df.iat[i, 2]   # assumed col 2 = first preference
    second_pref = df.iat[i, 3]  # assumed col 3 = second preference

    if (
        first_pref == "PCA (ML in Finance)" and
        second_pref == "Fama French Regressions"
    ):
        assigned_names = constrained_output_map.get("PCA (ML in Finance)", set())
        name = email_map.get(email, email)
        if name in assigned_names:
            target_students.append({
                "Name": name,
                "Email": email,
                "Pref1": first_pref,
                "Pref2": second_pref
            })

print("\nPeople who ranked PCA #1, Fama French #2, and were assigned to PCA:")
for s in target_students:
    print(f"{s['Name']} ({s['Email']})")

print(f"\nTotal: {len(target_students)}")
