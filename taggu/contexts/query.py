import abc
import pathlib as pl
import typing as typ
import collections.abc
import enum

import taggu.contexts.library as tlib
import taggu.contexts.discovery as td
import taggu.logging as tl
import taggu.types as tt
import taggu.meta_cache as tmc
import taggu.helpers as th

logger = tl.get_logger(__name__)

Label = str
LabelContainer = typ.Container[Label]
LabelExtractor = typ.Callable[[pl.Path], str]

FieldValueGen = typ.Generator[tt.FieldValue, None, None]

MappingIterFunc = typ.Callable[[typ.Mapping], typ.Generator[typ.Any, None, None]]


def mis_keys(d: typ.Mapping) -> typ.Generator[typ.Any, None, None]:
    yield from d.keys()


def mis_vals(d: typ.Mapping) -> typ.Generator[typ.Any, None, None]:
    yield from d.values()


def mis_pairs(d: typ.Mapping) -> typ.Generator[typ.Any, None, None]:
    yield from d.items()


class MappingIterStyle(enum.Enum):
    KEYS = mis_keys
    VALS = mis_vals
    PAIRS = mis_pairs


def field_flattener(*, field_value: typ.Union[None, str, typ.Sequence, typ.Mapping], flatten_limit: typ.Optional[int],
                    mapping_iter_style: MappingIterStyle):
    next_fl: typ.Optional[int] = (flatten_limit - 1) if flatten_limit is not None else None

    if field_value is None:
        # Just yield None.
        yield None
    # TODO: Need to check for bytes as well?
    elif isinstance(field_value, str):
        # Just yield the value.
        yield field_value
    elif isinstance(field_value, collections.abc.Sequence):
        if flatten_limit is None or flatten_limit > 0:
            for i in field_value:
                yield from field_flattener(field_value=i, flatten_limit=next_fl, mapping_iter_style=mapping_iter_style)
        else:
            yield field_value
    elif isinstance(field_value, collections.abc.Mapping):
        if flatten_limit is None or flatten_limit > 0:
            mis: MappingIterFunc = mapping_iter_style
            for i in mis(field_value):
                yield from field_flattener(field_value=i, flatten_limit=next_fl, mapping_iter_style=mapping_iter_style)
        else:
            yield field_value


