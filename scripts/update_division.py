import os
import json
from pathlib import Path

FILENAME = "contests.json"
CONTEST_FILE = os.path.join(Path(__file__).parent.parent.absolute(), FILENAME)

divisions = {
        'Div. 1': '1',
        'Div. 2': '2',
        'Div. 1 + Div. 2': '1&2',
        'Div. 3': '3',
        'Div. 4': '4',
        'Educational': 'E',
        'Kotlin': 'kotlin'
}

with open(CONTEST_FILE, 'r') as f:
    data = json.load(f)
    contests = data['contests']
    for contest in contests:
        for (key, value) in divisions.items():
            if contest['name'].find(key) >= 0:
                contest['div'] = value
    data['contests'] = contests

with open(CONTEST_FILE, 'w') as f:
    json.dump(data, f, indent=4)
