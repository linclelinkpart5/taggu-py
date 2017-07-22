import typing as typ
import os
import os.path
import pathlib as pl

import yaml

import taggu.logging as tl
import taggu.exceptions as tex

logger = tl.get_logger(__name__)


def is_valid_item_name(item_file_name: str) -> bool:
    # Use use os.path here since the initial name will be a string.
    # Trying to use pathlib here would cause unexpected key folding (e.g. item_name/ -> item_name).
    head, tail = os.path.split(item_file_name)

    # If tail is empty, then either the path was empty, or it ended in a dir separator.
    # In either case, that would make the name invalid.
    if not tail:
        return False

    # If head is not empty, then either the path contained more than one path segment, or was absolute.
    # In either case, that would make the name invalid.
    if head:
        return False

    # If tail is a curdir or pardir item, that is also invalid.
    if tail == os.path.pardir or tail == os.path.curdir:
        return False

    return True


def gen_suffix_item_filter(target_ext: str) -> typ.Callable[[pl.Path], bool]:
    def item_filter(abs_item_path: pl.Path) -> bool:
        ext = abs_item_path.suffix
        return (abs_item_path.is_file() and ext == target_ext) or abs_item_path.is_dir()

    return item_filter


def fuzzy_file_lookup(*, abs_dir_path: pl.Path, prefix_file_name: str) -> pl.Path:
    pattern = f'{prefix_file_name}*'
    results = tuple(abs_dir_path.glob(pattern))

    if len(results) != 1:
        msg = (f'Incorrect number of matches for fuzzy lookup of "{prefix_file_name}" in directory "{abs_dir_path}"; '
               f'expected: 1, found: {len(results)}')
        logger.error(msg)
        raise tex.NonUniqueFuzzyFileLookup(msg)

    return results[0]


def read_yaml_file(abs_yaml_file_path: pl.Path) -> typ.Any:
    logger.debug(f'Opening YAML file "{abs_yaml_file_path}"')
    with abs_yaml_file_path.open() as f:
        data = yaml.load(f, Loader=yaml.BaseLoader)

    return data


def item_discovery(*
                   , abs_dir_path: pl.Path
                   , item_filter: typ.Callable[[pl.Path], bool]=None
                   ) -> typ.AbstractSet[pl.Path]:
    """Finds item names in a given directory. These items must pass a filter in order to be selected."""
    logger.info(f'Looking for valid items in directory "{abs_dir_path}"')

    def helper():
        for item in abs_dir_path.iterdir():
            item_name = item.name

            if item_filter is not None:
                if item_filter(item):
                    logger.debug(f'Item "{item_name}" passed filter, marking as eligible')
                    yield item_name
                else:
                    logger.debug(f'Item "{item_name}" failed filter, skipping')
            else:
                logger.debug(f'Marking item "{item_name}" as eligible')
                yield item_name

    return frozenset(helper())
