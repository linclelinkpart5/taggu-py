import typing as typ
import os.path
import glob

import yaml

import taggu.logging as tl
import taggu.exceptions as tex
import taggu.types as tt

logger = tl.get_logger(__name__)


def is_well_behaved_file_name(item_file_name: str) -> bool:
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


def gen_suffix_item_filter(target_ext: str) -> tt.ItemFilter:
    def item_filter(abs_item_path: str) -> bool:
        _, ext = os.path.splitext(abs_item_path)
        return (os.path.isfile(abs_item_path) and ext == target_ext) or os.path.isdir(abs_item_path)

    return item_filter


def fuzzy_file_lookup(*, abs_dir_path: str, prefix_file_name: str) -> str:
    path = os.path.join(abs_dir_path, prefix_file_name)
    results = glob.glob('{}*'.format(path))

    if len(results) != 1:
        msg = (f'Incorrect number of matches for fuzzy lookup of "{prefix_file_name}" in directory "{abs_dir_path}"; '
               f'expected: 1, found: {len(results)}')
        logger.error(msg)
        raise tex.NonUniqueFuzzyFileLookup(msg)

    return results[0]


def read_yaml_file(abs_yaml_file_path: str) -> typ.Any:
    logger.debug(f'Opening YAML file "{abs_yaml_file_path}"')
    with open(abs_yaml_file_path) as f:
        data = yaml.load(f, Loader=yaml.BaseLoader)

    return data


def item_discovery(*, abs_dir_path: str, item_filter: tt.ItemFilter=None) -> typ.AbstractSet[str]:
    """Finds item names in a given directory. These items must pass a filter in order to be selected."""
    # TODO: Remove, just for testing.
    if item_filter is None:
        item_filter = gen_suffix_item_filter('.flac')

    def helper():
        with os.scandir(abs_dir_path) as it:
            for item in it:
                item_name = item.name
                item_path = os.path.normpath(os.path.join(abs_dir_path, item_name))

                if item_filter is not None:
                    if item_filter(item_path):
                        logger.debug(f'Item "{item_name}" passed filter, marking as eligible')
                        yield item_name
                    else:
                        logger.debug(f'Item "{item_name}" failed filter, skipping')
                else:
                    yield item_name

    return frozenset(helper())
