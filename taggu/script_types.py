'''Defines types used in Taggu scripting.'''

import enum
import decimal
import datetime
import collections.abc
import typing as typ


class ScriptTypes(enum.Enum):
    '''A set of types that are used in Taggu scripting.'''
    NULL = None
    STRING = str
    INTEGER = int
    FLOAT = float
    DECIMAL = decimal.Decimal
    BOOLEAN = bool
    DATE = datetime.date
    TIME = datetime.time
    SEQUENCE = collections.abc.Sequence
    MAPPING = collections.abc.Mapping

SCALARS = frozenset((ScriptTypes.STRING, ScriptTypes.INTEGER, ScriptTypes.FLOAT,
                     ScriptTypes.DECIMAL, ScriptTypes.BOOLEAN, ScriptTypes.DATE, ScriptTypes.TIME))
CONTAINERS = frozenset((ScriptTypes.SEQUENCE, ScriptTypes.MAPPING))


# class ConversionMethod(enum.Enum):
#     '''Represents the method of conversion between a given pair of Taggu scripting types.'''
#     NOT_POSSIBLE = 0
#     EXPLICIT = 1
#     IMPLICIT = 2


def get_conversion(source: ScriptTypes, target: ScriptTypes) -> typ.Optional[typ.Callable]:
    '''For a given source and target script type, returns a method that performs the conversion,
    or None if the convserion is not possible.'''
    if target is ScriptTypes.NULL:
        # Result is always null.
        return lambda _: None

    elif target is ScriptTypes.STRING:
        # Anything can convert to string.
        # TODO: Finer control for sequences and mappings.
        return str

    elif target is ScriptTypes.INTEGER:
        if source in {ScriptTypes.STRING, ScriptTypes.INTEGER, ScriptTypes.FLOAT,
                      ScriptTypes.DECIMAL, ScriptTypes.BOOLEAN}:
            return int

    elif target is ScriptTypes.FLOAT:
        if source in {ScriptTypes.STRING, ScriptTypes.INTEGER, ScriptTypes.FLOAT,
                      ScriptTypes.DECIMAL, ScriptTypes.BOOLEAN}:
            return float

    elif target is ScriptTypes.DECIMAL:
        if source in {ScriptTypes.STRING, ScriptTypes.INTEGER, ScriptTypes.FLOAT,
                      ScriptTypes.DECIMAL, ScriptTypes.BOOLEAN}:
            return decimal.Decimal

    elif target is ScriptTypes.BOOLEAN:
        if source is ScriptTypes.STRING:
            # TODO: Do some high-level coercion.
            return bool

        if source in {ScriptTypes.INTEGER, ScriptTypes.FLOAT, ScriptTypes.DECIMAL,
                      ScriptTypes.BOOLEAN, ScriptTypes.SEQUENCE, ScriptTypes.MAPPING}:
            return bool

        # TODO: Add option to allow None -> False conversion.

    if source in SCALARS and target is ScriptTypes.SEQUENCE:
        return lambda x: (x,), False

    if source is ScriptTypes.SEQUENCE and target is ScriptTypes.MAPPING:

        return lambda x: (x,), False

    return None
