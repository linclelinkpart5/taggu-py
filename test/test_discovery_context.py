import logging
import pathlib as pl
import tempfile
import unittest

import taggu.contexts.discovery as tcd
import taggu.contexts.library as tcl
import taggu.helpers as th
import test.helpers as tsth


class TestDiscovery(unittest.TestCase):
    def setUp(self):
        self.root_dir_obj = tempfile.TemporaryDirectory()

        self.root_dir_pl = pl.Path(self.root_dir_obj.name)
        self.lib_ctx = tcl.gen_library_ctx(root_dir=self.root_dir_pl, media_item_filter=tsth.default_item_filter,
                                           self_meta_file_name=tsth.SELF_META_FN, item_meta_file_name=tsth.ITEM_META_FN)
        self.dis_ctx = tcd.gen_discovery_ctx(library_context=self.lib_ctx)

        dir_hier_map = tsth.gen_default_dir_hier_map()
        tsth.write_dir_hierarchy(root_dir=self.root_dir_pl,
                                 dir_mapping=dir_hier_map,
                                 item_file_suffix=tsth.ITEM_FILE_EXT,
                                 apply_random_salt=True)
        tsth.write_meta_files(root_dir=self.root_dir_pl, item_filter=tsth.default_item_filter, include_const_key=False)

    def test_meta_files_from_item(self):
        lib_ctx = self.lib_ctx
        dis_ctx = tcd.gen_discovery_ctx(library_context=lib_ctx)
        root_dir = lib_ctx.get_root_dir()

        def helper(curr_rel_path: pl.Path, curr_abs_path: pl.Path):
            def yielder():
                if curr_abs_path.is_dir():
                    yield curr_rel_path / tsth.SELF_META_FN
                if curr_rel_path != curr_rel_path.parent:
                    yield curr_rel_path.parent / tsth.ITEM_META_FN

            expected = tuple(yielder())
            produced = tuple(dis_ctx.meta_files_from_item(rel_item_path=curr_rel_path))
            self.assertEqual(expected, produced)

        tsth.traverse(root_dir=root_dir, func=helper)

    def test_items_from_meta_file(self):
        lib_ctx = self.lib_ctx
        dis_ctx = tcd.gen_discovery_ctx(library_context=lib_ctx)
        root_dir = lib_ctx.get_root_dir()

        # Collect all relative meta paths.
        meta_paths = set()
        for meta_fn in (tsth.SELF_META_FN, tsth.ITEM_META_FN):
            for meta_abs_path in root_dir.rglob(meta_fn):
                meta_rel_path = meta_abs_path.relative_to(root_dir)
                meta_paths.add((meta_rel_path, meta_abs_path))

        meta_paths = frozenset(meta_paths)

        # Test each relative meta path.
        for meta_rel_path, meta_abs_path in meta_paths:
            if meta_rel_path.name == tsth.ITEM_META_FN:
                def yielder():
                    # Get all interesting items in the same directory as this item meta file.
                    parent_abs_path = meta_abs_path.parent
                    for entry in parent_abs_path.iterdir():
                        if tsth.default_item_filter(entry):
                            item_rel_path = entry.relative_to(lib_ctx.get_root_dir())
                            yield (item_rel_path,
                                   {tsth.gen_item_meta_key(item_rel_path): tsth.gen_item_meta_str_val(item_rel_path)})

            elif meta_rel_path.name == tsth.SELF_META_FN:
                def yielder():
                    # Get the parent dir containing this self meta file.
                    yield (meta_rel_path.parent,
                           {tsth.gen_self_meta_key(meta_rel_path.parent):
                            tsth.gen_self_meta_str_val(meta_rel_path.parent)})
            else:
                # Not a meta file.
                continue

            # Sort the outputs.
            expected = sorted(yielder(), key=lambda x: x[0])
            produced = sorted(dis_ctx.items_from_meta_file(rel_meta_path=meta_rel_path), key=lambda x: x[0])
            self.assertEqual(expected, produced)

    def tearDown(self):
        self.root_dir_obj.cleanup()


if __name__ == '__main__':
    logging.getLogger(tcd.__name__).setLevel(level=logging.WARNING)
    logging.getLogger(tcl.__name__).setLevel(level=logging.WARNING)
    logging.getLogger(th.__name__).setLevel(level=logging.WARNING)
    unittest.main()
