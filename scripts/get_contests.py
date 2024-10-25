import time
import os
import json
import itertools
import subprocess
from pathlib import Path
from datetime import datetime, timezone

import requests
import yaml
import pandas as pd
import numpy as np

import codeforces

CONFIG_FILE = os.path.join(Path(__file__).parent.absolute(), 'configuration.yml')
FILENAME = "contests.json"
CONTEST_FILE = os.path.join(Path(__file__).parent.parent.absolute(), FILENAME)
FETCH_PAGE_FILE_PATH = os.path.join(Path(__file__).parent.absolute(), 'fetch_page.js')
FINISHED = 'FINISHED'
EMPTY_STRING = ''
DIVISIONS = {
        'Div. 1': '1',
        'Div. 2': '2',
        'Div. 1 + Div. 2': '1&2',
        'Div. 3': '3',
        'Div. 4': '4',
        'Educational': 'E',
        'Kotlin': 'kotlin',
        'CodeTON': 'codeton',
        'Global': 'global',
        'VK Cup': 'vk-cup',
        'April Fools': 'april-fools',
}

with open(CONFIG_FILE) as f:
    config = yaml.safe_load(f)


def replace_nan(x):
    if isinstance(x, str):
        return x
    if np.isnan(x):
        return None
    return x


def strip_x(x: str):
    if not isinstance(x, str):
        return x
    return x.strip('x').strip()


def get_problems(contest_id):
    p = subprocess.Popen(['node', FETCH_PAGE_FILE_PATH, str(contest_id)], stdout=subprocess.PIPE)
    out = p.stdout.read()

    df = pd.read_html(out)[1]
    if 'Name' not in df.columns:
        print('Some ERROR')
    df.dropna(axis=1, how='all', inplace=True)
    columns = ['idx', 'name', 'solved_count']
    df.columns = [columns[i] for i in range(len(df.columns))]
    indices = [str(val) for val in df['idx'].values]
    solved_count = []
    names = [name.split('standard')[0].strip() for name in df['name']]
    if 'solved_count' in df.columns:
        df['solved_count'] = df['solved_count'].apply(strip_x)
        solved_count = df['solved_count'].apply(replace_nan).values
    problems = [{"index": idx, "solvedCount": count, "name": name} for idx, count, name in itertools.zip_longest(indices, solved_count, names)]
    return problems


def verify_problems_and_add_if_absent(contests):
    processed_contests = []
    for contest in contests:
        if contest['id'] in config.get('skip-ids', []):
            continue
        try:
            print(f"Verifying for contest {contest['id']}")
            problems = get_problems(contest['id'])
            time.sleep(10)
            current_contest_problems = contest.get('problems', [])
            if len(problems) <= len(current_contest_problems):
                processed_contests.append(contest)
                continue
            else:
                print(f'Adding problems for contest: {contest}')
            # add problems
            present_index = set(problem['index'] for problem in current_contest_problems)
            for problem in problems:
                if problem['index'] not in present_index:
                    current_contest_problems.append({
                        'contestId': contest['id'],
                        'index': problem['index'],
                        'name': problem['name'],
                        'tags': [],
                        'solvedCount': problem['solvedCount'],
                    })
            contest['problems'] = current_contest_problems
            processed_contests.append(contest)
        except Exception as e:
            print(f'Exception occured: {e}')
            config.get('skip-ids', []).append(contest['id'])
            processed_contests.append(contest)
            continue
    return processed_contests


def get_new_added_contests_id(previous, current):
    previous_contests_id = set(contest['id'] for contest in previous)
    current_contests_id = set(contest['id'] for contest in current)

    return current_contests_id - previous_contests_id


def get_contest_division(contest):
    for (key, value) in DIVISIONS.items():
        if contest['name'].find(key) >= 0:
            return value
    return EMPTY_STRING


def add_division_to_contests(contests):
    for contest in contests:
        contest['div'] = get_contest_division(contest)


def get_saved_contests():
    with open(CONTEST_FILE) as f:
        data = json.load(f)
    contests = [contest for contest in data['contests'] if contest['phase'] == FINISHED]
    return contests


if __name__ == "__main__":

    contests = codeforces.get_contests()
    not_finished_contests = [contest for contest in contests if contest['phase'] != FINISHED]
    contests = [contest for contest in contests if contest['phase'] == FINISHED]
    add_division_to_contests(contests)

    problems = codeforces.get_problems()

    # add problems list to each contest
    for contest in contests:
        for problem in problems:
            if contest['id'] == problem['contestId']:
                contest['problems'] = contest.get('problems') or []
                contest['problems'].append(problem)

    # sort the problems based on index
    for contest in contests:
        if contest.get('problems') is None:
            continue
        contest['problems'].sort(key=lambda p: p['index'])


    # get only contests which are completed
    saved_contests = get_saved_contests()

    # get new contests added and also the contests which are not yet started
    new_contests_id_added = get_new_added_contests_id(saved_contests, contests)

    new_contests = [contest for contest in contests if contest['id'] in new_contests_id_added]
    print(f'Adding {len(new_contests_id_added)} contests')
    new_contests = verify_problems_and_add_if_absent(new_contests)
    new_contests_id_added = [contest['id'] for contest in new_contests]

    print(f"Saving the contests data to the file, Total Contests: {len(contests)}, Previous total contests: {len(saved_contests)}")
    if new_contests_id_added:
        print(f"New contests added: {','.join(str(contest_id) for contest_id in new_contests_id_added)}")
    else:
        print("No new contests added.")
        exit(1)

    with open(CONTEST_FILE, 'w') as f:
        json.dump({
            'contests': [*saved_contests, *new_contests, *not_finished_contests],
            'last_updated': datetime.now(timezone.utc).isoformat(),
            }, f, indent=4)

    with open(CONFIG_FILE, 'w') as f:
        yaml.dump(config, f)
