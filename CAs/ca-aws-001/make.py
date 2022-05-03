import json

with open('provision.json', 'wt') as t:
    with open('template.json', 'rt') as p:
        data = {
            "templateBody": json.dumps(json.load(p)),
            "roleArn": "arn:aws:iam::514573433251:role/just-in-time-provisioning-role"
        }
        t.write(json.dumps(data, indent=2))
