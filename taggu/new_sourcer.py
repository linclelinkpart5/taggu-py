import enum
import typing as typ
import os.path
import collections.abc
import glob

import yaml

import taggu.new_types as tt


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


def fuzzy_file_lookup(*, target_dir: str, needle: str) -> str:
    path = os.path.join(target_dir, needle)
    results = glob.glob('{}*'.format(path))

    if len(results) != 1:
        msg = (f'Incorrect number of matches for fuzzy lookup of "{needle}" in directory "{target_dir}"; '
               f'expected: 1, found: {len(results)}')
        # logger.error(msg)
        raise Exception(msg)

    return results[0]


def yield_contains_dir(path: str) -> typ.Iterable[str]:
    if os.path.isdir(path):
        yield path


def yield_siblings_dir(path: str) -> typ.Iterable[str]:
    par_dir = os.path.dirname(path)
    if par_dir != path:
        yield par_dir


def read_yaml_file(yaml_file_path: str) -> typ.Any:
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
                        yield item_name
                    else:
                        pass
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
        # if len(item_names) != len(yaml_data):
        #     logger.warning(f'Counts of items in directory and metadata blocks do not match; '
        #                    f'found {len(item_names)} item(s) '
        #                    f'and {len(yaml_data)} metadata block(s)'
        #                    )

        for item_name, meta_block in zip(sorted(item_names), yaml_data):
            item_path = os.path.join(sub_dir, item_name)
            yield item_path, meta_block

    elif isinstance(yaml_data, collections.abc.Mapping):
        # Performing mapped application of metadata to interesting items.
        for item_name, meta_block in yaml_data.items():
            # Test if item name from metadata has a valid name.
            if not is_valid_item_file_name(item_name):
                # logger.warning(f'Item name "{item_name}" is not valid, skipping')
                continue

            item_path = fuzzy_file_lookup(target_dir=sub_dir, needle=item_name)
            item_name = os.path.basename(item_path)

            # Test if the item name is in the list of discovered item names.
            if item_name not in item_names:
                # logger.warning(f'Item "{item_name}" not found in eligible item names for this directory, '
                #                f'skipping')
                continue

            # rel_item_path = os.path.relpath(item_path, start=lib_root_dir)
            # yield rel_item_path, meta_block
            yield item_path, meta_block


def meta_pairs_contains(yaml_data: typ.Any
                        , sub_dir: str
                        , _: typ.Optional[tt.ItemFilter]=None
                        ) -> typ.Iterable[typ.Tuple[str, tt.Metadata]]:
    # The target of the self metadata is the folder containing the self metadata file.
    if isinstance(yaml_data, collections.abc.Mapping):
        yield sub_dir, yaml_data


class MetaSource(enum.Enum):
    ITEM = tt.MetaSourceSpec(file_name='taggu_item.yml', dir_getter=yield_siblings_dir, multiplexer=meta_pairs_siblings)
    SELF = tt.MetaSourceSpec(file_name='taggu_self.yml', dir_getter=yield_contains_dir, multiplexer=meta_pairs_contains)

    @classmethod
    def meta_files_from_item(cls, item_path: str) -> typ.Iterable[typ.Tuple[str, 'MetaSource']]:
        """Given an item path, yields all possible meta file paths that could provide immediate metadata for that item.
        This does not check if the resulting meta file paths exist, so appropriate checking is needed.
        """
        for meta_source in cls:
            dir_getter: tt.DirGetter = meta_source.value.dir_getter
            file_name: str = meta_source.value.file_name

            # This loop will normally execute either zero or one time.
            for meta_dir in dir_getter(item_path):
                yield os.path.normpath(os.path.join(meta_dir, file_name)), meta_source

    @classmethod
    def items_from_meta_file(cls, meta_path: str, item_filter: tt.ItemFilter=None):
        """Given a meta file path, yields all item paths that this meta file provides metadata for, along with the
        metadata itself.
        """
        # Check that the provided path exists and is a file.
        if not os.path.isfile(meta_path):
            msg = f'Meta file "{meta_path}" does not exist, or is not a file'
            raise Exception(msg)

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
            raise Exception(msg)

        # Open the meta file and read as YAML.
        yaml_data = read_yaml_file(meta_path)

        multiplexer: tt.Multiplexer = target_meta_source.value.multiplexer

        # Multiplexer needs to know the directory it is based in.
        yield from multiplexer(yaml_data, containing_dir, item_filter)
