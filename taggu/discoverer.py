import typing as typ
import os.path
import collections.abc
import enum
import pathlib as pl
import itertools as it
import copy
import concurrent.futures as cf
import abc

import taggu.types as tt
import taggu.logging as tl
import taggu.exceptions as tex
import taggu.helpers as th
import taggu.labels as tlb


logger = tl.get_logger(__name__)

MetadataCache = typ.MutableMapping[pl.Path, tt.Metadata]

MetadataResolver = typ.Callable[[pl.Path, str], typ.Generator[str, None, None]]


class ItemContext(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def yield_field(cls, *, field_name: str, labels: typ.Optional[typ.Collection[str]]=None) \
            -> typ.Generator[str, None, None]:
        pass

    @classmethod
    @abc.abstractmethod
    def yield_parent_fields(cls, *, field_name: str, labels: typ.Optional[typ.Collection[str]]=None) \
            -> typ.Generator[str, None, None]:
        pass

    @classmethod
    @abc.abstractmethod
    def yield_child_fields(cls, *, field_name: str, labels: typ.Optional[typ.Collection[str]]=None) \
            -> typ.Generator[str, None, None]:
        pass


def norm(path: pl.Path) -> pl.Path:
    return pl.Path(os.path.normpath(path))


def generate_discoverer(*
                        , root_dir: pl.Path
                        , media_item_filter: tt.ItemFilter=None
                        , self_meta_file_name: pl.Path=pl.Path('taggu_self.yml')
                        , item_meta_file_name: pl.Path=pl.Path('taggu_item.yml')
                        , label_ext: tlb.LabelExtractor=tlb.default_label_extractor
                        , media_item_sort_key: typ.Callable[[pl.Path], typ.Any]=None
                        ) -> typ.Type['Discoverer']:
    # Expand user dir directives (~ and ~user), collapse dotted (. and ..) entries in path, and absolute-ize.
    root_dir = root_dir.expanduser().resolve()

    meta_cache: MetadataCache = {}
    visited_real_meta_paths: typ.MutableSet = set()

    def co_norm(rel_sub_path: pl.Path) -> typ.Tuple[pl.Path, pl.Path]:
        abs_sub_path = norm(root_dir / rel_sub_path)
        rel_sub_path = abs_sub_path.relative_to(root_dir)
        return rel_sub_path, abs_sub_path

    def yield_contains_dir(rel_sub_path: pl.Path) -> typ.Iterable[pl.Path]:
        rel_sub_path, abs_sub_path = co_norm(rel_sub_path=rel_sub_path)
        if abs_sub_path.is_dir():
            yield rel_sub_path

    def yield_siblings_dir(rel_sub_path: pl.Path) -> typ.Iterable[pl.Path]:
        par_dir = rel_sub_path.parent
        if par_dir != rel_sub_path:
            yield par_dir

    def yield_item_meta_pairs(yaml_data: typ.Any
                              , rel_sub_dir_path: pl.Path
                              ) -> typ.Iterable[typ.Tuple[pl.Path, tt.Metadata]]:
        rel_sub_dir_path, abs_sub_dir_path = co_norm(rel_sub_path=rel_sub_dir_path)

        # Find eligible item names in this directory.
        item_names: typ.AbstractSet[str] = th.item_discovery(abs_dir_path=abs_sub_dir_path,
                                                             item_filter=media_item_filter)

        # File metadata can be either a dictionary or sequence.
        if isinstance(yaml_data, collections.abc.Sequence):
            # Performing sequential application of metadata to interesting items.
            # Check that there are an equal number of metadata entries and interesting items.
            if len(item_names) != len(yaml_data):
                logger.warning(f'Counts of items in directory and metadata blocks do not match; '
                               f'found {len(item_names)} item(s) '
                               f'and {len(yaml_data)} metadata block(s)'
                               )

            for item_name, meta_block in zip(sorted(item_names, key=media_item_sort_key), yaml_data):
                rel_item_path = rel_sub_dir_path / item_name
                yield rel_item_path, meta_block

        elif isinstance(yaml_data, collections.abc.Mapping):
            # Performing mapped application of metadata to interesting items.
            for item_name, meta_block in yaml_data.items():
                # Test if item name from metadata has a valid name.
                if not th.is_valid_item_name(item_name):
                    logger.warning(f'Item name "{item_name}" is not valid, skipping')
                    continue

                item_path = th.fuzzy_file_lookup(abs_dir_path=abs_sub_dir_path, prefix_file_name=item_name)
                item_name = item_path.name

                # Test if the item name is in the list of discovered item names.
                if item_name not in item_names:
                    logger.warning(f'Item "{item_name}" not found in eligible item names for this directory, '
                                   f'skipping')
                    continue

                rel_item_path = item_path.relative_to(root_dir)
                yield rel_item_path, meta_block

    def yield_self_meta_pairs(yaml_data: typ.Any
                              , rel_sub_dir_path: pl.Path
                              ) -> typ.Iterable[typ.Tuple[pl.Path, tt.Metadata]]:
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
        def meta_files_from_item(cls, rel_item_path: pl.Path) -> typ.Iterable[pl.Path]:
            """Given an item path, yields all possible meta file paths that could provide direct metadata for that item.
            This does not verify that any of the resulting meta file paths exist, so appropriate checking is needed.
            """
            for meta_source in MetaSource:
                dir_getter: tt.DirGetter = meta_source.value.dir_getter
                file_name: pl.Path = meta_source.value.file_name

                # This loop will normally execute either zero or one time.
                for meta_dir in dir_getter(rel_item_path):
                    yield meta_dir / file_name

        @classmethod
        def items_from_meta_file(cls, rel_meta_path: pl.Path) -> typ.Iterable[typ.Tuple[pl.Path, tt.Metadata]]:
            """Given a meta file path, yields all item paths that this meta file provides metadata for, along with the
            metadata itself and the meta source type.
            """
            rel_meta_path, abs_meta_path = co_norm(rel_sub_path=rel_meta_path)

            # Check that the provided path exists and is a file.
            if not abs_meta_path.is_file():
                msg = f'Meta file "{rel_meta_path}" does not exist, or is not a file'
                logger.error(msg)
                return

            # Get the meta file name and containing dir path.
            rel_containing_dir = rel_meta_path.parent
            meta_file_name = pl.Path(rel_meta_path.name)

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
            rel_containing_dir = norm(rel_containing_dir)
            yield from multiplexer(yaml_data, rel_containing_dir)

        @classmethod
        def meta_files_from_items(cls, rel_item_paths: typ.Iterable[pl.Path]) \
                -> typ.Iterable[pl.Path]:
            for rel_item_path in rel_item_paths:
                yield from cls.meta_files_from_item(rel_item_path=rel_item_path)

        @classmethod
        def items_from_meta_files(cls, rel_meta_paths: typ.Iterable[pl.Path]) \
                -> typ.Iterable[typ.Tuple[pl.Path, tt.Metadata]]:
            for rel_meta_path in rel_meta_paths:
                yield from cls.items_from_meta_file(rel_meta_path=rel_meta_path)

        @classmethod
        def cache_item(cls, *, rel_item_path: pl.Path):
            if rel_item_path in meta_cache:
                logger.debug(f'Found item "{rel_item_path}" in cache, using cached results')

            else:
                logger.debug(f'Item "{rel_item_path}" not found in cache, processing meta files')
                for rel_meta_path in Discoverer.meta_files_from_item(rel_item_path):
                    rel_meta_path, abs_meta_path = co_norm(rel_sub_path=rel_meta_path)

                    if abs_meta_path.is_file():
                        logger.info(f'Found meta file "{rel_meta_path}" for item "{rel_item_path}", processing')

                        for ip, md in Discoverer.items_from_meta_file(rel_meta_path=rel_meta_path):
                            meta_cache[ip] = md
                    else:
                        logger.debug(f'Meta file "{rel_meta_path}" does not exist '
                                     f'for item "{rel_item_path}", skipping')

########################################################################################################################
#   Field yielders
########################################################################################################################

        @classmethod
        def yield_field(cls, *,
                        rel_item_path: pl.Path,
                        field_name: str,
                        labels: typ.Optional[typ.Collection[str]]=None) -> typ.Generator[str, None, None]:
            if labels is not None and label_ext is not None:
                if label_ext(rel_item_path) not in labels:
                    return

            cls.cache_item(rel_item_path=rel_item_path)

            meta_dict = meta_cache.get(rel_item_path, {})
            if field_name in meta_dict:
                value = meta_dict[field_name]

                if isinstance(value, str):
                    yield value
                elif isinstance(value, collections.abc.Sequence):
                    yield from value

        @classmethod
        def yield_parent_fields(cls, *,
                                rel_item_path: pl.Path,
                                field_name: str,
                                labels: typ.Optional[typ.Collection[str]]=None,
                                max_distance: typ.Optional[int]=None) -> typ.Generator[str, None, None]:
            paths = rel_item_path.parents

            if max_distance is not None and max_distance >= 0:
                paths = paths[:max_distance]

            found = False
            for path in paths:
                for field_val in cls.yield_field(rel_item_path=path, field_name=field_name, labels=labels):
                    yield field_val
                    found = True

                if found:
                    return

        @classmethod
        def yield_child_fields(cls, *,
                               rel_item_path: pl.Path,
                               field_name: str,
                               labels: typ.Optional[typ.Collection[str]]=None,
                               max_distance: typ.Optional[int]=None) -> typ.Generator[str, None, None]:
            # TODO: This function has issues with cyclic folder hierarchies, fix.
            def helper(rip: pl.Path, md: typ.Optional[int]):
                rip, aip = co_norm(rel_sub_path=rip)

                # Only try and process children if this item is a directory.
                if aip.is_dir() and (md is None or md > 0):
                    child_item_names = th.item_discovery(abs_dir_path=aip, item_filter=media_item_filter)

                    for child_item_name in sorted(child_item_names, key=media_item_sort_key):
                        rel_child_path = rip / child_item_name

                        found = False
                        fields = cls.yield_field(rel_item_path=rel_child_path, field_name=field_name, labels=labels)

                        for field in fields:
                            yield field
                            found = True

                        if not found:
                            next_max_distance = md - 1 if md is not None else None

                            yield from helper(rel_child_path, next_max_distance)

            yield from helper(rel_item_path, max_distance)

########################################################################################################################
#   Cache manipulation
########################################################################################################################

        @classmethod
        def clear_cache(cls):
            meta_cache.clear()
            logger.info(f'Metadata cache cleared')

        @classmethod
        def clear_cache_branch(cls, paths: typ.Collection[pl.Path]):
            paths = frozenset(paths)

            def to_delete(p: pl.Path) -> bool:
                p_set = frozenset({p, *p.parents})
                return bool(p_set.intersection(paths))

            keys_to_delete = {key for key in meta_cache.keys() if to_delete(key)}
            for key in keys_to_delete:
                meta_cache.pop(key, None)

        @classmethod
        def cache_copy(cls):
            return copy.copy(meta_cache)

        @classmethod
        def cache_deepcopy(cls):
            return copy.deepcopy(meta_cache)

########################################################################################################################
#   Item contexts
########################################################################################################################

        @classmethod
        def generate_item_context(cls, *, rel_item_path: pl.Path) -> typ.Type[ItemContext]:
            rel_item_path, abs_item_path = co_norm(rel_sub_path=rel_item_path)
            discoverer = cls

            class IC(ItemContext):
                @classmethod
                def yield_field(cls, *,
                                field_name: str,
                                labels: typ.Optional[typ.Collection[str]]=None) \
                        -> typ.Generator[str, None, None]:
                    yield from discoverer.yield_field(rel_item_path=rel_item_path,
                                                      field_name=field_name,
                                                      labels=labels)

                @classmethod
                def yield_parent_fields(cls, *,
                                        field_name: str,
                                        labels: typ.Optional[typ.Collection[str]]=None) \
                        -> typ.Generator[str, None, None]:
                    yield from discoverer.yield_parent_fields(rel_item_path=rel_item_path,
                                                              field_name=field_name,
                                                              labels=labels)

                @classmethod
                def yield_child_fields(cls, *,
                                       field_name: str,
                                       labels: typ.Optional[typ.Collection[str]]=None) \
                        -> typ.Generator[str, None, None]:
                    yield from discoverer.yield_child_fields(rel_item_path=rel_item_path,
                                                             field_name=field_name,
                                                             labels=labels)

            return IC

    return Discoverer
