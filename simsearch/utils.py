import time
import threading
import logging
import scipy
import random
import cPickle as pickle
import os
import copy


def get_basic_logger():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s')
    return logging.getLogger()
logger = get_basic_logger()


def show_time_taken(func):
    def new(self, *args, **kw):
        start = time.time()
        res = func(self, *args, **kw)
        timed = time.time() - start
        logger.info('%.2f sec.', timed)
        setattr(self, '_time_taken_'+func.__name__, timed)
        return res
    return new


class Serializable(object):
    @show_time_taken
    def dump(self, path):
        return pickle.dump(self, open(path, 'wb'), -1)

    @show_time_taken
    def dumps(self):
        return pickle.dumps(self, -1)

    @staticmethod
    @show_time_taken
    def load(path):
        return pickle.load(open(path, 'rb'))

    @staticmethod
    @show_time_taken
    def loads(ser_str):
        return pickle.loads(ser_str)


class ThreadingMixIn:
    def process_request_thread(self, request, client_address):
        try:
            self.finish_request(request, client_address)
            self.close_request(request)
        except:
            self.handle_error(request, client_address)
            self.close_request(request)

    def process_request(self, request, client_address):
        """Start a new thread to process the request."""
        t = threading.Thread(
            target = self.process_request_thread,
            args   = (request, client_address))
        t.start()


def listify(l):
    if not isinstance(l, list):
        l = [l]
    return l


# from webpy
def auto_assign(self, locals):
    """
    Automatically assigns local variables to `self`.

        >>> self = storage()
        >>> autoassign(self, dict(a=1, b=2))
        >>> self
        <Storage {'a': 1, 'b': 2}>

    Generally used in `__init__` methods, as in:

        def __init__(self, foo, bar, baz=1): autoassign(self, locals())
    """
    for (key, value) in locals.iteritems():
        if key == 'self':
            continue
        setattr(self, key, value)


# from tornado web
def _utf8(s):
    if isinstance(s, unicode):
        s = s.encode("utf-8")
    elif not isinstance(s, str):
        s = str(s)
    return s


# from tornado web
def _unicode(s):
    if isinstance(s, str):
        s = s.decode("utf-8")
    elif not isinstance(s, unicode):
        s = str(s).decode("utf-8")
    return s


# from tornado web
def _time_independent_equals(a, b):
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)
    return result == 0


# from tornado web
class _O(dict):
    """Makes a dictionary behave like an object."""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)
    def __setattr__(self, name, value):
        self[name] = value


def parse_config_file(path, **opts):
    cf = {}
    execfile(path, cf, cf)
    opts.update(**cf)
    return _O(opts)


def argsort_best(arr, best_k, reverse=False):
    """Fast computation of the best k elements in an array using a simple randomized
    algorithm.
    """
    def get_best_threshold(arr, threshold=0, sample_size=1000):
        if len(arr) >= sample_size:
            sample = random.sample(arr, sample_size)
            new_threshold = scipy.mean(sample)
        else:
            new_threshold = arr.mean()

        new_arr = arr[(arr >= new_threshold).nonzero()[0]]
        if len(new_arr) <= best_k:
            return threshold
        if new_threshold == threshold:
            return threshold
        else:
            return get_best_threshold(new_arr, new_threshold)

    threshold = get_best_threshold(arr)
    best_indexes = (arr >= threshold).nonzero()[0]

    if (arr[best_indexes] == threshold).all():
        best_indexes = best_indexes[:best_k]

    return scipy.array(sorted(best_indexes, key=lambda i: arr[i], reverse=reverse))[:best_k]


def get_all_sub_dirs(path):
    paths = []
    d = os.path.dirname(path)
    while d not in ('', '/'):
        paths.append(d)
        d = os.path.dirname(d)
    if '.' not in paths:
        paths.append('.')
    return paths


def save_attrs(obj, attr_names):
    return dict((k, copy.deepcopy(v)) for k, v in obj.__dict__.items() if k in attr_names)


def load_attrs(obj, attrs):
    for k, v in attrs.items():
        if k in obj.__dict__:
            obj.__dict__[k] = v
