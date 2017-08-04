import typing as typ
import decimal
import datetime
import enum
import collections.abc
import numbers as num

import taggu.helpers as th


class BaseTagguType(enum.Enum):
    STRING = str
    INTEGER = int
    DECIMAL = decimal.Decimal
    NUMBER = num.Real
    SEQUENCE = collections.abc.Sequence
    BOOLEAN = bool
    DATE = datetime.date
    NONE = None

TagguType = enum.Enum('TagguType', (*((e.name, e.value) for e in BaseTagguType),
                                    ('ANY', tuple(e.value for e in BaseTagguType))
                                    )
                      )

########################################################################################################################
#   List manipulation
########################################################################################################################


def list_(*scalars: TagguType.ANY.value) -> TagguType.SEQUENCE.value:
    return tuple(scalars)


def count(lst: TagguType.SEQUENCE.value) -> TagguType.INTEGER.value:
    return len(lst)


def elem(lst: TagguType.SEQUENCE.value, idx: TagguType.INTEGER.value) -> TagguType.ANY.value:
    try:
        return lst[idx]
    except IndexError:
        return None


def sort_(lst: TagguType.SEQUENCE.value) -> TagguType.SEQUENCE.value:
    return tuple(sorted(lst, key=TagguType.STRING.value))


def sortn(lst: TagguType.SEQUENCE.value) -> TagguType.SEQUENCE.value:
    try:
        return tuple(sorted(lst, key=TagguType.INTEGER.value))
    except ValueError:
        return sort_(lst=lst)


def uniq(lst: TagguType.SEQUENCE.value) -> TagguType.SEQUENCE.value:
    return tuple(th.dedupe(lst))

########################################################################################################################
#   Metadata access
########################################################################################################################


def lookup(field_name: TagguType.STRING.value, type: TagguType.STRING.value='parent', label: TagguType.STRING.value=None) -> TagguType.SEQUENCE.value:
    # TODO: Need a context containing the path to an item!
    pass

########################################################################################################################
#   Arithmetic
########################################################################################################################


def add(a: TagguType.NUMBER.value, b: TagguType.NUMBER.value) -> TagguType.NUMBER.value:
    return a + b


def sub(a: TagguType.NUMBER.value, b: TagguType.NUMBER.value) -> TagguType.NUMBER.value:
    return a - b


def mul(a: TagguType.NUMBER.value, b: TagguType.NUMBER.value) -> TagguType.NUMBER.value:
    return a * b


def div(a: TagguType.NUMBER.value, b: TagguType.NUMBER.value) -> TagguType.NUMBER.value:
    return a / b


def mod(a: TagguType.NUMBER.value, b: TagguType.NUMBER.value) -> TagguType.NUMBER.value:
    return a % b


def min_(a: TagguType.NUMBER.value, b: TagguType.NUMBER.value) -> TagguType.NUMBER.value:
    return min(a, b)


def max_(a: TagguType.NUMBER.value, b: TagguType.NUMBER.value) -> TagguType.NUMBER.value:
    return max(a, b)


def neg(a: TagguType.NUMBER.value) -> TagguType.NUMBER.value:
    return -a

########################################################################################################################
#   Logical comparisons
########################################################################################################################


def eq(a: TagguType.NUMBER.value, b: TagguType.NUMBER.value) -> TagguType.BOOLEAN.value:
    return a == b


def ne(a: TagguType.NUMBER.value, b: TagguType.NUMBER.value) -> TagguType.BOOLEAN.value:
    return a != b


def gt(a: TagguType.NUMBER.value, b: TagguType.NUMBER.value) -> TagguType.BOOLEAN.value:
    return a > b


def lt(a: TagguType.NUMBER.value, b: TagguType.NUMBER.value) -> TagguType.BOOLEAN.value:
    return a < b


def ge(a: TagguType.NUMBER.value, b: TagguType.NUMBER.value) -> TagguType.BOOLEAN.value:
    return a >= b


def le(a: TagguType.NUMBER.value, b: TagguType.NUMBER.value) -> TagguType.BOOLEAN.value:
    return a <= b

########################################################################################################################
#   Boolean operations
########################################################################################################################


def and_(*pred: TagguType.BOOLEAN.value) -> TagguType.BOOLEAN.value:
    return all(pred)


