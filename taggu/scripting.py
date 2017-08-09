import typing as typ
import decimal
import datetime
import enum
import collections.abc
import numbers as num

import taggu.helpers as th

# T = typ.TypeVar('T')
#
#
# class TagguTypeDef(typ.NamedTuple):
#     name: str
#     type: typ.Type[T]
#     to_str: typ.Callable[[T], str]
#     from_str: typ.Callable[[str], T]
#     # errors: typ.Sequence[typ.Type[Exception]]
#
#
# def str_to_bool(s: str) -> bool:
#     yeses = {'yes', 'true', 'y', '1'}
#
#     return s.casefold() in yeses
#
#
# class BaseTagguType(enum.Enum):
#     STRING = str
#     INTEGER = int
#     DECIMAL = decimal.Decimal
#     NUMBER = num.Real
#     SEQUENCE = collections.abc.Sequence
#     BOOLEAN = bool
#     DATE = datetime.date
#     NONE = None
#
# TagguType = enum.Enum('TagguType', (*((e.name, e.value) for e in BaseTagguType),
#                                     ('ANY', tuple(e.value for e in BaseTagguType))
#                                     )
#                       )

Field = str
Label = typ.Optional[str]
String = str
Value = typ.Optional[String]
StringSeq = typ.Sequence[String]
ValueSeq = typ.Sequence[Value]

########################################################################################################################
#   List manipulation
########################################################################################################################


def seq(*vals: Value) -> typ.Sequence[Value]:
    return tuple(vals)


def elem(lst: ValueSeq, idx: int) -> Value:
    try:
        return lst[idx]
    except IndexError:
        return None


def sort_(lst: ValueSeq) -> ValueSeq:
    return tuple(sorted(lst))


# def sortn(lst: typ.Sequence[str]) -> typ.Sequence[str]:
#     try:
#         return tuple(sorted(lst, key=int))
#     except ValueError:
#         return sort_(lst=lst)


def uniq(lst: ValueSeq) -> ValueSeq:
    return tuple(th.dedupe(lst))

########################################################################################################################
#   Metadata access
########################################################################################################################


def lookup(field_name: Field, label: Label=None) -> ValueSeq:
    # TODO: Need a context containing the path to an item!
    pass


def lookself(field_name: Field, label: Label=None) -> ValueSeq:
    # TODO: Need a context containing the path to an item!
    pass


def lookdown(field_name: Field, label: Label=None) -> ValueSeq:
    # TODO: Need a context containing the path to an item!
    pass

########################################################################################################################
#   Arithmetic
########################################################################################################################


# def add(a: TagguType.NUMBER.value, b: TagguType.NUMBER.value) -> TagguType.NUMBER.value:
#     return a + b
#
#
# def sub(a: TagguType.NUMBER.value, b: TagguType.NUMBER.value) -> TagguType.NUMBER.value:
#     return a - b
#
#
# def mul(a: TagguType.NUMBER.value, b: TagguType.NUMBER.value) -> TagguType.NUMBER.value:
#     return a * b
#
#
# def div(a: TagguType.NUMBER.value, b: TagguType.NUMBER.value) -> TagguType.NUMBER.value:
#     return a / b
#
#
# def mod(a: TagguType.NUMBER.value, b: TagguType.NUMBER.value) -> TagguType.NUMBER.value:
#     return a % b
#
#
# def min_(a: TagguType.NUMBER.value, b: TagguType.NUMBER.value) -> TagguType.NUMBER.value:
#     return min(a, b)
#
#
# def max_(a: TagguType.NUMBER.value, b: TagguType.NUMBER.value) -> TagguType.NUMBER.value:
#     return max(a, b)
#
#
# def neg(a: TagguType.NUMBER.value) -> TagguType.NUMBER.value:
#     return -a

########################################################################################################################
#   Logical comparisons
########################################################################################################################


# def eq(a: TagguType.NUMBER.value, b: TagguType.NUMBER.value) -> TagguType.BOOLEAN.value:
#     return a == b
#
#
# def ne(a: TagguType.NUMBER.value, b: TagguType.NUMBER.value) -> TagguType.BOOLEAN.value:
#     return a != b
#
#
# def gt(a: TagguType.NUMBER.value, b: TagguType.NUMBER.value) -> TagguType.BOOLEAN.value:
#     return a > b
#
#
# def lt(a: TagguType.NUMBER.value, b: TagguType.NUMBER.value) -> TagguType.BOOLEAN.value:
#     return a < b
#
#
# def ge(a: TagguType.NUMBER.value, b: TagguType.NUMBER.value) -> TagguType.BOOLEAN.value:
#     return a >= b
#
#
# def le(a: TagguType.NUMBER.value, b: TagguType.NUMBER.value) -> TagguType.BOOLEAN.value:
#     return a <= b

