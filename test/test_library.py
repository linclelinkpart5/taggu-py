import typing as typ
import unittest
import pathlib as pl
import tempfile
import os
import os.path
import random
import string
import logging
import copy
import collections
import contextlib
import functools as ft
import itertools as it

import taggu.library as tl
import taggu.exceptions as tex
import taggu.helpers as th

A_LABEL = 'ALBUM'
D_LABEL = 'DISC'
T_LABEL = 'TRACK'
S_LABEL = 'SUBTRACK'
SALT_STR = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
EXT = '.flac'
FUZZY_SEP = '_'
EXTRA_INELIGIBLE_FN = f'EXTRA{FUZZY_SEP}{SALT_STR}'
INVALID_ITEM_NAMES = ('', os.path.curdir, os.path.pardir, os.path.sep,
                      f'a{os.path.sep}', f'a{os.path.sep}{os.path.curdir}', f'a{os.path.sep}{os.path.pardir}')
if os.path.altsep:
    INVALID_ITEM_NAMES = tuple(it.chain(INVALID_ITEM_NAMES, (os.path.altsep,)))

HIERARCHY = (A_LABEL, D_LABEL, T_LABEL, S_LABEL)


LogEntry = collections.namedtuple('LogEntry', ('logger', 'level', 'message'))


@contextlib.contextmanager
def empty_context():
    """A context manager that does nothing, mainly useful for unit testing."""
    yield


def item_filter(abs_item_path: pl.Path) -> bool:
    ext = abs_item_path.suffix
    return (abs_item_path.is_file() and ext == EXT) or abs_item_path.is_dir()


def compare_log_record(record: logging.LogRecord, name: str, levelno: int, message: str) -> bool:
    return record.name == name and record.levelno == levelno and record.getMessage() == message


def yield_log_records(ctx_manager_records: typ.Sequence[logging.LogRecord]) -> typ.Generator[LogEntry, None, None]:
    for lr in ctx_manager_records:
        yield LogEntry(logger=lr.name, level=lr.levelno, message=lr.getMessage())


