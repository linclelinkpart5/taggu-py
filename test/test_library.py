import unittest
import unittest.mock as mock
import itertools as it
import pathlib as pl
import tempfile

import taggu.library as tl


class TestLibrary(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root_dir = pl.Path(self.tmp_dir.name)

    def test_gen_library_ctx(self):
        lib_ctx = tl.gen_library_ctx(root_dir=self.root_dir)

    def tearDown(self):
        self.tmp_dir.cleanup()

if __name__ == '__main__':
    unittest.main()
