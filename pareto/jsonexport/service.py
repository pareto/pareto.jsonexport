import os
import fcntl
import datetime
import time

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

    @classmethod
    def render(self, instance, recursive=False):
        serializer = ISerializer(instance)
        data = serializer.to_dict(recursive=recursive)
        return jsonutils.to_json(data)

    @classmethod
    def handle_event(cls, _type, instance):
        if cls.threaded:
            process = multiprocessing.Process(
                target=self._handle_event, args=(_type, instance))
            process.start()
        else:
            self._handle_event(_type, instance)

    def _handle_event(cls, _type, instance):
        # XXX add threading/multiprocessing
        assert _type in ('create', 'update', 'delete'), 'unsupported event'
        timestamp = time.time()
        data = cls.data_for_event(_type, instance)
        data['timestamp'] = timestamp
        cls.log_event(timestamp, _type, data['path'])
        cls.push_event(data)

    @classmethod
    def data_for_event(cls, _type, instance):
        data = {
            'type': _type,
            'path': '/'.join(instance.getPhysicalPath()),
        }
        if _type != 'delete':
            serializer = ISerializer(instance)
            instancedata = serializer.to_dict()
            data['data'] = instancedata
        return data

    @classmethod
    def push_event(cls, data):
        """ add a line to the event log and send the data to the remote service
        """
        # XXX add Zope logging
        for i in range(cls.maxtries):
            status = cls.post_data(data)
            if status in (200, 201, 204):
                break

    @classmethod
    def log_event(self, timestamp, _type, path):
        dt = datetime.datetime.from_timestamp(timestamp)
        logfile = os.path.join(cls.logdir, dt.strftime('changes-%Y%m%d.log'))
        fd = os.fopen(logfile, os.O_WRONLY | os.O_CREAT)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            try:
                os.write(fd, '%s %s %s\n' % (timestamp, _type, path))
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    @classmethod
    def post_data(self, data):
        jsondata = jsonutils.to_json(data)
        request = urllib2.Request(self.url)
        request.add_header('Content-Type', 'application/json')
        if self.username:
            creds = base64.standard_b64encode(
                '%s:%s' % (self.username, self.password))
            request.add_header('Authorization', 'Basic: %s' % (creds,))
        try:
            result = urllib2.urlopen(request)
        except (urllib2.HttpError, socket.Error):
            return -1
        else:
            return result.status


# actual Zope event handler dispatcher to the service's event dispatcher (not
# registered directly so it's easier to test, override, etc), registration to
# events is done from configure.zcml
def create_handler(event):
    service.handle_event('create', event.object)

def update_handler(event):
    service.handle_event('update', event.object)

def delete_handler(event):
    service.handle_event('delete', event.object)
