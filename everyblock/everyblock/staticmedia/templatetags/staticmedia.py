#   Copyright 2007,2008,2009 Everyblock LLC
#
#   This file is part of everyblock
#
#   everyblock is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   everyblock is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with everyblock.  If not, see <http://www.gnu.org/licenses/>.
#

import os.path
from django import template
from django.conf import settings
from everyblock.utils.genstaticversions import lookup

register = template.Library()

def has_minified_version(resource):
    if resource.startswith('/'):
        resource = resource[1:]
    return os.path.exists(minified_path(os.path.join(settings.EB_MEDIA_ROOT, resource)))

def minified_path(path):
    """
    Returns a path to a minified resource.

    Example:

    >>> minified_path('/scripts/maps.js')
    '/scripts/maps.min.js'
    """
    return '%s.min%s' % os.path.splitext(path)

def is_versioned(path):
    return lookup(path)

def versioned_path(path, vhash):
    return '/v%s%s' % (vhash, path)

def production_path(path):
    """
    Returns a path to a resource in a production environment, which
    may include a minified alternative and a version hash.
    """
    orig_path = path
    vhash = is_versioned(path)
    if vhash:
        path = versioned_path(path, vhash)
    if has_minified_version(orig_path):
        path = minified_path(path)
    return path

class AutoVersionNode(template.Node):
    def __init__(self, resource):
        self.resource = resource

    def render(self, context):
        path = self.resource
        if settings.AUTOVERSION_STATIC_MEDIA:
            path = production_path(path)
        return '%s%s' % (settings.EB_MEDIA_URL, path)

@register.tag(name='autoversion')
def do_autoversion(parser, token):
    try:
        tag_name, resource = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, '%r tag requires a single argument' % token.contents.split()[0]
    if not (resource[0] == resource[-1] and resource[0] in ('"', "'")):
        raise template.TemplateSyntaxError, "%r tag's argument should be in quotes" % tag_name
    return AutoVersionNode(resource[1:-1])
