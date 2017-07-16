"""Defines meta sources for taggu items.

Meta sources are what provide all of the metadata for items in the taggu hierarchy. They are able to tell what items
they provide direct metadata for, simply based on their metadata file system location and type.

In addition, this module also provides helpers to perform the reverse lookup: given an item path, find all metadata
file paths that *could* provide that item's immediate metadata.
"""

import os.path
import typing as typ
import pathlib as pl
import enum

import taggu.typehints as tth
import taggu.exceptions as tex

# For metadata file -> metadata for touched items, we need:
#   * library_root_dir
#   * rel_meta_dir (what directory the metadata file lives in, also used to find items touched by metadata file)
#   * meta_file_name (used to get the direct path to the metadata file, and to tell what meta source it is)
#   * yaml_reader (parses the metadata file into a YAML object)
#   * item_discovery (discovers items in a target directory, and filters based on some criteria, returning a set)
#   * multiplexer (converts YAML object into metadata blocks and associates metadata blocks to item paths)

# For target item -> provider metadata files, we need:
#   * library_root_dir
#   * rel_item_path (relative path of the item, and used as an anchor to find metadata files of each source type)
#   * meta_source_list (iterable of all meta source types, used to iterate and find metadata of each source type)
#   * location_flag (tells if the metadata file is inside or alongside the item)

# GIVEN: rel_item_path to a file; YIELDS: rel_meta_path to a ITEM meta file
# GIVEN: rel_item_path to a dir; YIELDS: rel_meta_path to a ITEM meta file, rel_meta_path to a SELF meta file
# GIVEN: rel_meta_path to a ITEM meta file; YIELDS: (rel_item_path, metadata) for each item that meta file refers to
# GIVEN: rel_meta_path to a SELF meta file; YIELDS: (rel_item_path, metadata) for each item that meta file refers to

ItemFilter = typ.Callable[[str], bool]


def co_normalize(root_dir: str, rel_sub_path: str) -> typ.Tuple[str, str, str]:
    # Verify that relative path is actually relative.
    if os.path.isabs(rel_sub_path):
        raise tex.AbsoluteSubpath()

    # Expand user dir directives (~ and ~user), collapse dotted (. and ..) entries in path, and absolute-ize.
    root_dir = os.path.abspath(os.path.expanduser(root_dir))

    # Re-calculate the desired relative sub path using the normalized root directory path.
    abs_sub_path = os.path.normpath(os.path.join(root_dir, rel_sub_path))
    rel_sub_path = os.path.relpath(abs_sub_path, start=root_dir)

    # If the relative path tries to escape the root, error.
    if rel_sub_path.startswith(os.path.pardir):
        raise tex.InvalidSubpath()

    return abs_sub_path, root_dir, rel_sub_path


def default_item_filter(abs_item_path) -> bool:
    _, ext = os.path.splitext(abs_item_path)
    return (os.path.isfile(abs_item_path) and ext == '.flac') or os.path.isdir(abs_item_path)


def item_discovery(*, abs_target_dir: str, item_filter: typ.Optional[ItemFilter]=None) -> typ.AbstractSet[str]:
    """Finds item paths for a given directory. These items must pass a filter in order to be selected."""
    def helper():
        with os.scandir(abs_target_dir) as it:
            for item in it:
                item_name = item.name
                item_path = os.path.join(abs_target_dir, item_name)

                if item_filter is not None:
                    if item_filter(item_path):
                        yield item_name
                    else:
                        pass
                else:
                    yield item_name

    return frozenset(helper())


def rel_item_meta_path_from_rel_item_path(*, root_dir: str, rel_item_path: str) -> typ.Generator[str, None, None]:
    pass


def rel_self_meta_path_from_rel_item_path(*, root_dir: str, rel_item_path: str) -> typ.Generator[str, None, None]:
    pass


class LocationFlag(enum.Enum):
    SIBLING = enum.auto()
    CONTAIN = enum.auto()


class MetaSourceSpec(typ.NamedTuple):
    file_name: str
    multiplexer: typ.Any
    location: LocationFlag
