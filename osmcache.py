import requests

import json
import logging

from time import time
from typing import Any, Dict, List


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
    OSM_API_URL = 'https://api.openstreetmap.org/api/0.6'
    OSM_USER_AGENT = 'aed_backup/1.0 (github.com/openstreetmap-polska)'
    CACHE_TIMEOUT = 3
    CACHE_RETRIES = 3
    OSM_CACHE_FILE = '.osm_cache.json'

    def __init__(self, cache_filename: str = OSM_CACHE_FILE):
        self.osm_cache_filename = cache_filename
        self.cache = self._load()

    def _load(self) -> Dict[str, Any]:
        try:
            with open(self.osm_cache_filename, 'r') as f:
                cache = json.load(f)
        except Exception as e:
            logging.exception(f'Cannot load cache file: {e}')
            cache = {'objects': {}}

        return cache

    def _save(self, cache: Dict[str, Any] = None) -> None:
        if cache is None:
            cache = self.cache
        cache['timestamp'] = int(time())
        with open(self.osm_cache_filename, 'w') as f:
            json.dump(cache, f, indent=4, ensure_ascii=False)

    def _fetch_object_history(
        self,
        obj_type: str,
        obj_id: str
    ) -> List[Dict[str, Any]]:
        response = requests.get(
            f'{self.OSM_API_URL}/{obj_type}/{obj_id}/history.json',
            headers={'User-Agent': self.OSM_USER_AGENT}
        )
        object_history = response.json()
        return object_history['elements']

    def update(self, overpass_data: Dict[Any, Any]) -> Dict[str, Any]:
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

        if to_update:
            logging.info(f'OSM Cache: Updating {len(to_update)} elements')
        for obj_type, obj_id in to_update:
            for i in range(1, self.CACHE_RETRIES + 1):
                try:
                    self.cache['objects'][obj_id] = self._fetch_object_history(
                        obj_type,
                        obj_id
                    )
                    break
                except Exception as e:
                    logging.warning(
                        f'[{i}/{self.CACHE_RETRIES}] Cannot update object'
                        f'{obj_id}: {e}'
                    )

        if to_update:
            self._save()

        return self.cache
