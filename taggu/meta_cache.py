"""A cache for meta files, along with the items that they provide metadata for."""

import typing as typ
import pathlib as pl
import abc

import taggu.types as tt
import taggu.contexts.discovery as tcd

MetadataCache = typ.MutableMapping[pl.Path, tt.Metadata]

MetaFileCache = typ.MutableMapping[pl.Path, MetadataCache]


class MetaCacher(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def get_discovery_context(cls) -> tcd.DiscoveryContext:
        pass

    @classmethod
    @abc.abstractmethod
    def get_cache(cls) -> MetaFileCache:
        pass

    @classmethod
    def cache_meta_files(cls, *, rel_meta_paths: typ.Iterable[pl.Path], force: bool=False):
        """Performs the work to ensure that the data contained in a meta file is present in the cache, if possible."""
        mfc: MetaFileCache = cls.get_cache()
        dis_ctx: tcd.DiscoveryContext = cls.get_discovery_context()

        for rel_meta_path in rel_meta_paths:
            # TODO: See if co-norming is needed here.
            if not force and rel_meta_path in mfc:
                continue

            # Remove any existing cached entries.
            cls.clear_meta_file(rel_meta_path=rel_meta_path)

            # TODO: Check which makes more sense in the case of an empty loop: an empty dict entry or no dict entry?
            for rel_item_path, metadata in dis_ctx.items_from_meta_file(rel_meta_path=rel_meta_path):
                if rel_meta_path not in mfc:
                    mfc[rel_meta_path] = {}

                mfc[rel_meta_path][rel_item_path] = metadata

    @classmethod
    def cache_meta_file(cls, *, rel_meta_path: pl.Path, force: bool=False):
        cls.cache_meta_files(rel_meta_paths=(rel_meta_path,), force=force)

    @classmethod
    def cache_item_files(cls, *, rel_item_paths: typ.Iterable[pl.Path], force: bool=False):
        dis_ctx: tcd.DiscoveryContext = cls.get_discovery_context()

        def func():
            for rel_item_path in rel_item_paths:
                # Find meta files that could provide meta info for this file.
                for rel_meta_path in dis_ctx.meta_files_from_item(rel_item_path=rel_item_path):
                    yield rel_meta_path

        # TODO: Add dedupe here.
        cls.cache_meta_files(rel_meta_paths=func(), force=force)

    @classmethod
    def cache_item_file(cls, *, rel_item_path: pl.Path, force: bool=False):
        cls.cache_item_files(rel_item_paths=(rel_item_path,), force=force)

    @classmethod
    def clear_meta_files(cls, *, rel_meta_paths: typ.Iterable[pl.Path]):
        mfc: MetaFileCache = cls.get_cache()
        for rel_meta_path in rel_meta_paths:
            mfc.pop(rel_meta_path, None)

    @classmethod
    def clear_meta_file(cls, *, rel_meta_path: pl.Path):
        cls.clear_meta_files(rel_meta_paths=(rel_meta_path,))

    @classmethod
    def clear_item_files(cls, *, rel_item_paths: typ.Iterable[pl.Path]):
        dis_ctx: tcd.DiscoveryContext = cls.get_discovery_context()

        def func():
            for rel_item_path in rel_item_paths:
                # Find meta files that could provide meta info for this file.
                for rel_meta_path in dis_ctx.meta_files_from_item(rel_item_path=rel_item_path):
                    yield rel_meta_path

        cls.clear_meta_files(rel_meta_paths=func())

    @classmethod
    def clear_item_file(cls, *, rel_item_path: pl.Path):
        cls.clear_item_files(rel_item_paths=(rel_item_path,))

    @classmethod
    def clear_all(cls):
        mfc: MetaFileCache = cls.get_cache()
        mfc.clear()

    @classmethod
    def get_meta_file(cls, *, rel_meta_path: pl.Path) -> MetadataCache:
        mfc: MetaFileCache = cls.get_cache()
        return mfc[rel_meta_path]

    @classmethod
    def get_item_file(cls, *, rel_item_path: pl.Path) -> tt.Metadata:
        dis_ctx: tcd.DiscoveryContext = cls.get_discovery_context()

        mc: MetadataCache = {}
        for rel_meta_path in dis_ctx.meta_files_from_item(rel_item_path=rel_item_path):
            if cls.contains_meta_file(rel_meta_path=rel_meta_path):
                mc: MetadataCache = cls.get_meta_file(rel_meta_path=rel_meta_path)

                if rel_item_path in mc:
                    return mc[rel_item_path]

        # Doing this so we can return a KeyError.
        return mc[rel_item_path]

    @classmethod
    def contains_meta_file(cls, *, rel_meta_path: pl.Path) -> bool:
        mfc: MetaFileCache = cls.get_cache()
        return rel_meta_path in mfc

    @classmethod
    def contains_item_file(cls, *, rel_item_path: pl.Path) -> bool:
        dis_ctx: tcd.DiscoveryContext = cls.get_discovery_context()

        for rel_meta_path in dis_ctx.meta_files_from_item(rel_item_path=rel_item_path):
            if cls.contains_meta_file(rel_meta_path=rel_meta_path):
                mc = cls.get_meta_file(rel_meta_path=rel_meta_path)

                if rel_item_path in mc:
                    return True

        return False


def gen_meta_cacher(*, discovery_context: tcd.DiscoveryContext) -> MetaCacher:
    meta_file_cache: MetaFileCache = {}

    class MC(MetaCacher):
        @classmethod
        def get_discovery_context(cls) -> tcd.DiscoveryContext:
            return discovery_context

        @classmethod
        def get_cache(cls) -> MetaFileCache:
            return meta_file_cache

    return MC()
