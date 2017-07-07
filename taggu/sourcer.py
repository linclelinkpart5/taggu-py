"""Manages reading Taggu metadata for all files within a given subdirectory of a root directory."""

import collections.abc
import typing as typ
import os.path
import glob

import yaml

import taggu.typehints as tth
import taggu.constants as tc
import taggu.metadata as tm
import taggu.logging as tl


logger = tl.get_logger(__name__)


def expect_file(*, path: tth.GenericPath):
    if not os.path.isfile(path):
        msg = f'Path "{path}" does not point to a file'
        logger.error(msg)
        raise Exception(msg)


def expect_dir(*, path: tth.GenericPath):
    if not os.path.isdir(path):
        msg = f'Path "{path}" does not point to a directory'
        logger.error(msg)
        raise Exception(msg)


def expect_exists(*, path: tth.GenericPath):
    if not os.path.exists(path):
        msg = f'Path "{path}" does not exist'
        logger.error(msg)
        raise Exception(msg)


def gen_suffix_item_filter(target_ext: str) -> tth.TargetItemFilter:
    def item_filter(path: tth.ItemFilePath) -> bool:
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


def read_self_metadata_file(self_fp: tth.SelfMetaFilePath) -> tth.SelfMetadata:
    with open(self_fp) as f:
        data = yaml.load(f, Loader=yaml.BaseLoader)

    return data


def read_file_metadata_file(file_fp: tth.FileMetaFilePath) -> tth.FileMetadata:
    with open(file_fp) as f:
        data = yaml.load(f, Loader=yaml.BaseLoader)

    return data


def metadata_per_item(*
                      , root_dir: tth.LibraryRootDirPath
                      , rel_target_dir: tth.LibrarySubDirPath
                      , item_filter: tth.TargetItemFilter=None
                      ):
    root_dir = os.path.normpath(os.path.expanduser(root_dir))

    target_dir = os.path.normpath(os.path.join(root_dir, rel_target_dir))

    rel_target_dir = os.path.relpath(target_dir, start=root_dir)

    item_names = get_items_in_dir(target_dir=target_dir, item_filter=item_filter)

    # Find Taggu files in this directory.
    target_taggu_self_path = os.path.join(target_dir, tc.Constants.TAGGU_SELF_FN)
    target_taggu_file_path = os.path.join(target_dir, tc.Constants.TAGGU_FILE_FN)

    item_meta = {}

    if os.path.isfile(target_taggu_self_path):
        logger.debug(f'Found self-level metadata file at "{target_taggu_self_path}", processing')

        # This is the containing dir's metadata.
        self_meta = read_self_metadata_file(target_taggu_self_path)

        if isinstance(self_meta, collections.abc.Mapping):
            # TODO: Should be a more intelligent update, not an overwrite of the value.
            item_meta[rel_target_dir] = self_meta
        else:
            raise Exception('Unknown schema for taggu_self')

    if os.path.isfile(target_taggu_file_path):
        logger.debug(f'Found file-level metadata file at "{target_taggu_file_path}", processing')

        # This is the listing of metadata for items in this folder.
        file_meta = read_file_metadata_file(target_taggu_file_path)

        # File metadata can be either a dictionary or sequence.
        if isinstance(file_meta, collections.abc.Sequence):
            # Performing sequential application of metadata to interesting items.
            # Check that there are an equal number of metadata entries and interesting items.
            if len(item_names) != len(file_meta):
                logger.warning(f'Counts of items in directory and metadata blocks do not match; '
                               f'found {len(item_names)} item(s) '
                               f'and {len(file_meta)} metadata block(s)'
                               )

            for item_name, meta_block in zip(sorted(item_names), file_meta):
                rel_item_path = os.path.join(rel_target_dir, item_name)
                item_meta[rel_item_path] = meta_block

        elif isinstance(file_meta, collections.abc.Mapping):
            # Performing mapped application of metadata to interesting items.
            for item_name, meta_block in file_meta.items():
                # Test if item name from metadata has a valid name.
                if not is_valid_item_file_name(item_name):
                    logger.warning(f'Item name "{item_name}" is not valid, skipping')
                    continue

                item_path = fuzzy_file_lookup(target_dir=target_dir, needle=item_name)
                item_name = os.path.basename(item_path)

                # Test if the item name is in the list of discovered item names.
                if item_name not in item_names:
                    logger.warning(f'Item "{item_name}" not found in eligible item names for this directory, '
                                   f'skipping')
                    continue

                rel_item_path = os.path.relpath(item_path, start=root_dir)
                item_meta[rel_item_path] = meta_block

        else:
            raise Exception('Unknown schema for taggu_file')

    for key, val in item_meta.items():
        print(key, val)
