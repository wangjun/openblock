#   Copyright 2007,2008,2009,2011 Everyblock LLC, OpenPlans, and contributors
#
#   This file is part of ebpub
#
#   ebpub is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   ebpub is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with ebpub.  If not, see <http://www.gnu.org/licenses/>.
#

from django import http
from django.conf import settings
from django.core.mail import SMTPConnection, EmailMultiAlternatives
from django.template.loader import render_to_string
from ebpub.metros.allmetros import get_metro
import constants # relative import
import random
import urllib

# In Python 2.5+, the sha library was deprecated in favor of hashlib.
try:
    import hashlib
    sha_constructor = hashlib.sha1
except ImportError:
    import sha
    sha_constructor = sha.new

###############################
# E-MAIL ADDRESS VERIFICATION #
###############################

# We use the same e-mail verification functions for account creation
# and password reset, but each takes a 'task' argument, which is either
# CREATE_TASK or RESET_TASK.

CREATE_TASK = 1
RESET_TASK = 2

def make_email_hash(email, task):
    salt = {CREATE_TASK: settings.PASSWORD_CREATE_SALT, RESET_TASK: settings.PASSWORD_RESET_SALT}[task]
    return sha_constructor(salt % (settings.SECRET_KEY, email)).hexdigest()[:6]

def verification_url(email, task):
    params = {'e': email, 'h': make_email_hash(email, task)}
    url = {CREATE_TASK: 'c', RESET_TASK: 'r'}[task]
    return '/accounts/%s/?%s' % (url, urllib.urlencode(params))

def send_verification_email(email, task):
    domain = settings.EB_DOMAIN
    url = 'http://%s%s' % (domain, verification_url(email, task))
    template_name = {CREATE_TASK: 'register', RESET_TASK: 'password_reset'}[task]
    text_content = render_to_string('accounts/%s_email.txt' % template_name, {'url': url, 'email': email})
    html_content = render_to_string('accounts/%s_email.html' % template_name, {'url': url, 'email': email})

    if settings.DEBUG:
        print text_content
        print html_content
    else:
        subject = {CREATE_TASK: 'Please confirm account', RESET_TASK: 'Password reset request'}[task]
        conn = SMTPConnection() # Use default settings.
        message = EmailMultiAlternatives(subject, text_content, settings.GENERIC_EMAIL_SENDER,
            [email], connection=conn)
        message.attach_alternative(html_content, 'text/html')
        message.send()


##############
# LOGGING IN #
##############

def login(request, user):
    """
    Logs the given user into the given HttpRequest, setting the correct
    bits in the session.
    """
    if constants.USER_SESSION_KEY in request.session:
        if request.session[constants.USER_SESSION_KEY] != user.id:
            # To avoid reusing another user's session, create a new, empty
            # session if the existing session corresponds to a different
            # authenticated user.
            request.session.flush()
    else:
        request.session.cycle_key()

    # Set the session variables. Note that we save the user's e-mail address
    # in the session, despite the fact that this is redundant, so that we can
    # access it without having to do a database lookup.
    request.session[constants.USER_SESSION_KEY] = user.id
    request.session[constants.EMAIL_SESSION_KEY] = user.email

    if hasattr(request, 'user'):
        request.user = user

def login_required(view_func):
    """
    Decorator that requires login before a given view function can be
    accessed.
    """
    def inner_view(request, *args, **kwargs):
        if not request.user.is_anonymous():
            return view_func(request, *args, **kwargs)
        request.session['next_url'] = request.path
        return http.HttpResponseRedirect('/accounts/login/')
    return inner_view
