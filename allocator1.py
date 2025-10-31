import pandas as pd

# Input Data Structure: 5 Hashmaps of 8 entries (Project --> Set(emails))
# Output Data Structure: 8 Sets of 10 people (or higher for quant, if capacity_map raises it)

# 1. Pull the google sheet data into the python

df = pd.read_csv("F25 ECON 1750 Final Project Preferences (Responses) - Form Responses 1.csv")
df2 = pd.read_csv("Roster - Sheet2.csv")

# Map each email to "First Last"
email_map = {
    row["Email"]: f"{row['First Name']} {row['Last Name']}"
    for _, row in df2.iterrows()
}

# Extract list of all student emails from the responses sheet
emails = df["Email Address"].tolist()

# 2. Build master_map
# master_map[n] = { project_name -> [list of emails who ranked that project at preference n] }
# where n = 1..5 corresponds to df columns 2..6 (1st choice .. 5th choice)

master_map: dict[int, dict[str, list[str]]] = {}

# For each of the 5 preference columns in the form (assumed to be df columns 2..6)
for n in range(2, 7):
    # Iterate through each row.
    for i in range(0, len(emails)):
        pref = df.iat[i, n]    # project this person ranked at pref # (n-1)
        email = emails[i]
        # If this rank bucket doesn't exist yet, create it
        if (n - 1) not in master_map:
            master_map[n - 1] = dict()
        # Append this person to the project's list at this rank
        if pref not in master_map[n - 1]:
            master_map[n - 1][pref] = [email]
        else:
            master_map[n - 1][pref].append(email)

# 3. Infer the list of projects from the first preference column
projs = set(df.iloc[:, 2].tolist())

# 4. Quant preferences and constraints

# Which projects are quant?
quant_projects = {
    "Fama French Regressions",
    "PCA (ML in Finance)"
}

# Capacity rules (edit these to raise/lower caps)
capacity_map = {
    "Fama French Regressions": 10,
    "PCA (ML in Finance)": 10
}
DEFAULT_CAP = 10

# For each student email, record their quant willingness
# Assumes df has a column "Would you be willing to do a quant project?"
quant_pref_map = {
    row["Email Address"]: row["Would you be willing to do a quant project?"]
    for _, row in df.iterrows()
}

# Helper to bucketize quant preference
def quant_bucket(pref_str: str) -> str:
    # "Yes, I would strictly prefer it"
    if isinstance(pref_str, str) and "strictly prefer" in pref_str:
        return "STRICT"
    # "I can do it if unavoidable"
    if isinstance(pref_str, str) and "unavoidable" in pref_str:
        return "CAN_DO"
    # "Never, please."
    return "NEVER"


# 5. Run the quant-prioritized matching algorithm

# This is the quant-aware result map:
# constrained_output_map[project] = set of assigned student display names
constrained_output_map: dict[str, set[str]] = {}
for proj in projs:
    constrained_output_map[proj] = set()

# Start with everyone unmatched
unmatched_constrained = list(emails)

# 5a. STRICT quant pre-pass
# Priority: students who STRICTLY prefer quant get placed
# into quant projects they ranked, if there's capacity.
for n in range(1, 6):  # preference ranks 1..5
    input_map = master_map[n]  # project -> [emails who picked proj at rank n]
    for proj in input_map:
        # only consider quant projects in this early pass
        if proj not in quant_projects:
            continue
        for person in input_map[proj]:
            if person in unmatched_constrained:
                pref_type = quant_bucket(quant_pref_map[person])
                if pref_type == "STRICT":
                    # Check capacity
                    cap = capacity_map.get(proj, DEFAULT_CAP)
                    if len(constrained_output_map[proj]) < cap:
                        constrained_output_map[proj].add(email_map.get(person, person))
                        unmatched_constrained.remove(person)

# 5b. Greedy fill for remaining students, in preference order (1..5)
# - skip quant for "NEVER" people
# - respect capacity per project
for n in range(1, 6):
    input_map = master_map[n]
    # Satisfy everyone who is able for each 
    for proj in input_map:
        for person in input_map[proj]:

            # already matched in this constrained pass?
            if person not in unmatched_constrained:
                continue

            pref_type = quant_bucket(quant_pref_map[person])

            # If this is quant and they said "Never", skip
            if proj in quant_projects and pref_type == "NEVER":
                continue

            # capacity check
            cap = capacity_map.get(proj, DEFAULT_CAP)
            if len(constrained_output_map[proj]) < cap:
                constrained_output_map[proj].add(email_map.get(person, person))
                unmatched_constrained.remove(person)

    print(f"[Quant pass] After Round {n} there are {len(unmatched_constrained)} unmatched.")

print("[Quant pass] Unmatched emails:", unmatched_constrained)

# 6. Output Matches (quant-aware)
for proj in constrained_output_map:
    print(f"[Quant pass] {proj} has {len(constrained_output_map[proj])} people")

# 7. Diagnostics / sanity checks

# 7a. Count STRICT quant people and how many landed in quant
strict_pref = set()
got_quant = set()

for email in emails:
    if "strictly prefer" in quant_pref_map[email]:
        strict_pref.add(email)

for proj in quant_projects:
    assigned_names = constrained_output_map.get(proj, set())
    # map names back to emails if possible
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

# 7b. Show people in quant projects who are NOT strict quant
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

# 7c. People who ranked PCA #1 and Fama French #2 and actually got PCA
target_students = []

for i in range(len(df)):
    email = df.at[i, "Email Address"]
    first_pref = df.iat[i, 2]   # assumed first choice in column 2
    second_pref = df.iat[i, 3]  # assumed second choice in column 3

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


# 8. Export final groups to Excel (final_groups.xlsx)
# We want 8 columns: one per project, each column is the names assigned there.

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

# Convert sets of names to sorted lists
project_to_lists = {
    proj: sorted(list(constrained_output_map[proj]))
    for proj in all_projects
}

# Find the max length so columns line up
max_len = max(len(v) for v in project_to_lists.values()) if len(project_to_lists) > 0 else 0

# Pad lists with "" so they're all the same length
for proj in project_to_lists:
    names_list = project_to_lists[proj]
    if len(names_list) < max_len:
        names_list += [""] * (max_len - len(names_list))
    project_to_lists[proj] = names_list

# Build DataFrame with 8 columns
final_df = pd.DataFrame(project_to_lists)

# Write DataFrame to Excel (requires `pip install openpyxl`)
final_df.to_excel("final_groups.xlsx", index=False)

print("\nWrote final_groups.xlsx")
