import pathlib as pl
import typing as typ
import io
import collections.abc

import yaml

import taggu.types as tt

ScriptTypes = tuple(m.value for m in tt.ScriptType)
ScriptType = typ.Union[ScriptTypes]

FunctionParam = typ.Union[ScriptType, 'FunctionMapping']
FunctionParamSequence = typ.Sequence[FunctionParam]

# A function call is a mapping of size 1, containing the name of the function as key and the parameters as the value.
FunctionMapping = typ.Mapping[str, FunctionParamSequence]

# An atom is either a literal, or a function call.
RuleAtom = typ.Union[ScriptType, FunctionMapping]

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


def unpack_function(func_mapping: FunctionMapping) -> typ.Optional[typ.Tuple[str, FunctionParamSequence]]:
    if len(func_mapping) != 1:
        return None

    func_name = tuple(func_mapping.keys())[0]
    func_params = func_mapping[func_name]

    return func_name, func_params


def evaluate(atom: RuleAtom) -> ScriptType:
    """Evaluates an atom as a function, or returns it unchanged."""
    if isinstance(atom, ScriptTypes):
        return atom
    elif isinstance(atom, collections.abc.Mapping):
        # Function call, evaluate the function.
        f_name, f_params = unpack_function(atom)

        # Need to evaluate each of the params.
        f_params = tuple(evaluate(param) for param in f_params)

        # Lookup function, and call it, using the converted params.


def convert_to_str(script_type: ScriptType) -> str:
    if script_type is None:
        return ''


def consolidate_atoms(rule_atom_sequence: RuleAtomSequence) -> str:
    buf = io.StringIO()
    for atom in rule_atom_sequence:
        evaluated_atom = evaluate(atom)
        converted_str: str = convert_to_str(evaluated_atom)
        buf.write(converted_str)
    return buf.getvalue()


def process_rules(rule_name_mapping: RuleNameMapping):
    pass
