import pandas as pd

# Load data
df = pd.read_csv("F25 ECON 1750 Final Project Preferences (Responses) - Form Responses 1.csv")
df2 = pd.read_csv("Roster - Sheet2.csv")
email_map = {
    row["Email"]: f"{row['First Name']} {row['Last Name']}"
    for _, row in df2.iterrows()
}

# Roster emails = who SHOULD have answered
roster_emails = set(df2["Email"].tolist())

# Response emails = who actually answered the form
response_emails = set(df["Email Address"].tolist())

# 1. People in roster with NO response at all
no_response = sorted(list(roster_emails - response_emails))

print("=== No form response at all ===")

no_response_names = []
for email in no_response:
    print(email_map[email])
print(f"Total missing entirely: {len(no_response)}")