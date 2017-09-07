import typing as typ
import pathlib as pl
import random
import string
import contextlib
import logging
import os.path
import re

import yaml

import taggu.types as tt

DirectoryHierarchyMapping = typ.Mapping[str, typ.Optional['DirectoryHierarchyMapping']]
TraverseVisitorFunc = typ.Callable[[pl.Path, pl.Path], None]

MetaKeyGen = typ.Callable[[pl.Path], str]
MetaValGen = typ.Callable[[pl.Path], typ.Union[str, typ.Sequence[str], typ.Mapping[str, str]]]


A_LABEL = 'ALBUM'
D_LABEL = 'DISC'
T_LABEL = 'TRACK'
S_LABEL = 'SUBTRACK'

META_FILE_EXT = '.yml'
SELF_META_FN = f'taggu_self{META_FILE_EXT}'
ITEM_META_FN = f'taggu_item{META_FILE_EXT}'

ITEM_FILE_EXT = '.flac'
ITEM_FN_SEP = '_'

CNST_META_KEY = 'cnst'

UNUSED_LABEL = 'UNUSED_LABEL'
LABEL_REGEX = re.compile(r'^([A-Z]+).*')

RANDOM_SALT_STR = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))


class LogEntry(typ.NamedTuple):
    logger: str
    level: int
    message: str


def gen_self_meta_key(rel_item_path: pl.Path) -> str:
    return f'self key "{rel_item_path}"'


def gen_item_meta_key(rel_item_path: pl.Path) -> str:
    return f'item key "{rel_item_path}"'


def gen_self_meta_str_val(rel_item_path: pl.Path) -> str:
    return f'self metadata for target "{rel_item_path}"'


def gen_item_meta_str_val(rel_item_path: pl.Path) -> str:
    return f'item metadata for target "{rel_item_path}"'


def gen_cnst_meta_str_val(rel_item_path: pl.Path) -> str:
    return f'cnst metadata for target "{rel_item_path}"'


@contextlib.contextmanager
def empty_context() -> typ.Generator[None, None, None]:
    """A context manager that does nothing, mainly useful for unit testing."""
    yield


def default_item_filter(abs_item_path: pl.Path) -> bool:
    ext = abs_item_path.suffix
    return (abs_item_path.is_file() and ext == ITEM_FILE_EXT) or abs_item_path.is_dir()


def gen_default_dir_hier_map() -> DirectoryHierarchyMapping:
    dir_hierarchy: DirectoryHierarchyMapping = {
        # Well-behaved album.
        f'{A_LABEL}01': {
            f'{D_LABEL}01': {
                f'{T_LABEL}01': None,
                f'{T_LABEL}02': None,
                f'{T_LABEL}03': None,
            },
            f'{D_LABEL}02': {
                f'{T_LABEL}01': None,
                f'{T_LABEL}02': None,
                f'{T_LABEL}03': None,
            },
        },

        # Album with a disc and tracks, and loose tracks not on a disc.
        f'{A_LABEL}02': {
            f'{D_LABEL}01': {
                f'{T_LABEL}01': None,
                f'{T_LABEL}02': None,
                f'{T_LABEL}03': None,
            },
            f'{T_LABEL}01': None,
            f'{T_LABEL}02': None,
            f'{T_LABEL}03': None,
        },

        # Album with discs and tracks, and subtracks on one disc.
        f'{A_LABEL}03': {
            f'{D_LABEL}01': {
                f'{T_LABEL}01': None,
                f'{T_LABEL}02': None,
                f'{T_LABEL}03': None,
            },
            f'{D_LABEL}02': {
                f'{T_LABEL}01': {
                    f'{S_LABEL}01': None,
                    f'{S_LABEL}02': None,
                },
                f'{T_LABEL}02': {
                    f'{S_LABEL}01': None,
                    f'{S_LABEL}02': None,
                },
                f'{T_LABEL}03': None,
                f'{T_LABEL}04': None,
            },
        },

        # Album that consists of one file.
        f'{A_LABEL}04': None,

        # A very messed-up album.
        f'{A_LABEL}05': {
            f'{D_LABEL}01': {
                f'{S_LABEL}01': None,
                f'{S_LABEL}02': None,
                f'{S_LABEL}03': None,
            },
            f'{D_LABEL}02': {
                f'{T_LABEL}01': {
                    f'{S_LABEL}01': None,
                    f'{S_LABEL}02': None,
                },
            },
            f'{T_LABEL}01': None,
            f'{T_LABEL}02': None,
            f'{T_LABEL}03': None,
        },
    }

    return dir_hierarchy


def write_dir_hierarchy(root_dir: pl.Path, dir_mapping: DirectoryHierarchyMapping,
                        item_file_suffix: str=None, apply_random_salt: bool=False) -> None:
    """Creates a folder and file hierarchy from a mapping file."""
    def helper(curr_dir_mapping: DirectoryHierarchyMapping,
               curr_rel_path: pl.Path=pl.Path()):
        for stub, child in curr_dir_mapping.items():
            if apply_random_salt:
                # Add an extra randomized-per-run string to the end of each entry name.
                # This helps with testing for fuzzy name lookups.
                stub = f'{stub}{ITEM_FN_SEP}{RANDOM_SALT_STR}'

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


