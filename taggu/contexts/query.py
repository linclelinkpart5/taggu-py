import abc
import pathlib as pl
import typing as typ
import collections.abc

import taggu.contexts.library as tlib
import taggu.contexts.discovery as td
import taggu.logging as tl
import taggu.types as tt
import taggu.meta_cache as tmc

logger = tl.get_logger(__name__)

Label = str
LabelContainer = typ.Container[Label]
LabelExtractor = typ.Callable[[pl.Path], str]

FieldValueGen = typ.Generator[tt.FieldValue, None, None]


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
                    labels: typ.Optional[LabelContainer]) -> FieldValueGen:
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

        meta_cacher: tmc.MetaCacher = cls.get_meta_cacher()

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
                        yield from field_val
                    elif isinstance(field_val, collections.abc.Mapping):
                        yield from field_val.keys()

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
                            labels: typ.Optional[LabelContainer]) -> FieldValueGen:
        paths = tuple(rel_item_path.parents)

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
                           max_distance: typ.Optional[int]=None,
                           labels: typ.Optional[LabelContainer]) -> FieldValueGen:
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
                    field_vals = cls.yield_field(rel_item_path=rel_child_path, field_name=field_name, labels=labels)

                    for field_val in field_vals:
                        yield field_val
                        found = True

                    if not found:
                        # If this child did not have the field, try its children.
                        next_max_distance = md - 1 if md is not None else None
                        yield from helper(rip=rel_child_path, md=next_max_distance)

        yield from helper(rel_item_path, max_distance)


def gen_lookup_ctx(*, discovery_context: td.DiscoveryContext,
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
