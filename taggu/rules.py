import pathlib as pl
import typing as typ
import io

import yaml

FunctionParam = typ.Union[typ.Any, 'FunctionMapping']
FunctionParamSequence = typ.Sequence[FunctionParam]

FunctionMapping = typ.Mapping[str, FunctionParamSequence]

# An atom is either a string literal, or a function call.
RuleAtom = typ.Union[str, FunctionMapping]

# Each atom is evaluated, stringified, and then concatenated together to form the final string value of the rule.
RuleAtomSequence = typ.Sequence[RuleAtom]

# A rule file contains mappings from field names to the atoms that comprise the value of the field name.
RuleNameMapping = typ.Mapping[str, RuleAtomSequence]


class RuleDef(typ.NamedTuple):
    field_name: str
    atom_seq: RuleAtomSequence


def read_rules_file(rules_yaml_file_path: pl.Path) -> RuleNameMapping:
    with rules_yaml_file_path.open() as f:
        return yaml.load(f)


def consolidate_atoms(rule_atom_sequence: RuleAtomSequence) -> str:
    buf = io.StringIO()
    for atom in rule_atom_sequence:
        buf.write(str(atom))
    return buf.getvalue()


def process_rules(rule_name_mapping: RuleNameMapping):
    pass
