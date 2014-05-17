import datetime
import re
import decimal
import copy

from ..matchstring import MatchString
from ..factory.entities import Coords
from ..fieldselector import stringify as stringify_field_selector, is_recursive as is_field_selector_recursive
from ...client import BadRequest
from ..packid import pack_id, unpack_id
from ..lang import DEFAULT_LANG


class Id(object):
    def __contains__(self, name):
        raise NotImplementedError('Subclasses should override this')

    def update_params(self, params, id):
        raise NotImplementedError('Subclasses should override this')

    def update_field_selector(self, api_field_selector):
        raise NotImplementedError('Subclasses should override this')

    def load_value(self, reactor, response):
        raise NotImplementedError('Subclasses should override this')


class ElementaryId(Id):
    def __init__(self, name):
        self.name = name

    def __contains__(self, name):
        return name == self.name

    def update_params(self, params, id):
        params[self.name] = id

    def update_field_selector(self, api_field_selector):
        api_field_selector[self.name] = {}

    def load_value(self, reactor, response):
        value = response[self.name]
        if value is None:
            return None
        else:
            return unicode(response[self.name])


class CompositeId(Id):
    def __init__(self, *names):
        self.names = names

    def __contains__(self, name):
        return name in self.names

    def update_params(self, params, id):
        parts = unpack_id(id, len(self.names))
        for name, value in zip(self.names, parts):
            params[name] = value

    def update_field_selector(self, api_field_selector):
        for name in self.names:
            api_field_selector[name] = {}

    def load_value(self, reactor, response):
        return pack_id(unicode(response[name]) for name in self.names)


class IdList(object):
    def update_params(self, params, ids):
        raise NotImplementedError('Subclasses should override this')

    def get_key(self, id):
        raise NotImplementedError('Subclasses should override this')


class ElementaryIdList(IdList):
    def __init__(self, param_name):
        self.param_name = param_name

    def update_params(self, params, ids):
        params[self.param_name] = '|'.join(ids)

    def get_key(self, id):
        return unicode(id)


class CompositeTupleIdList(IdList):
    def __init__(self, param_name):
        self.param_name = param_name

    def update_params(self, params, ids):
        params[self.param_name] = '|'.join(map(self.get_key, ids))

    def get_key(self, id):
        return '({0})'.format(','.join(map(unicode, unpack_id(id))))


class FieldPickers(object):
    def __init__(self, **pickers):
        assert 'id' not in pickers, '\'id\' is a reserved field name'
        self._pickers = pickers

    def iteritems(self):
        return self._pickers.iteritems()

    def __contains__(self, field_name):
        return field_name in self._pickers

    def get(self, field_name, default=None):
        return self._pickers.get(field_name, default)

    def __getitem__(self, field_name):
        return self._pickers[field_name]

    def __len__(self):
        return len(self._pickers)

    def __or__(self, other):
        result = FieldPickers()
        result._pickers.update(self._pickers)
        result._pickers.update(other._pickers)
        return result

    def bind_to_entity_class(self, entity_class):
        for field_name, picker in self._pickers.iteritems():
            picker.bind_to_field(entity_class.fields[field_name])

    def load_values(self, reactor, response, field_selector):
        values = {}
        for field_name, subfield_selector in field_selector.iteritems():
            picker = self.get(field_name)
            if picker is not None:
                values[field_name] = picker.load_value(reactor, response, subfield_selector)
        return values

    def update_field_selector(self, api_field_selector, field_selector):
        for field_name, subfield_selector in field_selector.iteritems():
            picker = self.get(field_name)
            if picker is not None:
                picker.update_field_selector(api_field_selector, subfield_selector)


