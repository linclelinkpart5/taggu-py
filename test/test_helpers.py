import unittest

import taggu.helpers as th


class TestHelpers(unittest.TestCase):
    def test_count_plural(self):
        s = th.pluralize(n=0, single='item')
        self.assertEqual(s, '0 items')

        s = th.pluralize(n=1, single='item')
        self.assertEqual(s, '1 item')

        s = th.pluralize(n=-1, single='item')
        self.assertEqual(s, '-1 item')

        s = th.pluralize(n=2, single='item')
        self.assertEqual(s, '2 items')

        s = th.pluralize(n=-2, single='item')
        self.assertEqual(s, '-2 items')

        s = th.pluralize(n=0, single='entry', plural='entries')
        self.assertEqual(s, '0 entries')

        s = th.pluralize(n=1, single='entry', plural='entries')
        self.assertEqual(s, '1 entry')

        s = th.pluralize(n=-1, single='entry', plural='entries')
        self.assertEqual(s, '-1 entry')

        s = th.pluralize(n=2, single='entry', plural='entries')
        self.assertEqual(s, '2 entries')

        s = th.pluralize(n=-2, single='entry', plural='entries')
        self.assertEqual(s, '-2 entries')