########################################################################################################################
#   Boolean operations
########################################################################################################################


# def and_(*pred: TagguType.BOOLEAN.value) -> TagguType.BOOLEAN.value:
#     return all(pred)
#
#
# def or_(*pred: TagguType.BOOLEAN.value) -> TagguType.BOOLEAN.value:
#     return any(pred)
#
#
# def xor_(*pred: TagguType.BOOLEAN.value) -> TagguType.BOOLEAN.value:
#     res = False
#     for p in pred:
#         res ^= p
#     return res
#
#
# def not_(pred: TagguType.BOOLEAN.value) -> TagguType.BOOLEAN.value:
#     return not pred

########################################################################################################################
#   Control flow
########################################################################################################################


def ifelse(cond: Value, then_val: Value, else_val: Value) -> Value:
    if cond:
        return then_val
    return else_val


def if_(cond: Value, then_val: Value) -> Value:
    return ifelse(cond=cond, then_val=then_val, else_val=None)


def default(val: Value, else_val: Value) -> Value:
    if bool(val):
        return val
    return else_val


def first(*vals: Value) -> Value:
    for val in vals:
        if bool(val):
            return val

    return None


def guard(*vals: Value) -> Value:
    ret = None
    for val in vals:
        if bool(val):
            if ret is None:
                ret = ''
            ret += str(val)
        else:
            return None
    return ret

########################################################################################################################
#   String manipulation
########################################################################################################################


# def length(string: TagguType.STRING.value) -> TagguType.INTEGER.value:
#     return len(string)


def join(lst: ValueSeq, sep: String) -> String:
    return sep.join(lst)


def joinl(lst: ValueSeq, sep: String, last_sep: String) -> String:
    f_lst = lst[:-1]
    l_elem = lst[-1:]

    f_join = [sep.join(f_lst)]
    f_join.extend(l_elem)

    return last_sep.join(f_join)


def joinlt(lst: ValueSeq, sep: String, last_sep: String, two_sep: String) -> String:
    if len(lst) == 2:
        return two_sep.join(lst)

    return joinl(lst=lst, sep=sep, last_sep=last_sep)

########################################################################################################################
#   Conversions from string
########################################################################################################################


# def int_(string: TagguType.STRING.value) -> TagguType.INTEGER.value:
#     try:
#         return int(string)
#     except ValueError:
#         return int()
#
#
# def deci(string: TagguType.STRING.value) -> TagguType.DECIMAL.value:
#     try:
#         return decimal.Decimal(string)
#     except decimal.DecimalException:
#         return decimal.Decimal()
#
#
# def bool_(string: TagguType.STRING.value) -> TagguType.BOOLEAN.value:
#     T_VALS = frozenset(('y', 'yes', 't', 'true', 'on', '1'))
#     F_VALS = frozenset(('n', 'no', 'f', 'false', 'off', '0'))
#     cf_str = string.casefold()
#     if cf_str in T_VALS:
#         return True
#     else:
#         return False
#
#
# def date(string: TagguType.STRING.value) -> TagguType.DATE.value:
#     try:
#         return datetime.datetime.strptime(string, '%Y-%m-%d').date()
#     except ValueError:
#         return datetime.date.min


########################################################################################################################
#   Variables
########################################################################################################################


# def put(name: TagguType.STRING.value, val: TagguType.ANY.value) -> TagguType.ANY.value:
#     # TODO: Need a context containing instance variables!
#     pass
#
#
# def puts(name: TagguType.STRING.value, val: TagguType.ANY.value) -> TagguType.NONE.value:
#     # TODO: Need a context containing instance variables!
#     pass
#
#
# def get(name: TagguType.STRING.value) -> TagguType.ANY.value:
#     # TODO: Need a context containing instance variables!
#     pass

########################################################################################################################
#   Utility & helper methods
########################################################################################################################


# def valid(val: TagguType.ANY.value) -> TagguType.BOOLEAN.value:
#     return bool(val)


def index() -> int:
    # TODO: Need a context containing the path to an item!
    pass


def total() -> int:
    # TODO: Need a context containing the path to an item!
    pass


def nil(*_) -> None:
    pass