class EntityFieldPickers(FieldPickers):
    def __init__(self, id, **pickers):
        super(EntityFieldPickers, self).__init__(**pickers)
        self.id = id
        self.entity_class = None

    def __or__(self, other):
        result = EntityFieldPickers(self.id)
        result._pickers.update(self._pickers)
        result._pickers.update(other._pickers)
        return result

    def bind_to_entity_class(self, entity_class):
        if self.entity_class is None:
            self.entity_class = entity_class
            super(EntityFieldPickers, self).bind_to_entity_class(entity_class)

    def update_field_selector(self, api_field_selector, field_selector, with_id=False):
        super(EntityFieldPickers, self).update_field_selector(api_field_selector, field_selector)
        if with_id:
            self.id.update_field_selector(api_field_selector)

    def load_id(self, reactor, response):
        return self.id.load_value(reactor, response)

    def load_id_and_values(self, reactor, response, field_selector):
        return self.load_id(reactor, response), self.load_values(reactor, response, field_selector)

    def load_entity(self, reactor, response, field_selector):
        id, values = self.load_id_and_values(reactor, response, field_selector)
        return reactor.spawn_entity(self.entity_class, id, field_selector, values)

    def make_inline_picker(self):
        return InlineEntityPicker(self)

    def make_picker(self, field_name, has_subfield_selector=True, lifted_fields=None):
        return EntityPicker(field_name, self, has_subfield_selector, lifted_fields)

    def make_list_picker(self, field_name, has_subfield_selector=True, lifted_fields=None, unique=False):
        return EntityListPicker(field_name, self, has_subfield_selector, lifted_fields=lifted_fields, unique=unique)

    def make_map_picker(self, field_name, has_subfield_selector=True):
        return EntityMapPicker(field_name, self, has_subfield_selector)

    def make_inline_list_picker(self):
        return InlineEntityListPicker(self)


class Picker(object):
    def __init__(self):
        self.field = None

    def update_field_selector(self, api_field_selector, subfield_selector):
        raise NotImplementedError('Subclasses should override this')

    def load_value(self, reactor, response, subfield_selector):
        raise NotImplementedError('Subclasses should override this')

    def bind_to_field(self, field):
        if self.field is not None and field is not self.field:
            raise ValueError('Picker already bound to different field')
        self.field = field


class ElementaryPicker(Picker):
    def __init__(self, field_name):
        super(ElementaryPicker, self).__init__()
        self.field_name = field_name

    def update_field_selector(self, api_field_selector, subfield_selector):
        api_field_selector[self.field_name] = {}

    def load_value(self, reactor, response, subfield_selector):
        if self.field_name not in response and self.field.variant:
            return None
        return self.prep_value(reactor, response[self.field_name], subfield_selector)

    def prep_value(self, reactor, value, subfield_selector):
        raise NotImplementedError('Subclasses should override this')


# class LiftingPicker(Picker):
#     def __init__(self, picker, **lifted_keys):
#         assert isinstance(picker, ElementaryPicker)
#
#         super(LiftingPicker, self).__init__()
#         self.picker = picker
#         self.lifted_keys = lifted_keys
#
#     def update_field_selector(self, api_field_selector, subfield_selector):
#         self.picker.update_field_selector(api_field_selector, subfield_selector)
#
#     def load_value(self, reactor, response, subfield_selector):
#         lifted_subresponses = []
#         for subresponse in response[self.picker.field_name]:
#             subresponse = subresponse.copy()
#             for k, v in self.lifted_keys.iteritems():
#                 subresponse[v] = response[k]
#             lifted_subresponses.append(subresponse)
#         lifted_response = response.copy()
#         lifted_response[self.picker.field_name] = lifted_subresponses
#         return self.picker.load_value(reactor, response, subfield_selector)


class SimplePicker(ElementaryPicker):
    def prep_value(self, reactor, value, subfield_selector):
        return value


class DecimalPicker(ElementaryPicker):
    def prep_value(self, reactor, value, subfield_selector):
        # 'None' is required by services/grades/grade_type 'decimal_value' field
        if value in (None, 'None', ''):
            return None
        return decimal.Decimal(value)


class URLPicker(ElementaryPicker):
    def prep_value(self, reactor, value, subfield_selector):
        return value if value else None


class USOSwebURLPicker(ElementaryPicker):
    def prep_value(self, reactor, value, subfield_selector):
        if value is None or value == '':
            return None

        # fix for profile_url in services/courses/unit
        if isinstance(value, list):
            value = value[0]

        lang_param = 'lang=' + ('2' if reactor.lang == 'en' else '1')
        if '?' in value:
            return value + '&' + lang_param
        else:
            return value + '?' + lang_param


class MappingPicker(ElementaryPicker):
    def __init__(self, field_name, mapping, open=False):
        super(MappingPicker, self).__init__(field_name)
        self.mapping = mapping
        self.open = open

    def prep_value(self, reactor, value, subfield_selector):
        if self.open:
            try:
                value = self.mapping.get(value, value)
            except TypeError:
                # Probably unhashable type, just ignore it
                pass

            return copy.deepcopy(value)
        else:
            return copy.deepcopy(self.mapping[value])


