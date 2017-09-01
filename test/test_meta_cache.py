import logging
import pathlib as pl
import tempfile
import typing as typ
import unittest

import taggu.contexts.discovery as tcd
import taggu.contexts.library as tcl
import taggu.meta_cache as tmc
import taggu.helpers as th
import test.helpers as tsth


class TestQuery(unittest.TestCase):
    def setUp(self):
        self.root_dir_obj = tempfile.TemporaryDirectory()

        self.root_dir_pl = pl.Path(self.root_dir_obj.name)
        self.lib_ctx = tcl.gen_library_ctx(root_dir=self.root_dir_pl, media_item_filter=tsth.default_item_filter,
                                           self_meta_file_name=tsth.SELF_META_FN, item_meta_file_name=tsth.ITEM_META_FN)
        self.dis_ctx = tcd.gen_discovery_ctx(library_context=self.lib_ctx)

        dir_hier_map = tsth.gen_default_dir_hier_map()
        tsth.write_dir_hierarchy(root_dir=self.root_dir_pl,
                                 dir_mapping=dir_hier_map,
                                 item_file_suffix=tsth.ITEM_FILE_EXT)
        tsth.write_meta_files(root_dir=self.root_dir_pl, item_filter=tsth.default_item_filter)

    def test_generate(self):
        dis_ctx: tcd.DiscoveryContext = self.dis_ctx
        meta_cacher: tmc.MetaCacher = tmc.gen_meta_cacher(discovery_context=dis_ctx)

        # Expected type of meta cacher.
        self.assertIsInstance(meta_cacher, tmc.MetaCacher)

        # Cache starts out empty.
        expected = {}
        produced = meta_cacher.get_cache()
        self.assertEqual(expected, produced)

        # Discovery context is same instance as what was passed in.
        expected = dis_ctx
        produced = meta_cacher.get_discovery_context()
        self.assertIs(expected, produced)

    def test_cache_meta_files(self):
        dis_ctx: tcd.DiscoveryContext = self.dis_ctx
        meta_cacher: tmc.MetaCacher = tmc.gen_meta_cacher(discovery_context=dis_ctx)

        sample_rel_item_meta_path = pl.Path(tsth.ITEM_META_FN)
        sample_rel_self_meta_path = pl.Path(tsth.SELF_META_FN)

        meta_cacher.cache_meta_files(rel_meta_paths=(sample_rel_item_meta_path, sample_rel_self_meta_path))

        mc = meta_cacher.get_cache()
        self.assertEqual(len(mc), 2)
        self.assertIn(sample_rel_item_meta_path, mc)
        self.assertIn(sample_rel_self_meta_path, mc)

        # Clear cache.
        meta_cacher.clear_all()
        mc = meta_cacher.get_cache()
        self.assertEqual(len(mc), 0)

    def tearDown(self):
        # import ipdb; ipdb.set_trace()
        # input('Press ENTER to continue and cleanup')

        self.root_dir_obj.cleanup()

if __name__ == '__main__':
    logging.getLogger(tcd.__name__).setLevel(level=logging.WARNING)
    logging.getLogger(tcl.__name__).setLevel(level=logging.WARNING)
    logging.getLogger(th.__name__).setLevel(level=logging.WARNING)
    unittest.main()

