import re


def pack_id(id):
    return '|'.join(part.replace('\\', '\\\\').replace('|', '\\|') for part in id)


def unpack_id(id, size=None):
    fragments = re.split(r'\\(.)|\|', id, re.DOTALL)
    parts = [fragments[0]]
    for i in xrange(1, len(fragments), 2):
        sep = fragments[i]
        if sep is None:
            parts.append('')
        elif sep == '|' or sep == '\\':
            parts[-1] += sep
        else:
            raise ValueError('Invalid escape character: {0}'.format(sep))
        parts[-1] += fragments[i + 1]

    if size is not None and len(parts) != size:
        raise ValueError('Invalid number of parts')
    return tuple(parts)
