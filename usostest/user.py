from usos import tal
from .toolbox.testcase import TestCase


class TestUserGet(TestCase):
    def test_default_fields(self):
        self.add_method_call(
            'services/users/user',
            {
                'fields': 'first_name|last_name',
                'user_id': '169934'
            },
            {
                'first_name': 'Krzysztof',
                'last_name': 'Rusek',
            }
        )
        self.assert_same(
            self.get(tal.User, '169934'),
            tal.User(
                '169934',
                first_name='Krzysztof',
                last_name='Rusek',
            )
        )

    def test_fields_from_users_user(self):
        self.add_method_call(
            'services/users/user',
            {
                'fields': 'first_name|last_name|room[id|building_id|number|building_name]|sex|homepage_url|mobile_numbers|phone_numbers|profile_url',
                'user_id': '777',
            },
            {
                'first_name': 'AAAA',
                'last_name': 'BBBBBBBBBB',
                'room': {
                    'building_id': '33',
                    'number': '50000',
                    'id': '20000',
                    'building_name': {
                        'en': '',
                        'pl': 'Some building name',
                    },
                },
                'sex': 'M',
                'homepage_url': 'http://www.mimuw.edu.pl/~XXXXXXXXXXXXX',
                'mobile_numbers': [],
                'phone_numbers': None,
                'profile_url': 'https://usosweb.uw.edu.pl/kontroler.php?_action=actionx:katalog2/osoby/pokazOsobe(os_id:777)',
            }
        )
        
        self.assert_same(
            self.get(tal.User, '777', 'first_name|last_name|sex|profile_url|homepage_url|phone_numbers|mobile_numbers|room'),
            tal.User(
                '777',
                first_name='AAAA',
                last_name='BBBBBBBBBB',
                sex='male',
                profile_url='https://usosweb.uw.edu.pl/kontroler.php?_action=actionx:katalog2/osoby/pokazOsobe(os_id:777)&lang=2',
                homepage_url='http://www.mimuw.edu.pl/~XXXXXXXXXXXXX',
                phone_numbers=[],
                mobile_numbers=[],
                room=tal.Room(
                    '20000',
                    number='50000',
                    building=tal.Building(
                        '33',
                        name='Some building name',
                    ),
                ),
            )
        )

    def test_authored_theses(self):
        self.add_method_call(
            'services/theses/user',
            {
                'fields': 'authored_theses[titles|id]',
                'user_id': '55',
            },
            {
                'authored_theses': [
                    {
                        'titles': {
                            'en': 'Show me 1',
                            'pl': 'Hide me 1',
                        },
                        'id': '666345',
                    },
                    {
                        'titles': {
                            'en': 'Show me 2',
                            'pl': 'Hide me 2',
                        },
                        'id': '26393',
                    },
                ],
            }
        )
        
        self.assert_same(
            self.get(tal.User, '55', 'authored_theses'),
            tal.User(
                '55',
                authored_theses=[
                    tal.Thesis(
                        '666345',
                        name='Show me 1',
                    ),
                    tal.Thesis(
                        '26393',
                        name='Show me 2',
                    ),
                ],
            )
        )

    def test_user_not_found(self):
        self.add_method_call(
            'services/users/user',
            {
                'fields': 'first_name|last_name',
                'user_id': '5555555555',
            },
            None
        )
        
        self.assertRaises(tal.EntityNotFound, self.get, tal.User, '5555555555', None)
