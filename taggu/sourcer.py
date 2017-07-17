"""Manages reading Taggu metadata for all files within a given subdirectory of a root directory."""
import enum
import typing as typ
import os.path
import collections.abc
import glob

import yaml

import taggu.types as tt
import taggu.logging as tl


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
    def item_filter(path: str) -> bool:
        _, ext = os.path.splitext(path)
        return (os.path.isfile(path) and ext == target_ext) or os.path.isdir(path)

    return item_filter


def fuzzy_file_lookup(*, abs_dir: str, prefix_fn: str) -> str:
    path = os.path.join(abs_dir, prefix_fn)
    results = glob.glob('{}*'.format(path))

    if len(results) != 1:
        msg = (f'Incorrect number of matches for fuzzy lookup of "{prefix_fn}" in directory "{abs_dir}"; '
               f'expected: 1, found: {len(results)}')
        logger.error(msg)
        raise Exception(msg)

    return results[0]


def yield_contains_dir(abs_path: str) -> typ.Iterable[str]:
    if os.path.isdir(abs_path):
        yield abs_path


def yield_siblings_dir(abs_path: str) -> typ.Iterable[str]:
    par_dir = os.path.dirname(abs_path)
    if par_dir != abs_path:
        yield par_dir


def read_yaml_file(yaml_file_path: str) -> typ.Any:
    logger.debug(f'Opening YAML file "{yaml_file_path}"')
    with open(yaml_file_path) as f:
        data = yaml.load(f, Loader=yaml.BaseLoader)

    return data


def item_discovery(*, dir_path: str, item_filter: tt.ItemFilter=None) -> typ.AbstractSet[str]:
    """Finds item names in a given directory. These items must pass a filter in order to be selected."""
    # TODO: Remove, just for testing.
    if item_filter is None:
        item_filter = gen_suffix_item_filter('.flac')

    def helper():
        with os.scandir(dir_path) as it:
            for item in it:
                item_name = item.name
                item_path = os.path.join(dir_path, item_name)

                if item_filter is not None:
                    if item_filter(item_path):
                        logger.debug(f'Item "{item_name}" passed filter, marking as eligible')
                        yield item_name
                    else:
                        logger.debug(f'Item "{item_name}" failed filter, skipping')
                else:
                    yield item_name

    return frozenset(helper())


def meta_pairs_siblings(yaml_data: typ.Any
                        , sub_dir: str
                        , item_filter: typ.Optional[tt.ItemFilter]=None
                        ) -> typ.Iterable[typ.Tuple[str, tt.Metadata]]:
    # Find eligible item names in this directory.
    item_names = item_discovery(dir_path=sub_dir, item_filter=item_filter)

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
            item_path = os.path.join(sub_dir, item_name)
            yield item_path, meta_block

    elif isinstance(yaml_data, collections.abc.Mapping):
        # Performing mapped application of metadata to interesting items.
        for item_name, meta_block in yaml_data.items():
            # Test if item name from metadata has a valid name.
            if not is_valid_item_file_name(item_name):
                logger.warning(f'Item name "{item_name}" is not valid, skipping')
                continue

            item_path = fuzzy_file_lookup(abs_dir=sub_dir, prefix_fn=item_name)
            item_name = os.path.basename(item_path)

            # Test if the item name is in the list of discovered item names.
            if item_name not in item_names:
                logger.warning(f'Item "{item_name}" not found in eligible item names for this directory, '
                               f'skipping')
                continue

            yield item_path, meta_block


def meta_pairs_contains(yaml_data: typ.Any
                        , sub_dir: str
                        , _: typ.Optional[tt.ItemFilter]=None
                        ) -> typ.Iterable[typ.Tuple[str, tt.Metadata]]:
    # The target of the self metadata is the folder containing the self metadata file.
    if isinstance(yaml_data, collections.abc.Mapping):
        yield sub_dir, yaml_data


