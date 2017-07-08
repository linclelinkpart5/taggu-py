import typing as typ
import enum

GenericPath = str

LibraryRootDirPath = GenericPath
LibrarySubDirPath = GenericPath
FileName = GenericPath
ItemFileName = FileName
AbsItemFilePath = GenericPath
RelItemFilePath = GenericPath

SelfMetaFilePath = GenericPath
ItemMetaFilePath = GenericPath

MetadataKey = typ.NewType('MetadataKey', str)
MetadataValue = typ.Union[str, typ.Sequence[str]]

Metadata = typ.Mapping[MetadataKey, MetadataValue]
LayeredMetadata = Metadata

MetadataSequence = typ.Sequence[Metadata]
MetadataMapping = typ.Mapping[ItemFileName, Metadata]

SelfMetadata = Metadata
FileMetadata = typ.Union[MetadataMapping, MetadataSequence]

TargetItemFilter = typ.Callable[[AbsItemFilePath], bool]

MetadataPair = typ.Tuple[RelItemFilePath, Metadata]
MetadataPairIter = typ.Iterable[MetadataPair]

YamlProcessor = typ.Callable[[typ.Any, str, str], MetadataPairIter]


class SourceType(enum.Enum):
    # Lower entries override higher entries.
    ITEM = enum.auto()
    SELF = enum.auto()


class SourceSpec(typ.NamedTuple):
    type: SourceType
    file_name: FileName
    processor: YamlProcessor

MetadataCache = typ.MutableMapping[RelItemFilePath, typ.MutableMapping[SourceType, Metadata]]
