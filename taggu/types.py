import typing as typ
import pathlib as pl

ItemFilter = typ.Callable[[pl.Path], bool]
ItemSortKey = typ.Callable[[pl.Path], typ.Any]

MetadataKey = typ.NewType('MetadataKey', str)
FieldValue = typ.Optional[str]
MetadataValue = typ.Union[FieldValue, typ.Sequence[FieldValue]]

Metadata = typ.Mapping[MetadataKey, MetadataValue]

DirGetter = typ.Callable[[pl.Path], 'PathGen']
Multiplexer = typ.Callable[[typ.Any, pl.Path], 'PathMetadataPairGen']

# MetaSourceSpec = typ.Tuple[pl.Path, DirGetter, Multiplexer]


class MetaSourceSpec(typ.NamedTuple):
    meta_file_name: pl.Path
    dir_getter: DirGetter
    multiplexer: Multiplexer

MetaSourceSpecGen = typ.Generator[MetaSourceSpec, None, None]

MetadataResolver = typ.Callable[[pl.Path, str], typ.Generator[str, None, None]]

PathGen = typ.Generator[pl.Path, None, None]

PathMetadataPair = typ.Tuple[pl.Path, Metadata]
PathMetadataPairGen = typ.Generator[PathMetadataPair, None, None]