def gen_simple_metadata_block(*, rel_item_path: pl.Path,
                              meta_key_gen: MetaKeyGen,
                              meta_val_gen: MetaValGen,
                              include_const_key: bool=False) -> typ.Mapping:
    data = {meta_key_gen(rel_item_path): meta_val_gen(rel_item_path)}
    if include_const_key:
        data[CNST_META_KEY] = gen_cnst_meta_str_val(rel_item_path)
    return data


def gen_complex_metadata_block(*, rel_item_path: pl.Path) -> typ.Mapping:
    data = {
        'key a': 'val a',
        'key b': ['val b', 'val c'],
        'key c': {
            'key d': 'val d',
            'key e': ['val e', 'val f'],
        },
        'key f': None,
        None: 'val g',
    }

    return data


def gen_simple_item_metadata(rel_item_path: pl.Path, include_const_key: bool=False) -> typ.Any:
    return gen_simple_metadata_block(rel_item_path=rel_item_path, meta_key_gen=gen_item_meta_key,
                                     meta_val_gen=gen_item_meta_str_val, include_const_key=include_const_key)


def gen_simple_self_metadata(rel_item_path: pl.Path, include_const_key: bool=False) -> typ.Any:
    return gen_simple_metadata_block(rel_item_path=rel_item_path, meta_key_gen=gen_self_meta_key,
                                     meta_val_gen=gen_self_meta_str_val, include_const_key=include_const_key)


def write_meta_files(root_dir: pl.Path, item_filter: tt.ItemFilter=None, include_const_key: bool=False) -> None:
    def helper(curr_rel_path: pl.Path=pl.Path()):
        curr_abs_path = root_dir / curr_rel_path
        if curr_abs_path.is_dir():
            # Create self meta file.
            with (curr_abs_path / SELF_META_FN).open(mode='w') as stream:
                data = gen_simple_self_metadata(curr_rel_path, include_const_key=include_const_key)
                yaml.dump(data, stream)

            # Create item meta file.
            data = {}
            for abs_entry in curr_abs_path.iterdir():
                item_name = abs_entry.name
                if abs_entry.is_dir():
                    helper(curr_rel_path=(curr_rel_path / item_name))

                if item_filter is None or item_filter(abs_entry):
                    data[item_name] = gen_simple_item_metadata(curr_rel_path / item_name,
                                                               include_const_key=include_const_key)

            with (curr_abs_path / ITEM_META_FN).open(mode='w') as stream:
                yaml.dump(data, stream)

    helper()


def traverse(root_dir: pl.Path, func: TraverseVisitorFunc, offset_sub_path: pl.Path=pl.Path(),
             action_filter: tt.ItemFilter=None, prune_filter: tt.ItemFilter=None) -> None:
    def helper(curr_rel_path: pl.Path=pl.Path()):
        curr_abs_path = root_dir / curr_rel_path

        if action_filter is None or action_filter(curr_abs_path):
            func(curr_rel_path, curr_abs_path)

        if curr_abs_path.is_dir() and (prune_filter is None or prune_filter(curr_abs_path)):
            for entry in curr_abs_path.iterdir():
                entry_name = entry.name
                helper(curr_rel_path / entry_name)

    helper(curr_rel_path=offset_sub_path)


def yield_fs_contents_recursively(root_dir: pl.Path, offset_sub_path: pl.Path=pl.Path(),
                                  pass_filter: tt.ItemFilter=None, prune_filter: tt.ItemFilter=None) -> tt.PathGen:
    def helper(curr_rel_path: pl.Path=pl.Path()):
        curr_abs_path = root_dir / curr_rel_path

        if pass_filter is None or pass_filter(curr_abs_path):
            yield curr_rel_path

        if curr_abs_path.is_dir() and (prune_filter is None or prune_filter(curr_abs_path)):
            for entry in curr_abs_path.iterdir():
                entry_name = entry.name
                yield from helper(curr_rel_path / entry_name)

    yield from helper(curr_rel_path=offset_sub_path)


def touch_extra_files(root_dir: pl.Path, fns: typ.Iterable[typ.Union[str, pl.Path]]) -> None:
    def is_dir(abs_path):
        return abs_path.is_dir()

    for fn in fns:
        def func(_, abs_path):
            (abs_path / fn).touch(exist_ok=True)
        traverse(root_dir=root_dir, func=func, action_filter=is_dir)


def yield_log_entries(ctx_manager_records: typ.Iterable[logging.LogRecord]) -> typ.Generator[LogEntry, None, None]:
    for lr in ctx_manager_records:
        yield LogEntry(logger=lr.name, level=lr.levelno, message=lr.getMessage())


def yield_invalid_fns() -> typ.Generator[str, None, None]:
    yield ''
    yield os.path.curdir
    yield os.path.pardir
    yield os.path.sep
    if os.path.altsep:
        yield os.path.altsep
    yield os.path.join('a', '')
    yield os.path.join('a', os.path.curdir)
    yield os.path.join('a', os.path.pardir)
    yield os.path.join('a', 'b')


def is_meta_file_path(abs_path: pl.Path) -> bool:
    return abs_path.name in {SELF_META_FN, ITEM_META_FN}


def default_label_extractor(abs_item_path: pl.Path) -> typ.Optional[str]:
    fn = abs_item_path.name
    m = LABEL_REGEX.match(fn)
    if m:
        return m.group(1)
