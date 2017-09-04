import logging
import pathlib as pl
import tempfile
import unittest
import random

import taggu.contexts.discovery as tcd
import taggu.contexts.library as tcl
import taggu.meta_cache as tmc
import taggu.helpers as th
import test.helpers as tsth


RANDOM_SEED = 27

random.seed(RANDOM_SEED)


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

        self.rel_meta_paths = frozenset(tsth.yield_fs_contents_recursively(root_dir=self.root_dir_pl,
                                                                           pass_filter=tsth.is_meta_file_path))

        self.rel_item_paths = frozenset(tsth.yield_fs_contents_recursively(root_dir=self.root_dir_pl,
                                                                           pass_filter=tsth.default_item_filter))

    def new_meta_cacher(self) -> tmc.MetaCacher:
        return tmc.gen_meta_cacher(discovery_context=self.dis_ctx)

    def test_generate(self):
        dis_ctx: tcd.DiscoveryContext = self.dis_ctx
        meta_cacher = tmc.gen_meta_cacher(discovery_context=dis_ctx)

        # Expected type of meta cacher.
        self.assertIsInstance(meta_cacher, tmc.MetaCacher)

        # Cache should start out empty.
        mc = meta_cacher.get_cache()
        self.assertFalse(mc)

    def test_get_discovery_context(self):
        dis_ctx: tcd.DiscoveryContext = self.dis_ctx
        meta_cacher = tmc.gen_meta_cacher(discovery_context=dis_ctx)

        # Discovery context is same instance as what was passed in.
        expected = dis_ctx
        produced = meta_cacher.get_discovery_context()
        self.assertIs(expected, produced)

    def test_get_cache(self):
        meta_cacher = self.new_meta_cacher()

        # Cache starts out empty.
        expected = {}
        produced = meta_cacher.get_cache()
        self.assertEqual(expected, produced)

    def test_cache_meta_files(self):
        meta_cacher = self.new_meta_cacher()

        rel_meta_paths = self.rel_meta_paths

        meta_cacher.cache_meta_files(rel_meta_paths=rel_meta_paths)

        mc = meta_cacher.get_cache()

        self.assertEqual(mc.keys(), rel_meta_paths)

        # Clear cache.
        meta_cacher.clear_all()
        mc = meta_cacher.get_cache()
        self.assertEqual(len(mc), 0)

    def test_cache_item_files(self):
        meta_cacher = self.new_meta_cacher()

        rel_item_paths = self.rel_item_paths

        meta_cacher.cache_item_files(rel_item_paths=rel_item_paths)

        mc = meta_cacher.get_cache()

        cont_rel_item_paths = set()
        for metadata in mc.values():
            cont_rel_item_paths.update(metadata.keys())

        self.assertEqual(cont_rel_item_paths, rel_item_paths)

    def test_clear_meta_files(self):
        meta_cacher = self.new_meta_cacher()

        rel_meta_paths = self.rel_meta_paths

        meta_cacher.cache_meta_files(rel_meta_paths=rel_meta_paths)

        # Clear a portion of the meta files, chosen randomly.
        rel_meta_paths_to_delete = frozenset(random.sample(rel_meta_paths, k=(len(rel_meta_paths) // 2)))
        rel_meta_paths_to_retain = rel_meta_paths - rel_meta_paths_to_delete

        meta_cacher.clear_meta_files(rel_meta_paths=rel_meta_paths_to_delete)

        mc = meta_cacher.get_cache()

        self.assertEqual(mc.keys(), rel_meta_paths_to_retain)
        self.assertFalse(rel_meta_paths_to_delete.intersection(mc.keys()))

    def test_clear_item_files(self):
        meta_cacher = self.new_meta_cacher()

        rel_item_paths = self.rel_item_paths

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
        meta_cacher = self.new_meta_cacher()

        rel_meta_paths = self.rel_meta_paths

        meta_cacher.cache_meta_files(rel_meta_paths=rel_meta_paths)
        mc = meta_cacher.get_cache()

        # Assert that cache has been used and is non-empty.
        self.assertTrue(mc)

        meta_cacher.clear_all()
        mc = meta_cacher.get_cache()

        self.assertFalse(mc)

    def test_get_meta_file(self):
        meta_cacher = self.new_meta_cacher()

        rel_meta_paths = self.rel_meta_paths

        meta_cacher.cache_meta_files(rel_meta_paths=rel_meta_paths)
        mc = meta_cacher.get_cache()

        for rel_meta_path in rel_meta_paths:
            expected = mc[rel_meta_path]
            produced = meta_cacher.get_meta_file(rel_meta_path=rel_meta_path)
            self.assertEqual(expected, produced)

        with self.assertRaises(KeyError):
            meta_cacher.get_meta_file(rel_meta_path=pl.Path('DOES_NOT_EXIST'))

    def test_get_item_file(self):
        root_dir: pl.Path = self.root_dir_pl
        meta_cacher = self.new_meta_cacher()

        rel_item_paths = self.rel_item_paths

        meta_cacher.cache_item_files(rel_item_paths=rel_item_paths)

        for rel_item_path in rel_item_paths:
            abs_item_path = root_dir / rel_item_path
            if abs_item_path.is_dir():
                expected = tsth.gen_self_metadata(rel_item_path=rel_item_path)
            else:
                expected = tsth.gen_item_metadata(rel_item_path=rel_item_path)
            produced = meta_cacher.get_item_file(rel_item_path=rel_item_path)
            self.assertEqual(expected, produced)

        with self.assertRaises(KeyError):
            meta_cacher.get_item_file(rel_item_path=pl.Path('DOES_NOT_EXIST'))

    def test_contains_meta_file(self):
        meta_cacher = self.new_meta_cacher()

        rel_meta_paths = self.rel_meta_paths

        for rel_meta_path in rel_meta_paths:
            meta_cacher.cache_meta_file(rel_meta_path=rel_meta_path)
            self.assertTrue(meta_cacher.contains_meta_file(rel_meta_path=rel_meta_path))
            meta_cacher.clear_meta_file(rel_meta_path=rel_meta_path)
            self.assertFalse(meta_cacher.contains_meta_file(rel_meta_path=rel_meta_path))

    def test_contains_item_file(self):
        meta_cacher = self.new_meta_cacher()

        rel_item_paths = self.rel_item_paths

        for rel_item_path in rel_item_paths:
            meta_cacher.cache_item_file(rel_item_path=rel_item_path)
            self.assertTrue(meta_cacher.contains_item_file(rel_item_path=rel_item_path))
            meta_cacher.clear_item_file(rel_item_path=rel_item_path)
            self.assertFalse(meta_cacher.contains_item_file(rel_item_path=rel_item_path))

    def tearDown(self):
        self.root_dir_obj.cleanup()

if __name__ == '__main__':
    logging.getLogger(tcd.__name__).setLevel(level=logging.WARNING)
    logging.getLogger(tcl.__name__).setLevel(level=logging.WARNING)
    logging.getLogger(th.__name__).setLevel(level=logging.WARNING)
    unittest.main()

