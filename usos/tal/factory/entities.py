import datetime
import decimal
from collections import namedtuple

from .. import naming
from ..matchstring import MatchString


def _field_order():
    i = 0
    while True:
        yield i
        i += 1
_field_order = _field_order()


def _prep_data_type(x):
    if isinstance(x, type):
        return x()
    else:
        return x


class DataType(object):
    def check(self, value):
        raise NotImplementedError('Subclasses should override this')


class DateType(DataType):
    def check(self, value):
        if not isinstance(value, datetime.date):
            raise ValueError('Not a date: {0!r}'.format(value))


class DateTimeType(DataType):
    def check(self, value):
        if not isinstance(value, datetime.datetime):
            raise ValueError('Not a datetime: {0!r}'.format(value))


class BoolType(DataType):
    def check(self, value):
        if value is not False and value is not True:
            raise ValueError('Not a bool: {0!r}'.format(value))


class DecimalType(DataType):
    def check(self, value):
        if not isinstance(value, decimal.Decimal):
            raise ValueError('Not a decimal: {0!r}'.format(value))


class MatchStringType(DataType):
    def check(self, value):
        if not isinstance(value, MatchString):
            raise ValueError('Not a match string: {0!r}'.format(value))


class EnumType(DataType):
    def __init__(self, *members):
        self.members = members

    def check(self, value):
        if not isinstance(value, basestring) or value not in self.members:
            raise ValueError('Not an enum member: {0!r}. Valid values: {1!r}'.format(value, self.members))


class OpenEnumType(DataType):
    def __init__(self, *members):
        self.members = members

    def check(self, value):
        if not isinstance(value, basestring):
            # TODO warning in debug mode
            raise ValueError('Not an enum member: {0!r}'.format(value))


Coords = namedtuple('Coords', ['lat', 'long'])


class CoordsType(DataType):
    def check(self, value):
        if not isinstance(value, Coords):
            raise ValueError('Not coordinates: {0!r}'.format(value))


class StringType(DataType):
    def check(self, value):
        if not isinstance(value, basestring):
            raise ValueError('Not a string: {0!r}'.format(value))


class IntType(DataType):
    def check(self, value):
        if not isinstance(value, (int, long)) or isinstance(value, bool):
            raise ValueError('Not an integer: {0!r}'.format(value))


class URLType(DataType):
    def check(self, value):
        # TODO also try to parse it
        if not isinstance(value, basestring):
            raise ValueError('Not an URL: {0!r}'.format(value))


class EmailType(DataType):
    def check(self, value):
        # TODO try also to parse it
        if not isinstance(value, basestring):
            raise ValueError('Not an email: {0!r}'.format(value))


class PhoneNumberType(DataType):
    def check(self, value):
        if not isinstance(value, basestring):
            raise ValueError('Not a phone number: {0!r}'.format(value))


class ListType(DataType):
    def __init__(self, item_type):
        self.item_type = _prep_data_type(item_type)

    def check(self, value):
        if not isinstance(value, list):
            raise ValueError('Not a list: {0!r}'.format(value))
        for item in value:
            self.item_type.check(item)


class OptionalType(DataType):
    def __init__(self, item_type):
        self.item_type = _prep_data_type(item_type)

    def check(self, value):
        if value is not None:
            self.item_type.check(value)


class Field(object):
    def __init__(self, default=False, variant=False):
        self.entity_class = None
        self.name = None
        self.default = default
        self.variant = variant
        self._order = next(_field_order)

    def get_default_subfield_selector(self):
        raise NotImplementedError('Subclasses should override this')


class DataField(Field):
    def __init__(self, type, default=False, variant=False):
        super(DataField, self).__init__(default=default, variant=variant)
        self.type = _prep_data_type(type)

    def get_default_subfield_selector(self):
        return {}


class BaseEntityField(Field):
    def __init__(self, ref_entity_class, default=False, variant=False):
        super(BaseEntityField, self).__init__(default=default, variant=variant)
        self._ref_entity_class = ref_entity_class

    @property
    def ref_entity_class(self):
        if isinstance(self._ref_entity_class, basestring):
            entity_class = _entity_classes_by_name[self._ref_entity_class]
            self._ref_entity_class = entity_class
        return self._ref_entity_class

    def get_default_subfield_selector(self):
        return self.ref_entity_class.get_default_field_selector()

    def map(self, f, value):
        raise NotImplementedError('Subclasses should override this')


class EntityField(BaseEntityField):
    def map(self, f, value):
        return f(value)


class OptionalEntityField(BaseEntityField):
    def map(self, f, value):
        return None if value is None else f(value)


class EntityListField(BaseEntityField):
    def map(self, f, value):
        return map(f, value)


class EntityMapField(BaseEntityField):
    def map(self, f, value):
        return {k: f(v) for k, v in value.iteritems()}


class EntityFields(object):
    def __init__(self, fields):
        self._fields = fields
        self._field_list = fields.values()
        self._field_list.sort(key=lambda f: f._order)

    def __iter__(self):
        return iter(self._field_list)

    def __getitem__(self, item):
        return self._fields[item]

    def __len__(self):
        return len(self._fields)


class EntityMeta(type):
    def __new__(cls, name, bases, attrs):
        new_attrs = {}
        fields = {}
        searchable = False
        hidden = False
        for k, v in attrs.iteritems():
            if isinstance(v, Field):
                if v.entity_class is not None:
                    raise ValueError('Field {0} is already bound to class {1}'.format(v, v.entity_class))
                fields[k] = v
            elif k == 'entity_searchable':
                searchable = v
            elif k == 'entity_hidden':
                hidden = v
            else:
                new_attrs[k] = v

        subclass = super(EntityMeta, cls).__new__(cls, name, bases, new_attrs)
        subclass.fields = EntityFields(fields)
        for field_name, field in fields.iteritems():
            field.name = field_name
            field.entity_class = subclass
        if name != 'Entity' and not hidden:
            _entity_classes_by_name[name] = subclass

        if searchable:
            lowercase_name = naming.generic_to_lowercase_underscore(naming.camelcase_to_generic(name))
            search_item_entity_field = EntityField(name)
            search_item_class = cls('SearchItem', (Entity, ), {
                lowercase_name: search_item_entity_field,
                'entity': property(lambda self: getattr(self, lowercase_name)),
                'match': DataField(MatchStringType),
            })
            setattr(search_item_class, 'entity_field', search_item_entity_field)

            subclass.SearchItem = search_item_class

        return subclass


_entity_classes_by_name = {}


class Entity(object):
    __metaclass__ = EntityMeta
    _default_field_selector = None
    fields = None

    def __init__(self, id, **kwargs):
        self.id = id
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

    def __repr__(self):
        return '<{0} {1}>'.format(self.__class__.__name__, self.__dict__)

    def is_loaded(self, field):
        if not isinstance(field, basestring):
            field = field.name

        return field in self.__dict__

    @classmethod
    def get_default_field_names(cls):
        return [field.name for field in cls.fields if field.default]

    @classmethod
    def get_default_field_selector(cls):
        if not cls._default_field_selector:
            selector = {}
            for field in cls.fields:
                if not field.default:
                    continue
                selector[field.name] = field.get_default_subfield_selector()
            cls._default_field_selector = selector
        return cls._default_field_selector


def get_entity_classes():
    return _entity_classes_by_name.values()
