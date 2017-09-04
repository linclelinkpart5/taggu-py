import yaml.reader
import yaml.scanner
import yaml.parser
import yaml.composer
import yaml.constructor

import taggu.yaml.resolver as tyr


class TagguLoader(yaml.reader.Reader, yaml.scanner.Scanner, yaml.parser.Parser, yaml.composer.Composer,
                  yaml.constructor.BaseConstructor, tyr.TagguResolver):
    """A custom PyYAML loader that only generates strings and nulls as scalars."""

    def __init__(self, stream):
        yaml.reader.Reader.__init__(self, stream)
        yaml.scanner.Scanner.__init__(self)
        yaml.parser.Parser.__init__(self)
        yaml.composer.Composer.__init__(self)
        yaml.constructor.BaseConstructor.__init__(self)
        tyr.TagguResolver.__init__(self)
