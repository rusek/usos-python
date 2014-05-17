import os.path

from usos.tal import naming, EntityNotFound, MatchString
from usos.tal.factory.entities import Entity

TEST_DIR = os.path.dirname(os.path.dirname(__file__))


def try_ascii(x):
    if isinstance(x, unicode):
        try:
            return str(x)
        except UnicodeEncodeError:
            return x
    else:
        return x


class Guard(object):
    def __init__(self, exit_func):
        self.exit_func = exit_func

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit_func()


class TestWriter(object):
    def __init__(self, entity_class):
        entity_name_lower = naming.convert(entity_class.__name__, 'camelcase', 'lowercase_underscore')

        self._indent = ''
        self._f = open(os.path.join(TEST_DIR, '{0}.py'.format(entity_name_lower)), 'a')

    def indent(self):
        self._indent += '    '

        return Guard(self.dedent)

    def dedent(self):
        self._indent = self._indent[:-4]

    def append(self, s):
        self._f.write(self._indent)
        self._f.write(s)
        self._f.write('\n')

    def append_header(self):
        self.append('')
        self.append('')
        self.append('class GeneratedTestCase(TestCase):')
        self.indent()
        self.append('def test_unspecified(self):')
        self.indent()

    def append_footer(self):
        self.dedent()
        self.dedent()
        self.append('')

    def append_value(self, value, prefix='', suffix=''):
        if isinstance(value, list):
            if value:
                self.append(prefix + '[')
                with self.indent():
                    for item in value:
                        self.append_value(item, suffix=',')
                self.append(']' + suffix)
            else:
                self.append(prefix + '[]' + suffix)
        elif isinstance(value, dict):
            if value:
                self.append(prefix + '{')
                with self.indent():
                    for k, v in value.iteritems():
                        self.append_value(v, prefix=repr(try_ascii(k)) + ': ', suffix=',')
                self.append('}' + suffix)
            else:
                self.append(prefix + '{}' + suffix)
        elif isinstance(value, MatchString):
            self.append(
                '{0}tal.MatchString.from_html({1!r}){2}'.format(
                    prefix,
                    try_ascii(value.format('<b>', '</b>', escape='html')),
                    suffix
                )
            )
        elif isinstance(value, Entity):
            name = type(value).__name__
            if name == 'SearchItem':
                name = value.entity_field.ref_entity_class.__name__ + '.' + name

            self.append('{0}tal.{1}('.format(prefix, name))
            with self.indent():
                self.append_value(value.id, suffix=',')
                for field in type(value).fields:
                    if hasattr(value, field.name):
                        self.append_value(getattr(value, field.name), prefix=field.name + '=', suffix=',')
            self.append(')' + suffix)
        else:
            self.append(prefix + repr(try_ascii(value)) + suffix)

    def append_requests(self, requests):
        for path, params, response in requests:
            self.append('self.add_method_call(')
            self.indent()
            self.append_value(path, suffix=',')
            self.append_value(params, suffix=',')
            self.append_value(response)
            self.dedent()
            self.append(')')
        if requests:
            self.append('')

    def wrap_in_assert_same(self, second):
        self.append('self.assert_same(')
        self.indent()

        def exit_func():
            self.append_value(second)
            self.dedent()
            self.append(')')

        return Guard(exit_func)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        with self._f:
            if exc_type is not None:
                self.append_footer()

    @classmethod
    def open_test(cls, entity_class):
        writer = cls(entity_class)
        try:
            writer.append_header()
            return writer
        except:
            writer._f.close()
            raise


def make_get_test(entity_class, ids, fields, result, requests):
    if len(ids) == 1:
        id, = ids
        if not result:
            make_get_single_failure_test(entity_class, id, fields, requests)
        else:
            make_get_single_test(entity_class, id, fields, result[id], requests)
    else:
        make_get_many_test(entity_class, ids, fields, result, requests)


def make_get_single_failure_test(entity_class, id, fields, requests):
    with TestWriter.open_test(entity_class) as writer:
        writer.append_requests(requests)
        writer.append(
            'self.assertRaises(tal.EntityNotFound, self.get, tal.{0}, {1!r}, {2!r})'.format(
                entity_class.__name__,
                try_ascii(id),
                try_ascii(fields)
            )
        )


def make_get_single_test(entity_class, id, fields, result, requests):
    with TestWriter.open_test(entity_class) as writer:
        writer.append_requests(requests)
        with writer.wrap_in_assert_same(result):
            writer.append(
                'self.get(tal.{0}, {1!r}, {2!r}),'.format(
                    entity_class.__name__,
                    try_ascii(id),
                    try_ascii(fields)
                )
            )


def make_get_many_test(entity_class, ids, fields, result, requests):
    with TestWriter.open_test(entity_class) as writer:
        writer.append_requests(requests)
        with writer.wrap_in_assert_same(result):
            writer.append(
                'self.get_many(tal.{0}, {1!r}, {2!r}),'.format(
                    entity_class.__name__,
                    map(try_ascii, ids),
                    try_ascii(fields)
                )
            )


def make_list_test(entity_class, domain, fields, result, requests):
    with TestWriter.open_test(entity_class) as writer:
        writer.append_requests(requests)
        with writer.wrap_in_assert_same(result):
            writer.append(
                'self.list(tal.{0}, {1!r}, {2!r}),'.format(
                    entity_class.__name__,
                    try_ascii(domain),
                    try_ascii(fields)
                )
            )


def make_search_test(entity_class, query, fields, result, requests):
    with TestWriter.open_test(entity_class) as writer:
        writer.append_requests(requests)
        with writer.wrap_in_assert_same(result):
            writer.append(
                'self.search(tal.{0}, {1!r}, {2!r}),'.format(
                    entity_class.__name__,
                    try_ascii(query),
                    try_ascii(fields)
                )
            )
