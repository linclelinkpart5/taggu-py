import logging
import pathlib as pl
import tempfile
import typing as typ
import unittest

import yaml

import taggu.contexts.discovery as td
import taggu.contexts.library as tl
import taggu.helpers as th

A_LABEL = 'ALBUM'
D_LABEL = 'DISC'
T_LABEL = 'TRACK'
S_LABEL = 'SUBTRACK'
META_SELF = 'taggu_self.yml'
META_ITEM = 'taggu_item.yml'
ITEM_FILE_EXT = '.flac'
MAIN_KEY = 'info'
SELF_META_STR_TEMPLATE = 'self metadata for target "{}"'
ITEM_META_STR_TEMPLATE = 'item metadata for target "{}"'

DirectoryHierarchy = typ.Mapping[str, typ.Optional['DirectoryHierarchy']]


def item_filter(abs_item_path: pl.Path) -> bool:
    return (abs_item_path.is_file() and abs_item_path.suffix == ITEM_FILE_EXT) or abs_item_path.is_dir()


class TestDiscovery(unittest.TestCase):
    def setUp(self):
        self.root_dir_obj = tempfile.TemporaryDirectory()

        self.root_dir_pl = pl.Path(self.root_dir_obj.name)

        self.library_context = tl.gen_library_ctx(root_dir=self.root_dir_pl,
                                                  media_item_filter=item_filter,
                                                  media_item_sort_key=None,
                                                  self_meta_file_name=META_SELF,
                                                  item_meta_file_name=META_ITEM)

        dir_hierarchy: DirectoryHierarchy = {
            # Well-behaved album.
            f'{A_LABEL}_01': {
                f'{D_LABEL}_01': {
                    f'{T_LABEL}_01': None,
                    f'{T_LABEL}_02': None,
                    f'{T_LABEL}_03': None,
                },
                f'{D_LABEL}_02': {
                    f'{T_LABEL}_01': None,
                    f'{T_LABEL}_02': None,
                    f'{T_LABEL}_03': None,
                },
            },

            # Album with a disc and tracks, and loose tracks not on a disc.
            f'{A_LABEL}_02': {
                f'{D_LABEL}_01': {
                    f'{T_LABEL}_01': None,
                    f'{T_LABEL}_02': None,
                    f'{T_LABEL}_03': None,
                },
                f'{T_LABEL}_01': None,
                f'{T_LABEL}_02': None,
                f'{T_LABEL}_03': None,
            },

            # Album with discs and tracks, and subtracks on one disc.
            f'{A_LABEL}_03': {
                f'{D_LABEL}_01': {
                    f'{T_LABEL}_01': None,
                    f'{T_LABEL}_02': None,
                    f'{T_LABEL}_03': None,
                },
                f'{D_LABEL}_02': {
                    f'{T_LABEL}_01': {
                        f'{S_LABEL}_01': None,
                        f'{S_LABEL}_02': None,
                    },
                    f'{T_LABEL}_02': {
                        f'{S_LABEL}_01': None,
                        f'{S_LABEL}_02': None,
                    },
                    f'{T_LABEL}_03': None,
                    f'{T_LABEL}_04': None,
                },
            },

            # Album that consists of one file.
            f'{A_LABEL}_04': None,

            # A very messed-up album.
            f'{A_LABEL}_05': {
                f'{D_LABEL}_01': {
                    f'{S_LABEL}_01': None,
                    f'{S_LABEL}_02': None,
                    f'{S_LABEL}_03': None,
                },
                f'{D_LABEL}_02': {
                    f'{T_LABEL}_01': {
                        f'{S_LABEL}_01': None,
                        f'{S_LABEL}_02': None,
                    },
                },
                f'{T_LABEL}_01': None,
                f'{T_LABEL}_02': None,
                f'{T_LABEL}_03': None,
            },
        }

        def make_dir_hierarchy(curr_dir_mapping: DirectoryHierarchy, curr_rel_path: pl.Path=pl.Path()):
            """Creates a folder and file hierarchy from a mapping file."""
            for stub, child in curr_dir_mapping.items():
                if child is None:
                    # Create this entry as a file.
                    # Current relative path is to be a directory.
                    curr_abs_path = self.root_dir_pl / curr_rel_path
                    curr_abs_path.mkdir(parents=True, exist_ok=True)

                    (curr_abs_path / stub).with_suffix(ITEM_FILE_EXT).touch(exist_ok=True)
                else:
                    # Repeat the process with each child element.
                    next_rel_path = curr_rel_path / stub
                    next_dir_mapping = child
                    make_dir_hierarchy(curr_dir_mapping=next_dir_mapping, curr_rel_path=next_rel_path)

        make_dir_hierarchy(curr_dir_mapping=dir_hierarchy)

        def make_meta_files(curr_rel_path: pl.Path=pl.Path()):
            curr_abs_path = self.root_dir_pl / curr_rel_path
            if curr_abs_path.is_dir():
                # Create self meta file.
                with (curr_abs_path / META_SELF).open(mode='w') as stream:
                    data = {MAIN_KEY: SELF_META_STR_TEMPLATE.format(curr_rel_path)}
                    yaml.dump(data, stream)

                # Create item meta file.
                data = {}
                for abs_entry in curr_abs_path.iterdir():
                    item_name = abs_entry.name
                    if abs_entry.is_dir():
                        make_meta_files(curr_rel_path=(curr_rel_path / item_name))

                    if item_filter(abs_entry):
                        data[item_name] = {MAIN_KEY: ITEM_META_STR_TEMPLATE.format(curr_rel_path / item_name)}

                with (curr_abs_path / META_ITEM).open(mode='w') as stream:
                    yaml.dump(data, stream)

        make_meta_files()

    def traverse(self, func: typ.Callable[[pl.Path, pl.Path], None],
                 rel_sub_path: pl.Path=pl.Path(), file_filter=item_filter):
        lib_ctx = self.library_context

        def helper(curr_rel_path: pl.Path):
            curr_rel_path, curr_abs_path = lib_ctx.co_norm(rel_sub_path=curr_rel_path)

            func(curr_rel_path, curr_abs_path)

            if curr_abs_path.is_dir():
                for entry in curr_abs_path.iterdir():
                    if item_filter is not None and not item_filter(entry):
                        continue
                    entry_name = entry.name
                    helper(curr_rel_path / entry_name)

        helper(rel_sub_path)

    def test_meta_files_from_item(self):
        lib_ctx = self.library_context
        dis_ctx = td.gen_discovery_ctx(library_context=lib_ctx)

        def helper(curr_rel_path: pl.Path, curr_abs_path: pl.Path):
            def yielder():
                if curr_abs_path.is_dir():
                    yield curr_rel_path / META_SELF
                if curr_rel_path != curr_rel_path.parent:
                    yield curr_rel_path.parent / META_ITEM

            expected = tuple(yielder())
            produced = tuple(dis_ctx.meta_files_from_item(rel_item_path=curr_rel_path))
            # print('Expected:', expected)
            # print('Produced:', produced)
            self.assertEqual(expected, produced)

        self.traverse(helper)

    def test_items_from_meta_file(self):
        lib_ctx = self.library_context
        dis_ctx = td.gen_discovery_ctx(library_context=lib_ctx)
        root_dir = lib_ctx.get_root_dir()

        # Collect all relative meta paths.
        meta_paths = set()
        for meta_fn in (META_SELF, META_ITEM):
            for meta_abs_path in root_dir.rglob(meta_fn):
                meta_rel_path = meta_abs_path.relative_to(root_dir)
                meta_paths.add((meta_rel_path, meta_abs_path))

        meta_paths = frozenset(meta_paths)

        # Test each relative meta path.
        for meta_rel_path, meta_abs_path in meta_paths:
            if meta_rel_path.name == META_ITEM:
                def yielder():
                    # Get all interesting items in the same directory as this item meta file.
                    parent_abs_path = meta_abs_path.parent
                    for entry in parent_abs_path.iterdir():
                        if item_filter(entry):
                            item_rel_path = entry.relative_to(lib_ctx.get_root_dir())
                            yield (item_rel_path, {MAIN_KEY: ITEM_META_STR_TEMPLATE.format(item_rel_path)})

            elif meta_rel_path.name == META_SELF:
                def yielder():
                    # Get the parent dir containing this self meta file.
                    yield meta_rel_path.parent, {MAIN_KEY: SELF_META_STR_TEMPLATE.format(meta_rel_path.parent)}
            else:
                # Not a meta file.
                continue

            # Sort the outputs.
            expected = sorted(yielder(), key=lambda x: x[0])
            produced = sorted(dis_ctx.items_from_meta_file(rel_meta_path=meta_rel_path), key=lambda x: x[0])
            # print('Expected:', expected)
            # print('Produced:', produced)
            self.assertEqual(expected, produced)

    def tearDown(self):
        # import ipdb; ipdb.set_trace()

        self.root_dir_obj.cleanup()

if __name__ == '__main__':
    logging.getLogger(td.__name__).setLevel(level=logging.WARNING)
    logging.getLogger(tl.__name__).setLevel(level=logging.WARNING)
    logging.getLogger(th.__name__).setLevel(level=logging.WARNING)
    unittest.main()