# class CompositePicker(Picker):  # TODO unused, should be removed
#     def __init__(self, *field_names):
#         super(CompositePicker, self).__init__()
#         self.field_names = field_names
#
#     def update_field_selector(self, api_field_selector, subfield_selector):
#         for field_name in self.field_names:
#             api_field_selector[field_name] = {}
#
#     def load_value(self, reactor, response, subfield_selector):
#         value = tuple(response[field_name] for field_name in self.field_names)
#         return self.prep_value(reactor, value, subfield_selector)
#
#     def prep_value(self, reactor, value, subfield_selector):
#         raise NotImplementedError('Subclasses should override this')


# class NestedPicker(Picker):
#     def __init__(self, field_name, picker, nested_field=True, nested_response=True):
#         super(NestedPicker, self).__init__()
#         self.field_name = field_name
#         self.picker = picker
#         self.nested_field = nested_field
#         self.nested_response = nested_response
#
#     def update_field_selector(self, api_field_selector, subfield_selector):
#         if self.nested_field:
#             api_subfield_selector = api_field_selector.setdefault(self.field_name, {})
#             self.picker.update_field_selector(api_subfield_selector, subfield_selector)
#         else:
#             self.picker.update_field_selector(api_field_selector, subfield_selector)
#
#     def load_value(self, reactor, response, subfield_selector):
#         if self.nested_response:
#             return self.picker.load_value(reactor, response[self.field_name], subfield_selector)
#         else:
#             return self.picker.load_value(reactor, response, subfield_selector)


# Could be expressed using InlineEntityPicker, but it's nice to have it
class EntityIdPicker(Picker):
    def __init__(self, *field_names):
        super(EntityIdPicker, self).__init__()
        if len(field_names) == 1:
            self.id = ElementaryId(field_names[0])
        else:
            self.id = CompositeId(*field_names)

    def update_field_selector(self, api_field_selector, subfield_selector):
        self.id.update_field_selector(api_field_selector)

    def load_value(self, reactor, response, subfield_selector):
        id = self.id.load_value(reactor, response)
        if id is None:
            return None
        else:
            return reactor.spawn_entity(self.field.ref_entity_class, id, subfield_selector)


class InlineEntityListPicker(Picker):
    def __init__(self, entity_subfield_pickers):
        super(InlineEntityListPicker, self).__init__()
        self.entity_subfield_pickers = entity_subfield_pickers

    def update_field_selector(self, api_field_selector, subfield_selector):
        self.entity_subfield_pickers.update_field_selector(api_field_selector, subfield_selector, with_id=True)

    def load_value(self, reactor, response, subfield_selector):
        it = response.itervalues() if isinstance(response, dict) else iter(response)
        ret = []
        for subresponse in it:
            if subresponse is None:
                continue
            ret.append(self.entity_subfield_pickers.load_entity(reactor, subresponse, subfield_selector))
        return ret

    def bind_to_field(self, field):
        super(InlineEntityListPicker, self).bind_to_field(field)
        self.entity_subfield_pickers.bind_to_entity_class(field.ref_entity_class)


class InlineEntityPicker(Picker):
    def __init__(self, entity_subfield_pickers):
        super(InlineEntityPicker, self).__init__()
        self.entity_subfield_pickers = entity_subfield_pickers

    def update_field_selector(self, api_field_selector, subfield_selector):
        self.entity_subfield_pickers.update_field_selector(api_field_selector, subfield_selector, with_id=True)

    def load_value(self, reactor, response, subfield_selector):
        entity_id = self.entity_subfield_pickers.load_id(reactor, response)
        if entity_id is None:
            return None
        entity_values = self.entity_subfield_pickers.load_values(reactor, response, subfield_selector)
        return reactor.spawn_entity(self.field.ref_entity_class, entity_id, subfield_selector, entity_values)

    def bind_to_field(self, field):
        super(InlineEntityPicker, self).bind_to_field(field)
        self.entity_subfield_pickers.bind_to_entity_class(field.ref_entity_class)


class FieldLifter(object):
    def __init__(self, lifted_fields):
        self.lifted_fields = lifted_fields

    def __nonzero__(self):
        return bool(self.lifted_fields)

    def unlift_subfield_selector(self, api_field_selector, api_subfield_selector):
        for field_name, lifted_field_name in self.lifted_fields.iteritems():
                unlifted_field_selector = api_subfield_selector.pop(lifted_field_name, None)
                if unlifted_field_selector is not None:
                    api_field_selector[field_name] = unlifted_field_selector

    def lift_values(self, subresponse, response):
        for field_name, lifted_field_name in self.lifted_fields.iteritems():
            if field_name in response:
                subresponse[lifted_field_name] = response[field_name]


