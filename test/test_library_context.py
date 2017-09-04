import collections
import copy
import functools as ft
import itertools as it
import logging
import os
import os.path
import pathlib as pl
import tempfile
import typing as typ
import unittest

import taggu.contexts.library as tl
import taggu.exceptions as tex
import taggu.helpers as th

import test.helpers as tsth

EXTRA_INELIGIBLE_FN = f'EXTRA{tsth.ITEM_FN_SEP}noneligible'


class TestLibrary(unittest.TestCase):
    def setUp(self):
        self.root_dir_obj = tempfile.TemporaryDirectory()

        self.root_dir_pl = pl.Path(self.root_dir_obj.name)

        dir_hier_map = tsth.gen_default_dir_hier_map()
        tsth.write_dir_hierarchy(root_dir=self.root_dir_pl,
                                 dir_mapping=dir_hier_map,
                                 item_file_suffix=tsth.ITEM_FILE_EXT,
                                 apply_random_salt=True)
        tsth.write_meta_files(root_dir=self.root_dir_pl, item_filter=tsth.default_item_filter)
        tsth.touch_extra_files(root_dir=self.root_dir_pl, fns=('folder.png', 'output.log', EXTRA_INELIGIBLE_FN))

    def test_gen_library_ctx(self):
        # Normal usage.
        root_dir = self.root_dir_pl
        lib_ctx = tl.gen_library_ctx(root_dir=root_dir, media_item_filter=tsth.default_item_filter)

        self.assertEqual(root_dir, lib_ctx.get_root_dir())
        self.assertIs(tsth.default_item_filter, lib_ctx.get_media_item_filter())
        self.assertEqual(tsth.SELF_META_FN, lib_ctx.get_self_meta_file_name())
        self.assertEqual(tsth.ITEM_META_FN, lib_ctx.get_item_meta_file_name())

        # Test that root dir is normalized.
        lib_ctx = tl.gen_library_ctx(root_dir=(root_dir / 'dummy' / os.path.pardir),
                                     media_item_filter=tsth.default_item_filter)

        self.assertEqual(root_dir, lib_ctx.get_root_dir())

    def test_lib_ctx_co_norm(self):
        root_dir = self.root_dir_pl
        lib_ctx = tl.gen_library_ctx(root_dir=root_dir, media_item_filter=tsth.default_item_filter)

        # Normal usage.
        rel_sub_path = pl.Path('TEST')
        expected = (rel_sub_path, root_dir / rel_sub_path)
        produced = lib_ctx.co_norm(rel_sub_path=rel_sub_path)
        self.assertEqual(expected, produced)

        # Empty/curdur relative path should produce an absolute path of just the root dir.
        rel_sub_path = pl.Path('.')
        expected = (rel_sub_path, root_dir)
        produced = lib_ctx.co_norm(rel_sub_path=rel_sub_path)
        self.assertEqual(expected, produced)

        # Exception is raised if a path escapes the root dir.
        rel_sub_path = pl.Path(os.path.pardir)
        with self.assertRaises(tex.EscapingSubpath), self.assertLogs(logger=tl.__name__, level=logging.ERROR) as ctx:
            lib_ctx.co_norm(rel_sub_path=rel_sub_path)

        msg = (f'Normalized absolute path "{(root_dir / os.path.pardir).resolve()}" '
               f'is not a sub path of root directory "{root_dir}"')
        expected_log_records = frozenset((tsth.LogEntry(logger=tl.__name__, level=logging.ERROR, message=msg),))
        produced_log_records = frozenset(tsth.yield_log_entries(ctx.records))
        self.assertEqual(expected_log_records, produced_log_records)

        # Exception is raised if the relative path is actually absolute.
        rel_sub_path = pl.Path(root_dir.root)
        with self.assertRaises(tex.AbsoluteSubpath), self.assertLogs(logger=tl.__name__, level=logging.ERROR) as ctx:
            lib_ctx.co_norm(rel_sub_path=rel_sub_path)

        msg = f'Sub path "{rel_sub_path}" is not a relative path'
        expected_log_records = frozenset((tsth.LogEntry(logger=tl.__name__, level=logging.ERROR, message=msg),))
        produced_log_records = frozenset(tsth.yield_log_entries(ctx.records))
        self.assertEqual(expected_log_records, produced_log_records)

    def test_lib_ctx_yield_contains_dir(self):
        root_dir = self.root_dir_pl
        lib_ctx = tl.gen_library_ctx(root_dir=root_dir, media_item_filter=tsth.default_item_filter)

        def func(rel_sub_path: pl.Path, abs_sub_path: pl.Path):
            if abs_sub_path.is_dir():
                # A relative path to a directory yields the directory.
                expected = (rel_sub_path,)
                produced = tuple(lib_ctx.yield_contains_dir(rel_sub_path=rel_sub_path))
                self.assertEqual(expected, produced)

            else:
                # A relative path to anything else yields nothing.
                expected = ()
                produced = tuple(lib_ctx.yield_contains_dir(rel_sub_path=rel_sub_path))
                self.assertEqual(expected, produced)

        tsth.traverse(root_dir=root_dir, func=func)

    def test_lib_ctx_yield_siblings_dir(self):
        root_dir = self.root_dir_pl
        lib_ctx = tl.gen_library_ctx(root_dir=root_dir, media_item_filter=tsth.default_item_filter)

        def func(rel_sub_path: pl.Path, _: pl.Path):
            if len(rel_sub_path.parts) == 0:
                # An empty normalized relative path (i.e. at the root) yields nothing.
                expected = ()
                produced = tuple(lib_ctx.yield_siblings_dir(rel_sub_path=rel_sub_path))
                self.assertEqual(expected, produced)

            else:
                # Any non-empty normalized relative path yields the parent of that path.
                expected = (rel_sub_path.parent,)
                produced = tuple(lib_ctx.yield_siblings_dir(rel_sub_path=rel_sub_path))
                self.assertEqual(expected, produced)

        tsth.traverse(root_dir=root_dir, func=func)

    def test_lib_ctx_fuzzy_name_lookup(self):
        root_dir = self.root_dir_pl
        lib_ctx = tl.gen_library_ctx(root_dir=root_dir, media_item_filter=tsth.default_item_filter)

        def func(rel_sub_path: pl.Path, abs_sub_path: pl.Path):
            if abs_sub_path.is_dir():
                entries: typ.Sequence[str] = tuple(sorted(os.listdir(str(abs_sub_path))))

                filtered_entries = tuple(entry for entry in entries if tsth.default_item_filter(abs_sub_path / entry))

                for entry in filtered_entries:
                    # Look up each item by its unique first portion.
                    expected = entry
                    prefix = expected.split(tsth.ITEM_FN_SEP)[0]
                    produced = lib_ctx.fuzzy_name_lookup(rel_sub_dir_path=rel_sub_path,
                                                         prefix_item_name=prefix)
                    self.assertEqual(expected, produced)
                    self.assertNotEqual(prefix, produced)

                if len(entries) != 1:
                    # Get a common prefix filename that will match all entries.
                    common_prefix: str = os.path.commonprefix(entries)

                    msg = (f'Incorrect number of matches for fuzzy lookup of "{common_prefix}" '
                           f'in directory "{rel_sub_path}"; '
                           f'expected: 1, found: {len(filtered_entries)}')
                    expected_log_records = frozenset(tsth.LogEntry(logger=tl.__name__,
                                                                   level=logging.ERROR, message=msg),)

                    with self.assertRaises(tex.NonUniqueFuzzyFileLookup), \
                            self.assertLogs(logger=tl.__name__, level=logging.ERROR) as ctx:
                        lib_ctx.fuzzy_name_lookup(rel_sub_dir_path=rel_sub_path, prefix_item_name=common_prefix)

                        produced_log_records = frozenset(tsth.yield_log_entries(ctx.records))
                        self.assertEqual(expected_log_records, produced_log_records)

        tsth.traverse(root_dir=root_dir, func=func)

    def test_lib_ctx_item_names_in_dir(self):
        root_dir = self.root_dir_pl
        lib_ctx = tl.gen_library_ctx(root_dir=root_dir, media_item_filter=tsth.default_item_filter)

        def func(rel_sub_path: pl.Path, abs_sub_path: pl.Path):
            if abs_sub_path.is_dir():
                all_entries: typ.AbstractSet[str] = frozenset(os.listdir(str(abs_sub_path)))
            else:
                all_entries: typ.AbstractSet[str] = frozenset()

            passed_entries: typ.AbstractSet[str] = lib_ctx.item_names_in_dir(rel_sub_dir_path=rel_sub_path)

            self.assertLessEqual(passed_entries, all_entries)

            filtered_entries = all_entries - passed_entries
            for entry in filtered_entries:
                self.assertFalse(tsth.default_item_filter(abs_sub_path / entry))
            for entry in passed_entries:
                self.assertTrue(tsth.default_item_filter(abs_sub_path / entry))

        tsth.traverse(root_dir=root_dir, func=func)

    def test_lib_ctx_yield_self_meta_pairs(self):
        root_dir = self.root_dir_pl
        lib_ctx = tl.gen_library_ctx(root_dir=root_dir, media_item_filter=tsth.default_item_filter)

        yaml_data = {
            'field_1': 'single_value',
            'field_2': ['list_of_values', 'another_one'],
            'field_3': None,
        }

        def func(rel_sub_path: pl.Path, abs_sub_path: pl.Path):
            if abs_sub_path.is_dir():
                expected = ((rel_sub_path, yaml_data),)
                produced = tuple(lib_ctx.yield_self_meta_pairs(yaml_data=yaml_data,
                                                               rel_sub_dir_path=rel_sub_path))
                self.assertEqual(expected, produced)

        tsth.traverse(root_dir=root_dir, func=func)

    def test_lib_ctx_yield_item_meta_pairs_a(self):
        root_dir = self.root_dir_pl
        lib_ctx = tl.gen_library_ctx(root_dir=root_dir, media_item_filter=tsth.default_item_filter)

        def sequence_func(rel_sub_path: pl.Path, abs_sub_path: pl.Path):
            if abs_sub_path.is_dir():
                passed_items = lib_ctx.item_names_in_dir(rel_sub_dir_path=rel_sub_path)
                sorted_passed_items = sorted(passed_items)
                num_passed_items = len(passed_items)

                extra_records = ({f'extra_item': f'extra_value'},)

                # Construct YAML data.
                exact_record_seq = tuple({f'item_{i+1}': f'value_{i+1}'} for i in range(num_passed_items))
                extra_record_seq = tuple(it.chain(exact_record_seq, extra_records))
                insuf_record_seq = exact_record_seq[:-1]

                extra_data_log_messages = frozenset((f'Counts of items in directory and metadata blocks do not match; '
                                                     f'found {th.pluralize(num_passed_items, "item")} '
                                                     f'and {th.pluralize(len(extra_record_seq), "metadata block")}',))
                insuf_data_log_messages = frozenset(f'Counts of items in directory and metadata blocks do not match; '
                                                    f'found {th.pluralize(num_passed_items, "item")} '
                                                    f'and {th.pluralize(len(insuf_record_seq), "metadata block")}'
                                                    for _ in range(len(passed_items) - len(insuf_record_seq)))

                # Log records expected.
                extra_data_log_records = frozenset(tsth.LogEntry(logger=tl.__name__,
                                                                 level=logging.WARNING,
                                                                 message=msg)
                                                   for msg in extra_data_log_messages)
                insuf_data_log_records = frozenset(tsth.LogEntry(logger=tl.__name__,
                                                                 level=logging.WARNING,
                                                                 message=msg)
                                                   for msg in insuf_data_log_messages)

                # Create a partialed method that generates a logging checker.
                # TODO: Generalize and move to module/class level.
                logging_ctx_mgr = ft.partial(self.assertLogs, logger=tl.__name__, level=logging.WARNING)

                expected_data_and_logs = (
                    (exact_record_seq, frozenset()),
                    (extra_record_seq, extra_data_log_records),
                    (insuf_record_seq, insuf_data_log_records),
                )

                for record_seq, expected_log_records in expected_data_and_logs:
                    ctx_mgr = logging_ctx_mgr if expected_log_records else tsth.empty_context

                    # Construct YAML data.
                    yaml_data = list(record_seq)

                    with ctx_mgr() as ctx:
                        expected = tuple((rel_sub_path / item_name, yaml_block)
                                         for item_name, yaml_block in zip(sorted_passed_items, yaml_data))
                        produced = tuple(lib_ctx.yield_item_meta_pairs(yaml_data=copy.deepcopy(yaml_data),
                                                                       rel_sub_dir_path=rel_sub_path))
                        self.assertEqual(expected, produced)

                    if ctx:
                        produced_log_records = frozenset(tsth.yield_log_entries(ctx.records))
                        self.assertEqual(expected_log_records, produced_log_records)

        tsth.traverse(root_dir=root_dir, func=sequence_func)

    def test_lib_ctx_yield_item_meta_pairs_b(self):
        root_dir = self.root_dir_pl
        lib_ctx = tl.gen_library_ctx(root_dir=root_dir, media_item_filter=tsth.default_item_filter)

        # Warnings to check for:
        # 1) Invalid item names.
        # 2) Already-processed item names.
        # 3) Item names not found in directory.
        # 4) Unreferenced file names found in directory.

        LookupRecord = collections.namedtuple('LookupRecord', ('item_name', 'fuzzy_item_name', 'meta_block'))

        def mapping_func(rel_sub_path: pl.Path, abs_sub_path: pl.Path):
            if abs_sub_path.is_dir():
                passed_items = lib_ctx.item_names_in_dir(rel_sub_dir_path=rel_sub_path)
                sorted_passed_items = sorted(passed_items)

                extra_records = tuple(LookupRecord(item_name=EXTRA_INELIGIBLE_FN,
                                                   fuzzy_item_name=EXTRA_INELIGIBLE_FN.split(tsth.ITEM_FN_SEP)[0],
                                                   meta_block={f'extra_item': f'extra_value'})
                                      for _ in abs_sub_path.glob(EXTRA_INELIGIBLE_FN))
                inval_records = tuple(LookupRecord(item_name=invalid_item_name,
                                                   fuzzy_item_name=invalid_item_name,
                                                   meta_block={f'inval_item': f'inval_value'})
                                      for invalid_item_name in tsth.yield_invalid_fns())

                # Construct YAML data.
                exact_record_seq = tuple(LookupRecord(item_name=item_name,
                                                      fuzzy_item_name=item_name.split(tsth.ITEM_FN_SEP)[0],
                                                      meta_block={f'item_{i+1}': f'value_{i+1}'})
                                         for i, item_name in enumerate(sorted_passed_items))
                extra_record_seq = tuple(it.chain(exact_record_seq, extra_records))
                insuf_record_seq = exact_record_seq[:-1]
                inval_record_seq = tuple(it.chain(exact_record_seq, inval_records))
                # dupli_record_seq = tuple(it.chain(exact_record_seq, exact_record_seq[:-1]))

                # Log messages expected.
                extra_data_log_messages = frozenset(f'Item "{EXTRA_INELIGIBLE_FN}" not found in eligible item names '
                                                    f'for this directory, skipping'
                                                    for _ in extra_records)
                insuf_data_log_messages = frozenset(f'Found 1 eligible item remaining not referenced in metadata'
                                                    for _ in range(len(passed_items) - len(insuf_record_seq)))
                inval_data_log_messages = frozenset(f'Item name "{invalid_item_name}" is not valid, skipping'
                                                    for invalid_item_name in tsth.yield_invalid_fns())

                # Log records expected.
                extra_data_log_records = frozenset(tsth.LogEntry(logger=tl.__name__,
                                                                 level=logging.WARNING,
                                                                 message=msg)
                                                   for msg in extra_data_log_messages)
                insuf_data_log_records = frozenset(tsth.LogEntry(logger=tl.__name__,
                                                                 level=logging.WARNING,
                                                                 message=msg)
                                                   for msg in insuf_data_log_messages)
                inval_data_log_records = frozenset(tsth.LogEntry(logger=tl.__name__,
                                                                 level=logging.WARNING,
                                                                 message=msg)
                                                   for msg in inval_data_log_messages)

                # Create a partialed method that generates a logging checker.
                # TODO: Generalize and move to module/class level.
                logging_ctx_mgr = ft.partial(self.assertLogs, logger=tl.__name__, level=logging.WARNING)

                expected_data_and_logs = (
                    (exact_record_seq, frozenset()),
                    (extra_record_seq, extra_data_log_records),
                    (insuf_record_seq, insuf_data_log_records),
                    (inval_record_seq, inval_data_log_records),
                )

                for record_seq, expected_log_records in expected_data_and_logs:
                    ctx_mgr = logging_ctx_mgr if expected_log_records else tsth.empty_context

                    # Construct YAML data.
                    yaml_data = {r.fuzzy_item_name: r.meta_block for r in record_seq}

                    with ctx_mgr() as ctx:
                        expected = {rel_sub_path / r.item_name: r.meta_block
                                    for r in record_seq if r.item_name in passed_items}
                        produced = {k: v for k, v in lib_ctx.yield_item_meta_pairs(yaml_data=yaml_data,
                                                                                   rel_sub_dir_path=rel_sub_path)}
                        self.assertEqual(expected, produced)

                    if ctx:
                        produced_log_records = frozenset(tsth.yield_log_entries(ctx.records))
                        self.assertEqual(expected_log_records, produced_log_records)

        tsth.traverse(root_dir=root_dir, func=mapping_func)

    def test_lib_ctx_yield_meta_source_specs(self):
        root_dir = self.root_dir_pl
        lib_ctx = tl.gen_library_ctx(root_dir=root_dir, media_item_filter=tsth.default_item_filter)

        expected = (
            (pl.Path(lib_ctx.get_self_meta_file_name()), lib_ctx.yield_contains_dir, lib_ctx.yield_self_meta_pairs),
            (pl.Path(lib_ctx.get_item_meta_file_name()), lib_ctx.yield_siblings_dir, lib_ctx.yield_item_meta_pairs),
        )
        produced = tuple(lib_ctx.yield_meta_source_specs())
        self.assertEqual(expected, produced)

    def tearDown(self):
        # Uncomment this to inspect the created directory structure.
        # import ipdb; ipdb.set_trace()

        self.root_dir_obj.cleanup()

if __name__ == '__main__':
    logging.getLogger(tl.__name__).setLevel(level=logging.WARNING)
    unittest.main()
