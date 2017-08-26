import logging
import pathlib as pl
import tempfile
import typing as typ
import unittest

import yaml

import taggu.contexts.discovery as td
import taggu.contexts.library as tl
import taggu.contexts.query as tq
import taggu.helpers as th
import test.helpers as tsth


class TestQuery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root_dir_obj = tempfile.TemporaryDirectory()

        cls.root_dir_pl = pl.Path(cls.root_dir_obj.name)
        cls.lib_ctx = tl.gen_library_ctx(root_dir=cls.root_dir_pl, media_item_filter=tsth.default_item_filter,
                                         self_meta_file_name=tsth.SELF_META_FN, item_meta_file_name=tsth.ITEM_META_FN)
        cls.dis_ctx = td.gen_discovery_ctx(library_context=cls.lib_ctx)

        dir_hier_map = tsth.gen_default_dir_hier_map()
        tsth.write_dir_hierarchy(root_dir=cls.root_dir_pl,
                                 dir_mapping=dir_hier_map,
                                 item_file_suffix=tsth.ITEM_FILE_EXT,
                                 apply_random_salt=True)
        tsth.write_meta_files(root_dir=cls.root_dir_pl, item_filter=tsth.default_item_filter)

    def test_get_meta_cache(self):
        # TODO: Create label extractor in helpers.
        qry_ctx = tq.gen_lookup_ctx(discovery_context=self.dis_ctx, label_ext=None)

        # Meta cache starts out empty.
        expected = {}
        produced = qry_ctx.get_meta_cache()
        self.assertEqual(expected, produced)

    def test_all_meta_files_present(self):
        root_dir = self.root_dir_pl

        def func(curr_rel_path: pl.Path, curr_abs_path: pl.Path):
            file_names_in_dir = frozenset(d.name for d in curr_abs_path.iterdir())
            self.assertIn(tsth.ITEM_META_FN, file_names_in_dir)
            self.assertIn(tsth.SELF_META_FN, file_names_in_dir)

        tsth.traverse(root_dir=root_dir, func=func, action_filter=lambda a: a.is_dir())

    def test_yield_field(self):
        # TODO: Create label extractor in helpers.
        root_dir = self.root_dir_pl
        qry_ctx = tq.gen_lookup_ctx(discovery_context=self.dis_ctx, label_ext=None)

        # TODO: CONTINUE HERE!
        def func(curr_rel_path: pl.Path, curr_abs_path: pl.Path):
            expected = (tsth.ITEM_META_STR_TEMPLATE.format(curr_rel_path),) if curr_rel_path.parts else ()
            produced = tuple(qry_ctx.yield_field(rel_item_path=curr_rel_path,
                                                 field_name=tsth.ITEM_META_KEY,
                                                 labels=None))
            self.assertEqual(expected, produced)

            expected = (tsth.SELF_META_STR_TEMPLATE.format(curr_rel_path),) if curr_abs_path.is_dir() else ()
            produced = tuple(qry_ctx.yield_field(rel_item_path=curr_rel_path,
                                                 field_name=tsth.SELF_META_KEY,
                                                 labels=None))
            self.assertEqual(expected, produced)

        tsth.traverse(root_dir=root_dir, func=func, action_filter=tsth.default_item_filter)

    def test_yield_parent_fields(self):
        pass

    def test_yield_child_fields(self):
        pass

    def test_cache_item(self):
        pass

    def test_clear_cache(self):
        pass

    @classmethod
    def tearDownClass(cls):
        # import ipdb; ipdb.set_trace()
        input('Press ENTER to continue and cleanup')

        cls.root_dir_obj.cleanup()

if __name__ == '__main__':
    unittest.main()
