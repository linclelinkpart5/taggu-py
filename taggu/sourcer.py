"""Manages reading Taggu metadata for all files within a given subdirectory of a root directory."""

import collections.abc
import typing as typ
import os.path
import glob
import pathlib as pl
import enum
import itertools as it

import yaml

import taggu.typehints as tth
import taggu.logging as tl


logger = tl.get_logger(__name__)


def norm_join(path_a: str, path_b: str) -> str:
    return os.path.normpath(os.path.join(path_a, path_b))


def gen_suffix_item_filter(target_ext: str) -> tth.TargetItemFilter:
    def item_filter(path: tth.AbsItemPath) -> bool:
        _, ext = os.path.splitext(path)
        return (os.path.isfile(path) and ext == target_ext) or os.path.isdir(path)

    return item_filter


def is_valid_item_file_name(item_file_name: tth.ItemFileName) -> bool:
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


def is_valid_rel_sub_path(rel_sub_path: str) -> bool:
    as_pl = pl.Path(rel_sub_path)

    if os.path.isabs(rel_sub_path):
        return False

    for part in as_pl.parts:
        if part == os.path.pardir:
            return False

    return True


def fuzzy_file_lookup(*, target_dir: tth.GenericPath, needle: tth.ItemFileName) -> tth.ItemFileName:
    path = os.path.join(target_dir, needle)
    results = glob.glob('{}*'.format(path))

    if len(results) != 1:
        msg = (f'Incorrect number of matches for fuzzy lookup of "{needle}" in directory "{target_dir}"; '
               f'expected: 1, found: {len(results)}')
        logger.error(msg)
        raise Exception(msg)

    return results[0]


def get_items_in_dir(*, target_dir: str, item_filter: tth.TargetItemFilter=None) -> typ.AbstractSet[str]:
    # TODO: Default filter should be configurable.
    if item_filter is None:
        item_filter = gen_suffix_item_filter('.flac')

    def helper():
        with os.scandir(target_dir) as it:
            for item in it:
                item_name = item.name
                item_path = os.path.join(target_dir, item_name)

                if item_filter(item_path):
                    logger.debug(f'Item "{item_name}" passed filter, marking as eligible')
                    yield item_name
                else:
                    logger.debug(f'Item "{item_name}" failed filter, skipping')

    return frozenset(helper())


def read_yaml_file(yaml_file_path: str) -> typ.Any:
    with open(yaml_file_path) as f:
        data = yaml.load(f, Loader=yaml.BaseLoader)

    return data


def co_normalize(*, root_dir: str, rel_sub_path: str) -> typ.Tuple[str, str, str]:
    # Expand user dir directives (~ and ~user) and collapse dotted (. and ..) entries in path.
    root_dir = os.path.abspath(os.path.expanduser(root_dir))

    # Re-calculate the desired relative sub path using the normalized root directory path.
    abs_sub_path = os.path.normpath(os.path.join(root_dir, rel_sub_path))
    rel_sub_path = os.path.relpath(abs_sub_path, start=root_dir)

    return abs_sub_path, root_dir, rel_sub_path


def item_meta_pairs(yaml_data: typ.Any, lib_root_dir: str, rel_sub_dir: str) -> tth.MetadataPairIter:
    abs_sub_dir, lib_root_dir, rel_sub_dir = co_normalize(root_dir=lib_root_dir, rel_sub_path=rel_sub_dir)

    # Find eligible item names in this directory.
    item_names = get_items_in_dir(target_dir=abs_sub_dir, item_filter=None)

    # File metadata can be either a dictionary or sequence.
    if isinstance(yaml_data, collections.abc.Sequence):
        # Performing sequential application of metadata to interesting items.
        # Check that there are an equal number of metadata entries and interesting items.
        if len(item_names) != len(yaml_data):
            logger.warning(f'Counts of items in directory and metadata blocks do not match; '
                           f'found {len(item_names)} item(s) '
                           f'and {len(yaml_data)} metadata block(s)'
                           )

        for item_name, meta_block in zip(sorted(item_names), yaml_data):
            rel_item_path = os.path.join(rel_sub_dir, item_name)
            yield rel_item_path, meta_block

    elif isinstance(yaml_data, collections.abc.Mapping):
        # Performing mapped application of metadata to interesting items.
        for item_name, meta_block in yaml_data.items():
            # Test if item name from metadata has a valid name.
            if not is_valid_item_file_name(item_name):
                logger.warning(f'Item name "{item_name}" is not valid, skipping')
                continue

            item_path = fuzzy_file_lookup(target_dir=abs_sub_dir, needle=item_name)
            item_name = os.path.basename(item_path)

            # Test if the item name is in the list of discovered item names.
            if item_name not in item_names:
                logger.warning(f'Item "{item_name}" not found in eligible item names for this directory, '
                               f'skipping')
                continue

            rel_item_path = os.path.relpath(item_path, start=lib_root_dir)
            yield rel_item_path, meta_block


