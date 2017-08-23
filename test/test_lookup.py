import logging
import pathlib as pl
import tempfile
import typing as typ
import unittest

import yaml

import taggu.contexts.discovery as td
import taggu.contexts.library as tl
import taggu.helpers as th

A_LABEL = 'ALBUM'
D_LABEL = 'DISC'
T_LABEL = 'TRACK'
S_LABEL = 'SUBTRACK'
META_SELF = 'taggu_self.yml'
META_ITEM = 'taggu_item.yml'
ITEM_FILE_EXT = '.flac'
MAIN_KEY = 'info'
SELF_META_STR_TEMPLATE = 'self metadata for target "{}"'
ITEM_META_STR_TEMPLATE = 'item metadata for target "{}"'

DirectoryHierarchy = typ.Mapping[str, typ.Union['DirectoryHierarchy', None]]


def item_filter(abs_item_path: pl.Path) -> bool:
    return (abs_item_path.is_file() and abs_item_path.suffix == ITEM_FILE_EXT) or abs_item_path.is_dir()


class TestDiscovery(unittest.TestCase):
    def setUp(self):
        pass

    def test_get_discovery_context(self):
        pass

    def test_get_meta_cache(self):
        pass

    def test_yield_field(self):
        pass

    def test_yield_parent_fields(self):
        pass

    def test_yield_child_fields(self):
        pass

    def test_cache_item(self):
        pass

    def test_clear_cache(self):
        pass

    def tearDown(self):
        # import ipdb; ipdb.set_trace()
        pass

if __name__ == '__main__':
    logging.getLogger(td.__name__).setLevel(level=logging.WARNING)
    logging.getLogger(tl.__name__).setLevel(level=logging.WARNING)
    logging.getLogger(th.__name__).setLevel(level=logging.WARNING)
    unittest.main()
