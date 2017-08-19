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

import taggu.library as tl
import taggu.exceptions as tex
import taggu.helpers as th

A_LABEL = 'ALBUM'
D_LABEL = 'DISC'
T_LABEL = 'TRACK'
S_LABEL = 'SUBTRACK'
META_SELF = 'taggu_self.yml'
META_ITEM = 'taggu_item.yml'

DirectoryHierarchy = typ.Mapping[str, typ.Union['DirectoryHierarchy', None]]


class TestDiscovery(unittest.TestCase):
    def setUp(self):
        self.root_dir_obj = tempfile.TemporaryDirectory()

        self.root_dir_pl = pl.Path(self.root_dir_obj.name)

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

        def make_dir_hierarchy(curr_rel_path: pl.Path, curr_dir_mapping: DirectoryHierarchy):
            for stub, child in curr_dir_mapping.items():
                if child is None:
                    # Create this entry as a file.
                    # Current relative path is to be a directory.
                    curr_abs_path = self.root_dir_pl / curr_rel_path
                    curr_abs_path.mkdir(parents=True, exist_ok=True)

                    (curr_abs_path / stub).touch(exist_ok=True)
                else:
                    # Repeat the process with each child element.
                    next_rel_path = curr_rel_path / stub
                    next_dir_mapping = child
                    make_dir_hierarchy(curr_rel_path=next_rel_path, curr_dir_mapping=next_dir_mapping)

        make_dir_hierarchy(curr_rel_path=pl.Path(), curr_dir_mapping=dir_hierarchy)

    def test_meta_files_from_item(self):
        # Normal usage.
        root_dir = self.root_dir_pl
        # lib_ctx = tl.gen_library_ctx(root_dir=root_dir, media_item_filter=item_filter)
        #
        # self.assertEqual(root_dir, lib_ctx.get_root_dir())
        # self.assertIs(item_filter, lib_ctx.get_media_item_filter())
        # self.assertEqual('taggu_self.yml', lib_ctx.get_self_meta_file_name())
        # self.assertEqual('taggu_item.yml', lib_ctx.get_item_meta_file_name())
        #
        # # Test that root dir is normalized.
        # lib_ctx = tl.gen_library_ctx(root_dir=(root_dir / 'dummy' / '..'), media_item_filter=item_filter)
        #
        # self.assertEqual(root_dir, lib_ctx.get_root_dir())

    def test_items_from_meta_file(self):
        pass

    def test_meta_files_from_items(self):
        pass

    def test_items_from_meta_files(self):
        pass

    def tearDown(self):
        import ipdb; ipdb.set_trace()

        self.root_dir_obj.cleanup()

if __name__ == '__main__':
    logging.getLogger(tl.__name__).setLevel(level=logging.WARNING)
    unittest.main()