class BaseEntityPicker(ElementaryPicker):
    def __init__(self, field_name, entity_subfield_pickers, has_subfield_selector=True, lifted_fields=None):
        super(BaseEntityPicker, self).__init__(field_name)
        self.entity_subfield_pickers = entity_subfield_pickers
        self.has_subfield_selector = has_subfield_selector
        self.field_lifter = FieldLifter(lifted_fields or {})

    def update_field_selector(self, api_field_selector, subfield_selector):
        if self.has_subfield_selector or self.field_lifter is not None:
            api_subfield_selector = {}
            self.entity_subfield_pickers.update_field_selector(
                api_subfield_selector, subfield_selector, with_id=True)
            self.field_lifter.unlift_subfield_selector(api_field_selector, api_subfield_selector)
            if not self.has_subfield_selector:
                api_subfield_selector = {}
        else:
            api_subfield_selector = {}

        api_field_selector[self.field_name] = api_subfield_selector

    def bind_to_field(self, field):
        super(BaseEntityPicker, self).bind_to_field(field)
        self.entity_subfield_pickers.bind_to_entity_class(field.ref_entity_class)


class EntityPicker(BaseEntityPicker):
    def load_value(self, reactor, response, subfield_selector):
        if self.field_name not in response and self.field.variant:
            return None

        value = response[self.field_name]
        if value is None:
            return None
        else:
            self.field_lifter.lift_values(value, response)
            return self.entity_subfield_pickers.load_entity(reactor, value, subfield_selector)


class EntityMapPicker(BaseEntityPicker):
    def load_value(self, reactor, response, subfield_selector):
        if self.field_name not in response and self.field.variant:
            return None

        value = response[self.field_name]
        ret = {}
        for k, v in value.iteritems():
            # "if" needed by course_grades field in services/grades/course_edition
            if v is not None:
                self.field_lifter.lift_values(v, response)
                ret[k] = self.entity_subfield_pickers.load_entity(reactor, v, subfield_selector)
        return ret


class AncestorFromListPicker(BaseEntityPicker):
    def load_value(self, reactor, response, subfield_selector):
        if self.field_name not in response and self.field.variant:
            return None

        value = response[self.field_name]
        if is_field_selector_recursive(subfield_selector, self.field.name):
            ancestor_entity = None
            for ancestor_response in value:
                self.field_lifter.lift_values(ancestor_response, response)
                ancestor_id, ancestor_values = self.entity_subfield_pickers.load_id_and_values(
                    reactor, ancestor_response, subfield_selector)
                ancestor_values[self.field.name] = ancestor_entity
                ancestor_entity = reactor.spawn_entity(
                    self.field.entity_class, ancestor_id, subfield_selector, ancestor_values)
            return ancestor_entity
        elif value:
            self.field_lifter.lift_values(value[-1], response)
            return self.entity_subfield_pickers.load_entity(reactor, value[-1], subfield_selector)
        else:
            return None


def _iter_unique_entity_info(it):
    seen_ids = set()
    for response, id, values in it:
        if id not in seen_ids:
            seen_ids.add(id)
            yield response, id, values


class EntityListPicker(BaseEntityPicker):
    def __init__(self, field_name, entity_subfield_pickers, has_subfield_selector=True, lifted_fields=None,
                 unique=False):
        super(EntityListPicker, self).__init__(
            field_name,
            entity_subfield_pickers,
            has_subfield_selector=has_subfield_selector,
            lifted_fields=lifted_fields,
        )
        self.unique = unique

    def load_value(self, reactor, response, subfield_selector):
        if self.field_name not in response and self.field.variant:
            return None

        ret = []
        it = self._iter_entity_info_unfiltered(reactor, response, subfield_selector)
        if self.unique:
            it = _iter_unique_entity_info(it)
        if is_field_selector_recursive(subfield_selector, self.field.name):
            it = self._iter_add_recursive_entities(reactor, it, subfield_selector)

        for _, entity_id, entity_values in it:
            ret.append(reactor.spawn_entity(
                self.field.ref_entity_class, entity_id, subfield_selector, entity_values))

        return ret

    def _iter_add_recursive_entities(self, reactor, it, subfield_selector):
        for entity_response, entity_id, entity_values in it:
                if self.field_name in entity_response:
                    entity_values[self.field.name] = self.load_value(
                        reactor, entity_response, subfield_selector)
                yield entity_response, entity_id, entity_values

    def _iter_entity_info_unfiltered(self, reactor, response, subfield_selector):
        for entity_response in response[self.field_name]:
            self.field_lifter.lift_values(entity_response, response)
            entity_id, entity_values = self.entity_subfield_pickers.load_id_and_values(
                reactor, entity_response, subfield_selector)
            yield entity_response, entity_id, entity_values


