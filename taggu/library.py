import typing as typ
import os.path
import collections.abc
import pathlib as pl
import abc

import taggu.logging as tl
import taggu.exceptions as tex
import taggu.helpers as th
import taggu.labels as tlb


logger = tl.get_logger(__name__)

ItemFilter = typ.Callable[[pl.Path], bool]
ItemSortKey = typ.Callable[[pl.Path], typ.Any]

MetadataKey = typ.NewType('MetadataKey', str)
MetadataValue = typ.Union[str, typ.Sequence[str]]

Metadata = typ.Mapping[MetadataKey, MetadataValue]

DirGetter = typ.Callable[[pl.Path], typ.Iterable[pl.Path]]
Multiplexer = typ.Callable[[typ.Any, pl.Path, typ.Optional[ItemFilter]], typ.Iterable[typ.Tuple[pl.Path, Metadata]]]

MetaSourceSpec = typ.Tuple[pl.Path, DirGetter, Multiplexer]

MetadataCache = typ.MutableMapping[pl.Path, Metadata]

MetadataResolver = typ.Callable[[pl.Path, str], typ.Generator[str, None, None]]

RootDirectoryNormer = typ.Callable[[pl.Path], typ.Tuple[pl.Path, pl.Path]]

MetadataPair = typ.Tuple[pl.Path, Metadata]
MetadataPairGen = typ.Generator[MetadataPair, None, None]

########################################################################################################################
#   Library context
########################################################################################################################