class QueryContext(abc.ABC):
    """Handles retrieving individual fields from metadata for an item."""

    @classmethod
    @abc.abstractmethod
    def get_discovery_context(cls) -> td.DiscoveryContext:
        """Returns the discovery context used in this lookup context."""
        pass

    @classmethod
    @abc.abstractmethod
    def get_label_extractor(cls) -> typ.Optional[LabelExtractor]:
        """Returns the label extractor used in this lookup context."""
        pass

    @classmethod
    @abc.abstractmethod
    def get_meta_cacher(cls) -> typ.Optional[tmc.MetaCacher]:
        pass

    @classmethod
    def yield_field(cls, *,
                    rel_item_path: pl.Path,
                    field_name: str,
                    labels: typ.Optional[LabelContainer],
                    mapping_iter_style: MappingIterStyle,
                    recursive: bool=True) -> FieldValueGen:
        """Given a relative item path and a field name, yields metadata entries matching that field for that item.
        Only direct metadata for that item is looked up, no parent or child metadata is used.
        """
        label_extractor: LabelExtractor = cls.get_label_extractor()
        discovery_context: td.DiscoveryContext = cls.get_discovery_context()

        if labels is not None and label_extractor is not None:
            logger.debug(f'Checking if item path "{rel_item_path}" meets label requirements')
            if label_extractor(rel_item_path) not in labels:
                extracted_label = label_extractor(rel_item_path)
                if extracted_label not in labels:
                    logger.info(f'Item "{rel_item_path}" with label "{extracted_label}" '
                                f'did not match any expected labels, skipping')
                    return

        meta_cacher: typ.Optional[tmc.MetaCacher] = cls.get_meta_cacher()

        for rel_meta_path in discovery_context.meta_files_from_item(rel_item_path):
            if meta_cacher is not None:
                meta_cacher.cache_meta_file(rel_meta_path=rel_meta_path)
                temp_cache = meta_cacher.get_meta_file(rel_meta_path=rel_meta_path)
            else:
                temp_cache: typ.MutableMapping[pl.Path, tt.Metadata] = {
                    k: v for k, v in discovery_context.items_from_meta_file(rel_meta_path=rel_meta_path)
                }

            if rel_item_path in temp_cache:
                meta_dict = temp_cache[rel_item_path]

                if field_name in meta_dict:
                    logger.debug(f'Found field "{field_name}" for item "{rel_item_path}" '
                                 f'in meta file "{rel_meta_path}"')

                    field_val = meta_dict[field_name]

                    if field_val is None:
                        yield None
                    elif isinstance(field_val, str):
                        yield field_val
                    elif isinstance(field_val, collections.abc.Sequence):
                        if recursive:
                            # Recursively flatten the iterables.
                            yield from th.recursive_flatten(field_val)
                        else:
                            # Flatten only this level.
                            yield from field_val
                    elif isinstance(field_val, collections.abc.Mapping):
                        mis = mapping_iter_style.value
                        i = mis(field_val)

                        if recursive:
                            yield from th.recursive_flatten(i)
                        else:
                            yield from i
                    else:
                        logger.warning(f'Field "{field_name}" in meta file "{rel_meta_path}" had unexpected type, '
                                       f'skipping')
                        # TODO: Correct to continue, or better to break?
                        continue

                    # No need to look at other meta files, just return.
                    return
                else:
                    logger.debug(f'Could not find field "{field_name}" for item "{rel_item_path}" '
                                 f'in meta file "{rel_meta_path}", trying next meta file, if available')

            else:
                logger.warning(f'Could not find item "{rel_item_path}" in meta file "{rel_meta_path}"')

    @classmethod
    def yield_parent_fields(cls, *,
                            rel_item_path: pl.Path,
                            field_name: str,
                            max_distance: typ.Optional[int]=None,
                            labels: typ.Optional[LabelContainer],
                            mapping_iter_style: MappingIterStyle) -> FieldValueGen:
        paths = tuple(rel_item_path.parents)

        if max_distance is not None and max_distance >= 0:
            paths = paths[:max_distance]

        found = False
        for path in paths:
            for field_val in cls.yield_field(rel_item_path=path, field_name=field_name, labels=labels,
                                             mapping_iter_style=mapping_iter_style):
                yield field_val
                found = True

            if found:
                return

    @classmethod
    def yield_child_fields(cls, *,
                           rel_item_path: pl.Path,
                           field_name: str,
                           max_distance: typ.Optional[int]=None,
                           labels: typ.Optional[LabelContainer],
                           mapping_iter_style: MappingIterStyle) -> FieldValueGen:
        # TODO: This function has issues with cyclic folder hierarchies, fix.
        dis_ctx: td.DiscoveryContext = cls.get_discovery_context()
        lib_ctx: tlib.LibraryContext = dis_ctx.get_library_context()

        def helper(rip: pl.Path, md: typ.Optional[int]):
            rip, aip = lib_ctx.co_norm(rel_sub_path=rip)

            # Only try and process children if this item is a directory.
            if aip.is_dir() and (md is None or md > 0):
                for child_item_name in lib_ctx.sorted_item_names_in_dir(rel_sub_dir_path=rip):
                    rel_child_path = rip / child_item_name

                    found = False
                    field_vals = cls.yield_field(rel_item_path=rel_child_path, field_name=field_name, labels=labels,
                                                 mapping_iter_style=mapping_iter_style)

                    for field_val in field_vals:
                        yield field_val
                        found = True

                    if not found:
                        # If this child did not have the field, try its children.
                        next_max_distance = md - 1 if md is not None else None
                        yield from helper(rip=rel_child_path, md=next_max_distance)

        yield from helper(rel_item_path, max_distance)

    # @classmethod
    # def get_field(cls, *,
    #               rel_item_path: pl.Path,
    #               field_name: str,
    #               labels: typ.Optional[LabelContainer]):
    #     # 1) <field absent>: None
    #     # 2) None: None
    #     # 3) <any str value, including empty>: that str value
    #     # 4) <any seq value, including empty>: that seq value, as a tuple
    #     # 5) <any map value, including empty>: that map value, as a dict
    #     pass


def gen_query_ctx(*, discovery_context: td.DiscoveryContext,
                  label_extractor: typ.Optional[LabelExtractor],
                  use_cache: bool=True) -> QueryContext:
    meta_cacher = None
    if use_cache:
        meta_cacher = tmc.gen_meta_cacher(discovery_context=discovery_context)

    class QC(QueryContext):
        @classmethod
        def get_discovery_context(cls) -> td.DiscoveryContext:
            return discovery_context

        @classmethod
        def get_label_extractor(cls) -> typ.Optional[LabelExtractor]:
            return label_extractor

        @classmethod
        def get_meta_cacher(cls) -> typ.Optional[tmc.MetaCacher]:
            return meta_cacher

    return QC()
