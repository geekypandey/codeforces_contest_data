import os
import json
import time
import itertools
from pathlib import Path
from datetime import datetime, timezone

import requests

response = None


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


def get_all_problems():
    """Fetch all the contests using codeforces api"""
    url = "https://codeforces.com/api/problemset.problems"
    res = requests.get(url)
    if res.status_code != 200:
        raise RuntimeError(f"Request status code : {res.status_code}. Try again!")
    res = res.json()
    if res["status"] != "OK":
        raise RuntimeError(f"Response from codeforces, status: {res['status']}")
    return res['result']
    # problems = res['result']['problems']
    # problemsStat = res['result']['problemStatistics']


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


if __name__ == "__main__":
    FILENAME = "contests.json"
    CONTEST_FILE = os.path.join(Path(__file__).parent.parent.absolute(), FILENAME)

    # get all contests
    contests = get_all_contests()
    problems = get_all_problems()

    # add solvedCount to problem for each problem
    problemStats = dict()
    for pStat in problems['problemStatistics']:
        problemStats[f"{pStat['contestId']}/{pStat['index']}"] = pStat['solvedCount']

    for problem in problems['problems']:
        problem['solvedCount'] = problemStats.get(f"{problem['contestId']}/{problem['index']}", None)
    problems = problems['problems']

    # add problems list to each contest
    for contest in contests:
        for problem in problems:
            if contest['id'] == problem['contestId']:
                contest['problems'] = contest.get('problems') or []
                contest['problems'].append(problem)

    # add division for each contest
    for contest in contests:
        contest['div'] = get_contest_division(contest)

    current_datetime_utc = datetime.now(timezone.utc)

    with open(CONTEST_FILE) as f:
        saved_contest_data = json.load(f)
    print(f"Saving the contests data to the file, Total Contests: {len(contests)}, Previous total contests: {len(saved_contest_data['contests'])}")
    with open(CONTEST_FILE, 'w') as f:
        json.dump({'contests': contests, 'last_updated': current_datetime_utc.isoformat()}, f)