class EntityIdListPicker(ElementaryPicker):
    def prep_value(self, reactor, value, subfield_selector):
        return [reactor.spawn_entity(self.field.ref_entity_class, unicode(id), subfield_selector)
                for id in value]


class EntityIdMapPicker(ElementaryPicker):
    def __init__(self, field_name, flipped=False):
        super(EntityIdMapPicker, self).__init__(field_name)
        self.flipped = flipped

    def prep_value(self, reactor, value, subfield_selector):
        if self.flipped:
            it = ((v, k) for k, v in value.iteritems())
        else:
            it = value.iteritems()

        return {key: reactor.spawn_entity(self.field.ref_entity_class, unicode(id), subfield_selector)
                for key, id in it}


class DatePicker(ElementaryPicker):
    _date_re = re.compile(r'^(\d{4})-(\d{2})-(\d{2})$')

    def prep_value(self, reactor, value, subfield_selector):
        if value is None or value == '':
            return None
        match = self._date_re.match(value)
        return datetime.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))


def load_datetime(value):
    if value is None or value == '':
        return None
    if '.' in value:
        return datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')
    else:
        return datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S')


class DateTimePicker(ElementaryPicker):
    def prep_value(self, reactor, value, subfield_selector):
        return load_datetime(value)


class LangDictPicker(ElementaryPicker):
    def prep_value(self, reactor, value, subfield_selector):
        return value[reactor.lang] or value[DEFAULT_LANG] or ''


class CoordsPicker(ElementaryPicker):
    def prep_value(self, reactor, value, subfield_selector):
        return Coords(value['lat'], value['long']) if value is not None else None


class BaseGetMethod(object):
    def __init__(self, path, entity_class, field_pickers, has_fields_param=True):
        self.path = path
        self.entity_class = entity_class
        self.fields = {}
        for field_name, field in field_pickers.iteritems():
            field.bind_to_field(entity_class.fields[field_name])
            self.fields[field_name] = field
        self.has_fields_param = has_fields_param
        self.field_names = frozenset(self.fields.keys())
        self.field_pickers = field_pickers


class BaseGetMethodCandidacy(object):
    def __init__(self, method, targets, field_selector, score):
        self.method = method
        self.targets = targets
        self.field_selector = field_selector
        self.field_names = field_selector.viewkeys()
        self.score = score

    def execute(self, reactor):
        raise NotImplementedError('Subclasses should override this')


class GetMethodCandidacy(BaseGetMethodCandidacy):
    def __init__(self, method, target, field_names):
        super(GetMethodCandidacy, self).__init__(
            method,
            [target],
            target.get_field_selector(field_names),
            len(field_names)
        )

    def execute(self, reactor):
        target, = self.targets
        return {target.entity.id: self.method.execute_get(reactor, target.entity.id, self.field_selector)}


class GetMethod(BaseGetMethod):
    def __init__(self, path, entity_class, id, field_pickers, has_fields_param=True, extra_params=None):
        super(GetMethod, self).__init__(path, entity_class, field_pickers, has_fields_param)
        self.id = id
        self.extra_params = {} if extra_params is None else extra_params

    def make_candidacy(self, targets):
        for target in targets:
            common_field_names = self.field_names.intersection(target.field_names)
            if common_field_names:
                return GetMethodCandidacy(self, target, common_field_names)
        return None

    def execute_get(self, reactor, id, field_selector):
        try:
            response = reactor.call_method(self.path, self._prep_params(id, field_selector))
        except BadRequest as e:
            if e.get('error') == 'object_not_found':
                return None
            elif e.get('error') == 'param_invalid':
                if e.get('param_name') in self.id:
                    return None
            else:
                msg = e.get('message', '').lower()
                if 'does not exist' in msg or 'no such' in msg:
                    return None
            raise
        if response is None:
            return None

        return self.field_pickers.load_values(
            reactor,
            response,
            field_selector
        )

    def _prep_params(self, id, field_selector):
        params = {}

        self.id.update_params(params, id)

        if self.has_fields_param:
            api_field_selector = {}
            self.field_pickers.update_field_selector(api_field_selector, field_selector)
            params['fields'] = stringify_field_selector(api_field_selector)

        params.update(self.extra_params)

        return params


