import typing as typ
import pathlib as pl
import enum
import decimal
import datetime

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


class ScriptType(enum.Enum):
    INTEGER = int
    DECIMAL = decimal.Decimal
    STRING = str
    BOOLEAN = bool
    DATE = datetime.date
    TIME = datetime.time
    TIMESPAN = datetime.timedelta
    NONE = None


class ScriptFuncDef(typ.NamedTuple):
    name: str
    args: typ.Sequence[ScriptType]
    processor: typ.Callable
