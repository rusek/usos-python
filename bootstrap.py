import bottle
import json
import os.path
import urlparse
import subprocess
import threading
import time

from usos.client import Client
from usos.tal import Session


class ShutdownThread(threading.Thread):
    def run(self):
        time.sleep(1)
        WSGIRefServer.instance.shutdown()

oauth_verifier = None

@bottle.route('/')
def authorized():
    global oauth_verifier

    oauth_verifier = bottle.request.query['oauth_verifier']

    t = ShutdownThread()
    t.start()
    return """
        <b>

        Close window!

        </b>
    """


class WSGIRefServer(bottle.ServerAdapter):
    instance = None

    def run(self, handler): # pragma: no cover
        from wsgiref.simple_server import make_server, WSGIRequestHandler
        if self.quiet:
            class QuietHandler(WSGIRequestHandler):
                def log_request(*args, **kw): pass
            self.options['handler_class'] = QuietHandler
        srv = make_server(self.host, self.port, handler, **self.options)
        WSGIRefServer.instance = srv
        srv.serve_forever()


DIR = os.path.abspath(os.path.dirname(__file__))
CRED_FILE = os.path.join(DIR, 'credentials.json')

cred = json.load(open(CRED_FILE))

client = Client('https://usosapps.uw.edu.pl/')

client.consumer = cred['consumer_key'], cred['consumer_secret']
client.token = cred['token_key'], cred['token_secret']

try:
    client.call_method('services/apisrv/now', {})
except StopIteration:
    port = 8080
    client.token = None
    response = client.call_method('services/oauth/request_token', dict(
        oauth_callback='http://localhost:{0}/'.format(port),
        scopes='studies|offline_access|cards|crstests|email|grades|mobile_numbers|photo|placement_tests|slips|'
               'student_exams'
    ))
    response = dict(urlparse.parse_qsl(response))
    token = response['oauth_token'], response['oauth_token_secret']
    link = client.base_url + 'services/oauth/authorize?oauth_token=' + response['oauth_token']
    subprocess.check_call(['nohup', 'firefox', '-new-window', link], stdin=open('/dev/null'), stdout=open('/dev/null'),
                          stderr=open('/dev/null'))
    bottle.run(server=WSGIRefServer, quiet=True, host='localhost', port=port)

    client.token = token
    response = client.call_method('services/oauth/access_token', dict(
        oauth_verifier=oauth_verifier
    ))
    response = dict(urlparse.parse_qsl(response))

    token = response['oauth_token'], response['oauth_token_secret']
    client.token = token
    cred['token_key'], cred['token_secret'] = token
    json.dump(cred, open(CRED_FILE, 'w'))

session = Session(client)
