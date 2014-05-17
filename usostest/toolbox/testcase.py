import copy
import unittest

from usos.tal import Session
from usos.tal.factory.entities import Entity
from usos.tal.fieldselector import parse_basic as parse_basic_field_selector


class BaseClient(object):
    def __init__(self, call_method):
        self.call_method = call_method


class MethodCall(object):
    def __init__(self, params, response):
        self.params = params
        self.response = response

    def match_params(self, params):
        if self.params.viewkeys() != params.viewkeys():
            return False
        for param_name, param_value in params.iteritems():
            expected_value = self.params[param_name]
            if param_name == 'fields':
                if parse_basic_field_selector(param_value) != parse_basic_field_selector(expected_value):
                    return False
            else:
                if param_value != expected_value:
                    return False
        return True

    def get_response(self):
        if isinstance(self.response, Exception):
            raise self.response
        else:
            return copy.deepcopy(self.response)


class TestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestCase, self).__init__(*args, **kwargs)
        self._method_calls = {}
        self._session = Session(BaseClient(self._call_method))
        self._session.lang = 'en'

    def _call_method(self, path, params):
        method_calls = self._method_calls.get(path)
        self.assertIsNotNone(method_calls)
        for method_call in method_calls:
            if method_call.match_params(params):
                method_calls.remove(method_call)
                return method_call.get_response()
        self.fail('No method call matches {0}'.format(params))

    def add_method_call(self, path, params, response):
        self._method_calls.setdefault(path, []).append(MethodCall(params, response))

    def get(self, entity_class, id, fields=None):
        return self._session.get(entity_class, id, fields)

    def get_many(self, entity_class, ids, fields=None):
        return self._session.get_many(entity_class, ids, fields)

    def list(self, entity_class, domain, fields=None):
        return self._session.list(entity_class, domain, fields)

    def search(self, entity_class, query, fields=None):
        return self._session.search(entity_class, query, fields)

    def assert_same(self, first, second):
        if isinstance(first, (list, tuple)):
            self.assertIs(type(first), type(second))
            self.assertEqual(len(first), len(second))
            for first_item, second_item in zip(first, second):
                self.assert_same(first_item, second_item)
        elif isinstance(first, dict):
            self.assertIsInstance(second, dict)
            self.assertEqual(first.viewkeys(), second.viewkeys())
            for key in first.iterkeys():
                self.assert_same(first[key], second[key])
        elif isinstance(first, Entity):
            self.assertIs(type(first), type(second))
            for field in type(first).fields:
                if field.name in first.__dict__:
                    self.assertIn(field.name, second.__dict__)
                    self.assert_same(getattr(first, field.name), getattr(second, field.name))
                else:
                    self.assertNotIn(field.name, second.__dict__)
        else:
            self.assertEqual(first, second)
