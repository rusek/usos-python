#!/usr/bin/env python

from __future__ import unicode_literals

from usos import tal
from usos.tal.factory.entities import (
    EntityField, OptionalEntityField, EntityListField, EntityMapField, get_entity_classes)
from usos.tal import naming
from usos.tal.methods import registry as method_registry
from usos.client import ClientError
from usostest.toolbox.generator import make_get_test, make_list_test, make_search_test

import argparse
import sys

from bootstrap import client as base_client


class ClientWrapper(object):
    def __init__(self, client):
        self.client = client
        self.requests = []

    def call_method(self, path, params):
        if verbose:
            print 'Calling {0} with {1}'.format(path, params)
        try:
            ret = self.client.call_method(path, params)
            self.requests.append((path, params, ret))
            return ret
        except ClientError as e:
            self.requests.append((path, params, e))
            raise

client_wrapper = ClientWrapper(base_client)
session = tal.Session(client_wrapper)
use_colors = sys.stdout.isatty()

if sys.stdout.encoding is None:
    import codecs
    sys.stdout = codecs.getwriter('UTF-8')(sys.stdout)


class LangAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        session.lang = values


make_test = False
verbose = False


class MakeTestAction(argparse.Action):
    def __init__(self, *args, **kwargs):
        super(MakeTestAction, self).__init__(nargs=0, *args, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        global make_test
        make_test = True


class VerboseAction(argparse.Action):
    def __init__(self, *args, **kwargs):
        super(VerboseAction, self).__init__(nargs=0, *args, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        global verbose
        verbose = True

parser = argparse.ArgumentParser()
parser.add_argument('--lang', action=LangAction)
parser.add_argument('--make_test', action=MakeTestAction)
parser.add_argument('--verbose', action=VerboseAction)

subparsers = parser.add_subparsers()


def print_entity(entity, indent='', child_indent=''):
    print '{0}{1}(id={2})'.format(indent, entity.__class__.__name__, entity.id)
    for field in entity.fields:
        if entity.is_loaded(field):
            value = getattr(entity, field.name)
            if isinstance(field, (EntityField, OptionalEntityField)) and value is not None:
                print_entity(value, '{0}  {1}: '.format(child_indent, field.name), '{0}  '.format(child_indent))
            elif isinstance(field, EntityListField):
                print '{0}  {1}: ({2} {3})'.format(
                    child_indent, field.name, len(value), 'item' if len(value) == 1 else 'items')
                for child_entity in value:
                    print_entity(child_entity, '{0}    '.format(child_indent), '{0}    '.format(child_indent))
            elif isinstance(field, EntityMapField):
                print '{0}  {1}: ({2} {3})'.format(
                    child_indent, field.name, len(value), 'item' if len(value) == 1 else 'items')
                for child_key, child_entity in value.iteritems():
                    print_entity(
                        child_entity,
                        '{0}    {1}: '.format(child_indent, child_key),
                        '{0}    '.format(child_indent)
                    )
            else:
                if isinstance(value, tal.MatchString):
                    if use_colors:
                        value = value.format('\x1b[31;1m', '\x1b[0m')
                    else:
                        value = unicode(value)

                print '{0}  {1}: {2}'.format(child_indent, field.name, value)


def add_extra_user_parsers(subparsers):
    def current_user(args):
        response = session.get_current_user(args.fields)
        print_entity(response)

    parser = subparsers.add_parser('current')
    parser.add_argument('--fields', default=None)
    parser.set_defaults(func=current_user)


def add_entity_parser(entity_class, name):
    def entity_get(args):
        response = session.get_many(entity_class, args.ids, args.fields)
        if make_test:
            make_get_test(entity_class, args.ids, args.fields, response, client_wrapper.requests)

        for entity in response.values():
            print_entity(entity)
        #print 'entity_get', entity_class, args

    def entity_search(args):
        query = unicode(args.query, 'UTF-8', 'replace')
        response = session.search(entity_class, query, args.fields)
        if make_test:
            make_search_test(entity_class, query, args.fields, response, client_wrapper.requests)

        for entity in response:
            print_entity(entity)

    def entity_list(args):
        response = session.list(entity_class, args.domain, args.fields)
        if make_test:
            make_list_test(entity_class, args.domain, args.fields, response, client_wrapper.requests)

        for entity in response:
            print_entity(entity)

    def entity_fields(args):
        for field in entity_class.fields:
            print field.name

    def entity_domains(args):
        for domain in method_registry.get_list_domains(entity_class):
            print domain

    entity_parser = subparsers.add_parser(name)
    entity_subparsers = entity_parser.add_subparsers()

    entity_get_parser = entity_subparsers.add_parser('get')
    entity_get_parser.add_argument('ids', nargs='+')
    entity_get_parser.add_argument('--fields', default=None)
    entity_get_parser.set_defaults(func=entity_get)

    entity_fields_parser = entity_subparsers.add_parser('fields')
    entity_fields_parser.set_defaults(func=entity_fields)

    entity_domains_parser = entity_subparsers.add_parser('domains')
    entity_domains_parser.set_defaults(func=entity_domains)

    entity_search_parser = entity_subparsers.add_parser('search')
    entity_search_parser.add_argument('query')
    entity_search_parser.add_argument('--fields', default=None)
    entity_search_parser.set_defaults(func=entity_search)

    entity_list_parser = entity_subparsers.add_parser('list')
    entity_list_parser.add_argument('domain')
    entity_list_parser.add_argument('--fields', default=None)
    entity_list_parser.set_defaults(func=entity_list)

    if name == 'user':
        add_extra_user_parsers(entity_subparsers)


for entity_class in get_entity_classes():
    add_entity_parser(entity_class, naming.convert(entity_class.__name__, 'camelcase', 'lowercase_underscore'))


def now(args):
    print session.now()

now_parser = subparsers.add_parser('now')
now_parser.set_defaults(func=now)

args = parser.parse_args()
args.func(args)