class MetaSource(enum.Enum):
    """Represents sources of metadata for items in a Taggu library.
    The order of the items here is important, it represents the order of overriding (last element overrides previous).
    """
    ITEM = tt.MetaSourceSpec(file_name='taggu_item.yml', dir_getter=yield_siblings_dir, multiplexer=meta_pairs_siblings)
    SELF = tt.MetaSourceSpec(file_name='taggu_self.yml', dir_getter=yield_contains_dir, multiplexer=meta_pairs_contains)

    def __str__(self):
        return '{}.{}'.format(type(self).__name__, self.name)

    __repr__ = __str__

    @classmethod
    def meta_files_from_item(cls, item_path: str) -> typ.Iterable[typ.Tuple[str, 'MetaSource']]:
        """Given an item path, yields all possible meta file paths that could provide immediate metadata for that item.
        This does not verify that any of the resulting meta file paths exist, so appropriate checking is needed.
        """
        for meta_source in cls:
            dir_getter: tt.DirGetter = meta_source.value.dir_getter
            file_name: str = meta_source.value.file_name

            # This loop will normally execute either zero or one time.
            for meta_dir in dir_getter(item_path):
                yield os.path.normpath(os.path.join(meta_dir, file_name)), meta_source

    @classmethod
    def items_from_meta_file(cls
                             , meta_path: str
                             , item_filter: tt.ItemFilter=None
                             ) -> typ.Iterable[typ.Tuple[str, tt.Metadata, 'MetaSource']]:
        """Given a meta file path, yields all item paths that this meta file provides metadata for, along with the
        metadata itself and the meta source type.
        """
        # Check that the provided path exists and is a file.
        if not os.path.isfile(meta_path):
            msg = f'Meta file "{meta_path}" does not exist, or is not a file'
            logger.error(msg)
            # raise Exception(msg)
            return

        # Get the meta file name and containing dir path.
        # Use containing dir path to find interesting items.
        containing_dir, meta_file_name = os.path.split(meta_path)

        # Find the meta source matching this meta file name.
        target_meta_source: MetaSource = None
        for meta_source in cls:
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
        yaml_data = read_yaml_file(meta_path)

        multiplexer: tt.Multiplexer = target_meta_source.value.multiplexer

        # Multiplexer needs to know the directory it is based in.
        for path, metadata in multiplexer(yaml_data, containing_dir, item_filter):
            yield path, metadata, target_meta_source

    # @classmethod
    # def metadata_for_item(cls
    #                       , item_path: str
    #                       , meta_cache: MetadataCache
    #                       , force: bool=False
    #                       , item_filter: tt.ItemFilter=None
    #                       ) -> typ.Iterable[typ.Tuple[str, 'MetaSource', tt.Metadata]]:
    #     # Normalize item path.
    #     item_path = os.path.normpath(item_path)
    #
    #     if force:
    #         logger.info(f'Forced fetch of item "{item_path}", defeating cache')
    #
    #         # Remove any possible remnants of cache.
    #         meta_cache.pop(item_path, None)
    #
    #     if item_path in meta_cache:
    #         logger.debug(f'Found item "{item_path}" in cache, using cached results')
    #
    #     else:
    #         logger.debug(f'Item "{item_path}" not found in cache, processing meta files')
    #         for meta_path, meta_source in cls.meta_files_from_item(item_path):
    #             if os.path.isfile(meta_path):
    #                 logger.info(f'Found meta file "{meta_path}" of type {meta_source.name} '
    #                             f'for item "{item_path}", processing')
    #                 for ip, md, ms in cls.items_from_meta_file(meta_path=meta_path, item_filter=item_filter):
    #                     meta_cache.setdefault(ip, {})[ms] = md
    #             else:
    #                 logger.debug(f'Meta file "{meta_path}" of type {meta_source.name} '
    #                              f'does not exist for item "{item_path}", skipping')
    #
    #     if item_path in meta_cache:
    #         for ms, md in meta_cache[item_path].items():
    #             yield item_path, ms, md


def generate_sourcer(*, root_dir: str, item_filter: tt.ItemFilter=None):
    pass
