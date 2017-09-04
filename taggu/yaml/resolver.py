import re

import yaml.resolver


class TagguResolver(yaml.resolver.BaseResolver):
    pass


TagguResolver.add_implicit_resolver(
        'tag:yaml.org,2002:merge',
        re.compile(r'^(?:<<)$'),
        ['<'])

TagguResolver.add_implicit_resolver(
        'tag:yaml.org,2002:null',
        re.compile(r'''^(?: ~
                    |null|Null|NULL
                    | )$''', re.X),
        ['~', 'n', 'N', ''])

TagguResolver.add_implicit_resolver(
        'tag:yaml.org,2002:value',
        re.compile(r'^(?:=)$'),
        ['='])
