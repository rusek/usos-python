from .lang import DEFAULT_LANG
from .reactor import Reactor
from .fieldselector import parse as parse_field_selector
from .entities import User
from .extras import get_current_user, now


def _prep_fields(fields, entity_class):
    if fields is None:
        fields = entity_class.get_default_field_selector()
    elif isinstance(fields, basestring):
        fields = parse_field_selector(fields, entity_class)
    return fields


class EntityNotFound(Exception):
    pass


class Session(object):
    def __init__(self, client):
        self.client = client
        self.lang = DEFAULT_LANG

    def _make_reactor(self):
        return Reactor(self)

    def get(self, entity_class, id, fields=None):
        with self._make_reactor() as reactor:
            entity = reactor.spawn_entity(entity_class, id, _prep_fields(fields, entity_class), weak=True)
        if entity.id is None:
            raise EntityNotFound
        return entity

    def get_many(self, entity_class, ids, fields=None):
        with self._make_reactor() as reactor:
            entities = {id: reactor.spawn_entity(entity_class, id, _prep_fields(fields, entity_class), weak=True)
                        for id in ids}
        for id in entities.keys():
            if entities[id].id is None:
                del entities[id]
        return entities

    def search(self, entity_class, query, fields=None):
        with self._make_reactor() as reactor:
            return reactor.spawn_search(entity_class, query, _prep_fields(fields, entity_class))

    def list(self, entity_class, domain, fields=None):
        with self._make_reactor() as reactor:
            return reactor.spawn_list(entity_class, domain, _prep_fields(fields, entity_class))

    def get_current_user(self, fields=None):
        with self._make_reactor() as reactor:
            return get_current_user(reactor, _prep_fields(fields, User))

    def now(self):
        return now(self)
