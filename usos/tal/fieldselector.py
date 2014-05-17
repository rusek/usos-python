from .factory.entities import BaseEntityField
import re

_field_selector_re = re.compile(r'([][|*])|([a-zA-Z_][a-zA-Z_0-9]*)|(.)', flags=re.DOTALL)


def tokenize(s):
    for punct, name, other in _field_selector_re.findall(s):
        if punct:
            yield punct, None
        elif name:
            yield 'field', name
        else:
            raise ValueError('Invalid field selector: {0}'.format(s))
    yield 'eof', None


class BasicParser(object):
    def __init__(self, s):
        self.source = s
        self._it = tokenize(s)
        self.token_type, self.token_value = None, None
        self.next_token()

    def next_token(self):
        self.token_type, self.token_value = next(self._it)

    def parse_field(self):
        if self.token_type != 'field':
            raise ValueError('Invalid field selector: {0}'.format(self.source))
        field_name = self.token_value
        self.next_token()
        if self.token_type == '[':
            self.next_token()
            subfield_selector = self.parse_field_selector()
            if self.token_type != ']':
                raise ValueError('Invalid field selector: {0}'.format(self.source))
            self.next_token()
        else:
            subfield_selector = {}

        return field_name, subfield_selector

    def parse_field_selector(self):
        result = {}

        field, subfield_selector = self.parse_field()
        result[field] = subfield_selector
        while self.token_type == '|':
            self.next_token()
            field, subfield_selector = self.parse_field()
            result[field] = subfield_selector

        return result


class Parser(object):
    def __init__(self, s):
        self.source = s
        self._it = tokenize(s)
        self.token_type, self.token_value = None, None
        self.next_token()

    def next_token(self):
        self.token_type, self.token_value = next(self._it)

    def parse_field(self, entity_class):
        if self.token_type != 'field':
            raise ValueError('Invalid field selector: {0}'.format(self.source))
        field_name = self.token_value
        field = entity_class.fields[field_name]
        self.next_token()
        if self.token_type == '*':
            recursive = True
            self.next_token()
        else:
            recursive = False

        if self.token_type == '[':
            if not isinstance(field, BaseEntityField):
                raise ValueError('Subfields only supported for entity fields')

            self.next_token()
            subfields = self.parse_field_selector(field.ref_entity_class)
            if self.token_type != ']':
                raise ValueError('Invalid field selector: {0}'.format(self.source))
            self.next_token()
        else:
            subfields = field.get_default_subfield_selector()

        if recursive:
            subfields[field_name] = subfields

        return field_name, subfields

    def parse_field_selector(self, entity_class):
        result = {}

        if self.token_type == 'field':
            field, subfields = self.parse_field(entity_class)
            result[field] = subfields
            while self.token_type == '|':
                self.next_token()
                field, subfields = self.parse_field(entity_class)
                result[field] = subfields
        elif self.token_type == '*':
            self.next_token()
            for field in entity_class.fields:
                result[field.name] = field.get_default_subfield_selector()

        return result


def parse(s, entity_class):
    parser = Parser(s)
    fields = parser.parse_field_selector(entity_class)
    if parser.token_type != 'eof':
        raise ValueError('Invalid field selector: {0}'.format(s))
    return fields


def parse_basic(s):
    parser = BasicParser(s)
    field_selector = parser.parse_field_selector()
    if parser.token_type != 'eof':
        raise ValueError('Invalid field selector: {0}'.format(s))
    return field_selector


def stringify(s):
    # Current implementation does not work with recursive fields
    return '|'.join(('{0}[{1}]'.format(k, stringify(v)) if v else k) for k, v in s.iteritems())


def is_recursive(field_selector, field_name):
    return field_selector.get(field_name) is field_selector