def self_meta_pairs(yaml_data: typ.Any, lib_root_dir: str, rel_sub_dir: str) -> tth.MetadataPairIter:
    _, lib_root_dir, rel_sub_dir = co_normalize(root_dir=lib_root_dir, rel_sub_path=rel_sub_dir)

    # The target of the self metadata is the folder containing the self metadata file.
    if isinstance(yaml_data, collections.abc.Mapping):
        yield rel_sub_dir, yaml_data


def parent_dir(rel_sub_path: str) -> typ.Tuple[str, str]:
    rel_sub_path = os.path.normpath(rel_sub_path)
    return os.path.normpath(os.path.dirname(rel_sub_path)), rel_sub_path


def all_parent_dirs(rel_sub_path: str) -> typ.Generator[str, None, None]:
    rel_sub_dir, rel_sub_path = parent_dir(rel_sub_path)
    while rel_sub_dir != rel_sub_path:
        yield rel_sub_dir
        rel_sub_path = rel_sub_dir
        rel_sub_dir, _ = parent_dir(rel_sub_path)


def item_meta_file_names(*, root_dir: str, rel_item_path: str, meta_file_name: str) -> typ.Iterable[str]:
    abs_item_path, root_dir, rel_item_path = co_normalize(root_dir=root_dir, rel_sub_path=rel_item_path)

    # Try to get dir name of rel item path.
    rel_item_dir, _ = parent_dir(rel_item_path)

    # Check if the dirname operation returned the same result, after normalization.
    # If so, then the rel item path is at the root dir, so just return without yielding.
    if rel_item_dir != rel_item_path:
        rel_meta_path = os.path.normpath(os.path.join(rel_item_dir, meta_file_name))
        if os.path.exists(os.path.join(root_dir, rel_meta_path)):
            yield rel_meta_path


def self_meta_file_names(*, root_dir: str, rel_item_path: str, meta_file_name: str) -> typ.Iterable[str]:
    abs_item_path, root_dir, rel_item_path = co_normalize(root_dir=root_dir, rel_sub_path=rel_item_path)

    # Check if abs item path is a directory.
    if os.path.isdir(abs_item_path):
        rel_meta_path = os.path.normpath(os.path.join(rel_item_path, meta_file_name))
        if os.path.exists(os.path.join(root_dir, rel_meta_path)):
            yield rel_meta_path


class MetaSource(enum.Enum):
    ITEM = tth.MetaSourceSpec(file_name='taggu_item.yml', processor=item_meta_pairs, finder=item_meta_file_names)
    SELF = tth.MetaSourceSpec(file_name='taggu_self.yml', processor=self_meta_pairs, finder=self_meta_file_names)


def imm_meta_files_for_item(root_dir: str, rel_item_path: str) -> typ.Iterable[typ.Tuple[str, MetaSource]]:
    abs_item_path, root_dir, rel_item_path = co_normalize(root_dir=root_dir, rel_sub_path=rel_item_path)

    if not os.path.exists(abs_item_path):
        return

    for meta_source in MetaSource:
        meta_file_name = meta_source.value.file_name
        finder = meta_source.value.finder

        for i in finder(root_dir=root_dir, rel_item_path=rel_item_path, meta_file_name=meta_file_name):
            yield i, meta_source


def par_meta_files_for_item(root_dir: str, rel_item_path: str) -> typ.Iterable[typ.Tuple[str, MetaSource]]:
    abs_item_path, root_dir, rel_item_path = co_normalize(root_dir=root_dir, rel_sub_path=rel_item_path)

    if not os.path.exists(abs_item_path):
        return

    for rel_par_path in all_parent_dirs(rel_item_path):
        for meta_source in MetaSource:
            meta_file_name = meta_source.value.file_name
            finder = meta_source.value.finder

            for i in finder(root_dir=root_dir, rel_item_path=rel_par_path, meta_file_name=meta_file_name):
                yield i, meta_source


