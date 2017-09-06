import logging
import pathlib as pl
import tempfile
import unittest
import io
import itertools as it
import typing as typ

import yaml

import taggu.yaml.loader as tyl


def dquote(raw_str: str) -> str:
    return f'"{raw_str}"'


def squote(raw_str: str) -> str:
    return f"'{raw_str}'"


def json_seq(*raw_strs: str) -> str:
    return '[{}]'.format(', '.join(raw_strs))


def yaml_seq(*raw_strs: str, indent: int=0) -> str:
    prefix_template = (' ' * indent) + '- {}'
    return '\n'.join(prefix_template.format(s) for s in raw_strs)


PYTHON_STRINGS = frozenset(('test', '12345', 'True', '-3.14', '2017-01-01'))

BSTR_REPRS = PYTHON_STRINGS
NULL_REPRS = frozenset(('null', 'Null', 'NULL', '~'))


class TestYamlLoader(unittest.TestCase):
    def setUp(self):
        pass

    def test_yaml_loader(self):
        def yield_eps():
            for val in NULL_REPRS:
                # Bare values representing null are processed into Nones.
                yield val, None

            for val in BSTR_REPRS:
                # All non-null bare YAML values are parsed as strings,
                # even if the value could successfully represent a more specialized data type
                # (e.g. an integer or float).
                yield val, val

            for val in it.chain(NULL_REPRS, BSTR_REPRS):
                # Single and double quoted values are ALWAYS parsed as strings.
                yield dquote(val), val
                yield squote(val), val

            for val_combo in it.product(it.chain(NULL_REPRS, BSTR_REPRS), repeat=3):
                exp = [None if val in NULL_REPRS else val for val in val_combo]
                yield json_seq(*val_combo), exp
                yield yaml_seq(*val_combo), exp

                dquoted = tuple(dquote(val) for val in val_combo)

                yield json_seq(*dquoted), list(val_combo)
                yield yaml_seq(*dquoted), list(val_combo)

                squoted = tuple(squote(val) for val in val_combo)

                yield json_seq(*squoted), list(val_combo)
                yield yaml_seq(*squoted), list(val_combo)

            # TODO: Add tests for mappings.

        for yaml_str, expected in yield_eps():
            yaml_str_io = io.StringIO(yaml_str)
            produced = yaml.load(yaml_str_io, Loader=tyl.TagguLoader)

            self.assertEqual(expected, produced)

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