class GetManyMethodCandidacy(BaseGetMethodCandidacy):
    def __init__(self, method, targets, field_names):
        super(GetManyMethodCandidacy, self).__init__(
            method,
            targets,
            targets[0].get_field_selector(field_names),
            len(targets) * len(field_names)
        )

    def execute(self, reactor):
        return self.method.execute_get_many(reactor, (target.entity.id for target in self.targets), self.field_selector)


class GetManyMethod(BaseGetMethod):
    def __init__(self, path, entity_class, ids, field_pickers, has_fields_param=True, limit=None):
        super(GetManyMethod, self).__init__(path, entity_class, field_pickers, has_fields_param)
        self.ids = ids
        self.limit = limit

    def make_candidacy(self, targets):
        matched_targets = []
        matched_field_names = None
        for target in targets:
            field_names = self.field_names.intersection(target.field_names)
            if not field_names:
                continue

            if matched_targets and not target.has_same_field_selector(matched_targets[0]):
                continue

            if not matched_targets:
                matched_field_names = field_names
            matched_targets.append(target)
            if len(matched_targets) == self.limit:
                break

        if matched_field_names:
            return GetManyMethodCandidacy(self, matched_targets, matched_field_names)
        else:
            return None

    def execute_get_many(self, reactor, ids, field_selector):
        if not isinstance(ids, list):
            ids = list(ids)
        response = reactor.call_method(self.path, self._prep_params(ids, field_selector))
        ret = {}
        for id in ids:
            key = self.ids.get_key(id)
            value = response.get(key)
            if value is not None:
                ret[id] = self.field_pickers.load_values(reactor, value, field_selector)
            else:
                ret[id] = None
        return ret

    def _prep_params(self, ids, field_selector):
        params = {}

        self.ids.update_params(params, ids)

        if self.has_fields_param:
            api_field_selector = {}
            self.field_pickers.update_field_selector(api_field_selector, field_selector)
            params['fields'] = stringify_field_selector(api_field_selector)

        return params


class GetManyAsListMethod(GetManyMethod):
    def __init__(self, path, entity_class, ids, entity_field_pickers, has_fields_param=True, limit=None):
        super(GetManyAsListMethod, self).__init__(
            path, entity_class, ids, entity_field_pickers, has_fields_param, limit)
        self.entity_field_pickers = entity_field_pickers

    def execute_get_many(self, reactor, ids, field_selector):
        if not isinstance(ids, list):
            ids = list(ids)
        response = reactor.call_method(self.path, self._prep_params(ids, field_selector))

        # FIXME this is a disaster and works (barely) with crstests/user_points
        ret = dict.fromkeys(ids, dict.fromkeys(field_selector.keys(), None))
        for entity_response in response:
            id, values = self.entity_field_pickers.load_id_and_values(reactor, entity_response, field_selector)
            ret[id] = values
        return ret

    def _prep_params(self, ids, field_selector):
        params = {}

        self.ids.update_params(params, ids)

        if self.has_fields_param:
            api_field_selector = {}
            self.entity_field_pickers.update_field_selector(api_field_selector, field_selector, with_id=True)
            params['fields'] = stringify_field_selector(api_field_selector)

        return params


