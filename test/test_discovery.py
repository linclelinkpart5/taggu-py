import typing as typ
import unittest
import pathlib as pl
import tempfile
import os
import os.path
import random
import string
import logging
import copy
import collections
import contextlib
import functools as ft
import itertools as it

import yaml

import taggu.library as tl
import taggu.discovery as td
import taggu.exceptions as tex
import taggu.helpers as th

A_LABEL = 'ALBUM'
D_LABEL = 'DISC'
T_LABEL = 'TRACK'
S_LABEL = 'SUBTRACK'
META_SELF = 'taggu_self.yml'
META_ITEM = 'taggu_item.yml'
ITEM_FILE_EXT = '.flac'

DirectoryHierarchy = typ.Mapping[str, typ.Union['DirectoryHierarchy', None]]


def item_filter(abs_item_path: pl.Path) -> bool:
    return (abs_item_path.is_file() and abs_item_path.suffix == ITEM_FILE_EXT) or abs_item_path.is_dir()


class TestDiscovery(unittest.TestCase):
    def setUp(self):
        self.root_dir_obj = tempfile.TemporaryDirectory()

        self.root_dir_pl = pl.Path(self.root_dir_obj.name)

        self.library_context = tl.gen_library_ctx(root_dir=self.root_dir_pl,
                                                  media_item_filter=item_filter,
                                                  media_item_sort_key=None,
                                                  self_meta_file_name=META_SELF,
                                                  item_meta_file_name=META_ITEM)

        dir_hierarchy: DirectoryHierarchy = {
            # Well-behaved album.
            f'{A_LABEL}_01': {
                f'{D_LABEL}_01': {
                    f'{T_LABEL}_01': None,
                    f'{T_LABEL}_02': None,
                    f'{T_LABEL}_03': None,
                },
                f'{D_LABEL}_02': {
                    f'{T_LABEL}_01': None,
                    f'{T_LABEL}_02': None,
                    f'{T_LABEL}_03': None,
                },
            },

            # Album with a disc and tracks, and loose tracks not on a disc.
            f'{A_LABEL}_02': {
                f'{D_LABEL}_01': {
                    f'{T_LABEL}_01': None,
                    f'{T_LABEL}_02': None,
                    f'{T_LABEL}_03': None,
                },
                f'{T_LABEL}_01': None,
                f'{T_LABEL}_02': None,
                f'{T_LABEL}_03': None,
            },

            # Album with discs and tracks, and subtracks on one disc.
            f'{A_LABEL}_03': {
                f'{D_LABEL}_01': {
                    f'{T_LABEL}_01': None,
                    f'{T_LABEL}_02': None,
                    f'{T_LABEL}_03': None,
                },
                f'{D_LABEL}_02': {
                    f'{T_LABEL}_01': {
                        f'{S_LABEL}_01': None,
                        f'{S_LABEL}_02': None,
                    },
                    f'{T_LABEL}_02': {
                        f'{S_LABEL}_01': None,
                        f'{S_LABEL}_02': None,
                    },
                    f'{T_LABEL}_03': None,
                    f'{T_LABEL}_04': None,
                },
            },

            # Album that consists of one file.
            f'{A_LABEL}_04': None,

            # A very messed-up album.
            f'{A_LABEL}_05': {
                f'{D_LABEL}_01': {
                    f'{S_LABEL}_01': None,
                    f'{S_LABEL}_02': None,
                    f'{S_LABEL}_03': None,
                },
                f'{D_LABEL}_02': {
                    f'{T_LABEL}_01': {
                        f'{S_LABEL}_01': None,
                        f'{S_LABEL}_02': None,
                    },
                },
                f'{T_LABEL}_01': None,
                f'{T_LABEL}_02': None,
                f'{T_LABEL}_03': None,
            },
        }

        def make_dir_hierarchy(curr_dir_mapping: DirectoryHierarchy, curr_rel_path: pl.Path=pl.Path()):
            """Creates a folder and file hierarchy from a mapping file."""
            for stub, child in curr_dir_mapping.items():
                if child is None:
                    # Create this entry as a file.
                    # Current relative path is to be a directory.
                    curr_abs_path = self.root_dir_pl / curr_rel_path
                    curr_abs_path.mkdir(parents=True, exist_ok=True)

                    (curr_abs_path / stub).with_suffix(ITEM_FILE_EXT).touch(exist_ok=True)
                else:
                    # Repeat the process with each child element.
                    next_rel_path = curr_rel_path / stub
                    next_dir_mapping = child
                    make_dir_hierarchy(curr_dir_mapping=next_dir_mapping, curr_rel_path=next_rel_path)

        make_dir_hierarchy(curr_dir_mapping=dir_hierarchy)

        def make_meta_files(curr_rel_path: pl.Path=pl.Path()):
            curr_abs_path = self.root_dir_pl / curr_rel_path
            if curr_abs_path.is_dir():
                # Create self meta file.
                with (curr_abs_path / META_SELF).open(mode='w') as stream:
                    data = {'info': f'self metadata for target "{curr_rel_path}"'}
                    yaml.dump(data, stream)

                # Create item meta file.
                data = {}
                for abs_entry in curr_abs_path.iterdir():
                    item_name = abs_entry.name
                    if abs_entry.is_dir():
                        make_meta_files(curr_rel_path=(curr_rel_path / item_name))

                    if item_filter(abs_entry):
                        data[item_name] = {'info': f'item metadata for target "{curr_rel_path / item_name}"'}

                with (curr_abs_path / META_ITEM).open(mode='w') as stream:
                    yaml.dump(data, stream)

        make_meta_files()

    def traverse(self, func: typ.Callable[[pl.Path, pl.Path], None], rel_sub_path: pl.Path=pl.Path()):
        lib_ctx = self.library_context

        def helper(curr_rel_path: pl.Path):
            curr_rel_path, curr_abs_path = lib_ctx.co_norm(rel_sub_path=curr_rel_path)

            func(curr_rel_path, curr_abs_path)

            if curr_abs_path.is_dir():
                for entry_name in lib_ctx.item_names_in_dir(rel_sub_dir_path=curr_rel_path):
                    helper(curr_rel_path / entry_name)

        helper(rel_sub_path)

    def test_meta_files_from_item(self):
        # Normal usage.
        lib_ctx = self.library_context
        dis_ctx = td.gen_discovery_ctx(library_context=lib_ctx)

        def helper(curr_rel_path: pl.Path, curr_abs_path: pl.Path):
            def ym():
                if curr_rel_path != curr_rel_path.parent:
                    yield curr_rel_path.parent / META_ITEM
                if curr_abs_path.is_dir():
                    yield curr_rel_path / META_SELF

            expected = tuple(ym())
            produced = tuple(dis_ctx.meta_files_from_item(rel_item_path=curr_rel_path))
            self.assertEqual(expected, produced)

        self.traverse(helper)

    def test_items_from_meta_file(self):
        pass

    def test_meta_files_from_items(self):
        pass

    def test_items_from_meta_files(self):
        pass

    def tearDown(self):
        # import ipdb; ipdb.set_trace()

        self.root_dir_obj.cleanup()

if __name__ == '__main__':
    logging.getLogger(tl.__name__).setLevel(level=logging.WARNING)
    unittest.main()