class TestLibrary(unittest.TestCase):
    @classmethod
    def rel_path_from_nums(cls, nums: typ.Sequence[typ.Optional[int]], with_ext: bool=False) -> pl.Path:
        p = pl.Path()

        for lbl, num in zip(HIERARCHY, nums):
            if num is None:
                continue

            # This produces a name such that the portion before the underscore is unique for each file in a directory.
            stub = f'{lbl}{num:02}{FUZZY_SEP}{SALT_STR}'
            p = p / stub

        if with_ext:
            p = p.with_suffix(f'{EXT}')
        return p

    def setUp(self):
        self.root_dir_obj = tempfile.TemporaryDirectory()

        self.root_dir_pl = pl.Path(self.root_dir_obj.name)

        def deep_touch(path: pl.Path):
            path = self.root_dir_pl / path
            pl.Path(path.parent).mkdir(parents=True, exist_ok=True)
            path.touch(exist_ok=True)

            # Create other files.
            path.with_name('folder.png').touch(exist_ok=True)
            path.with_name('output.log').touch(exist_ok=True)
            path.with_name('taggu_file.yml').touch(exist_ok=True)
            path.with_name('taggu_self.yml').touch(exist_ok=True)
            path.with_name(EXTRA_INELIGIBLE_FN).touch(exist_ok=True)

        def nums() -> typ.Generator[typ.Sequence[typ.Optional[int]], None, None]:
            # Well-behaved album, disc, and track hierarchy.
            yield (1, 1, 1)
            yield (1, 1, 2)
            yield (1, 1, 3)
            yield (1, 2, 1)
            yield (1, 2, 2)
            yield (1, 2, 3)

            # Album with a disc and tracks, and loose tracks not on a disc.
            yield (2, 1, 1)
            yield (2, 1, 2)
            yield (2, 1, 3)
            yield (2, None, 1)
            yield (2, None, 2)
            yield (2, None, 3)

            # Album with discs and tracks, and subtracks on one disc.
            yield (3, 1, 1)
            yield (3, 1, 2)
            yield (3, 1, 3)
            yield (3, 2, 1, 1)
            yield (3, 2, 1, 2)
            yield (3, 2, 2, 1)
            yield (3, 2, 2, 2)
            yield (3, 2, 3)

            # Album that consists of one file.
            yield (4,)

            # A very messed-up album.
            yield (5, None, 1)
            yield (5, None, 2)
            yield (5, None, 3)
            yield (5, 1, None, 1)
            yield (5, 1, None, 2)
            yield (5, 2, 1, 1)
            yield (5, 2, 1, 2)

        for num_seq in nums():
            p = self.rel_path_from_nums(num_seq, with_ext=True)
            deep_touch(p)

    @staticmethod
    def traverse(lib_ctx: tl.LibraryContext, func: typ.Callable[[pl.Path, pl.Path], None]):
        def helper(curr_rel_path: pl.Path):
            curr_rel_path, curr_abs_path = lib_ctx.co_norm(rel_sub_path=curr_rel_path)

            func(curr_rel_path, curr_abs_path)

            if curr_abs_path.is_dir():
                for entry in os.listdir(curr_abs_path):
                    helper(curr_rel_path / entry)

        helper(pl.Path())

    def test_gen_library_ctx(self):
        # Normal usage.
        root_dir = self.root_dir_pl
        lib_ctx = tl.gen_library_ctx(root_dir=root_dir, media_item_filter=item_filter)

        self.assertEqual(root_dir, lib_ctx.get_root_dir())
        self.assertIs(item_filter, lib_ctx.get_media_item_filter())
        self.assertEqual('taggu_self.yml', lib_ctx.get_self_meta_file_name())
        self.assertEqual('taggu_item.yml', lib_ctx.get_item_meta_file_name())

        # Test that root dir is normalized.
        lib_ctx = tl.gen_library_ctx(root_dir=(root_dir / 'dummy' / os.path.pardir), media_item_filter=item_filter)

        self.assertEqual(root_dir, lib_ctx.get_root_dir())

    def test_lib_ctx_co_norm(self):
        root_dir = self.root_dir_pl
        lib_ctx = tl.gen_library_ctx(root_dir=root_dir, media_item_filter=item_filter)

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
        with self.assertRaises(tex.EscapingSubpath):
            lib_ctx.co_norm(rel_sub_path=rel_sub_path)

        # Exception is raised if the path is not absolute.
        rel_sub_path = pl.Path(root_dir.root)
        with self.assertRaises(tex.AbsoluteSubpath):
            lib_ctx.co_norm(rel_sub_path=rel_sub_path)

    def test_lib_ctx_yield_contains_dir(self):
        root_dir = self.root_dir_pl
        lib_ctx = tl.gen_library_ctx(root_dir=root_dir, media_item_filter=item_filter)

        def helper(rel_sub_path: pl.Path, abs_sub_path: pl.Path):
            if abs_sub_path.is_dir():
                # A relative path to a directory yields the directory.
                expected = (rel_sub_path,)
                produced = tuple(lib_ctx.yield_contains_dir(rel_sub_path=rel_sub_path))
                self.assertEqual(expected, produced)

            elif abs_sub_path.is_file():
                # A relative path to a file yields nothing.
                expected = ()
                produced = tuple(lib_ctx.yield_contains_dir(rel_sub_path=rel_sub_path))
                self.assertEqual(expected, produced)

        self.traverse(lib_ctx, helper)

    def test_lib_ctx_yield_siblings_dir(self):
        root_dir = self.root_dir_pl
        lib_ctx = tl.gen_library_ctx(root_dir=root_dir, media_item_filter=item_filter)

        def helper(rel_sub_path: pl.Path, _: pl.Path):
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

        self.traverse(lib_ctx, helper)

    def test_lib_ctx_fuzzy_name_lookup(self):
        root_dir = self.root_dir_pl
        lib_ctx = tl.gen_library_ctx(root_dir=root_dir, media_item_filter=item_filter)

        def helper(rel_sub_path: pl.Path, abs_sub_path: pl.Path):
            if abs_sub_path.is_dir():
                entries: typ.Sequence[str] = tuple(sorted(os.listdir(abs_sub_path)))

                filtered_entries = tuple(entry for entry in entries if item_filter(abs_sub_path / entry))

                for entry in filtered_entries:
                    # Look up each item by its unique first portion.
                    expected = entry
                    prefix = expected.split(FUZZY_SEP)[0]
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
                    expected_log_records = frozenset(LogEntry(logger=tl.__name__, level=logging.ERROR, message=msg),)

                    with self.assertRaises(tex.NonUniqueFuzzyFileLookup), \
                            self.assertLogs(logger=tl.__name__, level=logging.ERROR) as ctx:
                        lib_ctx.fuzzy_name_lookup(rel_sub_dir_path=rel_sub_path, prefix_item_name=common_prefix)

                        produced_log_records = frozenset(yield_log_records(ctx.records))
                        self.assertEqual(expected_log_records, produced_log_records)

        self.traverse(lib_ctx, helper)

    def test_lib_ctx_item_names_in_dir(self):
        root_dir = self.root_dir_pl
        lib_ctx = tl.gen_library_ctx(root_dir=root_dir, media_item_filter=item_filter)

        def helper(rel_sub_path: pl.Path, abs_sub_path: pl.Path):
            if abs_sub_path.is_dir():
                all_entries: typ.AbstractSet[str] = frozenset(os.listdir(abs_sub_path))
            else:
                all_entries: typ.AbstractSet[str] = frozenset()

            passed_entries: typ.AbstractSet[str] = lib_ctx.item_names_in_dir(rel_sub_dir_path=rel_sub_path)

            self.assertLessEqual(passed_entries, all_entries)

            filtered_entries = all_entries - passed_entries
            for entry in filtered_entries:
                self.assertFalse(item_filter(abs_sub_path / entry))
            for entry in passed_entries:
                self.assertTrue(item_filter(abs_sub_path / entry))

        self.traverse(lib_ctx, helper)

    def test_lib_ctx_yield_self_meta_pairs(self):
        root_dir = self.root_dir_pl
        lib_ctx = tl.gen_library_ctx(root_dir=root_dir, media_item_filter=item_filter)

        yaml_data = {
            'field_1': 'single_value',
            'field_2': ['list_of_values', 'another_one'],
            'field_3': None,
        }

        def helper(rel_sub_path: pl.Path, abs_sub_path: pl.Path):
            if abs_sub_path.is_dir():
                expected = ((rel_sub_path, yaml_data),)
                produced = tuple(lib_ctx.yield_self_meta_pairs(yaml_data=yaml_data,
                                                               rel_sub_dir_path=rel_sub_path))
                self.assertEqual(expected, produced)

        self.traverse(lib_ctx, helper)

    def test_lib_ctx_yield_item_meta_pairs_a(self):
        root_dir = self.root_dir_pl
        lib_ctx = tl.gen_library_ctx(root_dir=root_dir, media_item_filter=item_filter)

        def sequence_helper(rel_sub_path: pl.Path, abs_sub_path: pl.Path):
            if abs_sub_path.is_dir():
                passed_items = lib_ctx.item_names_in_dir(rel_sub_dir_path=rel_sub_path)
                sorted_passed_items = sorted(passed_items)
                num_passed_items = len(passed_items)

                extra_records = ({f'extra_item': f'extra_value'},)

                # Construct YAML data for exact, too many, and too few numbers of passed items.
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
                extra_data_log_records = frozenset(LogEntry(logger=tl.__name__, level=logging.WARNING, message=msg)
                                                   for msg in extra_data_log_messages)
                insuf_data_log_records = frozenset(LogEntry(logger=tl.__name__, level=logging.WARNING, message=msg)
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
                    ctx_mgr = empty_context
                    if expected_log_records:
                        ctx_mgr = logging_ctx_mgr

                    # Construct YAML data.
                    yaml_data = list(record_seq)

                    with ctx_mgr() as ctx:
                        expected = tuple((rel_sub_path / item_name, yaml_block)
                                         for item_name, yaml_block in zip(sorted_passed_items, yaml_data))
                        produced = tuple(lib_ctx.yield_item_meta_pairs(yaml_data=copy.deepcopy(yaml_data),
                                                                       rel_sub_dir_path=rel_sub_path))
                        self.assertEqual(expected, produced)

                    if ctx:
                        produced_log_records = frozenset(yield_log_records(ctx.records))
                        self.assertEqual(expected_log_records, produced_log_records)

        self.traverse(lib_ctx, sequence_helper)

    def test_lib_ctx_yield_item_meta_pairs_b(self):
        root_dir = self.root_dir_pl
        lib_ctx = tl.gen_library_ctx(root_dir=root_dir, media_item_filter=item_filter)

        # Warnings to check for:
        # 1) Invalid item names.
        # 2) Already-processed item names.
        # 3) Item names not found in directory.
        # 4) Unreferenced file names found in directory.

        LookupRecord = collections.namedtuple('LookupRecord', ('item_name', 'fuzzy_item_name', 'meta_block'))

        def mapping_helper(rel_sub_path: pl.Path, abs_sub_path: pl.Path):
            if abs_sub_path.is_dir():
                passed_items = lib_ctx.item_names_in_dir(rel_sub_dir_path=rel_sub_path)
                sorted_passed_items = sorted(passed_items)

                extra_records = tuple(LookupRecord(item_name=EXTRA_INELIGIBLE_FN,
                                                   fuzzy_item_name=EXTRA_INELIGIBLE_FN.split(FUZZY_SEP)[0],
                                                   meta_block={f'extra_item': f'extra_value'})
                                      for _ in abs_sub_path.glob(EXTRA_INELIGIBLE_FN))
                inval_records = tuple(LookupRecord(item_name=invalid_item_name,
                                                   fuzzy_item_name=invalid_item_name,
                                                   meta_block={f'inval_item': f'inval_value'})
                                      for invalid_item_name in INVALID_ITEM_NAMES)

                # Construct YAML data.
                exact_record_seq = tuple(LookupRecord(item_name=item_name,
                                                      fuzzy_item_name=item_name.split(FUZZY_SEP)[0],
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
                                                    for invalid_item_name in INVALID_ITEM_NAMES)

                # Log records expected.
                extra_data_log_records = frozenset(LogEntry(logger=tl.__name__, level=logging.WARNING, message=msg)
                                                   for msg in extra_data_log_messages)
                insuf_data_log_records = frozenset(LogEntry(logger=tl.__name__, level=logging.WARNING, message=msg)
                                                   for msg in insuf_data_log_messages)
                inval_data_log_records = frozenset(LogEntry(logger=tl.__name__, level=logging.WARNING, message=msg)
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
                    ctx_mgr = empty_context
                    if expected_log_records:
                        ctx_mgr = logging_ctx_mgr

                    # Construct YAML data.
                    yaml_data = {r.fuzzy_item_name: r.meta_block for r in record_seq}

                    with ctx_mgr() as ctx:
                        expected = {rel_sub_path / r.item_name: r.meta_block
                                    for r in record_seq if r.item_name in passed_items}
                        produced = {k: v for k, v in lib_ctx.yield_item_meta_pairs(yaml_data=yaml_data,
                                                                                   rel_sub_dir_path=rel_sub_path)}
                        # print('* Current Dir:', rel_sub_path)
                        # print('* Items in Dir:', tuple(abs_sub_path.iterdir()))
                        # print('* YAML Data:', yaml_data)
                        # print('* Expected Logs:', expected_log_records)
                        # print()
                        self.assertEqual(expected, produced)

                    if ctx:
                        produced_log_records = frozenset(yield_log_records(ctx.records))
                        self.assertEqual(expected_log_records, produced_log_records)

        self.traverse(lib_ctx, mapping_helper)

    def test_lib_ctx_yield_meta_source_specs(self):
        root_dir = self.root_dir_pl
        lib_ctx = tl.gen_library_ctx(root_dir=root_dir, media_item_filter=item_filter)

        expected = (
            (lib_ctx.get_item_meta_file_name(), lib_ctx.yield_siblings_dir, lib_ctx.yield_item_meta_pairs),
            (lib_ctx.get_self_meta_file_name(), lib_ctx.yield_contains_dir, lib_ctx.yield_self_meta_pairs),
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