class SearchMethod(object):
    def __init__(self, path, entity_class, picker, fields_param_mode='full', query_param_name='query'):
        self.path = path
        self.entity_class = entity_class
        self.picker = picker
        self.query_param_name = query_param_name

        # Possible values:
        # - 'none' - no fields param
        # - 'partial' - item subfields only (e.g. "user[id|first_name]|match")
        # - 'full' - full field support (e.g. "items[user[id|first_name]|match")
        self.fields_param_mode = fields_param_mode

        picker.bind_to_field(entity_class.SearchItem.entity_field)

    def execute_search(self, reactor, query, field_selector):
        params = {
            'lang': reactor.lang,
            self.query_param_name: query,
            'num': 20,
        }

        if self.fields_param_mode != 'none':
            api_field_selector = {'match': {}}
            self.picker.update_field_selector(api_field_selector, field_selector)
            api_field_selector = stringify_field_selector(api_field_selector)
            if self.fields_param_mode == 'full':
                params['fields'] = 'items[{0}]'.format(api_field_selector)
            else:
                params['fields'] = api_field_selector

        response = reactor.call_method(
            self.path,
            params
        )

        ret = []
        for item_dict in response['items']:
            entity = self.picker.load_value(reactor, item_dict, field_selector)
            search_item_entity_class = self.entity_class.SearchItem
            search_item_entity = search_item_entity_class(id='')
            setattr(search_item_entity, search_item_entity_class.entity_field.name, entity)
            search_item_entity.match = MatchString.from_html(item_dict['match'])
            ret.append(search_item_entity)
        return ret


def _iter_obj(obj):
    if hasattr(obj, 'itervalues'):  # dict?
        return obj.itervalues()
    else:
        return iter(obj)


def _iter_ht_selector((sel, subsel), obj):
    if sel == '*':
        if subsel:
            for sub in _iter_obj(obj):
                for v in _iter_ht_selector(subsel, sub):
                    yield v
        else:
            for sub in _iter_obj(obj):
                yield sub
    else:
        if subsel:
            for v in _iter_ht_selector(subsel, obj[sel]):
                yield v
        else:
            yield obj[sel]


class ListMethod(object):
    def __init__(self, domain, path, entity_class, entity_field_pickers, list_selector, extra_params=(),
                 x_fields_wrapper=None, has_fields_param=True):
        assert isinstance(entity_field_pickers, EntityFieldPickers)

        self.domain = domain
        self.path = path
        self.entity_class = entity_class
        self.entity_field_pickers = entity_field_pickers
        entity_field_pickers.bind_to_entity_class(entity_class)
        self.list_selector = list_selector
        # list selector in head-tail format:
        #   ('a', 'b', 'c') -> ('a', ('b', ('c', None)))
        self._ht_selector = reduce(lambda x, y: (y, x), reversed(list_selector), None)
        self.extra_params = extra_params
        self.has_fields_param = has_fields_param
        self._x_fields_wrapper = '{0}' if x_fields_wrapper is None else x_fields_wrapper

    def execute_list(self, reactor, _, field_selector):
        params = {}
        params.update(self.extra_params)
        if self.has_fields_param:
            api_field_selector = {}
            self.entity_field_pickers.update_field_selector(api_field_selector, field_selector, with_id=True)
            params['fields'] = self._x_fields_wrapper.format(stringify_field_selector(api_field_selector))

        response = reactor.call_method(self.path, params)
        ret = []
        for entity_dict in _iter_ht_selector(self._ht_selector, response):
            ret.append(self.entity_field_pickers.load_entity(reactor, entity_dict, field_selector))
        return ret


class Registry(object):
    def __init__(self):
        self._getter_methods = {}
        self._search_methods_by_entity_class = {}
        self._list_methods = {}

    def register_get_method(self, **kwargs):
        method = GetMethod(**kwargs)
        self._getter_methods.setdefault(method.entity_class, []).append(method)

    def register_get_many_method(self, **kwargs):
        method = GetManyMethod(**kwargs)
        self._getter_methods.setdefault(method.entity_class, []).append(method)

    def register_get_many_as_list_method(self, **kwargs):
        method = GetManyAsListMethod(**kwargs)
        self._getter_methods.setdefault(method.entity_class, []).append(method)

    def register_search_method(self, **kwargs):
        method = SearchMethod(**kwargs)
        self._search_methods_by_entity_class[method.entity_class] = method

    def register_list_method(self, **kwargs):
        method = ListMethod(**kwargs)
        self._list_methods[(method.entity_class, method.domain)] = method

    def get_search_method_by_entity_class(self, entity_class):
        return self._search_methods_by_entity_class[entity_class]

    def get_list_method(self, entity_class, domain):
        return self._list_methods[(entity_class, domain)]

    def get_getter_methods(self, entity_class):
        return list(self._getter_methods.get(entity_class, ()))

    def get_list_domains(self, entity_class):
        ret = []
        for (key_entity_class, key_domain) in self._list_methods:
            if key_entity_class is entity_class:
                ret.append(key_domain)
        return ret
