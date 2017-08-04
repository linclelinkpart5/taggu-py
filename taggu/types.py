import typing as typ
import pathlib as pl
import enum
import decimal
import datetime
import functools as ft
import collections.abc

ItemFilter = typ.Callable[[pl.Path], bool]

MetadataKey = typ.NewType('MetadataKey', str)
MetadataValue = typ.Union[str, typ.Sequence[str]]

Metadata = typ.Mapping[MetadataKey, MetadataValue]

DirGetter = typ.Callable[[pl.Path], typ.Iterable[pl.Path]]
Multiplexer = typ.Callable[[typ.Any, pl.Path, typ.Optional[ItemFilter]], typ.Iterable[typ.Tuple[pl.Path, Metadata]]]


class MetaSourceSpec(typ.NamedTuple):
    file_name: pl.Path
    dir_getter: DirGetter
    multiplexer: Multiplexer
