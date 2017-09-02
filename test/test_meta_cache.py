import logging
import pathlib as pl
import tempfile
import typing as typ
import unittest
import itertools as it
import random

import taggu.contexts.discovery as tcd
import taggu.contexts.library as tcl
import taggu.meta_cache as tmc
import taggu.helpers as th
import test.helpers as tsth


RANDOM_SEED = 27


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

    def test_get_discovery_context(self):
        dis_ctx: tcd.DiscoveryContext = self.dis_ctx
        meta_cacher: tmc.MetaCacher = tmc.gen_meta_cacher(discovery_context=dis_ctx)

        # Discovery context is same instance as what was passed in.
        expected = dis_ctx
        produced = meta_cacher.get_discovery_context()
        self.assertIs(expected, produced)

    def test_get_cache(self):
        dis_ctx: tcd.DiscoveryContext = self.dis_ctx
        meta_cacher: tmc.MetaCacher = tmc.gen_meta_cacher(discovery_context=dis_ctx)

        # Cache starts out empty.
        expected = {}
        produced = meta_cacher.get_cache()
        self.assertEqual(expected, produced)

    def test_cache_meta_files(self):
        root_dir: pl.Path = self.root_dir_pl
        dis_ctx: tcd.DiscoveryContext = self.dis_ctx
        meta_cacher: tmc.MetaCacher = tmc.gen_meta_cacher(discovery_context=dis_ctx)

        rel_meta_paths = frozenset(tsth.yield_fs_contents_recursively(root_dir=root_dir,
                                                                      pass_filter=tsth.is_meta_file_path))

        meta_cacher.cache_meta_files(rel_meta_paths=rel_meta_paths)

        mc = meta_cacher.get_cache()

        self.assertEqual(mc.keys(), rel_meta_paths)

        # Clear cache.
        meta_cacher.clear_all()
        mc = meta_cacher.get_cache()
        self.assertEqual(len(mc), 0)

    def test_cache_item_files(self):
        root_dir: pl.Path = self.root_dir_pl
        dis_ctx: tcd.DiscoveryContext = self.dis_ctx
        meta_cacher: tmc.MetaCacher = tmc.gen_meta_cacher(discovery_context=dis_ctx)

        rel_item_paths = frozenset(tsth.yield_fs_contents_recursively(root_dir=root_dir,
                                                                      pass_filter=tsth.default_item_filter))

        meta_cacher.cache_item_files(rel_item_paths=rel_item_paths)

        mc = meta_cacher.get_cache()

        cont_rel_item_paths = set()
        for metadata in mc.values():
            cont_rel_item_paths.update(metadata.keys())

        self.assertEqual(cont_rel_item_paths, rel_item_paths)

    def test_clear_meta_files(self):
        root_dir: pl.Path = self.root_dir_pl
        dis_ctx: tcd.DiscoveryContext = self.dis_ctx
        meta_cacher: tmc.MetaCacher = tmc.gen_meta_cacher(discovery_context=dis_ctx)

        rel_meta_paths = frozenset(tsth.yield_fs_contents_recursively(root_dir=root_dir,
                                                                      pass_filter=tsth.is_meta_file_path))

        meta_cacher.cache_meta_files(rel_meta_paths=rel_meta_paths)

        # Clear a portion of the meta files, chosen randomly.
        rel_meta_paths_to_delete = frozenset(random.sample(rel_meta_paths, k=(len(rel_meta_paths) // 2)))
        rel_meta_paths_to_retain = rel_meta_paths - rel_meta_paths_to_delete

        meta_cacher.clear_meta_files(rel_meta_paths=rel_meta_paths_to_delete)

        mc = meta_cacher.get_cache()

        self.assertEqual(mc.keys(), rel_meta_paths_to_retain)
        self.assertFalse(rel_meta_paths_to_delete.intersection(mc.keys()))

    def test_clear_item_files(self):
        root_dir: pl.Path = self.root_dir_pl
        dis_ctx: tcd.DiscoveryContext = self.dis_ctx
        meta_cacher: tmc.MetaCacher = tmc.gen_meta_cacher(discovery_context=dis_ctx)

        rel_item_paths = frozenset(tsth.yield_fs_contents_recursively(root_dir=root_dir,
                                                                      pass_filter=tsth.default_item_filter))

        meta_cacher.cache_item_files(rel_item_paths=rel_item_paths)

        # Clear a portion of the item files, chosen randomly.
        rel_item_paths_to_delete = frozenset(random.sample(rel_item_paths, k=(len(rel_item_paths) // 4)))

        meta_cacher.clear_item_files(rel_item_paths=rel_item_paths_to_delete)

        mc = meta_cacher.get_cache()

        cont_rel_item_paths = set()
        for metadata in mc.values():
            cont_rel_item_paths.update(metadata.keys())

        self.assertFalse(rel_item_paths_to_delete.intersection(cont_rel_item_paths))

    def test_clear_all(self):
        root_dir: pl.Path = self.root_dir_pl
        dis_ctx: tcd.DiscoveryContext = self.dis_ctx
        meta_cacher: tmc.MetaCacher = tmc.gen_meta_cacher(discovery_context=dis_ctx)

        rel_meta_paths = frozenset(tsth.yield_fs_contents_recursively(root_dir=root_dir,
                                                                      pass_filter=tsth.is_meta_file_path))

        meta_cacher.cache_meta_files(rel_meta_paths=rel_meta_paths)
        mc = meta_cacher.get_cache()

        # Assert that cache has been used and is non-empty.
        self.assertTrue(mc)

        meta_cacher.clear_all()
        mc = meta_cacher.get_cache()

        self.assertFalse(mc)

    def tearDown(self):
        # import ipdb; ipdb.set_trace()
        # input('Press ENTER to continue and cleanup')

        self.root_dir_obj.cleanup()

if __name__ == '__main__':
    logging.getLogger(tcd.__name__).setLevel(level=logging.WARNING)
    logging.getLogger(tcl.__name__).setLevel(level=logging.WARNING)
    logging.getLogger(th.__name__).setLevel(level=logging.WARNING)
    unittest.main()

