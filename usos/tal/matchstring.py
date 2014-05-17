from __future__ import unicode_literals

import re

_split_re = re.compile(r'([^<>]+)|<b\s*>([^<>]*)</b\s*>|<b\s*/>|(.)', flags=re.DOTALL)
_entity_re = re.compile(r'&(?:(\w+)|#(\d+)|#[xX]([0-9a-fA-F]+));?')

_named_entities = dict(
    quot='"',
    apos='\'',
    amp='&',
    lt='<',
    gt='>',
)


def _unescape(s):
    def repl(match):
        if match.group(1):
            try:
                return _named_entities[match.group(1)]
            except KeyError:
                raise ValueError('Unsupported HTML entity: {0}'.format(match.group(0)))
        elif match.group(2):
            return chr(int(match.group(2)))
        else:
            return chr(int(match.group(3), base=16))
    return _entity_re.sub(repl, s)


def _escape_html(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
             .replace('"', '&quot;').replace("'", '&#39;'))


class MatchString(object):
    def __init__(self, parts):
        self._parts = parts

    def format(self, start, end, escape=None):
        if escape in ('html', 'xml'):
            escape = _escape_html
        elif escape is None:
            escape = lambda x: x
        elif not callable(escape):
            raise ValueError('Invalid escape argument: {0}'.format(escape))

        ret = [escape(self._parts[0])]
        for i in xrange(1, len(self._parts), 2):
            ret.append(start)
            ret.append(escape(self._parts[i]))
            ret.append(end)
            ret.append(self._parts[i + 1])
        return ''.join(ret)

    def __iter__(self):
        highlighted = False
        for part in self._parts:
            if part:
                yield part, highlighted
            highlighted = not highlighted

    def __eq__(self, other):
        if isinstance(other, MatchString):
            return list(self) == list(other)
        else:
            return False

    @classmethod
    def from_html(cls, s):
        parts = ['']
        for normal, highlighted, invalid in _split_re.findall(s):
            if normal:
                parts[-1] += _unescape(normal)
            elif highlighted:
                parts.append(_unescape(highlighted))
                parts.append('')
            elif invalid:
                raise ValueError('Invalid match string: {0}'.format(s))
        return MatchString(parts)

    def __unicode__(self):
        return self.format('<b>', '</b>', 'html')

    def __str__(self):
        return str(unicode(self))

    def __repr__(self):
        return '{0}.{1}({2!r})'.format(self.__class__.__module__, self.__class__.__name__, self._parts)
