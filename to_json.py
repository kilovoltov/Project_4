import json

import data


with open('goals.json', 'w') as f:
    json.dump(data.goals, f)

with open('teachers.json', 'w') as f:
    json.dump(data.teachers, f)
