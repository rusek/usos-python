import re

# Generic name consists of words separated by spaces. Words which denote acronyms should use uppercase letters
# and others lowercase.
#
# Examples:
#   "course unit"
#   "profile URL"

_camel_case_part_re = re.compile('([A-Z]+[a-z0-9]*)')


def camelcase_to_generic(s):
    parts = _camel_case_part_re.split(s)
    if ''.join(parts[0::2]):
        raise ValueError('Invalid camel case name: {0}'.format(s))
    parts = parts[1::2]
    return ' '.join(part if part.isupper() else part.lower() for part in parts)


_acronyms = frozenset(['url'])


def lowercase_underscore_to_generic(s):
    return ' '.join(part.upper() if part in _acronyms else part for part in s.split('_'))


def generic_to_lowercase_underscore(s):
    return s.replace(' ', '_').lower()


def convert(s, src, dest):
    if src == 'camelcase':
        s = camelcase_to_generic(s)
    elif src != 'generic':
        raise ValueError('Invalid source: {0}'.format(src))

    if dest == 'lowercase_underscore':
        return generic_to_lowercase_underscore(s)
    elif dest == 'generic':
        return s
    else:
        raise ValueError('Invalid destination: {0}'.format(dest))
