# Python library for Remember The Milk API

__author__ = 'Sridhar Ratnakumar <http://nearfar.org/>'


import new
import warnings
import urllib
from md5 import md5


SERVICE_URL = 'http://api.rememberthemilk.com/services/rest/'
AUTH_SERVICE_URL = 'http://www.rememberthemilk.com/services/auth/'
DEBUG = False


class RTMError(Exception): pass

class RTMAPIError(RTMError): pass

class AuthStateMachine(object):

    class NoData(RTMError): pass

    def __init__(self, states):
        self.states = states
        self.data = {}

    def dataReceived(self, state, datum):
        if state not in self.states:
            raise RTMError, "Invalid state <%s>" % state
        self.data[state] = datum

    def get(self, state):
        if state in self.data:
            return self.data[state]
        else:
            raise AuthStateMachine.NoData, 'No data for <%s>' % state


class RTM(object):

    def __init__(self, apiKey, secret, token=None):
        self.apiKey = apiKey
        self.secret = secret
        self.auth = AuthStateMachine(['frob', 'token'])

        # this enables one to do 'rtm.tasks.getList()', for example
        for prefix, methods in API.items():
            setattr(self, prefix,
                    RTMAPICategory(self, prefix, methods))

        if token:
            self.auth.dataReceived('token', token)

    def _sign(self, params):
        "Sign the parameters with MD5 hash"
        pairs = ''.join(['%s%s' % (k,v) for k,v in sortedItems(params)])
        return md5(self.secret+pairs).hexdigest()

    def get(self, **params):
        "Get the XML response for the passed `params`."
        params['api_key'] = self.apiKey
        params['format'] = 'json'
        params['api_sig'] = self._sign(params)

        json = openURL(SERVICE_URL, params).read()
        data = dottedJSON(json)
        rsp = data.rsp

        if rsp.stat == 'fail':
            raise RTMAPIError, 'API call failed - %s (%s)' % (
                rsp.err.msg, rsp.err.code)
        else:
            return rsp

    def getNewFrob(self):
        rsp = self.get(method='rtm.auth.getFrob')
        self.auth.dataReceived('frob', rsp.frob)
        return rsp.frob

    def getAuthURL(self):
        try:
            frob = self.auth.get('frob')
        except AuthStateMachine.NoData:
            frob = self.getNewFrob()

        params = {
            'api_key': self.apiKey,
            'perms'  : 'delete',
            'frob'   : frob
            }
        params['api_sig'] = self._sign(params)
        return AUTH_SERVICE_URL + '?' + urllib.urlencode(params)

    def getToken(self):
        frob = self.auth.get('frob')
        rsp = self.get(method='rtm.auth.getToken', frob=frob)
        self.auth.dataReceived('token', rsp.auth.token)
        return rsp.auth.token

class RTMAPICategory:
    "See the `API` structure and `RTM.__init__`"

    def __init__(self, rtm, prefix, methods):
        self.rtm = rtm
        self.prefix = prefix
        self.methods = methods

    def __getattr__(self, attr):
        if attr in self.methods:
            rargs, oargs = self.methods[attr]
            name = 'rtm.%s.%s' % (self.prefix, attr)
            return lambda **params: self.callMethod(
                name, rargs, oargs, **params)
        else:
            raise AttributeError, 'No such attribute: %s' % attr

    def callMethod(self, name, rargs, oargs, **params):
        # Sanity checks
        for requiredArg in rargs:
            if requiredArg not in params:
                raise TypeError, 'Required parameter (%s) missing' % requiredArg

        for param in params:
            if param not in rargs + oargs:
                warnings.warn('Invalid parameter (%s)' % param)

        return self.rtm.get(method=name,
                            auth_token=self.rtm.auth.get('token'),
                            **params)



# Utility functions

def sortedItems(dictionary):
    "Return a list of (key, value) sorted based on keys"
    keys = dictionary.keys()
    keys.sort()
    for key in keys:
        yield key, dictionary[key]

def openURL(url, queryArgs=None):
    if queryArgs:
        url = url + '?' + urllib.urlencode(queryArgs)
    if DEBUG:
        print 'URL>', url
    return urllib.urlopen(url)

class dottedDict(object):
    "Make dictionary items accessible via the object-dot notation."

    def __init__(self, name, dictionary):
        self._name = name

        for key, value in dictionary.items():
            if type(value) is dict:
                value = dottedDict(key, value)
            elif type(value) in (list, tuple):
                value = [dottedDict('%s:%d' % (key, i), item)
                         for i, item in indexed(value)]
            setattr(self, key, value)

    def __repr__(self):
        children = [c for c in dir(self) if not c.startswith('_')]
        return 'dotted <%s> : %s' % (
            self._name,
            ', '.join(children))


def safeEval(string):
    return eval(string, {}, {})

def dottedJSON(json):
    return dottedDict('ROOT', safeEval(json))

def indexed(seq):
    index = 0
    for item in seq:
        yield index, item
        index += 1


# API spec

API = {
    'lists': {
        'getList':
            [(), ()]
        },
    'tasks': {
        'addTags':
            # [requiredArgs, optionalArgs]
            [('timeline', 'list_id', 'taskseries_id', 'task_id', 'tags'),
             ()],
        'getList':
            [(),
             ('list_id', 'filter', 'last_sync')]
        }
    }


def test(apiKey, secret, token=None):
    rtm = RTM(apiKey, secret, token)

    if token is None:
        print 'No token found'
        print 'Give me access here:', rtm.getAuthURL()
        raw_input('Press enter once you gave access')
        print 'Note down this token for future use:', rtm.getToken()

    rspTasks = rtm.tasks.getList(filter="due:today status:incomplete")
    print [t.name for t in rspTasks.tasks.list.taskseries]
    print rspTasks.tasks.list.id

    rspLists = rtm.lists.getList()
    # print rspLists.lists.list
    print [(x.name, x.id) for x in rspLists.lists.list]


