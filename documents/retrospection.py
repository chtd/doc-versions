# -*- encoding: utf-8 -*-

from datetime import datetime
from contextlib import contextmanager
from functools import wraps
import threading

from django.http import HttpResponseRedirect
from django.contrib import messages
from django.conf import settings


''' 
Retrospection is an ability to view the whole system state 
at some time in the past
'''


NOW_FIELD = 'RETROSPECTION_DATETIME'
DATETIME_FORMAT = getattr(settings, 'DATETIME_FORMAT', '%Y-%m-%d %H:%M:%S')
DJANGO_DATETIME_FORMAT = getattr(settings, 'DJANGO_DATETIME_FORMAT', "Y-m-d H:i:s")


def get_or_create_now():
    ''' 
    Return the thread-local object, that stores current time 
    in its "dt" attribute.
    '''
    if not hasattr(settings, NOW_FIELD):
        setattr(settings, NOW_FIELD, threading.local())
    return getattr(settings, NOW_FIELD)


def now(request=None):
    '''
    Return the time set in given request (or in current thread, if request 
    is not given). If there is no current time set in the thread, this
    time is set. Successive calls will return the same time till the end
    of this request, or till a new time will be set by **set_now** call.
    '''
    dt = getattr(get_or_create_now(), 'dt', None)
    if request is not None:
        dt = request.session.get(NOW_FIELD)
        if dt:
            try: return datetime.strptime(dt, DATETIME_FORMAT)
            except ValueError: pass
    if dt is None:
        dt = datetime.now()
        setattr(get_or_create_now(), 'dt', dt)
    return dt


def set_now(dt=None):
    '''
    Set new time for the thread to given **dt**, or to **datetime.now**, 
    if no argument is given.
    '''
    setattr(get_or_create_now(), 'dt', dt or datetime.now())


class RetrospectionMiddleware(object):
    exit_param = 'exit_retrospection'
    enter_param = 'enter_retrospection'

    def process_request(self, request):
        ''' 
        This middleware provides retrospection for django views:
        
        1. It stores **now** in the user session (if it is not set by the user)
        2. It blocks POST requests when **now** is set by the user - this is
        retrospection mode, so it is read only.
        
        Not all POST requests should be blocked, though - for example, we 
        should not block requests that cancel the retrospection mode.
        To make a POST request in retrospection, pass "post_in_retrospection"
        in request.POST.

        Include this middleware in **settings.MIDDLEWARE_CLASSES** after the
        django **SessionMiddleware**.
        '''
        dt = request.session.get(NOW_FIELD)
        now_obj = get_or_create_now()
        if dt: # we are in retrospection mode
            if request.method == 'POST' and \
                    not 'post_in_retrospection' in request.POST:
                messages.error(request, u'Retrospection mode is read-only')
                return HttpResponseRedirect(request.META['PATH_INFO'])
            if self.exit_param in request.GET:
                exit_retrospection(request)
                now_obj.dt = None
            else:
                try:
                    now_obj.dt = datetime.strptime(dt, DATETIME_FORMAT)
                except ValueError:
                    now_obj.dt = None
        elif self.enter_param in request.GET:
            # enter retrospection mode
            dt = request.GET[self.enter_param]
            try:
                dt = datetime.strptime(dt, DATETIME_FORMAT)
            except ValueError:
                dt = datetime.now()
            request.session[NOW_FIELD] = dt.strftime(DATETIME_FORMAT)
            now_obj.dt = dt

    def process_response(self, request, response):
        ''' 
        After we are done with request processing, 
        remove variable with current time.
        '''
        get_or_create_now().dt = None
        return response


def retrospection_context_processor(request):
    ''' 
    Add retrospection_dt to template context, if we are in retrospection mode
    '''
    dt = request.session.get(NOW_FIELD)
    if dt:
        return {'retrospection_dt': datetime.strptime(dt, DATETIME_FORMAT)}
    return {}


def exit_retrospection(request):
    '''
    Exit retrospection mode by removing the NOW_FIELD from user session
    '''
    del request.session[NOW_FIELD]


@contextmanager
def current_time(dt=None):
    '''
    A context manager to set current time to given value 
    (datetime.now() by default).
    '''
    old = now()
    set_now(dt)
    try: yield
    finally: set_now(old)


def with_real_time(f):
    ''' 
    Decorator that sets real time for the duration of function execution
    '''

    @wraps(f)
    def wrapper(*args, **kwargs):
        with current_time():
            return f(*args, **kwargs)
    return wrapper
