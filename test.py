import json

with open("cred.json", "r") as f:
    creds = json.load(f)

for cred in creds['creds']:
    print(type(creds)) 