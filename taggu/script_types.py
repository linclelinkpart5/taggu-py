'''Defines types used in Taggu scripting.'''

import enum
import decimal
import datetime
import collections.abc
import typing as typ
import abc

import dateutil.parser as dup

import taggu.exceptions as tex


class ScriptTypes(enum.Enum):
    '''A set of types that are used in Taggu scripting.'''
    NULL = type(None)
    STRING = str
    INTEGER = int
    FLOAT = float
    DECIMAL = decimal.Decimal
    BOOLEAN = bool
    DATE = datetime.date
    TIME = datetime.time
    SEQUENCE = collections.abc.Sequence
    MAPPING = collections.abc.Mapping


class ScriptTypeException(tex.TagguException):
    """Base class for all Taggu script type exceptions."""
    pass


class TypeConversionException(tex.TagguException):
    """Raised when a script type is not able to be converted into another."""
    pass


class ScriptTypeContext(abc.ABC):
    """Manages types for Taggu scripting."""

    # @classmethod
    # @abc.abstractmethod
    # def get_join_function(cls) -> typ.Callable[[typ.Sequence], str]:
    #     """Returns a function used to stringify and join items in a sequence."""
    #     pass

    # @classmethod
    # @abc.abstractmethod
    # def get_mapping_flatten_function(cls) -> typ.Callable[[typ.Mapping], typ.Sequence]:
    #     """Returns a function used to extract a sequence of values from a mapping."""
    #     pass

    @classmethod
    def get_type_of(cls, obj) -> typ.Optional[ScriptTypes]:
        """For a given object, returns the Taggu script type it matches, or None if it does not
        match any Taggu scripting type."""
        for st in ScriptTypes:
            if isinstance(obj, st.value):
                return st

        return None

    @classmethod
    def convert(cls, obj: typ.Any, target_type: ScriptTypes):
        """For a given object and target script type, attempts to convert the object to the target
        script type. If it is not possible, raises an exception.

        Note that for sequences and mappings, this attempts to convert between the two, as opposed
        to wrapping one in the other."""

        # TODO: Catch and report other parsing or conversion exceptions.

        source_type: ScriptTypes = cls.get_type_of(obj)

        if source_type is None:
            raise TypeConversionException('Source object is not a recognized scripting type')

        if source_type is target_type:
            # Return a the same object.
            return obj

        elif target_type is ScriptTypes.NULL:
            # Result is always null.
            return None

        elif target_type is ScriptTypes.STRING:
            if source_type is ScriptTypes.SEQUENCE:
                # join_func = cls.get_join_function()

                str_items = []
                for item in obj:
                    item_conv = cls.convert(obj=item, target_type=ScriptTypes.STRING)
                    str_items.append(item_conv)
                return ', '.join(str_items)

            elif source_type is ScriptTypes.MAPPING:
                # map_flat_func = cls.get_mapping_flatten_function()

                # seq = map_flat_func(obj)
                seq = tuple(obj.keys())
                return cls.convert(seq, target_type=ScriptTypes.STRING)

            elif source_type is ScriptTypes.NULL:
                # Null becomes an empty string.
                return ''

            # Anything else can convert to string.
            return str(obj)

        elif target_type is ScriptTypes.INTEGER:
            if source_type in {ScriptTypes.STRING, ScriptTypes.FLOAT, ScriptTypes.DECIMAL,
                               ScriptTypes.BOOLEAN}:
                return int(obj)

        elif target_type is ScriptTypes.FLOAT:
            if source_type in {ScriptTypes.STRING, ScriptTypes.INTEGER, ScriptTypes.DECIMAL,
                               ScriptTypes.BOOLEAN}:
                return float(obj)

        elif target_type is ScriptTypes.DECIMAL:
            if source_type in {ScriptTypes.STRING, ScriptTypes.INTEGER, ScriptTypes.FLOAT,
                               ScriptTypes.BOOLEAN}:
                return decimal.Decimal(obj)

        elif target_type is ScriptTypes.BOOLEAN:
            if source_type is ScriptTypes.STRING:
                # TODO: Do some high-level coercion.
                return True

            if source_type in {ScriptTypes.INTEGER, ScriptTypes.FLOAT, ScriptTypes.DECIMAL,
                               ScriptTypes.SEQUENCE, ScriptTypes.MAPPING}:
                return bool(obj)

            # TODO: Add option to allow None -> False conversion.

        elif target_type is ScriptTypes.DATE:
            if source_type is ScriptTypes.STRING:
                return dup.parse(obj).date()

        elif target_type is ScriptTypes.TIME:
            if source_type is ScriptTypes.STRING:
                return dup.parse(obj).time()

        elif target_type is ScriptTypes.SEQUENCE:
            if source_type is ScriptTypes.MAPPING:
                # TODO: Allow for using keys, values, or pairs.
                # TODO: Better to reshape, or encapsulate?
                return tuple(obj.keys())

            return (obj,)

        elif target_type is ScriptTypes.MAPPING:
            if source_type is ScriptTypes.SEQUENCE:
                # Treat as a mapping with integer indices as keys.
                return dict(enumerate(obj))

            # A singleton mapping, with a 0 as the key.
            return {0: obj}

        raise TypeConversionException(f'Unable to convert object of type {source_type.name} '
                                      f'to type {target_type.name}')

    # @classmethod
    # def get_conversion(cls, source: ScriptTypes, target: ScriptTypes) -> typ.Optional[typ.Callable]:
    #     """For a given source and target script type, returns a method that performs the conversion,
    #     or None if the conversion is not possible.

    #     Note that for sequences and mappings, this attempts to convert between the two, as opposed
    #     to wrapping one in the other."""
    #     if source is target:
    #         # Return an identity conversion.
    #         return lambda x: x

    #     elif target is ScriptTypes.NULL:
    #         # Result is always null.
    #         return lambda _: None

    #     elif target is ScriptTypes.STRING:
    #         if source is ScriptTypes.SEQUENCE:
    #             # Create a function that recursively stringifies items in a sequence.
    #             def func(seq):
    #                 for item in seq:
    #                     item_type = cls.get_type_of(item)
    #                     item_conv = cls.get_conversion(source=item_type, target=ScriptTypes.STRING)

    #         elif source is ScriptTypes.NULL:
    #             # Null becomes an empty string.
    #             return lambda _: ''

    #         # Anything else can convert to string.
    #         return str

    #     elif target is ScriptTypes.INTEGER:
    #         if source in {ScriptTypes.STRING, ScriptTypes.FLOAT, ScriptTypes.DECIMAL,
    #                       ScriptTypes.BOOLEAN}:
    #             return int

    #     elif target is ScriptTypes.FLOAT:
    #         if source in {ScriptTypes.STRING, ScriptTypes.INTEGER, ScriptTypes.DECIMAL,
    #                       ScriptTypes.BOOLEAN}:
    #             return float

    #     elif target is ScriptTypes.DECIMAL:
    #         if source in {ScriptTypes.STRING, ScriptTypes.INTEGER, ScriptTypes.FLOAT,
    #                       ScriptTypes.BOOLEAN}:
    #             return decimal.Decimal

    #     elif target is ScriptTypes.BOOLEAN:
    #         if source is ScriptTypes.STRING:
    #             # TODO: Do some high-level coercion.
    #             return bool

    #         if source in {ScriptTypes.INTEGER, ScriptTypes.FLOAT, ScriptTypes.DECIMAL,
    #                       ScriptTypes.SEQUENCE, ScriptTypes.MAPPING}:
    #             return bool

    #         # TODO: Add option to allow None -> False conversion.

    #     elif target is ScriptTypes.DATE:
    #         if source is ScriptTypes.STRING:
    #             return lambda x: dup.parse(x).date()

    #     elif target is ScriptTypes.TIME:
    #         if source is ScriptTypes.STRING:
    #             return lambda x: dup.parse(x).time()

    #     elif target is ScriptTypes.SEQUENCE:
    #         if source is ScriptTypes.MAPPING:
    #             # TODO: Allow for using keys, values, or pairs.
    #             # TODO: Better to reshape, or encapsulate?
    #             return lambda x: tuple(x.keys())

    #         return lambda x: (x,)

    #     elif target is ScriptTypes.MAPPING:
    #         if source is ScriptTypes.SEQUENCE:
    #             # Treat as a mapping with integer indices as keys.
    #             return lambda x: dict(enumerate(x))

    #         # A singleton mapping, with a 0 as the key.
    #         return lambda x: {0: x}

    #     return None
