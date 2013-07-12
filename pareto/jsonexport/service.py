import os
import fcntl
import datetime
import time

from interfaces import ISerializer


class service(object):
    url = ''
    maxtries = 3
    threaded = False

    @classmethod
    def render(cls, instance, recursive=False):
        serializer = ISerializer(instance)
        return serializer.serialize(recursive=recursive)

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
            data['data'] = cls.render(instance)
        return data

    @classmethod
    def push_event(cls, data):
        """ add a line to the event log and send the data to the remote service
        """
        jsondata = json.dumps(data)
        for i in range(cls.maxtries):
            status = cls.post_data(jsondata)
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


# actual Zope event handler dispatcher to the service's event dispatcher (not
# registered directly so it's easier to test, override, etc), registration to
# events is done from configure.zcml
def create_handler(event):
    service.handle_event('create', event.object)

def update_handler(event):
    service.handle_event('update', event.object)

def delete_handler(event):
    service.handle_event('delete', event.object)
