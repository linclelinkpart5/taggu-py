"""Manages reading Taggu metadata for all files within a given subdirectory of a root directory."""

import collections.abc
import typing as typ
import os.path
import glob

import yaml

import taggu.typehints as tth
import taggu.constants as tc
import taggu.logging as tl


logger = tl.get_logger(__name__)


def gen_suffix_item_filter(target_ext: str) -> tth.TargetItemFilter:
    def item_filter(path: tth.AbsItemFilePath) -> bool:
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


def fuzzy_file_lookup(*, target_dir: tth.GenericPath, needle: tth.ItemFileName) -> tth.ItemFileName:
    path = os.path.join(target_dir, needle)
    results = glob.glob('{}*'.format(path))

    if len(results) != 1:
        msg = (f'Incorrect number of matches for fuzzy lookup of "{needle}" in directory "{target_dir}"; '
               f'expected: 1, found: {len(results)}')
        logger.error(msg)
        raise Exception(msg)

    return results[0]


def get_items_in_dir(*, target_dir: tth.GenericPath
                     , item_filter: tth.TargetItemFilter=None) -> typ.AbstractSet[tth.ItemFileName]:
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


def co_normalize(*, root_dir: str, rel_sub_path: str) -> typ.Tuple[str, str]:
    # Expand user dir directives (~ and ~user) and collapse dotted (. and ..) entries in path.
    root_dir = os.path.normpath(os.path.expanduser(root_dir))

    # Re-calculate the desired relative sub path using the normalized root directory path.
    abs_sub_path = os.path.normpath(os.path.join(root_dir, rel_sub_path))
    rel_sub_path = os.path.relpath(abs_sub_path, start=root_dir)

    return root_dir, rel_sub_path


def item_meta_pairs(yaml_data: typ.Any, lib_root_dir: str, rel_sub_dir: str) -> tth.MetadataPairIter:
    lib_root_dir, rel_sub_dir = co_normalize(root_dir=lib_root_dir, rel_sub_path=rel_sub_dir)

    # Generate the absolute directory name.
    abs_sub_dir = os.path.join(lib_root_dir, rel_sub_dir)

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
    lib_root_dir, rel_sub_dir = co_normalize(root_dir=lib_root_dir, rel_sub_path=rel_sub_dir)

    # The target of the self metadata is the folder containing the self metadata file.
    if isinstance(yaml_data, collections.abc.Mapping):
        yield rel_sub_dir, yaml_data


SOURCES = frozenset((
    tth.SourceSpec(type=tth.SourceType.ITEM, file_name='taggu_item.yml', processor=item_meta_pairs),
    tth.SourceSpec(type=tth.SourceType.SELF, file_name='taggu_self.yml', processor=self_meta_pairs),
))

SOURCE_TYPE_MAP = {
    source.type: source for source in SOURCES
}


# def path_parts(path):
#     d = path
#     while d:
#         par, segment = os.path.split(d)
#         if d == par:
#             break
#         d = par
#         yield segment


def metadata_for_item(*
                      , root_dir: str
                      , rel_item_path: str
                      , cache: tth.MetadataCache
                      ):
    root_dir, rel_item_path = co_normalize(root_dir=root_dir, rel_sub_path=rel_item_path)

    # The relative path to the directory containing this item.
    rel_item_dir = os.path.dirname(rel_item_path)
    if rel_item_path != os.path.curdir:
        # Get parent metadata.
        metadata_for_item(root_dir=root_dir, rel_item_path=rel_item_dir, cache=cache)

    # Metadata not cached, need to read from file.
    target_sources = set(SOURCE_TYPE_MAP.keys())
    if rel_item_path in cache:
        target_sources -= cache[rel_item_path].keys()

    for target_source in target_sources:
        source = SOURCE_TYPE_MAP[target_source]
        rel_meta_file_path = os.path.join(rel_item_dir, source.file_name)
        abs_meta_file_path = os.path.join(root_dir, rel_meta_file_path)

        if os.path.exists(abs_meta_file_path):
            yaml_data = read_yaml_file(abs_meta_file_path)

            pair_iter = source.processor(yaml_data, root_dir, rel_item_dir)
            for rel_path, metadata in pair_iter:
                cache.setdefault(rel_path, {})[source.type] = metadata


# def metadata_per_item(*
#                       , root_dir: tth.LibraryRootDirPath
#                       , rel_target_dir: tth.LibrarySubDirPath
#                       , item_filter: tth.TargetItemFilter=None
#                       ):
#     root_dir = os.path.normpath(os.path.expanduser(root_dir))
#
#     target_dir = os.path.normpath(os.path.join(root_dir, rel_target_dir))
#
#     rel_target_dir = os.path.relpath(target_dir, start=root_dir)
#
#     item_names = get_items_in_dir(target_dir=target_dir, item_filter=item_filter)
#
#     # Find Taggu files in this directory.
#     target_taggu_self_path = os.path.join(target_dir, tc.Constants.TAGGU_SELF_FN)
#     target_taggu_item_path = os.path.join(target_dir, tc.Constants.TAGGU_ITEM_FN)
#
#     item_meta = {}
#
#     if os.path.isfile(target_taggu_self_path):
#         logger.debug(f'Found self-level metadata file at "{target_taggu_self_path}", processing')
#
#         # This is the containing dir's metadata.
#         self_meta = read_self_metadata_file(target_taggu_self_path)
#
#         if isinstance(self_meta, collections.abc.Mapping):
#             # TODO: Should be a more intelligent update, not an overwrite of the value.
#             item_meta[rel_target_dir] = self_meta
#         else:
#             raise Exception('Unknown schema for taggu_self')
#
#     if os.path.isfile(target_taggu_item_path):
#         logger.debug(f'Found file-level metadata file at "{target_taggu_item_path}", processing')
#
#         # This is the listing of metadata for items in this folder.
#         file_meta = read_item_metadata_file(target_taggu_item_path)
#
#         # File metadata can be either a dictionary or sequence.
#         if isinstance(file_meta, collections.abc.Sequence):
#             # Performing sequential application of metadata to interesting items.
#             # Check that there are an equal number of metadata entries and interesting items.
#             if len(item_names) != len(file_meta):
#                 logger.warning(f'Counts of items in directory and metadata blocks do not match; '
#                                f'found {len(item_names)} item(s) '
#                                f'and {len(file_meta)} metadata block(s)'
#                                )
#
#             for item_name, meta_block in zip(sorted(item_names), file_meta):
#                 rel_item_path = os.path.join(rel_target_dir, item_name)
#                 item_meta[rel_item_path] = meta_block
#
#         elif isinstance(file_meta, collections.abc.Mapping):
#             # Performing mapped application of metadata to interesting items.
#             for item_name, meta_block in file_meta.items():
#                 # Test if item name from metadata has a valid name.
#                 if not is_valid_item_file_name(item_name):
#                     logger.warning(f'Item name "{item_name}" is not valid, skipping')
#                     continue
#
#                 item_path = fuzzy_file_lookup(target_dir=target_dir, needle=item_name)
#                 item_name = os.path.basename(item_path)
#
#                 # Test if the item name is in the list of discovered item names.
#                 if item_name not in item_names:
#                     logger.warning(f'Item "{item_name}" not found in eligible item names for this directory, '
#                                    f'skipping')
#                     continue
#
#                 rel_item_path = os.path.relpath(item_path, start=root_dir)
#                 item_meta[rel_item_path] = meta_block
#
#         else:
#             raise Exception('Unknown schema for taggu_item')
#
#     for key, val in item_meta.items():
#         print(key, val)
