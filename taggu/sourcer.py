"""Manages reading Taggu metadata for all files within a given subdirectory of a root directory."""
import enum
import typing as typ
import os.path
import collections.abc
import glob

import yaml

import taggu.types as tt
import taggu.logging as tl
import taggu.exceptions as tex
import taggu.helpers as th


logger = tl.get_logger(__name__)


def is_valid_item_file_name(item_file_name: str) -> bool:
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


def generate_sourcer(*, root_dir: str, item_filter: tt.ItemFilter=None):
    root_dir, co_norm = th.gen_normed_root_dir_and_co_norm(root_dir=root_dir)

    def yield_meta_files(*, rel_item_path: str) -> typ.Generator[str, None, None]:
        # Yield ITEM meta file first, then SELF.
        rel_item_path, abs_item_path = co_norm(rel_sub_path=rel_item_path)

        # Look for an ITEM meta file.
        # Try to go up one directory.
        rel_par_dir = os.path.normpath(os.path.dirname(rel_item_path))
        abs_par_dir = os.path.normpath(os.path.dirname(abs_item_path))
        if rel_par_dir != rel_item_path:
            # If we were able to successfully go up one directory, check if there is an ITEM meta file here.
            rel_meta_path = os.path.normpath(os.path.join(rel_par_dir, 'taggu_item.yml'))
            abs_meta_path = os.path.normpath(os.path.join(abs_par_dir, 'taggu_item.yml'))
            if os.path.isfile(abs_meta_path):
                yield rel_meta_path

        # Look for a SELF meta file.
        # Check if the item path is a directory.
        if os.path.isdir(abs_item_path):
            rel_meta_path = os.path.normpath(os.path.join(rel_item_path, 'taggu_self.yml'))
            abs_meta_path = os.path.normpath(os.path.join(abs_item_path, 'taggu_self.yml'))
            if os.path.isfile(abs_meta_path):
                yield rel_meta_path

    def yield_contains_dir(rel_sub_path: str) -> typ.Iterable[str]:
        rel_sub_path, abs_sub_path = co_norm(rel_sub_path=rel_sub_path)
        if os.path.isdir(abs_sub_path):
            yield rel_sub_path

    def yield_siblings_dir(rel_sub_path: str) -> typ.Iterable[str]:
        rel_sub_path = os.path.normpath(rel_sub_path)
        par_dir = os.path.normpath(os.path.dirname(rel_sub_path))
        if par_dir != rel_sub_path:
            yield par_dir

    def meta_pairs_siblings(yaml_data: typ.Any
                            , rel_sub_dir_path: str
                            ) -> typ.Iterable[typ.Tuple[str, tt.Metadata]]:
        rel_sub_dir_path, abs_sub_dir_path = co_norm(rel_sub_path=rel_sub_dir_path)

        # Find eligible item names in this directory.
        item_names = item_discovery(abs_dir_path=abs_sub_dir_path, item_filter=item_filter)

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
                rel_item_path = os.path.normpath(os.path.join(rel_sub_dir_path, item_name))
                yield rel_item_path, meta_block

        elif isinstance(yaml_data, collections.abc.Mapping):
            # Performing mapped application of metadata to interesting items.
            for item_name, meta_block in yaml_data.items():
                # Test if item name from metadata has a valid name.
                if not is_valid_item_file_name(item_name):
                    logger.warning(f'Item name "{item_name}" is not valid, skipping')
                    continue

                item_path = fuzzy_file_lookup(abs_dir_path=abs_sub_dir_path, prefix_file_name=item_name)
                item_name = os.path.basename(item_path)

                # Test if the item name is in the list of discovered item names.
                if item_name not in item_names:
                    logger.warning(f'Item "{item_name}" not found in eligible item names for this directory, '
                                   f'skipping')
                    continue

                rel_item_path = os.path.relpath(item_path, start=root_dir)
                yield rel_item_path, meta_block

    def meta_pairs_contains(yaml_data: typ.Any
                            , rel_sub_dir_path: str
                            ) -> typ.Iterable[typ.Tuple[str, tt.Metadata]]:
        # The target of the self metadata is the folder containing the self metadata file.
        if isinstance(yaml_data, collections.abc.Mapping):
            yield rel_sub_dir_path, yaml_data

    class MetaSource(enum.Enum):
        """Represents sources of metadata for items in a Taggu library.
        The order of the items here is important, it represents the order of overriding (last element overrides previous).
        """
        ITEM = tt.MetaSourceSpec(file_name='taggu_item.yml', dir_getter=yield_siblings_dir, multiplexer=meta_pairs_siblings)
        SELF = tt.MetaSourceSpec(file_name='taggu_self.yml', dir_getter=yield_contains_dir, multiplexer=meta_pairs_contains)

        def __str__(self):
            return '{}.{}'.format(type(self).__name__, self.name)

        __repr__ = __str__

    class Sourcer:
        @classmethod
        def meta_files_from_item(cls, rel_item_path: str) -> typ.Iterable[typ.Tuple[str, MetaSource]]:
            """Given an item path, yields all possible meta file paths that could provide immediate metadata for that item.
            This does not verify that any of the resulting meta file paths exist, so appropriate checking is needed.
            """
            for meta_source in MetaSource:
                dir_getter: tt.DirGetter = meta_source.value.dir_getter
                file_name: str = meta_source.value.file_name

                # This loop will normally execute either zero or one time.
                for meta_dir in dir_getter(rel_item_path):
                    yield os.path.normpath(os.path.join(meta_dir, file_name)), meta_source

        @classmethod
        def items_from_meta_file(cls, rel_meta_path: str) -> typ.Iterable[typ.Tuple[str, tt.Metadata, MetaSource]]:
            """Given a meta file path, yields all item paths that this meta file provides metadata for, along with the
            metadata itself and the meta source type.
            """
            # Check that the provided path exists and is a file.
            if not os.path.isfile(rel_meta_path):
                msg = f'Meta file "{rel_meta_path}" does not exist, or is not a file'
                logger.error(msg)
                # raise Exception(msg)
                return

            # Get the meta file name and containing dir path.
            # Use containing dir path to find interesting items.
            containing_dir, meta_file_name = os.path.split(rel_meta_path)

            # Find the meta source matching this meta file name.
            target_meta_source: MetaSource = None
            for meta_source in MetaSource:
                if meta_file_name == meta_source.value.file_name:
                    target_meta_source = meta_source
                    break

            # If the target meta source is not set, then the file name did not match that of any of the meta sources.
            if target_meta_source is None:
                msg = f'Unknown meta file name "{meta_file_name}"'
                logger.error(msg)
                # raise Exception(msg)
                return

            # Open the meta file and read as YAML.
            yaml_data = read_yaml_file(rel_meta_path)

            multiplexer: tt.Multiplexer = target_meta_source.value.multiplexer

            # Multiplexer needs to know the directory it is based in.
            for path, metadata in multiplexer(yaml_data, containing_dir):
                yield path, metadata, target_meta_source

    return Sourcer