def all_meta_files_for_item(root_dir: str, rel_item_path: str) -> typ.Iterable[typ.Tuple[str, MetaSource]]:
    yield from it.chain(imm_meta_files_for_item(root_dir, rel_item_path)
                        , par_meta_files_for_item(root_dir, rel_item_path)
                        )


def parse_meta_file_in_dir(*, root_dir: str, rel_sub_dir: str, meta_source: MetaSource):
    abs_sub_dir, root_dir, rel_sub_dir = co_normalize(root_dir=root_dir, rel_sub_path=rel_sub_dir)

    meta_file_name = meta_source.value.file_name

    rel_meta_path = norm_join(rel_sub_dir, meta_file_name)
    abs_meta_path = norm_join(abs_sub_dir, rel_meta_path)

    if os.path.exists(abs_meta_path):
        yaml_data = read_yaml_file(abs_meta_path)

        processor: tth.Multiplexer = meta_source.value.processor

        yield from processor(yaml_data, root_dir, rel_sub_dir)


def metadata_for_path(*, root_dir: str, rel_item_path: str) -> typ.Iterable[typ.Tuple[str, tth.Metadata, MetaSource]]:
    for rel_dir, meta_source in imm_meta_files_for_item(root_dir=root_dir, rel_item_path=rel_item_path):
        rel_meta_file_path = os.path.join(rel_dir, meta_source.value.file_name)
        abs_meta_file_path = os.path.normpath(os.path.join(root_dir, rel_meta_file_path))

        if os.path.exists(abs_meta_file_path):
            yaml_data = read_yaml_file(abs_meta_file_path)

            processor: tth.Multiplexer = meta_source.value.processor

            for rel_item_p, metadata in processor(yaml_data, root_dir, rel_dir):
                yield rel_item_p, metadata, meta_source


MetadataCache = typ.MutableMapping[str, typ.MutableMapping[MetaSource, tth.Metadata]]


# This returns a closure that, for a given root dir, caches and fetches metadata.
def generate_cacher(*, root_dir: str):
    meta_cache: MetadataCache = collections.defaultdict(collections.defaultdict)

    class LookerUpper:
        @classmethod
        def cache_sub_path(cls, rel_item_path: str, force: bool=False):
            _, _, rel_item_path = co_normalize(root_dir=root_dir, rel_sub_path=rel_item_path)

            if force or rel_item_path not in meta_cache:
                # Clear any cache remnants, just in case.
                meta_cache.pop(rel_item_path, None)

                for rel_item_p, metadata, source in metadata_for_path(root_dir=root_dir, rel_item_path=rel_item_path):
                    meta_cache[rel_item_p][source] = metadata

        @classmethod
        def get_metadata(cls, rel_item_path: str, force: bool=False):
            cls.cache_sub_path(rel_item_path=rel_item_path, force=force)

            _, _, rel_item_path = co_normalize(root_dir=root_dir, rel_sub_path=rel_item_path)

            source_mapping = meta_cache[rel_item_path]


# def metadata_for_item(*, root_dir: str, rel_item_path: str, cache: tth.MetadataCache):
#     abs_item_path, root_dir, rel_item_path = co_normalize(root_dir=root_dir, rel_sub_path=rel_item_path)
#
#     # Check if this item is a file or directory.
#     if os.path.isfile(abs_item_path):
#         # Process item metadata file in same directory as this item, and above.
#         pass
#     elif os.path.isdir(abs_item_path):
#         # Process self metadata file contained in that directory, and above.
#         pass
#
#     # The relative path to the directory containing this item.
#     rel_item_dir = os.path.dirname(rel_item_path)
#     if rel_item_path != os.path.curdir:
#         # Get parent metadata.
#         metadata_for_item(root_dir=root_dir, rel_item_path=rel_item_dir, cache=cache)
#
#     # Metadata not cached, need to read from file.
#     target_sources = set(SOURCE_TYPE_MAP.keys())
#     if rel_item_path in cache:
#         target_sources -= cache[rel_item_path].keys()
#
#     for target_source in target_sources:
#         source = SOURCE_TYPE_MAP[target_source]
#         rel_meta_file_path = os.path.join(rel_item_dir, source.file_name)
#         abs_meta_file_path = os.path.join(root_dir, rel_meta_file_path)
#
#         if os.path.exists(abs_meta_file_path):
#             yaml_data = read_yaml_file(abs_meta_file_path)
#
#             pair_iter = source.processor(yaml_data, root_dir, rel_item_dir)
#             for rel_path, metadata in pair_iter:
#                 cache.setdefault(rel_path, {})[source.type] = metadata
