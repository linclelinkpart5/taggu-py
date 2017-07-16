import typing as typ


MetadataKey = typ.NewType('MetadataKey', str)
MetadataValue = typ.Union[str, typ.Sequence[str]]

Metadata = typ.Mapping[MetadataKey, MetadataValue]
LayeredMetadata = Metadata

MetadataSequence = typ.Sequence[Metadata]
MetadataMapping = typ.Mapping[str, Metadata]

SelfMetadata = Metadata
FileMetadata = typ.Union[MetadataMapping, MetadataSequence]

TargetItemFilter = typ.Callable[[str], bool]

MetadataPair = typ.Tuple[str, Metadata]
MetadataPairIter = typ.Iterable[MetadataPair]

Multiplexer = typ.Callable[[typ.Any, str, str], MetadataPairIter]

MetaFileFinder = typ.Callable[[str, str, str], typ.Iterable[str]]


class MetaSourceSpec(typ.NamedTuple):
    file_name: str
    multiplexer: Multiplexer
    finder: MetaFileFinder


import enum
import os.path


class SourceLoc(enum.Enum):
    SELF = 'taggu_self.yml'
    ITEM = 'taggu_item.yml'


def co_normalize(*, root_dir: str, rel_sub_path: str) -> typ.Tuple[str, str, str]:
    # Expand user dir directives (~ and ~user) and collapse dotted (. and ..) entries in path.
    root_dir = os.path.abspath(os.path.expanduser(root_dir))

    # Re-calculate the desired relative sub path using the normalized root directory path.
    abs_sub_path = os.path.normpath(os.path.join(root_dir, rel_sub_path))
    rel_sub_path = os.path.relpath(abs_sub_path, start=root_dir)

    return abs_sub_path, root_dir, rel_sub_path


def parent_dir(rel_sub_path: str) -> typ.Tuple[str, str]:
    rel_sub_path = os.path.normpath(rel_sub_path)
    return os.path.normpath(os.path.dirname(rel_sub_path)), rel_sub_path


def norm_join(path_a: str, path_b: str) -> str:
    return os.path.normpath(os.path.join(path_a, path_b))


class NewMetaSourceSpec(typ.NamedTuple):
    file_name: str
    location: SourceLoc

    def in_dir(self, root_dir: str, rel_dir_path: str, validate: bool=True) -> typ.Generator[str, None, None]:
        abs_dir_path, root_dir, rel_dir_path = co_normalize(root_dir=root_dir, rel_sub_path=rel_dir_path)

        if validate and not os.path.isdir(abs_dir_path):
            return

        rel_meta_path = norm_join(rel_dir_path, self.file_name)

        if validate and not os.path.exists(norm_join(root_dir, rel_meta_path)):
            return

        yield rel_meta_path

    def from_item_path(self, root_dir: str, rel_item_path: str, validate: bool=True) -> typ.Generator[str, None, None]:
        abs_item_path, root_dir, rel_item_path = co_normalize(root_dir=root_dir, rel_sub_path=rel_item_path)

        meta_file_name = self.file_name

        rel_meta_path = None

        if self.location.ITEM:
            # Try to get dir name of rel item path.
            rel_item_dir, rel_item_path = parent_dir(rel_item_path)

            # Check if the dirname operation returned the same result, after normalization.
            # If so, then the rel item path is at the root dir, so just return without yielding.
            if rel_item_dir != rel_item_path:
                rel_meta_path = norm_join(rel_item_dir, meta_file_name)

        elif self.location.SELF:
            # Check if abs item path is a directory.
            if os.path.isdir(abs_item_path):
                rel_meta_path = os.path.normpath(os.path.join(rel_item_path, meta_file_name))

        if rel_meta_path is None or (validate and not os.path.exists(norm_join(root_dir, rel_meta_path))):
            return

        yield rel_meta_path

    def process_from_sub_dir(self, root_dir: str, rel_sub_dir: str):
        pass

    def process_from_item_path(self, root_dir: str, rel_sub_path: str):
        # This just calls basedir and runs process_from_sub_dir on it.
        pass

    def process_all(self, root_dir: str):
        pass


# TODO: GIVEN A REL PATH TO A META FILE, FIND OUT WHAT ITEM(S) IT PROVIDES METADATA FOR.
