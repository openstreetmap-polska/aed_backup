import json
import logging
from time import sleep
from typing import Any

import requests

from osmcache import OsmCache
from report import create_report_md

QUERY_FILE = 'query.overpassql'
BACKUP_FILE = 'aed_overpass.json'
README_FILE = 'README.MD'

OVERPASS_API_URL = 'https://overpass-api.de/api/interpreter'

TIMEOUT = 30  # seconds
RETRIES = 5


def download_data() -> dict | None:
    with open(QUERY_FILE, 'r') as f:
        query = f.read().strip()
    logging.info(f'Read overpass query from file: {QUERY_FILE}')
    logging.info('Downloading overpass data...')
    for _ in range(RETRIES):
        try:
            response = requests.get(OVERPASS_API_URL, params={'data': query})
            if response.status_code != 200:
                logging.warning(f'Incorrect status code: {response.status_code}')
                continue

            return response.json()

        except Exception as e:
            logging.error(f'Error with downloading/parsing data: {e}')

        sleep(TIMEOUT)


def backup(overpass_result: dict) -> None:
    with open(BACKUP_FILE, 'w') as f:
        json.dump(overpass_result, f, indent=4, ensure_ascii=False)


def generate_report(overpass_result: dict, cache: dict[str, Any]) -> None:
    try:
        md_content = create_report_md(overpass_result, cache)
        with open(README_FILE, 'w') as f:
            f.write(md_content)

    except Exception as e:
        logging.exception(f'Error with creating report: {e}')


def overpass_diff(overpass_data: dict) -> tuple[int, int, int]:
    """
    :return: tuple with 3 numbers (created, modified, deleted) objects
    """
    created = 0
    modified = 0
    deleted = 0

    try:
        with open(BACKUP_FILE, 'r') as f:
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
        logging.info('Generated report')


if __name__ == '__main__':
    main()
