from .fieldselector import stringify as stringify_field_selector
from .methods import (
    primary_user_field_pickers, secondary_user_field_pickers
)
from .factory.methods import load_datetime
from .entities import User

_user_field_pickers = primary_user_field_pickers | secondary_user_field_pickers
_user_field_pickers.bind_to_entity_class(User)


def _make_fields_param_value(entity_pickers, field_selector):
    api_field_selector = {}
    entity_pickers.update_field_selector(api_field_selector, field_selector, with_id=True)
    return stringify_field_selector(api_field_selector)


def get_current_user(reactor, field_selector):
    response = reactor.call_method('services/users/user', dict(
        fields=_make_fields_param_value(_user_field_pickers, field_selector)
    ))
    return _user_field_pickers.load_entity(reactor, response, field_selector)


def now(session):
    return load_datetime(session.client.call_method('services/apisrv/now', {}))
