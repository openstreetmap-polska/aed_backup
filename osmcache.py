import json
import logging
from pathlib import Path
from time import time
from typing import Any

import requests
from tqdm import tqdm


OSM_API_URL = 'https://api.openstreetmap.org/api/0.6'
OSM_USER_AGENT = 'aed_backup/1.1 (+https://github.com/openstreetmap-polska/aed_backup)'
CACHE_TIMEOUT = 3
CACHE_RETRIES = 3
REQUEST_TIMEOUT = 30
OSM_CACHE_FILE = Path('.osm_cache.json')


class OsmCache:
    """
    Manage osm cache file with history of objects.

    File structure:
    {
        'timestamp': <int>,
        'objects': {
            "<osm_object_id>": [
                {
                    <osm_object_with_meta_version_1>
                },
                {
                    <osm_object_with_meta_version_2>
                },
                ...
            ],
            ...
        }
    }
    """

    def __init__(self):
        self.cache = self._load()
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': OSM_USER_AGENT})

    def _load(self) -> dict[str, Any]:
        try:
            with OSM_CACHE_FILE.open('r') as f:
                cache = json.load(f)
        except Exception as e:
            logging.exception(f'Cannot load cache file: {e}')
            cache = {'objects': {}}

        return cache

    def _save(self, cache: dict[str, Any] = None) -> None:
        if cache is None:
            cache = self.cache
        cache['timestamp'] = int(time())
        with OSM_CACHE_FILE.open('w') as f:
            json.dump(cache, f, indent=4, ensure_ascii=False)

    def _fetch_object_history(self, obj_type: str, obj_id: str) -> list[dict[str, Any]]:
        response = self.session.get(f'{OSM_API_URL}/{obj_type}/{obj_id}/history.json', timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        object_history = response.json()
        return object_history['elements']

    def update(self, overpass_data: dict) -> dict[str, Any]:
        to_update = []
        for elem in overpass_data['elements']:
            if 'tags' not in elem:  # skip additional/empty nodes/ways
                continue

            obj_id = str(elem['id'])
            if obj_id not in self.cache['objects']:
                to_update.append((elem['type'], obj_id))
                logging.debug(f'Elem {obj_id} not in cache!')
                continue

            cached_elements = self.cache['objects'][obj_id]
            if cached_elements[-1]['version'] != elem['version']:
                to_update.append((elem['type'], obj_id))

        for obj_type, obj_id in tqdm(to_update, desc='Updating cache', unit='elem'):
            for i in range(1, CACHE_RETRIES + 1):
                try:
                    self.cache['objects'][obj_id] = self._fetch_object_history(obj_type, obj_id)
                    break
                except Exception as e:
                    logging.warning(f'[{i}/{CACHE_RETRIES}] Cannot update object' f'{obj_id}: {e}')

        if to_update:
            self._save()

        return self.cache