class LibraryContext(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def get_root_dir(cls) -> pl.Path:
        pass

    @classmethod
    @abc.abstractmethod
    def get_media_item_filter(cls) -> typ.Optional[ItemFilter]:
        pass

    @classmethod
    @abc.abstractmethod
    def get_media_item_sort_key(cls) -> typ.Optional[ItemSortKey]:
        pass

    @classmethod
    @abc.abstractmethod
    def get_item_meta_file_name(cls) -> str:
        pass

    @classmethod
    @abc.abstractmethod
    def get_self_meta_file_name(cls) -> str:
        pass

    @classmethod
    def co_norm(cls, *, rel_sub_path: pl.Path) -> typ.Tuple[pl.Path, pl.Path]:
        """Normalizes a relative sub path with respect to the enclosed root directory.
        Returns a tuple of the re-normalized relative sub path and the absolute sub path.
        """
        if rel_sub_path.is_absolute():
            raise tex.AbsoluteSubpath()

        root_dir = cls.get_root_dir()
        path = root_dir / rel_sub_path
        abs_sub_path = pl.Path(os.path.normpath(path))
        try:
            rel_sub_path = abs_sub_path.relative_to(root_dir)
        except ValueError:
            raise tex.EscapingSubpath()
        return rel_sub_path, abs_sub_path

    @classmethod
    def yield_contains_dir(cls, *, rel_sub_path: pl.Path) -> typ.Generator[pl.Path, None, None]:
        rel_sub_path, abs_sub_path = cls.co_norm(rel_sub_path=rel_sub_path)
        if abs_sub_path.is_dir():
            yield rel_sub_path

    @classmethod
    def yield_siblings_dir(cls, *, rel_sub_path: pl.Path) -> typ.Generator[pl.Path, None, None]:
        par_dir = rel_sub_path.parent
        if par_dir != rel_sub_path:
            yield par_dir

    @classmethod
    def fuzzy_name_lookup(cls, *, rel_sub_dir_path: pl.Path, prefix_item_name: str) -> str:
        rel_sub_dir_path, abs_sub_dir_path = cls.co_norm(rel_sub_path=rel_sub_dir_path)

        pattern = f'{prefix_item_name}*'
        results = tuple(abs_sub_dir_path.glob(pattern))

        if len(results) != 1:
            msg = (f'Incorrect number of matches for fuzzy lookup of "{prefix_item_name}" '
                   f'in directory "{abs_sub_dir_path}"; '
                   f'expected: 1, found: {len(results)}')
            logger.error(msg)
            raise tex.NonUniqueFuzzyFileLookup(msg)

        abs_found_path = results[0]
        return abs_found_path.name

    @classmethod
    def item_names_in_dir(cls, *, rel_sub_dir_path: pl.Path) -> typ.AbstractSet[str]:
        """Finds item names in a given directory. These items must pass a filter in order to be selected."""
        rel_sub_dir_path, abs_sub_dir_path = cls.co_norm(rel_sub_path=rel_sub_dir_path)

        logger.info(f'Looking for valid items in directory "{rel_sub_dir_path}"')

        count = 0

        media_item_filter = cls.get_media_item_filter()

        def helper():
            # Make sure the path is a directory.
            # If not, we yield nothing.
            nonlocal count
            if abs_sub_dir_path.is_dir():
                for item in abs_sub_dir_path.iterdir():
                    count += 1
                    item_name = item.name

                    if media_item_filter is not None:
                        if media_item_filter(item):
                            logger.debug(f'Item "{item_name}" passed filter, marking as eligible')
                            yield item_name
                        else:
                            logger.debug(f'Item "{item_name}" failed filter, skipping')
                    else:
                        logger.debug(f'Marking item "{item_name}" as eligible')
                        yield item_name

        vals = frozenset(helper())
        logger.info(f'Found {th.pluralize(len(vals), "eligible item")} out of {count} '
                    f'in directory "{rel_sub_dir_path}"')
        return vals

    @classmethod
    def yield_item_meta_pairs(cls, *, yaml_data: typ.Any, rel_sub_dir_path: pl.Path) -> MetadataPairGen:
        rel_sub_dir_path, abs_sub_dir_path = cls.co_norm(rel_sub_path=rel_sub_dir_path)

        # Find eligible item names in this directory.
        item_names: typ.AbstractSet[str] = cls.item_names_in_dir(rel_sub_dir_path=rel_sub_dir_path)

        # File metadata can be either a dictionary or sequence.
        if isinstance(yaml_data, collections.abc.Sequence):
            # Performing sequential application of metadata to interesting items.
            # Check that there are an equal number of metadata entries and interesting items.
            # TODO: Perform this check for mappings as well.
            if len(item_names) != len(yaml_data):
                logger.warning(f'Counts of items in directory and metadata blocks do not match; '
                               f'found {th.pluralize(len(item_names), "item")} '
                               f'and {th.pluralize(len(yaml_data), "metadata block")}')

            media_item_sort_key = cls.get_media_item_sort_key()
            sorted_item_names: typ.Sequence[str] = tuple(sorted(item_names, key=media_item_sort_key))

            for item_name, meta_block in zip(sorted_item_names, yaml_data):
                rel_item_path = rel_sub_dir_path / item_name
                yield rel_item_path, meta_block

        elif isinstance(yaml_data, collections.abc.Mapping):
            # Performing mapped application of metadata to interesting items.
            processed_item_names = set()
            for item_name, meta_block in yaml_data.items():
                # Test if item name from metadata has a valid name.
                if not th.is_valid_item_name(item_name):
                    logger.warning(f'Item name "{item_name}" is not valid, skipping')
                    continue

                item_name = cls.fuzzy_name_lookup(rel_sub_dir_path=rel_sub_dir_path, prefix_item_name=item_name)

                # Warn if name was already processed.
                if item_name in processed_item_names:
                    logger.warning(f'Item "{item_name}" was already processed for this directory, skipping')
                    continue

                # Test if the item name is in the list of discovered item names.
                if item_name not in item_names:
                    logger.warning(f'Item "{item_name}" not found in eligible item names for this directory, '
                                   f'skipping')
                    continue

                rel_item_path = rel_sub_dir_path / item_name
                yield rel_item_path, meta_block
                processed_item_names.add(item_name)

            remaining_item_names = item_names - processed_item_names
            if remaining_item_names:
                logger.warning(f'Found {th.pluralize(len(remaining_item_names), "eligible item")} '
                               f'remaining not referenced in metadata')

    @classmethod
    def yield_self_meta_pairs(cls, *, yaml_data: typ.Any, rel_sub_dir_path: pl.Path) -> MetadataPairGen:
        # The target of the self metadata is the folder containing the self metadata file.
        if isinstance(yaml_data, collections.abc.Mapping):
            yield rel_sub_dir_path, yaml_data

    @classmethod
    def yield_meta_source_specs(cls) -> typ.Generator[MetaSourceSpec, None, None]:
        """Yields the meta source specifications for where to obtain data.
        The order these specifications are emitted designates their priority;
        later specifications override previous ones in the case of a conflict.
        """
        yield cls.get_item_meta_file_name(), cls.yield_siblings_dir, cls.yield_item_meta_pairs
        yield cls.get_self_meta_file_name(), cls.yield_contains_dir, cls.yield_self_meta_pairs


def gen_library_ctx(*,
                    root_dir: pl.Path,
                    media_item_filter: ItemFilter=None,
                    media_item_sort_key: ItemSortKey=None,
                    self_meta_file_name: str='taggu_self.yml',
                    item_meta_file_name: str='taggu_item.yml') -> LibraryContext:
    # Expand user dir directives (~ and ~user), collapse dotted (. and ..) entries in path, and absolute-ize.
    root_dir = pl.Path(os.path.abspath(os.path.expanduser(root_dir)))

    class LC(LibraryContext):
        @classmethod
        def get_root_dir(cls) -> pl.Path:
            return root_dir

        @classmethod
        def get_item_meta_file_name(cls) -> str:
            return item_meta_file_name

        @classmethod
        def get_self_meta_file_name(cls) -> str:
            return self_meta_file_name

        @classmethod
        def get_media_item_filter(cls) -> typ.Optional[ItemFilter]:
            return media_item_filter

        @classmethod
        def get_media_item_sort_key(cls) -> typ.Optional[ItemSortKey]:
            return media_item_sort_key

    return LC()


# ########################################################################################################################
# #   Item context
# ########################################################################################################################
#
#
# class ItemContext(abc.ABC):
#     @classmethod
#     @abc.abstractmethod
#     def yield_field(cls, *, field_name: str, labels: typ.Optional[typ.Collection[str]]=None) \
#             -> typ.Generator[str, None, None]:
#         pass
#
#     @classmethod
#     @abc.abstractmethod
#     def yield_parent_fields(cls, *, field_name: str, labels: typ.Optional[typ.Collection[str]]=None) \
#             -> typ.Generator[str, None, None]:
#         pass
#
#     @classmethod
#     @abc.abstractmethod
#     def yield_child_fields(cls, *, field_name: str, labels: typ.Optional[typ.Collection[str]]=None) \
#             -> typ.Generator[str, None, None]:
#         pass
#
# ########################################################################################################################
# #   Discoverer context
# ########################################################################################################################
#
#
# class DiscovererContext(abc.ABC):
#     """Handles retrieving meta file and item paths, along with raw metadata retrieval."""
#     @classmethod
#     @abc.abstractmethod
#     def meta_files_from_item(cls, rel_item_path: pl.Path) -> typ.Generator[pl.Path, None, None]:
#         """Given an item path, yields all valid meta file paths that could provide direct metadata for that item.
#         This also verifies that all of the resulting meta file paths exist.
#         """
#         pass
#
#     @classmethod
#     @abc.abstractmethod
#     def items_from_meta_file(cls, rel_meta_path: pl.Path) -> typ.Generator[typ.Tuple[pl.Path, Metadata], None, None]:
#         """Given a meta file path, yields all item paths that this meta file provides metadata for, along with the
#         metadata itself and the meta source type.
#         """
#         pass
#
#     @classmethod
#     def meta_files_from_items(cls, rel_item_paths: typ.Iterable[pl.Path]) \
#             -> typ.Generator[pl.Path, None, None]:
#         for rel_item_path in rel_item_paths:
#             yield from cls.meta_files_from_item(rel_item_path=rel_item_path)
#
#     @classmethod
#     def items_from_meta_files(cls, rel_meta_paths: typ.Iterable[pl.Path]) \
#             -> typ.Generator[typ.Tuple[pl.Path, Metadata], None, None]:
#         for rel_meta_path in rel_meta_paths:
#             yield from cls.items_from_meta_file(rel_meta_path=rel_meta_path)
#
#
# def norm(path: pl.Path) -> pl.Path:
#     return pl.Path(os.path.normpath(path))
#
#
# def generate_discoverer(*
#                         , root_dir: pl.Path
#                         , media_item_filter: ItemFilter=None
#                         , self_meta_file_name: pl.Path=pl.Path('taggu_self.yml')
#                         , item_meta_file_name: pl.Path=pl.Path('taggu_item.yml')
#                         , label_ext: tlb.LabelExtractor=tlb.default_label_extractor
#                         , media_item_sort_key: typ.Callable[[pl.Path], typ.Any]=None
#                         ) -> DiscovererContext:
#     # Expand user dir directives (~ and ~user), collapse dotted (. and ..) entries in path, and absolute-ize.
#     root_dir = root_dir.expanduser().resolve()
#
#     visited_real_meta_paths: typ.MutableSet = set()
#
#     def co_norm(rel_sub_path: pl.Path) -> typ.Tuple[pl.Path, pl.Path]:
#         abs_sub_path = norm(root_dir / rel_sub_path)
#         rel_sub_path = abs_sub_path.relative_to(root_dir)
#         return rel_sub_path, abs_sub_path
#
#     def yield_contains_dir(rel_sub_path: pl.Path) -> typ.Iterable[pl.Path]:
#         rel_sub_path, abs_sub_path = co_norm(rel_sub_path=rel_sub_path)
#         if abs_sub_path.is_dir():
#             yield rel_sub_path
#
#     def yield_siblings_dir(rel_sub_path: pl.Path) -> typ.Iterable[pl.Path]:
#         par_dir = rel_sub_path.parent
#         if par_dir != rel_sub_path:
#             yield par_dir
#
#     def yield_item_meta_pairs(yaml_data: typ.Any
#                               , rel_sub_dir_path: pl.Path
#                               ) -> typ.Iterable[typ.Tuple[pl.Path, Metadata]]:
#         rel_sub_dir_path, abs_sub_dir_path = co_norm(rel_sub_path=rel_sub_dir_path)
#
#         # Find eligible item names in this directory.
#         item_names: typ.AbstractSet[str] = th.item_discovery(abs_dir_path=abs_sub_dir_path,
#                                                              item_filter=media_item_filter)
#
#         # File metadata can be either a dictionary or sequence.
#         if isinstance(yaml_data, collections.abc.Sequence):
#             # Performing sequential application of metadata to interesting items.
#             # Check that there are an equal number of metadata entries and interesting items.
#             if len(item_names) != len(yaml_data):
#                 logger.warning(f'Counts of items in directory and metadata blocks do not match; '
#                                f'found {len(item_names)} item(s) '
#                                f'and {len(yaml_data)} metadata block(s)'
#                                )
#
#             for item_name, meta_block in zip(sorted(item_names, key=media_item_sort_key), yaml_data):
#                 rel_item_path = rel_sub_dir_path / item_name
#                 yield rel_item_path, meta_block
#
#         elif isinstance(yaml_data, collections.abc.Mapping):
#             # Performing mapped application of metadata to interesting items.
#             for item_name, meta_block in yaml_data.items():
#                 # Test if item name from metadata has a valid name.
#                 if not th.is_valid_item_name(item_name):
#                     logger.warning(f'Item name "{item_name}" is not valid, skipping')
#                     continue
#
#                 item_path = th.fuzzy_file_lookup(abs_dir_path=abs_sub_dir_path, prefix_file_name=item_name)
#                 item_name = item_path.name
#
#                 # Test if the item name is in the list of discovered item names.
#                 if item_name not in item_names:
#                     logger.warning(f'Item "{item_name}" not found in eligible item names for this directory, '
#                                    f'skipping')
#                     continue
#
#                 rel_item_path = item_path.relative_to(root_dir)
#                 yield rel_item_path, meta_block
#
#     def yield_self_meta_pairs(yaml_data: typ.Any
#                               , rel_sub_dir_path: pl.Path
#                               ) -> typ.Iterable[typ.Tuple[pl.Path, Metadata]]:
#         # The target of the self metadata is the folder containing the self metadata file.
#         if isinstance(yaml_data, collections.abc.Mapping):
#             yield rel_sub_dir_path, yaml_data
#
#     class MetaSource(enum.Enum):
#         """Represents sources of metadata for items in a Taggu library.
#         The order of entries here is important, it represents the order of overriding (last element overrides previous).
#         """
#         ITEM = MetaSourceSpec(file_name=item_meta_file_name
#                                  , dir_getter=yield_siblings_dir
#                                  , multiplexer=yield_item_meta_pairs
#                                  )
#         SELF = tt.MetaSourceSpec(file_name=self_meta_file_name
#                                  , dir_getter=yield_contains_dir
#                                  , multiplexer=yield_self_meta_pairs
#                                  )
#
#         def __str__(self):
#             return '{}.{}'.format(type(self).__name__, self.name)
#
#         __repr__ = __str__
#
#     class DC(DiscovererContext):
#         @classmethod
#         def meta_files_from_item(cls, rel_item_path: pl.Path) -> typ.Iterable[pl.Path]:
#             """Given an item path, yields all valid meta file paths that could provide direct metadata for that item.
#             This also verifies that all of the resulting meta file paths exist.
#             """
#             for meta_source in MetaSource:
#                 dir_getter: tt.DirGetter = meta_source.value.dir_getter
#                 file_name: pl.Path = meta_source.value.file_name
#
#                 # This loop will normally execute either zero or one time.
#                 for rel_meta_dir in dir_getter(rel_item_path):
#                     rel_meta_dir, abs_meta_dir = co_norm(rel_meta_dir)
#
#                     rel_meta_path = rel_meta_dir / file_name
#                     abs_meta_path = abs_meta_dir / file_name
#
#                     if abs_meta_path.is_file():
#                         logger.info(f'Found meta file "{rel_meta_path}" for item "{rel_item_path}"')
#                         yield rel_meta_path
#                     else:
#                         logger.debug(f'Meta file "{rel_meta_path}" does not exist for item "{rel_item_path}"')
#
#         @classmethod
#         def items_from_meta_file(cls, rel_meta_path: pl.Path) -> typ.Iterable[typ.Tuple[pl.Path, tt.Metadata]]:
#             """Given a meta file path, yields all item paths that this meta file provides metadata for, along with the
#             metadata itself and the meta source type.
#             """
#             rel_meta_path, abs_meta_path = co_norm(rel_sub_path=rel_meta_path)
#
#             # Check that the provided path exists and is a file.
#             if not abs_meta_path.is_file():
#                 msg = f'Meta file "{rel_meta_path}" does not exist, or is not a file'
#                 logger.error(msg)
#                 return
#
#             # Get the meta file name and containing dir path.
#             rel_containing_dir = rel_meta_path.parent
#             meta_file_name = pl.Path(rel_meta_path.name)
#
#             # Find the meta source matching this meta file name.
#             target_meta_source: MetaSource = None
#             for meta_source in MetaSource:
#                 if meta_file_name == meta_source.value.file_name:
#                     target_meta_source = meta_source
#                     break
#
#             # If the target meta source is not set, then the file name did not match that of any of the meta sources.
#             if target_meta_source is None:
#                 msg = f'Unknown meta file name "{meta_file_name}"'
#                 logger.error(msg)
#                 return
#
#             # Open the meta file and read as YAML.
#             # TODO: Add checking and logging for exceptions in here.
#             yaml_data = th.read_yaml_file(abs_meta_path)
#
#             multiplexer: tt.Multiplexer = target_meta_source.value.multiplexer
#
#             # Multiplexer needs to know the directory it is based in.
#             rel_containing_dir = norm(rel_containing_dir)
#             yield from multiplexer(yaml_data, rel_containing_dir)
#
#         def yield_field(self, *,
#                         rel_item_path: pl.Path,
#                         field_name: str,
#                         labels: typ.Optional[typ.Collection[str]]=None) -> typ.Generator[str, None, None]:
#             if labels is not None and label_ext is not None:
#                 if label_ext(rel_item_path) not in labels:
#                     return
#
#             self.cache_item(rel_item_path=rel_item_path)
#
#             meta_dict = self.meta_cache.get(rel_item_path, {})
#             if field_name in meta_dict:
#                 value = meta_dict[field_name]
#
#                 if isinstance(value, str):
#                     yield value
#                 elif isinstance(value, collections.abc.Sequence):
#                     yield from value
#
#         @classmethod
#         def yield_parent_fields(cls, *,
#                                 rel_item_path: pl.Path,
#                                 field_name: str,
#                                 labels: typ.Optional[typ.Collection[str]]=None,
#                                 max_distance: typ.Optional[int]=None) -> typ.Generator[str, None, None]:
#             paths = rel_item_path.parents
#
#             if max_distance is not None and max_distance >= 0:
#                 paths = paths[:max_distance]
#
#             found = False
#             for path in paths:
#                 for field_val in cls.yield_field(rel_item_path=path, field_name=field_name, labels=labels):
#                     yield field_val
#                     found = True
#
#                 if found:
#                     return
#
#         @classmethod
#         def yield_child_fields(cls, *,
#                                rel_item_path: pl.Path,
#                                field_name: str,
#                                labels: typ.Optional[typ.Collection[str]]=None,
#                                max_distance: typ.Optional[int]=None) -> typ.Generator[str, None, None]:
#             # TODO: This function has issues with cyclic folder hierarchies, fix.
#             def helper(rip: pl.Path, md: typ.Optional[int]):
#                 rip, aip = co_norm(rel_sub_path=rip)
#
#                 # Only try and process children if this item is a directory.
#                 if aip.is_dir() and (md is None or md > 0):
#                     child_item_names = th.item_discovery(abs_dir_path=aip, item_filter=media_item_filter)
#
#                     for child_item_name in sorted(child_item_names, key=media_item_sort_key):
#                         rel_child_path = rip / child_item_name
#
#                         found = False
#                         fields = cls.yield_field(rel_item_path=rel_child_path, field_name=field_name, labels=labels)
#
#                         for field in fields:
#                             yield field
#                             found = True
#
#                         if not found:
#                             next_max_distance = md - 1 if md is not None else None
#
#                             yield from helper(rel_child_path, next_max_distance)
#
#             yield from helper(rel_item_path, max_distance)
#
# ########################################################################################################################
# #   Item contexts
# ########################################################################################################################
#
#         @classmethod
#         def generate_item_context(cls, *, rel_item_path: pl.Path) -> ItemContext:
#             rel_item_path, abs_item_path = co_norm(rel_sub_path=rel_item_path)
#             discoverer = cls
#
#             class IC(ItemContext):
#                 @classmethod
#                 def yield_field(cls, *,
#                                 field_name: str,
#                                 labels: typ.Optional[typ.Collection[str]]=None) \
#                         -> typ.Generator[str, None, None]:
#                     yield from discoverer.yield_field(rel_item_path=rel_item_path,
#                                                       field_name=field_name,
#                                                       labels=labels)
#
#                 @classmethod
#                 def yield_parent_fields(cls, *,
#                                         field_name: str,
#                                         labels: typ.Optional[typ.Collection[str]]=None) \
#                         -> typ.Generator[str, None, None]:
#                     yield from discoverer.yield_parent_fields(rel_item_path=rel_item_path,
#                                                               field_name=field_name,
#                                                               labels=labels)
#
#                 @classmethod
#                 def yield_child_fields(cls, *,
#                                        field_name: str,
#                                        labels: typ.Optional[typ.Collection[str]]=None) \
#                         -> typ.Generator[str, None, None]:
#                     yield from discoverer.yield_child_fields(rel_item_path=rel_item_path,
#                                                              field_name=field_name,
#                                                              labels=labels)
#
#             return IC()
#
#     return DC()
