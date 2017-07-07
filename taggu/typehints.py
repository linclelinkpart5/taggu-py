import typing as typ

GenericPath = str

LibraryRootDirPath = GenericPath
LibrarySubDirPath = GenericPath
ItemFileName = GenericPath
ItemFilePath = GenericPath

SelfMetaFilePath = GenericPath
FileMetaFilePath = GenericPath

MetadataKey = typ.NewType('MetadataKey', str)
MetadataValue = typ.Union[str, typ.Sequence[str]]

MetadataMapping = typ.Mapping[MetadataKey, MetadataValue]

MetadataPair = typ.Tuple[ItemFilePath, MetadataMapping]

MetadataMappingSequence = typ.Sequence[MetadataMapping]
MetadataMappingMapping = typ.Mapping[ItemFilePath, MetadataMapping]

SelfMetadata = MetadataMapping
FileMetadata = typ.Union[MetadataMappingMapping, MetadataMappingSequence]

# Represents a priority hierarchy for a given item's metadata.
# The first element is its local metadata, second is its parent's, etc.

TargetItemFilter = typ.Callable[[ItemFilePath], bool]
