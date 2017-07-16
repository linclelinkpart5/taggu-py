class TagguException(Exception):
    pass


class InvalidSubpath(TagguException):
    pass


class AbsoluteSubpath(InvalidSubpath):
    pass


class EscapingSubpath(InvalidSubpath):
    pass
