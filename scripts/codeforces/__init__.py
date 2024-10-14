import requests

BASE_URL = 'https://codeforces.com/api'


def get_contests():
    """Fetch all the contests"""
    res = requests.get(f'{BASE_URL}/contest.list')
    if res.status_code != 200 and res['status'] != 'OK':
        raise RuntimeError(f'Issue with fetching contests status_code={res.status_code}')
    res = res.json()
    return res['result']


def get_problems():
    """Fetch all the problems"""
    res = requests.get(f'{BASE_URL}/problemset.problems')
    if res.status_code != 200 and res['status'] != 'OK':
        raise RuntimeError(f'Issue with fetching problems status_code={res.status_code}')
    res = res.json()
    return _add_solved_count_to_problems(res['result'])


def _add_solved_count_to_problems(problems):
    solvedCount = dict()
    _get_index = lambda x: str(x['contestId']) + str(x['index'])
    for problem in problems['problemStatistics']:
        solvedCount[_get_index(problem)] = problem['solvedCount']

    for problem in problems['problems']:
        problem['solvedCount'] = solvedCount.get(_get_index(problem), None)

    return problems['problems']
