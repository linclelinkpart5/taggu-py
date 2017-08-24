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
    def setUp(self):
        self.root_dir_obj = tempfile.TemporaryDirectory()

        self.root_dir_pl = pl.Path(self.root_dir_obj.name)
        self.lib_ctx = tl.gen_library_ctx(root_dir=self.root_dir_pl, media_item_filter=tsth.default_item_filter,
                                          self_meta_file_name=tsth.SELF_META_FN, item_meta_file_name=tsth.ITEM_META_FN)
        self.dis_ctx = td.gen_discovery_ctx(library_context=self.lib_ctx)

    def test_get_meta_cache(self):
        # TODO: Create label extractor in helpers.
        qry_ctx = tq.gen_lookup_ctx(discovery_context=self.dis_ctx, label_ext=None)

        # Meta cache starts out empty.
        expected = {}
        produced = qry_ctx.get_meta_cache()
        self.assertEqual(expected, produced)

    def test_yield_field(self):
        # TODO: Create label extractor in helpers.
        qry_ctx = tq.gen_lookup_ctx(discovery_context=self.dis_ctx, label_ext=None)

        # TODO: CONTINUE HERE!
        # qry_ctx.yield_field(rel_item_path=rel_item_path, field_name=field_name, labels=None)

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

        self.root_dir_obj.cleanup()

if __name__ == '__main__':
    logging.getLogger(td.__name__).setLevel(level=logging.WARNING)
    logging.getLogger(tl.__name__).setLevel(level=logging.WARNING)
    logging.getLogger(th.__name__).setLevel(level=logging.WARNING)
    unittest.main()
