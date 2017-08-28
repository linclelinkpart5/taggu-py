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

        dir_hier_map = tsth.gen_default_dir_hier_map()
        tsth.write_dir_hierarchy(root_dir=self.root_dir_pl,
                                 dir_mapping=dir_hier_map,
                                 item_file_suffix=tsth.ITEM_FILE_EXT,
                                 apply_random_salt=True)
        tsth.write_meta_files(root_dir=self.root_dir_pl, item_filter=tsth.default_item_filter, include_const_key=True)

    def test_yield_field(self):
        root_dir = self.root_dir_pl
        qry_ctx = tq.gen_lookup_ctx(discovery_context=self.dis_ctx)

        def func(curr_rel_path: pl.Path, curr_abs_path: pl.Path):
            # Validate item metadata.
            expected = (tsth.ITEM_META_VAL_STR_TEMPLATE.format(curr_rel_path),) if curr_rel_path.parts else ()
            produced = tuple(qry_ctx.yield_field(rel_item_path=curr_rel_path,
                                                 field_name=tsth.ITEM_META_KEY_STR_TEMPLATE.format(curr_rel_path)))
            self.assertEqual(expected, produced)

            # Validate self metadata.
            expected = (tsth.SELF_META_VAL_STR_TEMPLATE.format(curr_rel_path),) if curr_abs_path.is_dir() else ()
            produced = tuple(qry_ctx.yield_field(rel_item_path=curr_rel_path,
                                                 field_name=tsth.SELF_META_KEY_STR_TEMPLATE.format(curr_rel_path)))
            self.assertEqual(expected, produced)

        tsth.traverse(root_dir=root_dir, func=func, action_filter=tsth.default_item_filter)

    def test_yield_parent_fields(self):
        # TODO: Test distance parameter.
        root_dir = self.root_dir_pl
        qry_ctx = tq.gen_lookup_ctx(discovery_context=self.dis_ctx)

        def func(curr_rel_path: pl.Path, _: pl.Path):
            for rel_parent in curr_rel_path.parents:
                # Validate item metadata.
                item_field_name = tsth.ITEM_META_KEY_STR_TEMPLATE.format(rel_parent)
                expected = (tsth.ITEM_META_VAL_STR_TEMPLATE.format(rel_parent),) if rel_parent.parts else ()
                produced = tuple(qry_ctx.yield_parent_fields(rel_item_path=curr_rel_path,
                                                             field_name=item_field_name))
                self.assertEqual(expected, produced)

                # Validate self metadata.
                self_field_name = tsth.SELF_META_KEY_STR_TEMPLATE.format(rel_parent)
                expected = (tsth.SELF_META_VAL_STR_TEMPLATE.format(rel_parent),)
                produced = tuple(qry_ctx.yield_parent_fields(rel_item_path=curr_rel_path,
                                                             field_name=self_field_name))
                self.assertEqual(expected, produced)

        tsth.traverse(root_dir=root_dir, func=func, action_filter=tsth.default_item_filter)

    def test_yield_child_fields(self):
        # TODO: Test distance parameter.
        root_dir = self.root_dir_pl
        qry_ctx = tq.gen_lookup_ctx(discovery_context=self.dis_ctx)
        dis_ctx = qry_ctx.get_discovery_context()
        lib_ctx = dis_ctx.get_library_context()

        def func(curr_rel_path: pl.Path, curr_abs_path: pl.Path):
            if curr_abs_path.is_dir():
                expected = tuple(tsth.CNST_META_VAL_STR_TEMPLATE.format(curr_rel_path / p)
                                 for p in lib_ctx.sorted_item_names_in_dir(curr_rel_path))
                produced = tuple(qry_ctx.yield_child_fields(rel_item_path=curr_rel_path,
                                                            field_name=tsth.CNST_META_KEY))
                self.assertEqual(expected, produced)

                def subfunc(crp: pl.Path, cap: pl.Path):
                    if crp == curr_rel_path:
                        return

                    exp = (tsth.ITEM_META_VAL_STR_TEMPLATE.format(crp),) if crp.parents else ()
                    prd = tuple(qry_ctx.yield_child_fields(rel_item_path=curr_rel_path,
                                                           field_name=tsth.ITEM_META_KEY_STR_TEMPLATE.format(crp)))
                    self.assertEqual(exp, prd)

                    exp = (tsth.SELF_META_VAL_STR_TEMPLATE.format(crp),) if cap.is_dir() else ()
                    prd = tuple(qry_ctx.yield_child_fields(rel_item_path=curr_rel_path,
                                                           field_name=tsth.SELF_META_KEY_STR_TEMPLATE.format(crp)))
                    self.assertEqual(exp, prd)

                tsth.traverse(root_dir=root_dir, offset_sub_path=curr_rel_path,
                              func=subfunc, action_filter=tsth.default_item_filter)
            else:
                # Looking at a file item, which would have no children.
                expected = ()
                produced = tuple(qry_ctx.yield_child_fields(rel_item_path=curr_rel_path, field_name=tsth.CNST_META_KEY))
                self.assertEqual(expected, produced)

        tsth.traverse(root_dir=root_dir, func=func, action_filter=tsth.default_item_filter)

    def tearDown(self):
        # import ipdb; ipdb.set_trace()
        # input('Press ENTER to continue and cleanup')

        self.root_dir_obj.cleanup()

if __name__ == '__main__':
    logging.getLogger(td.__name__).setLevel(level=logging.WARNING)
    logging.getLogger(tl.__name__).setLevel(level=logging.WARNING)
    logging.getLogger(th.__name__).setLevel(level=logging.WARNING)
    logging.getLogger(tq.__name__).setLevel(level=logging.WARNING)
    unittest.main()
