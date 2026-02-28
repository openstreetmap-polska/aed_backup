import json
import logging
from pathlib import Path
from time import sleep
from typing import Any

import requests

from osmcache import OsmCache
from report import create_report_md

QUERY_FILE = Path('query.overpassql')
BACKUP_FILE = Path('aed_overpass.json')
README_FILE = Path('README.MD')
STATUS_FILE = Path('status.txt')

OVERPASS_API_URL = 'https://overpass-api.de/api/interpreter'

TIMEOUT = 30  # seconds
RETRIES = 5


def download_data() -> dict | None:
    query = QUERY_FILE.read_text().strip()
    logging.info(f'Read overpass query from file: {QUERY_FILE}')
    logging.info('Downloading overpass data...')
    for _ in range(RETRIES):
        try:
            response = requests.get(OVERPASS_API_URL, params={'data': query}, timeout=TIMEOUT)
            if response.status_code != 200:
                logging.warning(f'Incorrect status code: {response.status_code}')
                continue

            return response.json()

        except Exception as e:
            logging.error(f'Error with downloading/parsing data: {e}')

        sleep(TIMEOUT)


def backup(overpass_result: dict) -> None:
    with BACKUP_FILE.open('w') as f:
        json.dump(overpass_result, f, indent=4, ensure_ascii=False)


def generate_report(overpass_result: dict, cache: dict[str, Any]) -> None:
    try:
        md_content = create_report_md(overpass_result, cache)
        README_FILE.write_text(md_content)

    except Exception as e:
        logging.exception(f'Error with creating report: {e}')


def generate_status(diff: tuple[int, int, int]) -> None:
    created, modified, deleted = diff
    STATUS_FILE.write_text(f'C: {created}, M: {modified}, D: {deleted}')


def overpass_diff(overpass_data: dict) -> tuple[int, int, int]:
    """
    :return: tuple with 3 numbers (created, modified, deleted) objects
    """
    created = 0
    modified = 0
    deleted = 0

    try:
        with BACKUP_FILE.open('r') as f:
            old_data = json.load(f)

    except IOError:
        old_data = {'elements': []}

    old_elements = {elem['id']: elem for elem in old_data['elements']}
    for elem in overpass_data['elements']:
        elem_id = elem['id']

        if elem_id not in old_elements:
            created += 1
        else:
            if elem != old_elements[elem_id]:
                modified += 1

            del old_elements[elem_id]

    deleted += len(old_elements)

    return created, modified, deleted


def main():
    logging.basicConfig(
        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d,%H:%M:%S',
        level=logging.INFO,
    )
    overpass_data = download_data()
    if overpass_data is None:
        logging.info('Empty overpass data. Exiting!')
        exit(1)

    logging.info('Downloaded overpass data.')
    diff = overpass_diff(overpass_data)
    backup(overpass_data)

    osm_cache = OsmCache()
    cache = osm_cache.update(overpass_data)

    if any(diff):
        logging.info('Generating report')
        generate_report(overpass_data, cache)

    logging.info('Generating status')
    generate_status(diff)


if __name__ == '__main__':
    main()
```
