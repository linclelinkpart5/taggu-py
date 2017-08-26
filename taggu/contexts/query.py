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
    def get_meta_cache(cls) -> tt.MetadataCache:
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
    def cache_item(cls, *, rel_item_path: pl.Path):
        meta_cache = cls.get_meta_cache()
        discovery_context = cls.get_discovery_context()
        library_context = discovery_context.get_library_context()

        if rel_item_path in meta_cache:
            logger.debug(f'Found item "{rel_item_path}" in cache, using cached results')

        else:
            logger.debug(f'Item "{rel_item_path}" not found in cache, processing meta files')
            for rel_meta_path in discovery_context.meta_files_from_item(rel_item_path):
                rel_meta_path, abs_meta_path = library_context.co_norm(rel_sub_path=rel_meta_path)

                if abs_meta_path.is_file():
                    logger.info(f'Found meta file "{rel_meta_path}" for item "{rel_item_path}", processing')

                    for ip, md in discovery_context.items_from_meta_file(rel_meta_path=rel_meta_path):
                        # TODO: Allow option of overwriting entire dict or just fields.
                        # # Overwrite entire dict.
                        # meta_cache[ip] = md

                        # Overwrite new fields.
                        ex_cache = typ.cast(typ.MutableMapping, meta_cache.setdefault(ip, {}))
                        meta_cache[ip] = {k: v for k, v in it.chain(ex_cache.items(), md.items())}
                else:
                    logger.debug(f'Meta file "{rel_meta_path}" does not exist '
                                 f'for item "{rel_item_path}", skipping')

    @classmethod
    def clear_cache(cls):
        # TODO: Add number of items deleted to log message.
        meta_cache = cls.get_meta_cache()
        meta_cache.clear()
        logger.info(f'Metadata cache cleared')


def gen_lookup_ctx(*, discovery_context: td.DiscoveryContext,
                   label_ext: typ.Optional[LabelExtractor]) -> QueryContext:
    meta_cache: tt.MetadataCache = {}

    class QC(QueryContext):
        @classmethod
        def get_discovery_context(cls) -> td.DiscoveryContext:
            """Returns the discovery context used in this lookup context."""
            return discovery_context

        @classmethod
        def get_meta_cache(cls) -> tt.MetadataCache:
            return meta_cache

        @classmethod
        def yield_field(cls, *,
                        rel_item_path: pl.Path,
                        field_name: str,
                        labels: typ.Optional[LabelContainer]=None) -> FieldValueGen:
            """Given a relative item path and a field name, yields all metadata entries matching that field for that item.
            Only direct metadata for that item is looked up, no parent or child metadata is used.
            """
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
            # else:
            #     import pprint
            #     meta_dict_dump = pprint.pformat(meta_dict)
            #     meta_cache_dump = pprint.pformat(meta_cache)
            #     print(f'Could not find field name "{field_name}", for rel path "{rel_item_path}"\n'
            #           f'resulting dict = {meta_dict_dump}\nresulting cache = {meta_cache_dump}')

    return QC()
