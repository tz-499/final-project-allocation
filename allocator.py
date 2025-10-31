import pandas as pd

# Input Data Structure: 5 Hashmaps of 8 entries (Project --> Set(emails))
# Output Data Structure: 8 Sets of 10 people

# 1. Pull the google sheet data into the python

df = pd.read_csv("F25 ECON 1750 Final Project Preferences (Responses) - Form Responses 1.csv")

# 5 Hashmaps of 8 entries mapping project --> set(names)
master_map: dict[int, dict[str, list[str]]] = {}
output_map: dict[str, set[str]] = {}
emails = df['Email Address'].tolist()

# For each of the 5 columns
for n in range (2, 7):
    # Iterate through each row. 
    for i in range(0, len(emails)):
        pref = df.iat[i, n]
        email = emails[i]
        # If there is already a set, add to it. If not, create it
        if n-1 not in master_map:
            master_map[n-1] = dict()
        if pref not in master_map[n-1]:
            master_map[n-1][pref] = [email]
        else:
            master_map[n-1][pref].append(email)

# print(len(master_map), len(master_map[2]))

# 2. Run the matching algorithm
projs = set(df.iloc[:, 2].tolist())
for proj in projs:
    output_map[proj] = set()

# Satisfy everyone's first preferences
# Check if they are unmatched
# Check if there is availability
# Match and remove from the unmatched pile

unmatched = list(emails)
for n in range(1, 6):
    input_map = master_map[n]
    # Satisfy everyone who is able for each 
    for proj in input_map:
        for person in input_map[proj]:
            if person in unmatched:
                if len(output_map[proj]) <= 20:
                    output_map[proj].add(person)
                    unmatched.remove(person)
    print(f"After Round {n} there are {len(unmatched)} that are unmatched!")


# 3. Output Matches
