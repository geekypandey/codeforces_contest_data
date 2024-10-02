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


CONFIG_FILE = os.path.join(Path(__file__).parent.absolute(), 'configuration.yml')
FILENAME = "contests.json"
CONTEST_FILE = os.path.join(Path(__file__).parent.parent.absolute(), FILENAME)

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
    p = subprocess.Popen(['node', './fetch_page.js', str(contest_id)], stdout=subprocess.PIPE)
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
            if contest['phase'] == 'BEFORE':
                processed_contests.append(contest)
                continue
            print(f"Verifying for contest {contest['id']}")
            problems = get_problems(contest['id'])
            time.sleep(10)
            if len(problems) <= len(contest.get('problems', [])):
                processed_contests.append(contest)
                continue
            else:
                print(f'Adding problems for contest: {contest}')
            # add problems
            present_index = set(problem['index'] for problem in contest.get('problems', []))
            for problem in problems:
                if problem['index'] not in present_index:
                    contest.get('problems', []).append({
                        'contestId': contest['id'],
                        'index': problem['index'],
                        'name': problem['name'],
                        'tags': [],
                        'solvedCount': problem['solvedCount'],
                    })
            processed_contests.append(contest)
        except Exception as e:
            print(f'Exception occured: {e}')
            config.get('skip-ids', []).append(contest['id'])
            processed_contests.append(contest)
            continue
    return processed_contests


def get_all_contests():
    """Fetch all the contests using codeforces api"""
    url = "https://codeforces.com/api/contest.list"
    res = requests.get(url)
    if res.status_code != 200:
        raise RuntimeError(f"Request status code : {res.status_code}. Try again!")
    res = res.json()
    if res["status"] != "OK":
        raise RuntimeError(f"Response from codeforces, status: {res['status']}")
    return res["result"]


def add_solved_count_to_problems(problems):
    # add solvedCount to problem for each problem
    problemStats = dict()
    for pStat in problems['problemStatistics']:
        problemStats[f"{pStat['contestId']}/{pStat['index']}"] = pStat['solvedCount']

    for problem in problems['problems']:
        problem['solvedCount'] = problemStats.get(f"{problem['contestId']}/{problem['index']}", None)
    problems = problems['problems']
    return problems


def get_all_problems():
    """Fetch all the contests using codeforces api"""
    url = "https://codeforces.com/api/problemset.problems"
    res = requests.get(url)
    if res.status_code != 200:
        raise RuntimeError(f"Request status code : {res.status_code}. Try again!")
    res = res.json()
    if res["status"] != "OK":
        raise RuntimeError(f"Response from codeforces, status: {res['status']}")
    problems = add_solved_count_to_problems(res['result'])
    return problems


def get_new_added_contests_id(previous, current):
    previous_contests_id = set(contest['id'] for contest in previous)
    current_contests_id = set(contest['id'] for contest in current)

    return current_contests_id - previous_contests_id


def get_contest_division(contest):
    div = ""
    if contest["name"].find("Educational") >= 0:
        div = "E"
    elif contest["name"].find("Div. 1") >= 0:
        div = "1"
    elif contest["name"].find("Div. 2") >= 0:
        div = "2"
    elif contest["name"].find("Div. 3") >= 0:
        div = "3"
    elif contest["name"].find("Div. 4") >= 0:
        div = "4"
    return div


def add_division_to_contests(contests):
    for contest in contests:
        contest['div'] = get_contest_division(contest)


def get_previously_saved_contests():
    with open(CONTEST_FILE) as f:
        data = json.load(f)
    contests = [contest for contest in data['contests'] if contest['phase'] != 'BEFORE']
    return contests


if __name__ == "__main__":

    current_datetime_utc = datetime.now(timezone.utc)
    contests = get_all_contests()
    add_division_to_contests(contests)

    problems = get_all_problems()

    # add problems list to each contest
    for contest in contests:
        for problem in problems:
            if contest['id'] == problem['contestId']:
                contest['problems'] = contest.get('problems') or []
                contest['problems'].append(problem)


    # get only contests which are completed
    previously_saved_contests = get_previously_saved_contests()

    # get new contests added and also the contests which are not yet started
    new_contests_id_added = get_new_added_contests_id(previously_saved_contests, contests)

    new_contests = [contest for contest in contests if contest['id'] in new_contests_id_added]
    print(f'Adding {len(new_contests_id_added)} contests')
    new_contests = verify_problems_and_add_if_absent(new_contests)
    new_contests_id_added = [contest['id'] for contest in new_contests]

    print(f"Saving the contests data to the file, Total Contests: {len(contests)}, Previous total contests: {len(previously_saved_contests)}")
    if new_contests_id_added:
        print(f"New contests added: {','.join(str(contest_id) for contest_id in new_contests_id_added)}")
    else:
        print("No new contests added.")
        exit(1)

    with open(CONTEST_FILE, 'w') as f:
        json.dump({
            'contests': [*previously_saved_contests, *new_contests],
            'last_updated': current_datetime_utc.isoformat(),
            }, f)

    with open(CONFIG_FILE, 'w') as f:
        yaml.dump(config, f)
