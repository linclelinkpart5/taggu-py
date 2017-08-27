import typing as typ
import os.path
import collections.abc
import pathlib as pl
import abc

import taggu.logging as tl
import taggu.exceptions as tex
import taggu.helpers as th
import taggu.types as tt


logger = tl.get_logger(__name__)

########################################################################################################################
#   Library context
########################################################################################################################


class LibraryContext(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def get_root_dir(cls) -> pl.Path:
        pass

    @classmethod
    @abc.abstractmethod
    def get_media_item_filter(cls) -> typ.Optional[tt.ItemFilter]:
        pass

    @classmethod
    @abc.abstractmethod
    def get_media_item_sort_key(cls) -> typ.Optional[tt.ItemSortKey]:
        pass

    @classmethod
    @abc.abstractmethod
    def get_item_meta_file_name(cls) -> str:
        pass

    @classmethod
    @abc.abstractmethod
    def get_self_meta_file_name(cls) -> str:
        pass

    @classmethod
    def co_norm(cls, *, rel_sub_path: pl.Path) -> typ.Tuple[pl.Path, pl.Path]:
        """Normalizes a relative sub path with respect to the enclosed root directory.
        Returns a tuple of the re-normalized relative sub path and the absolute sub path.
        """
        if rel_sub_path.is_absolute():
            msg = f'Sub path "{rel_sub_path}" is not a relative path'
            logger.error(msg)
            raise tex.AbsoluteSubpath(msg)

        root_dir = cls.get_root_dir()
        path = root_dir / rel_sub_path
        abs_sub_path = pl.Path(os.path.normpath(path))
        try:
            rel_sub_path = abs_sub_path.relative_to(root_dir)
        except ValueError:
            msg = f'Normalized absolute path "{abs_sub_path}" is not a sub path of root directory "{root_dir}"'
            logger.error(msg)
            raise tex.EscapingSubpath(msg)
        return rel_sub_path, abs_sub_path

    @classmethod
    def yield_contains_dir(cls, rel_sub_path: pl.Path) -> tt.PathGen:
        rel_sub_path, abs_sub_path = cls.co_norm(rel_sub_path=rel_sub_path)
        if abs_sub_path.is_dir():
            yield rel_sub_path

    @classmethod
    def yield_siblings_dir(cls, rel_sub_path: pl.Path) -> tt.PathGen:
        par_dir = rel_sub_path.parent
        if par_dir != rel_sub_path:
            yield par_dir

    @classmethod
    def fuzzy_name_lookup(cls, *, rel_sub_dir_path: pl.Path, prefix_item_name: str) -> str:
        rel_sub_dir_path, abs_sub_dir_path = cls.co_norm(rel_sub_path=rel_sub_dir_path)

        pattern = f'{prefix_item_name}*'
        results = tuple(abs_sub_dir_path.glob(pattern))

        if len(results) != 1:
            msg = (f'Incorrect number of matches for fuzzy lookup of "{prefix_item_name}" '
                   f'in directory "{rel_sub_dir_path}"; '
                   f'expected: 1, found: {len(results)}')
            logger.error(msg)
            raise tex.NonUniqueFuzzyFileLookup(msg)

        abs_found_path = results[0]
        return abs_found_path.name

    @classmethod
    def yield_item_paths_in_dir(cls, rel_sub_dir_path: pl.Path) -> tt.PathGen:
        rel_sub_dir_path, abs_sub_dir_path = cls.co_norm(rel_sub_path=rel_sub_dir_path)
        root_dir = cls.get_root_dir()

        logger.info(f'Looking for valid items in directory "{rel_sub_dir_path}"')

        media_item_filter = cls.get_media_item_filter()

        # Make sure the path is a directory.
        # If not, we yield nothing.
        if abs_sub_dir_path.is_dir():
            for abs_item_path in abs_sub_dir_path.iterdir():
                rel_item_path = abs_item_path.relative_to(root_dir)

                if media_item_filter is not None:
                    if media_item_filter(abs_item_path):
                        logger.debug(f'Item "{rel_item_path}" passed filter, marking as eligible')
                        yield abs_item_path
                    else:
                        logger.debug(f'Item "{rel_item_path}" failed filter, skipping')
                else:
                    logger.debug(f'Marking item "{rel_item_path}" as eligible')
                    yield abs_item_path

    @classmethod
    def item_names_in_dir(cls, rel_sub_dir_path: pl.Path) -> typ.AbstractSet[str]:
        """Finds item names in a given directory. These items must pass a filter in order to be selected."""
        return frozenset(p.name for p in cls.yield_item_paths_in_dir(rel_sub_dir_path=rel_sub_dir_path))

    @classmethod
    def sorted_item_names_in_dir(cls, rel_sub_dir_path: pl.Path) -> typ.Sequence[str]:
        media_item_sort_key: tt.ItemSortKey = cls.get_media_item_sort_key()

        results = tuple(p.name for p in sorted(cls.yield_item_paths_in_dir(rel_sub_dir_path=rel_sub_dir_path),
                                               key=media_item_sort_key))
        return results

    @classmethod
    def yield_item_meta_pairs(cls, yaml_data: typ.Any, rel_sub_dir_path: pl.Path) -> tt.PathMetadataPairGen:
        rel_sub_dir_path, abs_sub_dir_path = cls.co_norm(rel_sub_path=rel_sub_dir_path)

        # Find eligible item names in this directory.
        item_names: typ.AbstractSet[str] = cls.item_names_in_dir(rel_sub_dir_path=rel_sub_dir_path)

        # File metadata can be either a dictionary or sequence.
        if isinstance(yaml_data, collections.abc.Sequence):
            # Performing sequential application of metadata to interesting items.
            # Check that there are an equal number of metadata entries and interesting items.
            # TODO: Perform this check for mappings as well.
            if len(item_names) != len(yaml_data):
                logger.warning(f'Counts of items in directory and metadata blocks do not match; '
                               f'found {th.pluralize(len(item_names), "item")} '
                               f'and {th.pluralize(len(yaml_data), "metadata block")}')

            media_item_sort_key = cls.get_media_item_sort_key()
            sorted_item_names: typ.Sequence[str] = tuple(sorted(item_names, key=media_item_sort_key))

            for item_name, meta_block in zip(sorted_item_names, yaml_data):
                rel_item_path = rel_sub_dir_path / item_name
                yield rel_item_path, meta_block

        elif isinstance(yaml_data, collections.abc.Mapping):
            # Performing mapped application of metadata to interesting items.
            processed_item_names = set()
            for item_name, meta_block in yaml_data.items():
                # Test if item name from metadata has a valid name.
                if not th.is_valid_item_name(item_name):
                    logger.warning(f'Item name "{item_name}" is not valid, skipping')
                    continue

                item_name = cls.fuzzy_name_lookup(rel_sub_dir_path=rel_sub_dir_path, prefix_item_name=item_name)

                # Warn if name was already processed.
                if item_name in processed_item_names:
                    logger.warning(f'Item "{item_name}" was already processed for this directory, skipping')
                    continue

                # Test if the item name is in the list of discovered item names.
                if item_name not in item_names:
                    logger.warning(f'Item "{item_name}" not found in eligible item names for this directory, '
                                   f'skipping')
                    continue

                rel_item_path = rel_sub_dir_path / item_name
                yield rel_item_path, meta_block
                processed_item_names.add(item_name)

            remaining_item_names = item_names - processed_item_names
            if remaining_item_names:
                logger.warning(f'Found {th.pluralize(len(remaining_item_names), "eligible item")} '
                               f'remaining not referenced in metadata')

    @classmethod
    def yield_self_meta_pairs(cls, yaml_data: typ.Any, rel_sub_dir_path: pl.Path) -> tt.PathMetadataPairGen:
        # The target of the self metadata is the folder containing the self metadata file.
        if isinstance(yaml_data, collections.abc.Mapping):
            yield rel_sub_dir_path, yaml_data

    @classmethod
    def yield_meta_source_specs(cls) -> tt.MetaSourceSpecGen:
        """Yields the meta source specifications for where to obtain data.
        The order these specifications are emitted designates their priority;
        earlier is higher priority in the case of a conflict.
        """
        yield tt.MetaSourceSpec(meta_file_name=pl.Path(cls.get_self_meta_file_name()),
                                dir_getter=cls.yield_contains_dir,
                                multiplexer=cls.yield_self_meta_pairs)
        yield tt.MetaSourceSpec(meta_file_name=pl.Path(cls.get_item_meta_file_name()),
                                dir_getter=cls.yield_siblings_dir,
                                multiplexer=cls.yield_item_meta_pairs)


def gen_library_ctx(*,
                    root_dir: pl.Path,
                    media_item_filter: tt.ItemFilter=None,
                    media_item_sort_key: tt.ItemSortKey=None,
                    self_meta_file_name: typ.Union[str, pl.Path]='taggu_self.yml',
                    item_meta_file_name: typ.Union[str, pl.Path]='taggu_item.yml') -> LibraryContext:
    # Expand user dir directives (~ and ~user), collapse dotted (. and ..) entries in path, and absolute-ize.
    root_dir = pl.Path(os.path.abspath(os.path.expanduser(root_dir)))

    class LC(LibraryContext):
        @classmethod
        def get_root_dir(cls) -> pl.Path:
            return root_dir

        @classmethod
        def get_item_meta_file_name(cls) -> str:
            return item_meta_file_name

        @classmethod
        def get_self_meta_file_name(cls) -> str:
            return self_meta_file_name

        @classmethod
        def get_media_item_filter(cls) -> typ.Optional[tt.ItemFilter]:
            return media_item_filter

        @classmethod
        def get_media_item_sort_key(cls) -> typ.Optional[tt.ItemSortKey]:
            return media_item_sort_key

    return LC()
