import json
import requests
import subprocess

from time import sleep
from typing import Any, Dict, Optional

from report import create_report_md, REPORT_DIR


QUERY_FILE = 'overpass_query.txt'
BACKUP_FILE = 'aed_overpass.json'
README_FILE = 'README.MD'


BACKUP_COMMIT_MSG = 'AED update'

OVERPASS_API_URL = 'https://lz4.overpass-api.de/api/interpreter'

TIMEOUT = 30  # seconds
RETRIES = 5


def git_add(filename: str) -> None:
    subprocess.run(['git', 'add', filename])


def git_commit(msg: str) -> None:
    subprocess.run(['git', 'commit', '-m', f'{msg}'])


def git_push() -> None:
    subprocess.run(['git', 'push'])


def download_data() -> Optional[Dict[Any, Any]]:
    with open(QUERY_FILE, 'r') as f:
        query = f.read().strip()

    for _ in range(RETRIES):
        try:
            response = requests.get(OVERPASS_API_URL, params={'data': query})
            if response.status_code != 200:
                print(f'Incorrect status code: {response.status_code}')
                continue

            return response.json()

        except Exception as e:
            print(f'Error with downloading/parsing data: {e}')

        sleep(TIMEOUT)


def backup(overpass_result: dict) -> None:
    with open(BACKUP_FILE, 'w') as f:
        json.dump(overpass_result, f, indent=4, ensure_ascii=False)

    git_add(BACKUP_FILE)


def generate_report(overpass_result) -> None:
    try:
        md_content = create_report_md(overpass_result)
        with open(README_FILE, 'w') as f:
            f.write(md_content)

        git_add(README_FILE)
        git_add(REPORT_DIR)

    except Exception as e:
        print(f'Error with creating report: {e}')


def main():
    overpass_data = download_data()
    if overpass_data is None:
        exit(1)

    backup(overpass_data)
    generate_report(overpass_data)

    git_push()


if __name__ == '__main__':
    main()

