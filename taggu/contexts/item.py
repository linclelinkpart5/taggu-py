import abc
import pathlib as pl
import typing as typ
import collections.abc
import itertools as it

import taggu.contexts.query as tcq
import taggu.helpers as th
import taggu.logging as tl
import taggu.types as tt

logger = tl.get_logger(__name__)


class ItemContext(abc.ABC):
    """Handles retrieving and caching individual fields from metadata for a specific constant item."""

    @classmethod
    @abc.abstractmethod
    def get_query_context(cls) -> tcq.QueryContext:
        pass

    @classmethod
    @abc.abstractmethod
    def get_rel_item_path(cls) -> pl.Path:
        pass

    @classmethod
    def yield_field(cls, *, field_name: str, labels: typ.Optional[tcq.LabelContainer],
                    mapping_iter_style=tcq.MappingIterStyle.KEYS) -> tcq.FieldValueGen:
        query_ctx = cls.get_query_context()
        rel_item_path = cls.get_rel_item_path()

        return query_ctx.yield_field(rel_item_path=rel_item_path, field_name=field_name, labels=labels,
                                     mapping_iter_style=mapping_iter_style)

    @classmethod
    def yield_parent_fields(cls, *, field_name: str, labels: typ.Optional[tcq.LabelContainer],
                            mapping_iter_style=tcq.MappingIterStyle.KEYS) -> tcq.FieldValueGen:
        query_ctx = cls.get_query_context()
        rel_item_path = cls.get_rel_item_path()

        return query_ctx.yield_parent_fields(rel_item_path=rel_item_path, field_name=field_name, labels=labels,
                                             mapping_iter_style=mapping_iter_style)

    @classmethod
    def yield_child_fields(cls, *, field_name: str, labels: typ.Optional[tcq.LabelContainer],
                           mapping_iter_style=tcq.MappingIterStyle.KEYS) -> tcq.FieldValueGen:
        query_ctx = cls.get_query_context()
        rel_item_path = cls.get_rel_item_path()

        return query_ctx.yield_child_fields(rel_item_path=rel_item_path, field_name=field_name, labels=labels,
                                            mapping_iter_style=mapping_iter_style)


def gen_item_ctx(*, query_context: tcq.QueryContext, rel_item_path: pl.Path) -> ItemContext:
    class IC(ItemContext):
        @classmethod
        def get_query_context(cls):
            return query_context

        @classmethod
        def get_rel_item_path(cls):
            return rel_item_path

    return IC()
