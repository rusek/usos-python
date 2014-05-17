from .methods import registry
from ..client import ClientError
from .factory.entities import BaseEntityField


class Target(object):
    def __init__(self, entity, field_selector, weak):
        self.entity = entity
        self._field_selector = field_selector
        self.weak = weak
        self.field_names = set(self._field_selector.keys())

    def kill(self):
        if self.weak:
            self.entity.id = None
            self.field_names.clear()
        else:
            raise ClientError('Entity {0} with id {1} not found'.format(type(self.entity), self.entity.id))

    def has_same_field_selector(self, other):
        return self._field_selector is other._field_selector and self.field_names == other.field_names

    def get_subfield_selector(self, field_name):
        return self._field_selector[field_name]

    def get_field_selector(self, field_names):
        return {field_name: subfield_selector
                for field_name, subfield_selector in self._field_selector.iteritems()
                if field_name in field_names}

    def resolve_field(self, field_name, value):
        self.weak = False
        setattr(self.entity, field_name, value)
        self.field_names.remove(field_name)

    def is_active(self):
        # TODO weak targets should always be active
        return bool(self.field_names)

    def __repr__(self):
        return '<Target {0} {1}>'.format(self.entity, self.field_names)


class Reactor(object):
    def __init__(self, session):
        self._session = session
        self._prerequisites = []
        self._targets = {}
        self._values_cache = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.execute()

    @property
    def lang(self):
        return self._session.lang

    def call_method(self, path, params):
        return self._session.client.call_method(path, params)

    def spawn_list(self, entity_class, domain, field_selector):
        ret = []

        def do_list():
            try:
                method = registry.get_list_method(entity_class, domain)
            except KeyError:
                raise ValueError('Could not find list method for {0} and domain {1}'.format(entity_class, domain))
            ret.extend(method.execute_list(self, domain, field_selector))

        self._prerequisites.append(do_list)
        return ret

    def spawn_search(self, entity_class, query, field_selector):
        ret = []

        def do_search():
            try:
                method = registry.get_search_method_by_entity_class(entity_class)
            except KeyError:
                raise ValueError('Could not find search method for {0}'.format(entity_class))
            ret.extend(method.execute_search(self, query, field_selector))

        self._prerequisites.append(do_search)
        return ret

    def _resolve_and_cache_field(self, target, field_name, value):
        entity_class = type(target.entity)
        id = target.entity.id
        field = entity_class.fields[field_name]
        if isinstance(field, BaseEntityField):
            self._values_cache.setdefault((entity_class, id), {})[field_name] = field.map(lambda e: e.id, value)
        else:
            subfield_selector = target.get_subfield_selector(field_name)
            if not subfield_selector:  # subfield_selector == {}
                self._values_cache.setdefault((entity_class, id), {})[field_name] = value

        target.resolve_field(field_name, value)

    def spawn_entity(self, entity_class, id, field_selector, values=None, weak=False):
        entity = entity_class(id=id)
        target = Target(entity, field_selector, weak)
        if values is not None:
            for field_name in field_selector.iterkeys():
                if field_name in values:
                    self._resolve_and_cache_field(target, field_name, values[field_name])
        if target.is_active():
            self._targets.setdefault(entity_class, []).append(target)
        return entity

    def execute(self):
        prerequisites, self._prerequisites = self._prerequisites, None
        for f in prerequisites:
            f()

        while self._targets:
            self._execute_once()
            self._resolve_fields_from_cache()

        self._prerequisites = []
        self._values_cache = {}

    def _resolve_fields_from_cache(self):
        # TODO provide more efficient implementation that works with BaseEntityField subclasses
        for entity_class, targets in self._targets.items():
            new_targets = []
            for target in targets:
                cached_values = self._values_cache.get((entity_class, target.entity.id))
                if cached_values:
                    for field_name in target.field_names.copy():
                        if field_name in cached_values:
                            field = entity_class.fields[field_name]
                            subfield_selector = target.get_subfield_selector(field_name)
                            if isinstance(field, BaseEntityField):
                                pass
                                # Won't work because new targets will be inserted :(
                                # target.resolve_field(
                                #     field_name,
                                #     field.map(
                                #         lambda id: self.spawn_entity(entity_class, id, subfield_selector),
                                #         cached_values[field_name]
                                #     )
                                # )
                            elif not subfield_selector:
                                target.resolve_field(field_name, cached_values[field_name])
                if target.is_active():
                    new_targets.append(target)
            if new_targets:
                self._targets[entity_class] = new_targets
            else:
                del self._targets[entity_class]

    def _execute_once(self):
        best_candidacy = None
        entity_class, available_targets = next(self._targets.iteritems())

        for method in registry.get_getter_methods(entity_class):
            candidacy = method.make_candidacy(available_targets)
            if candidacy is not None and (best_candidacy is None or candidacy.score > best_candidacy.score):
                best_candidacy = candidacy

        if best_candidacy is None:
            raise ValueError('Could not find any method for targets {0}'.format(available_targets))

        targets_values = best_candidacy.execute(self)

        for target in best_candidacy.targets:
            values = targets_values[target.entity.id]
            if values is None:
                target.kill()
            else:
                for field_name in best_candidacy.field_names:
                    self._resolve_and_cache_field(target, field_name, values[field_name])

        # Caution: best_candidacy.execute(...) may have spawned new entities
        available_targets = filter(Target.is_active, self._targets[entity_class])
        if available_targets:
            self._targets[entity_class] = available_targets
        else:
            del self._targets[entity_class]
