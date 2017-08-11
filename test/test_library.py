import typing as typ
import unittest
import itertools as it
import pathlib as pl
import tempfile
import os.path
import collections

import taggu.library as tl

A_LABEL = 'ALBUM'
D_LABEL = 'DISC'
T_LABEL = 'TRACK'
S_LABEL = 'SUBTRACK'
EXT = '.flac'

HIERARCHY = (A_LABEL, D_LABEL, T_LABEL, S_LABEL)


def item_filter(abs_item_path: pl.Path) -> bool:
    ext = abs_item_path.suffix
    return (abs_item_path.is_file() and ext == EXT) or abs_item_path.is_dir()


class TestLibrary(unittest.TestCase):
    def setUp(self):
        self.root_dir_obj = tempfile.TemporaryDirectory()

        self.root_dir_pl = pl.Path(self.root_dir_obj.name)

        def deep_touch(path: pl.Path):
            path = self.root_dir_pl / path
            pl.Path(path.parent).mkdir(parents=True, exist_ok=True)
            path.touch(exist_ok=True)

        def nums() -> typ.Generator[typ.Sequence[typ.Optional[int]], None, None]:
            # Well-behaved album, disc, and track hierarchy.
            yield (1, 1, 1)
            yield (1, 1, 2)
            yield (1, 1, 3)
            yield (1, 2, 1)
            yield (1, 2, 2)
            yield (1, 2, 3)

            # Album with a disc and tracks, and loose tracks not on a disc.
            yield (2, 1, 1)
            yield (2, 1, 2)
            yield (2, 1, 3)
            yield (2, None, 1)
            yield (2, None, 2)
            yield (2, None, 3)

            # Album with discs and tracks, and subtracks on one disc.
            yield (3, 1, 1)
            yield (3, 1, 2)
            yield (3, 1, 3)
            yield (3, 2, 1, 1)
            yield (3, 2, 1, 2)
            yield (3, 2, 2, 1)
            yield (3, 2, 2, 2)
            yield (3, 2, 3)

            # Album that consists of one file.
            yield (4,)

        for num_seq in nums():
            p = pl.Path()

            for lbl, num in zip(HIERARCHY, num_seq):
                if num is None:
                    continue

                stub = f'{lbl}{num:02}'
                p = p / stub

            p = p.with_suffix(f'{EXT}')
            deep_touch(p)

        # import ipdb; ipdb.set_trace()

    def test_gen_library_ctx(self):
        root_dir_pl = self.root_dir_pl
        dummy_dir_pl = root_dir_pl / 'dummy' / '..'
        lib_ctx = tl.gen_library_ctx(root_dir=dummy_dir_pl, media_item_filter=item_filter)

        self.assertEqual(root_dir_pl, lib_ctx.get_root_dir())
        self.assertIs(item_filter, lib_ctx.get_media_item_filter())

    def tearDown(self):
        self.root_dir_obj.cleanup()

if __name__ == '__main__':
    unittest.main()
