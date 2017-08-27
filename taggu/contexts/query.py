import abc
import pathlib as pl
import typing as typ
import collections.abc
import itertools as it

import taggu.contexts.library as tlib
import taggu.contexts.discovery as td
import taggu.helpers as th
import taggu.logging as tl
import taggu.types as tt

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
    def get_meta_file_cache(cls) -> tt.MetaFileCache:
        pass

    @classmethod
    @abc.abstractmethod
    def yield_field(cls, *,
                    rel_item_path: pl.Path,
                    field_name: str,
                    labels: typ.Optional[LabelContainer]=None) -> FieldValueGen:
        """Given a relative item path and a field name, yields all metadata entries matching that field for that item.
        Only direct metadata for that item is looked up, no parent or child metadata is used.
        """
        pass

    @classmethod
    def yield_parent_fields(cls, *,
                            rel_item_path: pl.Path,
                            field_name: str,
                            labels: typ.Optional[LabelContainer]=None,
                            max_distance: typ.Optional[int]=None) -> FieldValueGen:
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
                           labels: typ.Optional[LabelContainer]=None,
                           max_distance: typ.Optional[int]=None) -> FieldValueGen:
        # TODO: This function has issues with cyclic folder hierarchies, fix.
        dis_ctx: td.DiscoveryContext = cls.get_discovery_context()
        lib_ctx: tlib.LibraryContext = dis_ctx.get_library_context()

        def helper(rip: pl.Path, md: typ.Optional[int]):
            rip, aip = lib_ctx.co_norm(rel_sub_path=rip)

            # Only try and process children if this item is a directory.
            if aip.is_dir() and (md is None or md > 0):
                child_item_names = th.item_discovery(abs_dir_path=aip, item_filter=lib_ctx.get_media_item_filter())

                # TODO: Consider a LibraryContext.sorted_items_in_dir method.
                for child_item_name in sorted(child_item_names, key=lib_ctx.get_media_item_sort_key()):
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

    @classmethod
    def cache_meta_file(cls, *, rel_meta_path: pl.Path, force: bool=False):
        meta_file_cache: tt.MetaFileCache = cls.get_meta_file_cache()
        dis_ctx: td.DiscoveryContext = cls.get_discovery_context()

        if force:
            logger.debug(f'Defeating cache for meta file "{rel_meta_path}"')
            meta_file_cache.pop(rel_meta_path, None)

        if rel_meta_path in meta_file_cache:
            logger.debug(f'Found meta file "{rel_meta_path}" in cache, using cached results')
        else:
            logger.debug(f'Meta file "{rel_meta_path}" not found in cache, processing meta files')

            meta_file_cache[rel_meta_path] = {}
            for rel_item_path, metadata in dis_ctx.items_from_meta_file(rel_meta_path=rel_meta_path):
                meta_file_cache[rel_meta_path][rel_item_path] = metadata

    @classmethod
    def clear_cache(cls):
        # TODO: Add number of items deleted to log message.
        cache = cls.get_meta_file_cache()
        cache.clear()
        logger.info(f'Meta file cache cleared')


def gen_lookup_ctx(*, discovery_context: td.DiscoveryContext,
                   label_ext: typ.Optional[LabelExtractor]) -> QueryContext:
    meta_file_cache: tt.MetaFileCache = {}

    class QC(QueryContext):
        @classmethod
        def get_discovery_context(cls) -> td.DiscoveryContext:
            """Returns the discovery context used in this lookup context."""
            return discovery_context

        @classmethod
        def get_meta_file_cache(cls) -> tt.MetaFileCache:
            return meta_file_cache

        @classmethod
        def yield_field(cls, *,
                        rel_item_path: pl.Path,
                        field_name: str,
                        labels: typ.Optional[LabelContainer]=None) -> FieldValueGen:
            """Given a relative item path and a field name, yields metadata entries matching that field for that item.
            Only direct metadata for that item is looked up, no parent or child metadata is used.
            """
            logger.debug(f'Looking up field "{field_name}" for item file "{rel_item_path}"')
            if labels is not None and label_ext is not None:
                extracted_label = label_ext(rel_item_path)
                if extracted_label not in labels:
                    logger.info(f'Item "{rel_item_path}" with label "{extracted_label}" '
                                f'did not match any expected labels, skipping')
                    return
                else:
                    logger.debug(f'Item "{rel_item_path}" with label "{extracted_label}" matched expected labels')

            for rel_meta_path in discovery_context.meta_files_from_item(rel_item_path):
                logger.debug(f'Looking up meta file "{rel_meta_path}" for item "{rel_item_path}"')
                cls.cache_meta_file(rel_meta_path=rel_meta_path)

                if rel_meta_path in meta_file_cache:
                    logger.info(f'Found meta file "{rel_meta_path}" in cache')

                    if rel_item_path in meta_file_cache[rel_meta_path]:
                        logger.info(f'Found item file "{rel_item_path}" in cache for meta file "{rel_meta_path}"')

                        if field_name in meta_file_cache[rel_meta_path][rel_item_path]:
                            logger.info(f'Found field "{field_name}" in cache for item file "{rel_item_path}"')
                            found_field_data = meta_file_cache[rel_meta_path][rel_item_path][field_name]

                            if found_field_data is None:
                                yield None
                            elif isinstance(found_field_data, str):
                                yield found_field_data
                            elif isinstance(found_field_data, collections.abc.Sequence):
                                yield from found_field_data

                        else:
                            logger.info(f'Field "{field_name}" not found in cache for item file "{rel_item_path}", '
                                        f'skipping')
                            return
                    else:
                        logger.info(f'Item "{rel_item_path}" not found in cache for meta file "{rel_meta_path}", '
                                    f'skipping')
                        return
                else:
                    logger.info(f'Meta file "{rel_meta_path}" not found in cache, skipping')
                    return

    return QC()
