import json
import requests
import subprocess

from time import sleep

from report import create_report_md, REPORT_DIR


QUERY_FILE = 'overpass_query.txt'
BACKUP_FILE = 'aed_overpass.json'
README_FILE = 'README.MD'


BACKUP_COMMIT_MSG = 'AED update'

OVERPASS_API_URL = 'https://lz4.overpass-api.de/api/interpreter'

TIMEOUT = 30  # seconds
RETRIES = 5


def commit_and_push():
    subprocess.run(['git', 'add', BACKUP_FILE, README_FILE, REPORT_DIR])
    subprocess.run(['git', 'commit', '-m', f'{BACKUP_COMMIT_MSG}'])
    subprocess.run(['git', 'push'])


def backup():
    with open(QUERY_FILE, 'r') as f:
        query = f.read().strip()

    for _ in range(RETRIES):
        try:
            response = requests.get(OVERPASS_API_URL, params={'data': query})
            if response.status_code == 200:
                with open(BACKUP_FILE, 'w', encoding='utf8') as f:
                    overpass_result = response.json()
                    json.dump(overpass_result, f, indent=4, ensure_ascii=False)

                try:
                    md_content = create_report_md(overpass_result)
                    with open(README_FILE, 'w') as f:
                        f.write(md_content)

                except Exception as e:
                    print(f'Error with creating report: {e}')
                commit_and_push()
                exit(0)

            else:
                print(f'Incorrect status code: {response.status_code}')

        except Exception as e:
            print(f'Error with downloading/parsing data: {e}')

        sleep(TIMEOUT)

    exit(1)


if __name__ == '__main__':
    backup()

