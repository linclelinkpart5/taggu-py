import collections
import typing as typ
import os.path

import taggu.types as tt
import taggu.logging as tl
import taggu.exceptions as tex
import taggu.sourcer as ts


logger = tl.get_logger(__name__)

MetadataCache = typ.MutableMapping[str, typ.MutableMapping['MetaSource', tt.Metadata]]


# This returns a closure that, for a given root dir, fetches and caches metadata.
def generate_cacher(*, root_dir: str, item_filter: tt.ItemFilter=None):
    meta_cache: MetadataCache = {}

    # Expand user dir directives (~ and ~user), collapse dotted (. and ..) entries in path, and absolute-ize.
    root_dir = os.path.abspath(os.path.expanduser(root_dir))

    def co_norm(*, rel_sub_path: str) -> typ.Tuple[str, str]:
        abs_sub_path = os.path.normpath(os.path.join(root_dir, rel_sub_path))
        rel_sub_path = os.path.relpath(abs_sub_path, start=root_dir)

        if rel_sub_path.startswith(os.path.pardir):
            msg = f'Relative sub path is not anchored at root directory'
            logger.error(msg)
            raise tex.InvalidSubpath(msg)

        return rel_sub_path, abs_sub_path

    class LookerUpper:
        @classmethod
        def cache_sub_path(cls, *, rel_item_path: str, force: bool=False):
            rel_item_path, abs_item_path = co_norm(rel_sub_path=rel_item_path)

            if force:
                logger.info(f'Forced fetch of item "{rel_item_path}", defeating cache')

                # Remove any possible remnants of cache.
                meta_cache.pop(rel_item_path, None)

            if rel_item_path in meta_cache:
                logger.debug(f'Found item "{rel_item_path}" in cache, using cached results')

            else:
                logger.debug(f'Item "{rel_item_path}" not found in cache, processing meta files')
                for meta_path, meta_source in ts.MetaSource.meta_files_from_item(abs_item_path):
                    if os.path.isfile(meta_path):
                        logger.info(f'Found meta file "{meta_path}" of type {meta_source.name} '
                                    f'for item "{rel_item_path}", processing')

                        for ip, md, ms in ts.MetaSource.items_from_meta_file(meta_path=meta_path, item_filter=item_filter):
                            # TODO: Remove this once sourcer is converted back to using relative sub paths.
                            ip = os.path.relpath(ip, start=root_dir)
                            meta_cache.setdefault(ip, {})[ms] = md
                    else:
                        logger.debug(f'Meta file "{meta_path}" of type {meta_source.name} '
                                     f'does not exist for item "{rel_item_path}", skipping')

            if rel_item_path in meta_cache:
                for ms, md in meta_cache[rel_item_path].items():
                    yield rel_item_path, ms, md

        @classmethod
        def all_cache_entries(cls):
            return meta_cache

    return LookerUpper
