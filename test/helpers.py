import typing as typ
import pathlib as pl

import yaml

import taggu.types as tt
import taggu.contexts.library as tcl

DirectoryHierarchyMapping = typ.Mapping[str, typ.Optional['DirectoryHierarchyMapping']]
TraverseVisitorFunc = typ.Callable[[pl.Path, pl.Path], None]


A_LABEL = 'ALBUM'
D_LABEL = 'DISC'
T_LABEL = 'TRACK'
S_LABEL = 'SUBTRACK'

SELF_META_FN = 'taggu_self.yml'
ITEM_META_FN = 'taggu_item.yml'

ITEM_FILE_EXT = '.flac'

SELF_META_KEY = 'self'
ITEM_META_KEY = 'item'
SELF_META_STR_TEMPLATE = 'self metadata for target "{}"'
ITEM_META_STR_TEMPLATE = 'item metadata for target "{}"'


def gen_default_dir_hier_map() -> DirectoryHierarchyMapping:
    dir_hierarchy: DirectoryHierarchyMapping = {
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

    return dir_hierarchy


def write_dir_hierarchy(root_dir: pl.Path,
                        dir_mapping: DirectoryHierarchyMapping,
                        item_file_suffix: str=None) -> None:
    """Creates a folder and file hierarchy from a mapping file."""
    def helper(curr_dir_mapping: DirectoryHierarchyMapping,
               curr_rel_path: pl.Path=pl.Path()):
        for stub, child in curr_dir_mapping.items():
            if child is None:
                # Create this entry as a file.
                # Current relative path is to be a directory.
                curr_abs_path = root_dir / curr_rel_path
                curr_abs_path.mkdir(parents=True, exist_ok=True)

                file_path = (curr_abs_path / stub)
                if item_file_suffix is not None:
                    file_path = pl.Path(f'{file_path}{item_file_suffix}')
                file_path.touch(exist_ok=True)
            else:
                # This path will eventually be a directory.
                # Repeat the process with each child element.
                next_rel_path = curr_rel_path / stub
                next_dir_mapping = child
                helper(curr_dir_mapping=next_dir_mapping, curr_rel_path=next_rel_path)

    helper(curr_dir_mapping=dir_mapping)


def write_meta_files(root_dir: pl.Path, item_filter: tt.ItemFilter=None) -> None:
    def helper(curr_rel_path: pl.Path=pl.Path()):
        curr_abs_path = root_dir / curr_rel_path
        if curr_abs_path.is_dir():
            # Create self meta file.
            with (curr_abs_path / SELF_META_FN).open(mode='w') as stream:
                data = {SELF_META_KEY: SELF_META_STR_TEMPLATE.format(curr_rel_path)}
                yaml.dump(data, stream)

            # Create item meta file.
            data = {}
            for abs_entry in curr_abs_path.iterdir():
                item_name = abs_entry.name
                if abs_entry.is_dir():
                    helper(curr_rel_path=(curr_rel_path / item_name))

                if item_filter is None or item_filter(abs_entry):
                    data[item_name] = {ITEM_META_KEY: ITEM_META_STR_TEMPLATE.format(curr_rel_path / item_name)}

            with (curr_abs_path / ITEM_META_FN).open(mode='w') as stream:
                yaml.dump(data, stream)

    helper()


def traverse(root_dir: pl.Path, func: TraverseVisitorFunc,
             action_filter: tt.ItemFilter=None, prune_filter: tt.ItemFilter=None) -> None:
    def helper(curr_rel_path: pl.Path=pl.Path()):
        curr_abs_path = root_dir / curr_rel_path

        if action_filter is None or action_filter(curr_abs_path):
            func(curr_rel_path, curr_abs_path)

        if curr_abs_path.is_dir() and (prune_filter is None or prune_filter(curr_abs_path)):
            for entry in curr_abs_path.iterdir():
                entry_name = entry.name
                helper(curr_rel_path / entry_name)

    helper()
