import abc
import pathlib as pl
import typing as typ

import taggu.contexts.library as tlib
import taggu.helpers as th
import taggu.logging as tl
import taggu.types as tt

logger = tl.get_logger(__name__)


########################################################################################################################
#   Discovery context
########################################################################################################################


class DiscoveryContext(abc.ABC):
    """Handles retrieving meta file and item paths, along with raw metadata retrieval."""

    @classmethod
    @abc.abstractmethod
    def get_library_context(cls) -> tlib.LibraryContext:
        """Returns the library context used in this discovery context."""
        pass

    @classmethod
    @abc.abstractmethod
    def meta_files_from_item(cls, rel_item_path: pl.Path) -> tt.PathGen:
        """Given an item path, yields all valid meta file paths that could provide direct metadata for that item.
        This also verifies that all of the resulting meta file paths exist.
        """
        pass

    @classmethod
    @abc.abstractmethod
    def items_from_meta_file(cls, rel_meta_path: pl.Path) -> tt.PathMetadataPairGen:
        """Given a meta file path, yields all item paths that this meta file provides metadata for, along with the
        metadata itself and the meta source type.
        """
        pass

    @classmethod
    def meta_files_from_items(cls, rel_item_paths: typ.Iterable[pl.Path]) -> tt.PathGen:
        for rel_item_path in rel_item_paths:
            yield from cls.meta_files_from_item(rel_item_path=rel_item_path)

    @classmethod
    def items_from_meta_files(cls, rel_meta_paths: typ.Iterable[pl.Path]) -> tt.PathMetadataPairGen:
        for rel_meta_path in rel_meta_paths:
            yield from cls.items_from_meta_file(rel_meta_path=rel_meta_path)


def gen_discovery_ctx(*, library_context: tlib.LibraryContext) -> DiscoveryContext:
    class DC(DiscoveryContext):
        @classmethod
        def get_library_context(cls) -> tlib.LibraryContext:
            return library_context

        @classmethod
        def meta_files_from_item(cls, rel_item_path: pl.Path) -> tt.PathGen:
            meta_specs: tt.MetaSourceSpecGen = library_context.yield_meta_source_specs()
            for meta_spec in meta_specs:
                meta_file_name: pl.Path = meta_spec.meta_file_name
                dir_getter: tt.DirGetter = meta_spec.dir_getter

                # This loop will normally execute either zero or one time.
                for rel_meta_dir in dir_getter(rel_item_path):
                    rel_meta_dir, abs_meta_dir = library_context.co_norm(rel_sub_path=rel_meta_dir)

                    rel_meta_path = rel_meta_dir / meta_file_name
                    abs_meta_path = abs_meta_dir / meta_file_name

                    if abs_meta_path.is_file():
                        logger.info(f'Found meta file "{rel_meta_path}" for item "{rel_item_path}"')
                        yield rel_meta_path
                    else:
                        logger.debug(f'Meta file "{rel_meta_path}" does not exist for item "{rel_item_path}"')

        @classmethod
        def items_from_meta_file(cls, rel_meta_path: pl.Path) -> tt.PathMetadataPairGen:
            """Given a meta file path, yields all item paths that this meta file provides metadata for, along with the
            metadata itself and the meta source type.
            """
            rel_meta_path, abs_meta_path = library_context.co_norm(rel_sub_path=rel_meta_path)

            # Check that the provided path exists and is a file.
            if not abs_meta_path.is_file():
                msg = f'Meta file "{rel_meta_path}" does not exist, or is not a file'
                logger.error(msg)
                return

            # Get the meta file name and containing dir path.
            rel_containing_dir = rel_meta_path.parent
            meta_file_name = pl.Path(rel_meta_path.name)

            # Find the meta source matching this meta file name.
            target_meta_spec: typ.Optional[tt.MetaSourceSpec] = None
            meta_specs: tt.MetaSourceSpecGen = library_context.yield_meta_source_specs()
            for meta_spec in meta_specs:
                meta_fn: pl.Path = meta_spec.meta_file_name
                if meta_file_name == meta_fn:
                    target_meta_spec = meta_spec
                    break

            # If the target meta source is not set, then the file name did not match that of any of the meta sources.
            if target_meta_spec is None:
                msg = f'Unknown meta file name "{meta_file_name}"'
                logger.error(msg)
                return

            # Open the meta file and read as YAML.
            # TODO: Add checking and logging for exceptions in here.
            yaml_data = th.read_yaml_file(abs_meta_path)

            multiplexer: tt.Multiplexer = target_meta_spec.multiplexer
            yield from multiplexer(yaml_data, rel_containing_dir)

    return DC()
