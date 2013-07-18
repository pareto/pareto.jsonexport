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
    @classmethod
    def render(cls, instance, recursive=False):
        serializer = ISerializer(instance)
        data = serializer.to_dict(recursive=recursive)
        _json = jsonutils.to_json(data)
        import pprint, json
        open('/tmp/json', 'w').write(_json)
        open('/tmp/json_pretty', 'w').write(pprint.pformat(json.loads(_json)))
        return _json
