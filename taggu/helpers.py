import typing as typ
import os.path

import taggu.logging as tl
import taggu.exceptions as tex

logger = tl.get_logger(__name__)


CoNormalizer = typ.Callable[[str], typ.Tuple[str, str]]


def gen_normed_root_dir_and_co_norm(*, root_dir: str) -> typ.Tuple[str, CoNormalizer]:
    # Expand user dir directives (~ and ~user), collapse dotted (. and ..) entries in path, and absolute-ize.
    root_dir = os.path.abspath(os.path.expanduser(root_dir))

    def co_norm(rel_sub_path: str) -> typ.Tuple[str, str]:
        abs_sub_path = os.path.normpath(os.path.join(root_dir, rel_sub_path))
        rel_sub_path = os.path.relpath(abs_sub_path, start=root_dir)

        if rel_sub_path.startswith(os.path.pardir):
            msg = f'Relative sub path is not anchored at root directory'
            logger.error(msg)
            raise tex.InvalidSubpath(msg)

        return rel_sub_path, abs_sub_path

    return root_dir, co_norm