def or_(*pred: TagguType.BOOLEAN.value) -> TagguType.BOOLEAN.value:
    return any(pred)


def xor_(*pred: TagguType.BOOLEAN.value) -> TagguType.BOOLEAN.value:
    res = False
    for p in pred:
        res ^= p
    return res


def not_(pred: TagguType.BOOLEAN.value) -> TagguType.BOOLEAN.value:
    return not pred

########################################################################################################################
#   Control flow
########################################################################################################################


def if_(cond: TagguType.BOOLEAN.value, then_val: TagguType.ANY.value) -> TagguType.ANY.value:
    if cond:
        return then_val
    return None


def ifelse(cond: TagguType.BOOLEAN.value, then_val: TagguType.ANY.value, else_val: TagguType.ANY.value) -> TagguType.ANY.value:
    if cond:
        return then_val
    return else_val


def default(val: TagguType.ANY.value, else_val: TagguType.ANY.value) -> TagguType.ANY.value:
    if bool(val):
        return val
    return else_val


def first(*vals: TagguType.ANY.value) -> TagguType.ANY.value:
    for val in vals:
        if bool(val):
            return val

    return None


def guard(*vals: TagguType.ANY.value) -> TagguType.STRING.value:
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


def length(string: TagguType.STRING.value) -> TagguType.INTEGER.value:
    return len(string)


def join(lst: TagguType.SEQUENCE.value, sep: TagguType.STRING.value) -> TagguType.STRING.value:
    return sep.join(lst)


def joinl(lst: TagguType.SEQUENCE.value, sep: TagguType.STRING.value, last_sep: TagguType.STRING.value) -> TagguType.STRING.value:
    f_lst = lst[:-1]
    l_elem = lst[-1:]

    f_join = [sep.join(f_lst)]
    f_join.extend(l_elem)

    return last_sep.join(f_join)


def joinlt(lst: TagguType.SEQUENCE.value, sep: TagguType.STRING.value, last_sep: TagguType.STRING.value, two_sep: TagguType.STRING.value) -> TagguType.STRING.value:
    if len(lst) == 2:
        return two_sep.join(lst)

    return joinl(lst=lst, sep=sep, last_sep=last_sep)

########################################################################################################################
#   Conversions from string
########################################################################################################################


def int_(string: TagguType.STRING.value) -> TagguType.INTEGER.value:
    try:
        return int(string)
    except ValueError:
        return int()


def deci(string: TagguType.STRING.value) -> TagguType.DECIMAL.value:
    try:
        return decimal.Decimal(string)
    except decimal.DecimalException:
        return decimal.Decimal()


def bool_(string: TagguType.STRING.value) -> TagguType.BOOLEAN.value:
    T_VALS = frozenset(('y', 'yes', 't', 'true', 'on', '1'))
    F_VALS = frozenset(('n', 'no', 'f', 'false', 'off', '0'))
    cf_str = string.casefold()
    if cf_str in T_VALS:
        return True
    else:
        return False


def date(string: TagguType.STRING.value) -> TagguType.DATE.value:
    try:
        return datetime.datetime.strptime(string, '%Y-%m-%d').date()
    except ValueError:
        return datetime.date.min


########################################################################################################################
#   Variables
########################################################################################################################


def put(name: TagguType.STRING.value, val: TagguType.ANY.value) -> TagguType.ANY.value:
    # TODO: Need a context containing instance variables!
    pass


def puts(name: TagguType.STRING.value, val: TagguType.ANY.value) -> TagguType.NONE.value:
    # TODO: Need a context containing instance variables!
    pass


def get(name: TagguType.STRING.value) -> TagguType.ANY.value:
    # TODO: Need a context containing instance variables!
    pass

########################################################################################################################
#   Utility & helper methods
########################################################################################################################


def valid(val: TagguType.ANY.value) -> TagguType.BOOLEAN.value:
    return bool(val)


def index() -> TagguType.INTEGER.value:
    # TODO: Need a context containing the path to an item!
    pass


def total() -> TagguType.INTEGER.value:
    # TODO: Need a context containing the path to an item!
    pass


def nil(*_: TagguType.ANY.value) -> TagguType.NONE.value:
    pass
