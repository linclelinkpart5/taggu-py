import logging
import pathlib as pl
import tempfile
import unittest

import taggu.contexts.discovery as tcd
import taggu.contexts.library as tcl
import taggu.contexts.query as tcq
import taggu.contexts.item as tci
import taggu.helpers as th
import test.helpers as tsth


class TestQuery(unittest.TestCase):
    def setUp(self):
        self.root_dir_obj = tempfile.TemporaryDirectory()

        self.root_dir_pl = pl.Path(self.root_dir_obj.name)
        self.lib_ctx = tcl.gen_library_ctx(root_dir=self.root_dir_pl, media_item_filter=tsth.default_item_filter,
                                           self_meta_file_name=tsth.SELF_META_FN, item_meta_file_name=tsth.ITEM_META_FN)
        self.dis_ctx = tcd.gen_discovery_ctx(library_context=self.lib_ctx)
        self.qry_ctx = tcq.gen_query_ctx(discovery_context=self.dis_ctx,
                                         label_extractor=tsth.default_label_extractor,
                                         use_cache=True,
                                         mapping_iter_style=tcq.MappingIterStyle.KEYS)

        dir_hier_map = tsth.gen_default_dir_hier_map()
        tsth.write_dir_hierarchy(root_dir=self.root_dir_pl,
                                 dir_mapping=dir_hier_map,
                                 item_file_suffix=tsth.ITEM_FILE_EXT,
                                 apply_random_salt=True)
        tsth.write_meta_files(root_dir=self.root_dir_pl, item_filter=tsth.default_item_filter, include_const_key=True)

        self.rel_meta_paths = frozenset(tsth.yield_fs_contents_recursively(root_dir=self.root_dir_pl,
                                                                           pass_filter=tsth.is_meta_file_path))

        self.rel_item_paths = frozenset(tsth.yield_fs_contents_recursively(root_dir=self.root_dir_pl,
                                                                           pass_filter=tsth.default_item_filter))

    def test_generate(self):
        qry_ctx: tcq.QueryContext = self.qry_ctx
        rel_item_paths = self.rel_item_paths

        for rel_item_path in rel_item_paths:
            tci.gen_item_ctx(query_context=qry_ctx, rel_item_path=rel_item_path)

    def test_yield_field(self):
        root_dir = self.root_dir_pl
        qry_ctx: tcq.QueryContext = self.qry_ctx
        rel_item_paths = self.rel_item_paths

        distinct_labels = frozenset((tsth.UNUSED_LABEL,))

        for rel_item_path in rel_item_paths:
            abs_item_path = root_dir / rel_item_path
            matching_labels = frozenset((tsth.default_label_extractor(abs_item_path),))

            itm_ctx = tci.gen_item_ctx(query_context=qry_ctx, rel_item_path=rel_item_path)

            # Validate item metadata.
            expected = (tsth.gen_item_meta_scl_val(rel_item_path),) if rel_item_path.parts else ()
            produced = tuple(itm_ctx.yield_field(field_name=tsth.gen_item_meta_key(rel_item_path),
                                                 labels=None))
            self.assertEqual(expected, produced)

            # # Validate item metadata with matched labels.
            # produced = tuple(qry_ctx.yield_field(rel_item_path=rel_item_path,
            #                                      field_name=tsth.ITEM_META_KEY_STR_TEMPLATE.format(rel_item_path),
            #                                      labels=matching_labels))
            # self.assertEqual(expected, produced)
            #
            # # Validate item metadata with non-matched labels.
            # expected = ()
            # produced = tuple(qry_ctx.yield_field(rel_item_path=rel_item_path,
            #                                      field_name=tsth.ITEM_META_KEY_STR_TEMPLATE.format(rel_item_path),
            #                                      labels=distinct_labels))
            # self.assertEqual(expected, produced)
            #
            # # Validate self metadata.
            # expected = (tsth.SELF_META_VAL_STR_TEMPLATE.format(rel_item_path),) if curr_abs_path.is_dir() else ()
            # produced = tuple(qry_ctx.yield_field(rel_item_path=rel_item_path,
            #                                      field_name=tsth.SELF_META_KEY_STR_TEMPLATE.format(rel_item_path),
            #                                      labels=None))
            # self.assertEqual(expected, produced)
            #
            # # Validate self metadata with matched labels.
            # produced = tuple(qry_ctx.yield_field(rel_item_path=rel_item_path,
            #                                      field_name=tsth.SELF_META_KEY_STR_TEMPLATE.format(rel_item_path),
            #                                      labels=matching_labels))
            # self.assertEqual(expected, produced)
            #
            # # Validate self metadata with non-matched labels.
            # expected = ()
            # produced = tuple(qry_ctx.yield_field(rel_item_path=rel_item_path,
            #                                      field_name=tsth.SELF_META_KEY_STR_TEMPLATE.format(rel_item_path),
            #                                      labels=distinct_labels))
            # self.assertEqual(expected, produced)

    def test_yield_parent_fields(self):
        pass

    def test_yield_child_fields(self):
        pass

    def tearDown(self):
        self.root_dir_obj.cleanup()

if __name__ == '__main__':
    logging.getLogger(tcd.__name__).setLevel(level=logging.WARNING)
    logging.getLogger(tcl.__name__).setLevel(level=logging.WARNING)
    logging.getLogger(th.__name__).setLevel(level=logging.WARNING)
    logging.getLogger(tcq.__name__).setLevel(level=logging.WARNING)
    unittest.main()
