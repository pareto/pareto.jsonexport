import os
import fcntl
import datetime
import time
import urllib2
import socket
import base64

from zope import lifecycleevent

from interfaces import ISerializer

import jsonutils


class service(object):
    """ provide the core services, serialization and HTTP interaction

        this is basically the glue code of the application, where the
        components come together
    """
    # move to some pluggable config mechanism (with optional ZMI/Plone
    # management something)
    url = ''
    username = None
    password = None
    maxtries = 3
    threaded = False
    logdir = '/tmp/'

    @classmethod
    def render(cls, instance, recursive=False):
        serializer = ISerializer(instance)
        data = serializer.to_dict(recursive=recursive)
        return jsonutils.to_json(data)
