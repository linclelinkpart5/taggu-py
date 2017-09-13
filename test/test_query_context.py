import logging
import pathlib as pl
import tempfile
import unittest
import itertools as it

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

    def test_field_flattener_a(self):
        STR = 'test'

        field_value = STR

        expected = (field_value,)
        produced = tuple(tq.field_flattener(field_value=field_value, flatten_limit=0,
                                            mapping_iter_style=tq.MappingIterStyle.KEYS))
        self.assertEqual(expected, produced)

        produced = tuple(tq.field_flattener(field_value=field_value, flatten_limit=1,
                                            mapping_iter_style=tq.MappingIterStyle.KEYS))
        self.assertEqual(expected, produced)

        produced = tuple(tq.field_flattener(field_value=field_value, flatten_limit=None,
                                            mapping_iter_style=tq.MappingIterStyle.KEYS))
        self.assertEqual(expected, produced)

        field_value = None

        expected = (field_value,)
        produced = tuple(tq.field_flattener(field_value=field_value, flatten_limit=0,
                                            mapping_iter_style=tq.MappingIterStyle.KEYS))
        self.assertEqual(expected, produced)

        produced = tuple(tq.field_flattener(field_value=field_value, flatten_limit=1,
                                            mapping_iter_style=tq.MappingIterStyle.KEYS))
        self.assertEqual(expected, produced)

        produced = tuple(tq.field_flattener(field_value=field_value, flatten_limit=None,
                                            mapping_iter_style=tq.MappingIterStyle.KEYS))
        self.assertEqual(expected, produced)

        field_value = (STR, None)

        expected = (field_value,)
        produced = tuple(tq.field_flattener(field_value=field_value, flatten_limit=0,
                                            mapping_iter_style=tq.MappingIterStyle.KEYS))
        self.assertEqual(expected, produced)

        expected = field_value
        produced = tuple(tq.field_flattener(field_value=field_value, flatten_limit=1,
                                            mapping_iter_style=tq.MappingIterStyle.KEYS))
        self.assertEqual(expected, produced)

        produced = tuple(tq.field_flattener(field_value=field_value, flatten_limit=None,
                                            mapping_iter_style=tq.MappingIterStyle.KEYS))
        self.assertEqual(expected, produced)

        field_value = ((STR, None), STR, (None, None, (STR, STR)))

        expected = (field_value,)
        produced = tuple(tq.field_flattener(field_value=field_value, flatten_limit=0,
                                            mapping_iter_style=tq.MappingIterStyle.KEYS))
        self.assertEqual(expected, produced)

        expected = field_value
        produced = tuple(tq.field_flattener(field_value=field_value, flatten_limit=1,
                                            mapping_iter_style=tq.MappingIterStyle.KEYS))
        self.assertEqual(expected, produced)

        expected = (STR, None, STR, None, None, (STR, STR))
        produced = tuple(tq.field_flattener(field_value=field_value, flatten_limit=2,
                                            mapping_iter_style=tq.MappingIterStyle.KEYS))
        self.assertEqual(expected, produced)

        expected = (STR, None, STR, None, None, STR, STR)
        produced = tuple(tq.field_flattener(field_value=field_value, flatten_limit=None,
                                            mapping_iter_style=tq.MappingIterStyle.KEYS))
        self.assertEqual(expected, produced)

    def test_field_flattener_b(self):
        field_value = {f'key{i}': f'val{i}' for i in range(5)}

        expected = (field_value,)
        produced = tuple(tq.field_flattener(field_value=field_value, flatten_limit=0,
                                            mapping_iter_style=tq.MappingIterStyle.KEYS))
        self.assertEqual(expected, produced)

        expected = tuple(field_value.keys())
        produced = tuple(tq.field_flattener(field_value=field_value, flatten_limit=1,
                                            mapping_iter_style=tq.MappingIterStyle.KEYS))
        self.assertEqual(expected, produced)

        expected = (field_value,)
        produced = tuple(tq.field_flattener(field_value=field_value, flatten_limit=0,
                                            mapping_iter_style=tq.MappingIterStyle.VALS))
        self.assertEqual(expected, produced)

        expected = tuple(field_value.values())
        produced = tuple(tq.field_flattener(field_value=field_value, flatten_limit=1,
                                            mapping_iter_style=tq.MappingIterStyle.VALS))
        self.assertEqual(expected, produced)

        expected = (field_value,)
        produced = tuple(tq.field_flattener(field_value=field_value, flatten_limit=0,
                                            mapping_iter_style=tq.MappingIterStyle.PAIRS))
        self.assertEqual(expected, produced)

        expected = tuple(field_value.items())
        produced = tuple(tq.field_flattener(field_value=field_value, flatten_limit=1,
                                            mapping_iter_style=tq.MappingIterStyle.PAIRS))
        self.assertEqual(expected, produced)

        def yield_all(mapping):
            for k, v in mapping.items():
                yield k
                yield v

        expected = tuple(yield_all(field_value))
        produced = tuple(tq.field_flattener(field_value=field_value, flatten_limit=2,
                                            mapping_iter_style=tq.MappingIterStyle.PAIRS))
        self.assertEqual(expected, produced)

        field_value = {(f'key{i}_a', f'key{i}_b'): (f'val{i}_a', f'val{i}_b') for i in range(5)}

        expected = (field_value,)
        produced = tuple(tq.field_flattener(field_value=field_value, flatten_limit=0,
                                            mapping_iter_style=tq.MappingIterStyle.KEYS))
        self.assertEqual(expected, produced)

        expected = tuple(field_value.keys())
        produced = tuple(tq.field_flattener(field_value=field_value, flatten_limit=1,
                                            mapping_iter_style=tq.MappingIterStyle.KEYS))
        self.assertEqual(expected, produced)

        expected = tuple(it.chain.from_iterable(field_value.keys()))
        produced = tuple(tq.field_flattener(field_value=field_value, flatten_limit=2,
                                            mapping_iter_style=tq.MappingIterStyle.KEYS))
        self.assertEqual(expected, produced)

        expected = (field_value,)
        produced = tuple(tq.field_flattener(field_value=field_value, flatten_limit=0,
                                            mapping_iter_style=tq.MappingIterStyle.VALS))
        self.assertEqual(expected, produced)

        expected = tuple(field_value.values())
        produced = tuple(tq.field_flattener(field_value=field_value, flatten_limit=1,
                                            mapping_iter_style=tq.MappingIterStyle.VALS))
        self.assertEqual(expected, produced)

        expected = tuple(it.chain.from_iterable(field_value.values()))
        produced = tuple(tq.field_flattener(field_value=field_value, flatten_limit=2,
                                            mapping_iter_style=tq.MappingIterStyle.VALS))
        self.assertEqual(expected, produced)

    def test_yield_field(self):
        root_dir = self.root_dir_pl
        qry_ctx = tq.gen_query_ctx(discovery_context=self.dis_ctx,
                                   label_extractor=tsth.default_label_extractor,
                                   use_cache=True)

        def func(curr_rel_path: pl.Path, curr_abs_path: pl.Path):
            matching_labels = frozenset((tsth.default_label_extractor(curr_abs_path),))
            distinct_labels = frozenset((tsth.UNUSED_LABEL,))

            # Validate item metadata.
            expected = (tsth.gen_item_meta_str_val(curr_rel_path),) if curr_rel_path.parts else ()
            produced = tuple(qry_ctx.yield_field(rel_item_path=curr_rel_path,
                                                 field_name=tsth.gen_item_meta_key(curr_rel_path),
                                                 labels=None,
                                                 mapping_iter_style=tq.MappingIterStyle.KEYS))
            self.assertEqual(expected, produced)

            # Validate item metadata with matched labels.
            produced = tuple(qry_ctx.yield_field(rel_item_path=curr_rel_path,
                                                 field_name=tsth.gen_item_meta_key(curr_rel_path),
                                                 labels=matching_labels,
                                                 mapping_iter_style=tq.MappingIterStyle.KEYS))
            self.assertEqual(expected, produced)

            # Validate item metadata with non-matched labels.
            expected = ()
            produced = tuple(qry_ctx.yield_field(rel_item_path=curr_rel_path,
                                                 field_name=tsth.gen_item_meta_key(curr_rel_path),
                                                 labels=distinct_labels,
                                                 mapping_iter_style=tq.MappingIterStyle.KEYS))
            self.assertEqual(expected, produced)

            # Validate self metadata.
            expected = (tsth.gen_self_meta_str_val(curr_rel_path),) if curr_abs_path.is_dir() else ()
            produced = tuple(qry_ctx.yield_field(rel_item_path=curr_rel_path,
                                                 field_name=tsth.gen_self_meta_key(curr_rel_path),
                                                 labels=None,
                                                 mapping_iter_style=tq.MappingIterStyle.KEYS))
            self.assertEqual(expected, produced)

            # Validate self metadata with matched labels.
            produced = tuple(qry_ctx.yield_field(rel_item_path=curr_rel_path,
                                                 field_name=tsth.gen_self_meta_key(curr_rel_path),
                                                 labels=matching_labels,
                                                 mapping_iter_style=tq.MappingIterStyle.KEYS))
            self.assertEqual(expected, produced)

            # Validate self metadata with non-matched labels.
            expected = ()
            produced = tuple(qry_ctx.yield_field(rel_item_path=curr_rel_path,
                                                 field_name=tsth.gen_self_meta_key(curr_rel_path),
                                                 labels=distinct_labels,
                                                 mapping_iter_style=tq.MappingIterStyle.KEYS))
            self.assertEqual(expected, produced)

            # TODO: See if this test is better suited for the YAML loader test.
            # # Validate null metadata.
            # expected = (None,)
            # produced = tuple(qry_ctx.yield_field(rel_item_path=curr_rel_path,
            #                                      field_name=None,
            #                                      labels=None))
            # self.assertEqual(expected, produced)

        tsth.traverse(root_dir=root_dir, func=func, action_filter=tsth.default_item_filter)

    def test_yield_parent_fields(self):
        root_dir = self.root_dir_pl
        qry_ctx = tq.gen_query_ctx(discovery_context=self.dis_ctx, label_extractor=None, use_cache=True)

        def func(curr_rel_path: pl.Path, _: pl.Path):
            for rel_parent in curr_rel_path.parents:
                # Generate expected field names.
                item_field_name = tsth.gen_item_meta_key(rel_parent)
                self_field_name = tsth.gen_self_meta_key(rel_parent)

                # Calculate distance from relative parent path to relative target path.
                rel_parent_distance = len(curr_rel_path.parts) - len(rel_parent.parts)

                # Validate item metadata.
                expected = (tsth.gen_item_meta_str_val(rel_parent),) if rel_parent.parts else ()
                produced = tuple(qry_ctx.yield_parent_fields(rel_item_path=curr_rel_path,
                                                             field_name=item_field_name,
                                                             labels=None,
                                                             mapping_iter_style=tq.MappingIterStyle.KEYS))
                self.assertEqual(expected, produced)

                # Validate item metadata with exact max distance.
                produced = tuple(qry_ctx.yield_parent_fields(rel_item_path=curr_rel_path,
                                                             field_name=item_field_name,
                                                             labels=None,
                                                             max_distance=rel_parent_distance,
                                                             mapping_iter_style=tq.MappingIterStyle.KEYS))
                self.assertEqual(expected, produced)

                # Validate item metadata with insufficient max distance.
                expected = ()
                produced = tuple(qry_ctx.yield_parent_fields(rel_item_path=curr_rel_path,
                                                             field_name=item_field_name,
                                                             labels=None,
                                                             max_distance=(rel_parent_distance - 1),
                                                             mapping_iter_style=tq.MappingIterStyle.KEYS))
                self.assertEqual(expected, produced)

                # Validate self metadata.
                expected = (tsth.gen_self_meta_str_val(rel_parent),)
                produced = tuple(qry_ctx.yield_parent_fields(rel_item_path=curr_rel_path,
                                                             field_name=self_field_name,
                                                             labels=None,
                                                             mapping_iter_style=tq.MappingIterStyle.KEYS))
                self.assertEqual(expected, produced)

                # Validate self metadata with exact max distance.
                produced = tuple(qry_ctx.yield_parent_fields(rel_item_path=curr_rel_path,
                                                             field_name=self_field_name,
                                                             labels=None,
                                                             max_distance=rel_parent_distance,
                                                             mapping_iter_style=tq.MappingIterStyle.KEYS))
                self.assertEqual(expected, produced)

                # Validate self metadata with insufficient max distance.
                expected = ()
                produced = tuple(qry_ctx.yield_parent_fields(rel_item_path=curr_rel_path,
                                                             field_name=self_field_name,
                                                             labels=None,
                                                             max_distance=(rel_parent_distance - 1),
                                                             mapping_iter_style=tq.MappingIterStyle.KEYS))
                self.assertEqual(expected, produced)

        tsth.traverse(root_dir=root_dir, func=func, action_filter=tsth.default_item_filter)

    def test_yield_child_fields(self):
        root_dir = self.root_dir_pl
        qry_ctx = tq.gen_query_ctx(discovery_context=self.dis_ctx, label_extractor=None, use_cache=True)
        dis_ctx = qry_ctx.get_discovery_context()
        lib_ctx = dis_ctx.get_library_context()

        def func(curr_rel_path: pl.Path, curr_abs_path: pl.Path):
            if curr_abs_path.is_dir():
                expected = tuple(tsth.gen_cnst_meta_str_val(curr_rel_path / p)
                                 for p in lib_ctx.sorted_item_names_in_dir(curr_rel_path))
                produced = tuple(qry_ctx.yield_child_fields(rel_item_path=curr_rel_path,
                                                            field_name=tsth.CNST_META_KEY,
                                                            labels=None,
                                                            mapping_iter_style=tq.MappingIterStyle.KEYS))
                self.assertEqual(expected, produced)

                def subfunc(crp: pl.Path, cap: pl.Path):
                    # Skip this item if it is the same as the outer item.
                    if crp == curr_rel_path:
                        return

                    # Calculate relative distance between both endpoint relative paths.
                    rel_distance = len(crp.parts) - len(curr_rel_path.parts)

                    self.assertGreater(rel_distance, 0)

                    # Validate item metadata.
                    exp = (tsth.gen_item_meta_str_val(crp),) if crp.parents else ()
                    prd = tuple(qry_ctx.yield_child_fields(rel_item_path=curr_rel_path,
                                                           field_name=tsth.gen_item_meta_key(crp),
                                                           labels=None,
                                                           mapping_iter_style=tq.MappingIterStyle.KEYS))
                    self.assertEqual(exp, prd)

                    # Validate item metadata with exact max distance.
                    prd = tuple(qry_ctx.yield_child_fields(rel_item_path=curr_rel_path,
                                                           field_name=tsth.gen_item_meta_key(crp),
                                                           labels=None,
                                                           max_distance=rel_distance,
                                                           mapping_iter_style=tq.MappingIterStyle.KEYS))
                    self.assertEqual(exp, prd)

                    # Validate item metadata with insufficient max distance.
                    exp = ()
                    prd = tuple(qry_ctx.yield_child_fields(rel_item_path=curr_rel_path,
                                                           field_name=tsth.gen_item_meta_key(crp),
                                                           labels=None,
                                                           max_distance=(rel_distance - 1),
                                                           mapping_iter_style=tq.MappingIterStyle.KEYS))
                    self.assertEqual(exp, prd)

                    # Validate self metadata.
                    exp = (tsth.gen_self_meta_str_val(crp),) if cap.is_dir() else ()
                    prd = tuple(qry_ctx.yield_child_fields(rel_item_path=curr_rel_path,
                                                           field_name=tsth.gen_self_meta_key(crp),
                                                           labels=None,
                                                           mapping_iter_style=tq.MappingIterStyle.KEYS))
                    self.assertEqual(exp, prd)

                    # Validate item metadata with exact max distance.
                    prd = tuple(qry_ctx.yield_child_fields(rel_item_path=curr_rel_path,
                                                           field_name=tsth.gen_self_meta_key(crp),
                                                           labels=None,
                                                           max_distance=rel_distance,
                                                           mapping_iter_style=tq.MappingIterStyle.KEYS))
                    self.assertEqual(exp, prd)

                    # Validate item metadata with insufficient max distance.
                    exp = ()
                    prd = tuple(qry_ctx.yield_child_fields(rel_item_path=curr_rel_path,
                                                           field_name=tsth.gen_self_meta_key(crp),
                                                           labels=None,
                                                           max_distance=(rel_distance - 1),
                                                           mapping_iter_style=tq.MappingIterStyle.KEYS))
                    self.assertEqual(exp, prd)

                tsth.traverse(root_dir=root_dir, offset_sub_path=curr_rel_path,
                              func=subfunc, action_filter=tsth.default_item_filter)
            else:
                # Looking at a file item, which would have no children.
                expected = ()
                produced = tuple(qry_ctx.yield_child_fields(rel_item_path=curr_rel_path,
                                                            field_name=tsth.CNST_META_KEY,
                                                            labels=None,
                                                            mapping_iter_style=tq.MappingIterStyle.KEYS))
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
