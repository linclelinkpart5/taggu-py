import typing as typ

ItemFilter = typ.Callable[[str], bool]

MetadataKey = typ.NewType('MetadataKey', str)
MetadataValue = typ.Union[str, typ.Sequence[str]]

Metadata = typ.Mapping[MetadataKey, MetadataValue]

DirGetter = typ.Callable[[str], typ.Iterable[str]]
Multiplexer = typ.Callable[[typ.Any, str, typ.Optional[ItemFilter]], typ.Iterable[typ.Tuple[str, Metadata]]]


class MetaSourceSpec(typ.NamedTuple):
    file_name: str
    dir_getter: DirGetter
    multiplexer: Multiplexer
