import abc
import pathlib as pl
import typing as typ
import collections.abc
import itertools as it

import taggu.contexts.library as tlib
import taggu.contexts.discovery as td
import taggu.contexts.query as tq
import taggu.helpers as th
import taggu.logging as tl
import taggu.types as tt

logger = tl.get_logger(__name__)


class ItemContext(abc.ABC):
    """Handles retrieving and caching individual fields from metadata for a specific constant item."""

    @classmethod
    @abc.abstractmethod
    def yield_field(cls, *, field_name: str, labels: typ.Optional[tq.LabelContainer]) -> tq.FieldValueGen:
        pass
