import typing as typ
import os.path
import collections.abc
import enum

import taggu.types as tt
import taggu.logging as tl
import taggu.exceptions as tex
import taggu.helpers as th


logger = tl.get_logger(__name__)

MetadataCache = typ.MutableMapping[str, tt.Metadata]


def generate_discoverer(*
                        , root_dir: str
                        , item_filter: tt.ItemFilter=None
                        , self_meta_file_name: str='taggu_self.yml'
                        , item_meta_file_name: str='taggu_item.yml'
                        ):
    # Expand user dir directives (~ and ~user), collapse dotted (. and ..) entries in path, and absolute-ize.
    root_dir = os.path.abspath(os.path.expanduser(root_dir))

    meta_cache: MetadataCache = {}
    visited_real_meta_paths: typ.MutableSet = set()

    def co_norm(rel_sub_path: str) -> typ.Tuple[str, str]:
        abs_sub_path = os.path.normpath(os.path.join(root_dir, rel_sub_path))
        rel_sub_path = os.path.relpath(abs_sub_path, start=root_dir)

        if rel_sub_path.startswith(os.path.pardir):
            msg = f'Relative sub path is not anchored at root directory'
            logger.error(msg)
            raise tex.InvalidSubpath(msg)

        return rel_sub_path, abs_sub_path

    def yield_contains_dir(rel_sub_path: str) -> typ.Iterable[str]:
        rel_sub_path, abs_sub_path = co_norm(rel_sub_path=rel_sub_path)
        if os.path.isdir(abs_sub_path):
            yield rel_sub_path

    def yield_siblings_dir(rel_sub_path: str) -> typ.Iterable[str]:
        rel_sub_path = os.path.normpath(rel_sub_path)
        par_dir = os.path.normpath(os.path.dirname(rel_sub_path))
        if par_dir != rel_sub_path:
            yield par_dir

    def yield_item_meta_pairs(yaml_data: typ.Any
                              , rel_sub_dir_path: str
                              ) -> typ.Iterable[typ.Tuple[str, tt.Metadata]]:
        rel_sub_dir_path, abs_sub_dir_path = co_norm(rel_sub_path=rel_sub_dir_path)

        # Find eligible item names in this directory.
        item_names = th.item_discovery(abs_dir_path=abs_sub_dir_path, item_filter=item_filter)

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
                if not th.is_well_behaved_file_name(item_name):
                    logger.warning(f'Item name "{item_name}" is not valid, skipping')
                    continue

                item_path = th.fuzzy_file_lookup(abs_dir_path=abs_sub_dir_path, prefix_file_name=item_name)
                item_name = os.path.basename(item_path)

                # Test if the item name is in the list of discovered item names.
                if item_name not in item_names:
                    logger.warning(f'Item "{item_name}" not found in eligible item names for this directory, '
                                   f'skipping')
                    continue

                rel_item_path = os.path.relpath(item_path, start=root_dir)
                yield rel_item_path, meta_block

    def yield_self_meta_pairs(yaml_data: typ.Any
                              , rel_sub_dir_path: str
                              ) -> typ.Iterable[typ.Tuple[str, tt.Metadata]]:
        # The target of the self metadata is the folder containing the self metadata file.
        if isinstance(yaml_data, collections.abc.Mapping):
            yield rel_sub_dir_path, yaml_data

    class MetaSource(enum.Enum):
        """Represents sources of metadata for items in a Taggu library.
        The order of entries here is important, it represents the order of overriding (last element overrides previous).
        """
        ITEM = tt.MetaSourceSpec(file_name=item_meta_file_name
                                 , dir_getter=yield_siblings_dir
                                 , multiplexer=yield_item_meta_pairs
                                 )
        SELF = tt.MetaSourceSpec(file_name=self_meta_file_name
                                 , dir_getter=yield_contains_dir
                                 , multiplexer=yield_self_meta_pairs
                                 )

        def __str__(self):
            return '{}.{}'.format(type(self).__name__, self.name)

        __repr__ = __str__

    class Discoverer:
        @classmethod
        def meta_files_from_item(cls, rel_item_path: str) -> typ.Iterable[str]:
            """Given an item path, yields all possible meta file paths that could provide direct metadata for that item.
            This does not verify that any of the resulting meta file paths exist, so appropriate checking is needed.
            """
            for meta_source in MetaSource:
                dir_getter: tt.DirGetter = meta_source.value.dir_getter
                file_name: str = meta_source.value.file_name

                # This loop will normally execute either zero or one time.
                for meta_dir in dir_getter(rel_item_path):
                    yield os.path.normpath(os.path.join(meta_dir, file_name))

        @classmethod
        def items_from_meta_file(cls, rel_meta_path: str) -> typ.Iterable[typ.Tuple[str, tt.Metadata]]:
            """Given a meta file path, yields all item paths that this meta file provides metadata for, along with the
            metadata itself and the meta source type.
            """
            rel_meta_path, abs_meta_path = co_norm(rel_sub_path=rel_meta_path)

            # Check that the provided path exists and is a file.
            if not os.path.isfile(abs_meta_path):
                msg = f'Meta file "{rel_meta_path}" does not exist, or is not a file'
                logger.error(msg)
                return

            # Get the meta file name and containing dir path.
            rel_containing_dir, meta_file_name = os.path.split(rel_meta_path)

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
                return

            # Open the meta file and read as YAML.
            # TODO: Add checking and logging for exceptions in here.
            yaml_data = th.read_yaml_file(abs_meta_path)

            multiplexer: tt.Multiplexer = target_meta_source.value.multiplexer

            # Multiplexer needs to know the directory it is based in.
            rel_containing_dir = os.path.normpath(rel_containing_dir)
            yield from multiplexer(yaml_data, rel_containing_dir)

        @classmethod
        def meta_files_from_items(cls, rel_item_paths: typ.Iterable[str]) -> typ.Iterable[str]:
            for rel_item_path in rel_item_paths:
                yield from cls.meta_files_from_item(rel_item_path=rel_item_path)

        @classmethod
        def items_from_meta_files(cls, rel_meta_paths: typ.Iterable[str]) -> typ.Iterable[typ.Tuple[str, tt.Metadata]]:
            for rel_meta_path in rel_meta_paths:
                yield from cls.items_from_meta_file(rel_meta_path=rel_meta_path)

        @classmethod
        def lookup_items(cls, *, rel_item_paths: typ.Iterable[str], parents: bool = True):
            rel_item_paths, abs_item_paths = zip(*(co_norm(rel_sub_path=rel_item_path) for rel_item_path in rel_item_paths))

            for rel_item_path in rel_item_paths:
                if rel_item_path in meta_cache:
                    logger.debug(f'Found item "{rel_item_path}" in cache, using cached results')

                else:
                    logger.debug(f'Item "{rel_item_path}" not found in cache, processing meta files')
                    for rel_meta_path in Discoverer.meta_files_from_item(rel_item_path):
                        rel_meta_path, abs_meta_path = co_norm(rel_sub_path=rel_meta_path)

                        if os.path.isfile(abs_meta_path):
                            logger.info(f'Found meta file "{rel_meta_path}" for item "{rel_item_path}", processing')

                            for ip, md in Discoverer.items_from_meta_file(rel_meta_path=rel_meta_path):
                                meta_cache[ip] = md
                        else:
                            logger.debug(f'Meta file "{rel_meta_path}" does not exist '
                                         f'for item "{rel_item_path}", skipping')

                yield rel_item_path, meta_cache.setdefault(rel_item_path, {})

                if parents:
                    par_dir = os.path.normpath(os.path.dirname(rel_item_path))
                    if par_dir != rel_item_path:
                        yield from cls.lookup_items(rel_item_paths=(par_dir,), parents=parents)

        @classmethod
        def lookup_item(cls, *, rel_item_path: str, parents: bool=True):
            yield from cls.lookup_items(rel_item_paths=(rel_item_path,), parents=parents)

        @classmethod
        def field_for_item(cls, *, rel_item_path: str, field_name: str):
            pass

        # TODO: For full-library spelunk, keep track of visited files.

        @classmethod
        def clear_cache(cls):
            meta_cache.clear()
            logger.info(f'Metadata cache cleared')

        @classmethod
        def all_cache_entries(cls):
            return meta_cache

    return Discoverer
