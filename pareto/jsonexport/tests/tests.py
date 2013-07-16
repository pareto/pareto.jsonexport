import time
import os
import unittest
import multiprocessing
import tempfile
import shutil
import urllib2

try:
    import json
except ImportError:
    import simplejson as json

import transaction

from plone.app.testing import PloneSandboxLayer
from plone.testing import z2
from zope.configuration import xmlconfig
from plone.app.testing import PLONE_INTEGRATION_TESTING
from Products.CMFPlone.utils import _createObjectByType

from .. import serializers
from .. import service
from ..interfaces import ISerializer

here = os.path.abspath(os.path.dirname(__file__))


class DummyObject(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class TestCase(unittest.TestCase):
    def assertEquals(self, one, other):
        if isinstance(one, dict) and isinstance(other, dict):
            if sorted(one.keys()) != sorted(other.keys()):
                raise AssertionError(
                    'keys of dicts do not match (%r, %r)' % (
                        sorted(one.keys()), sorted(other.keys())))
            for key in one:
                try:
                    self.assertEquals(one[key], other[key])
                except AssertionError, e:
                    print '%r != %r' % (one, other)
                    print 'key %s: %r != %r' % (key, one[key], other[key])
                    raise e
        else:
            return super(TestCase, self).assertEquals(one, other)


class SerializersLayer(PloneSandboxLayer):
    defaultBases = (PLONE_INTEGRATION_TESTING,)

    def setUpZope(self, app, configurationContext):
        import pareto.jsonexport
        self.loadZCML('serializers.zcml', package=pareto.jsonexport)


class SerializersTestCase(TestCase):
    layer = SerializersLayer()

    def setUp(self):
        self.app = self.layer['app']
        self.portal = self.layer['portal']

        # Zope has good old factory methods to create content
        self.app.manage_addFolder('folder1', title='Folder 1')
        self.folder1 = self.app.folder1

        # Plone does it a little different...
        _createObjectByType(
            'Folder', self.portal, id='folder2', title='Folder 2')
        self.folder2 = self.portal.folder2
        self.folder2.setDescription('<p>Description.</p>')

        # AT document
        _createObjectByType(
            'Document', self.folder2, id='document1', title='Document 1')
        self.document1 = self.folder2.document1
        self.document1.setDescription('<p>Description.</p>')

        # AT NewsItem
        _createObjectByType(
            'News Item', self.folder2, id='newsitem1', title='News Item 1')
        self.newsitem1 = self.folder2.newsitem1
        self.newsitem1.setDescription('<p>Description.</p>')
        self.newsitem1.setImage(
            open(os.path.join(here, 'empty.png'), 'rb'), mimetype='image/png')
        self.newsitem1.setImageCaption('Image Caption 1')

    def test_non_archetypes_folder(self):
        serializer = ISerializer(self.folder1)
        results = serializer.to_dict()
        self.assertEquals(
            results, {
                'id': 'folder1',
                'title': 'Folder 1',
                '_children': []})

    def test_archetypes_folder(self):
        serializer = ISerializer(self.folder2)
        results = serializer.to_dict()
        self.assertEquals(
            results,
            dict(sorted({
                'id': 'folder2',
                'title': 'Folder 2',
                '_children': ['document1', 'newsitem1'],
                'description': '<p>Description.</p>',
                'subject': (),
                'creation_date': self.folder2.creation_date,
                'modification_date': self.folder2.modification_date,
                'creators': ('test_user_1_',),
                'contributors': ()}.items())))

    def test_archetypes_document(self):
        serializer = ISerializer(self.document1)
        results = dict(sorted(serializer.to_dict().items()))
        self.assertEquals(
            results,
            dict(sorted({
                'id': 'document1',
                'title': 'Document 1',
                'description': '<p>Description.</p>',
                'text': '',
                'subject': (),
                'creation_date': self.document1.creation_date,
                'modification_date': self.document1.modification_date,
                'creators': ('test_user_1_',),
                'contributors': ()}.items())))

    def test_archetypes_newsitem(self):
        serializer = ISerializer(self.newsitem1)
        result = serializer.to_dict()
        self.assertEquals(
            result, {
                'id': 'newsitem1',
                'title': 'News Item 1',
                'description': '<p>Description.</p>',
                'text': '',
                'subject': (),
                'creation_date': self.newsitem1.creation_date,
                'modification_date': self.newsitem1.modification_date,
                'image': self.newsitem1.getImage(),
                'imageCaption': 'Image Caption 1',
                'creators': ('test_user_1_',),
                'contributors': ()})

    def test_recursion(self):
        serializer = ISerializer(self.folder2)
        data = serializer.to_dict(recursive=True)
        self.assertEquals(len(data['_children']), 2)
        self.assertEquals(data['_children'][0]['id'], 'document1')
        self.assertEquals(data['_children'][1]['id'], 'newsitem1')


class ServiceTestCase(TestCase):
    layer = SerializersLayer()

    def setUp(self):
        self.portal = self.layer['portal']

        # Plone does it a little different...
        _createObjectByType(
            'Folder', self.portal, id='folder2', title='Folder 2')
        self.folder2 = self.portal.folder2

        # AT document
        _createObjectByType(
            'Document', self.folder2, id='document1', title='Document 1')
        self.document1 = self.folder2.document1
        self.document1.setDescription('<p>Description.</p>')

        # AT NewsItem
        _createObjectByType(
            'News Item', self.folder2, id='newsitem1', title='News Item 1')
        self.newsitem1 = self.folder2.newsitem1
        self.newsitem1.setDescription('<p>Description.</p>')
        self.newsitem1.setImage(
            open(os.path.join(here, 'empty.png'), 'rb'), mimetype='image/png')
        self.newsitem1.setImageCaption('Image Caption 1')

    def tearDown(self):
        pass

    def test_data_for_event(self):
        data = service.service.data_for_event('create', self.document1)
        self.assertEquals(len(data.keys()), 3)
        self.assertEquals(data['type'], 'create')
        self.assertEquals(data['path'], '/plone/folder2/document1')
        self.assertEquals(data['data']['id'], 'document1')

        data = service.service.data_for_event('delete', self.document1)
        self.assertEquals(
            data, {'path': '/plone/folder2/document1', 'type': 'delete'})

    def test_handle_event_threading(self):
        org_threaded = service.service.threaded
        org__handle_event = service.service._handle_event
        try:
            queue = multiprocessing.Queue()
            service.service.threaded = False
            @classmethod
            def _handle_event(cls, _type, instance):
                cls._handled = _type
                queue.put(_type)
            service.service._handle_event = _handle_event

            service.service.threaded = False
            service.service.handle_event('spam', self.document1)
            self.assertEquals(service.service._handled, 'spam')
            self.assertEquals(queue.get(), 'spam')

            service.service.threaded = True
            service.service.handle_event('eggs', self.document1)
            # I assume starting the sub-process takes so long that cls._handled
            # will always have the old value here
            self.assertRaises(
                multiprocessing.queues.Empty, queue.get, block=False)
            self.assertEquals(service.service._handled, 'spam')
            time.sleep(1)
            # since we use multiprocessing, after a while the queue will
            # be set, but cls._type will not, since the code runs in a
            # separate process
            self.assertEquals(service.service._handled, 'spam')
            self.assertEquals(queue.get(), 'eggs')
        finally:
            service.service.threaded = org_threaded
            service.service._handle_event = org__handle_event

    def test__handle_event(self):
        org_push_event = service.service.push_event
        org_log_event = service.service.log_event
        @classmethod
        def push_event(cls, data):
            cls._last_event = data
        service.service.push_event = push_event
        @classmethod
        def log_event(cls, timestamp, _type, path):
            cls._last_log = (timestamp, _type, path)
        service.service.log_event = log_event
        try:
            self.assertRaises(
                Exception, service.service._handle_event,
                'foobar', self.document1)

            before = time.time()
            service.service._handle_event('create', self.document1)
            self.assertEquals(
                sorted(service.service._last_event.keys()),
                ['data', 'path', 'timestamp', 'type'])
            self.assertEquals(
                service.service._last_event['path'],
                '/plone/folder2/document1')
            self.assertEquals(
                service.service._last_event['type'], 'create')
            self.assert_(
                service.service._last_event['timestamp'] >= before and
                service.service._last_event['timestamp'] <= time.time())
            self.assertEquals(
                service.service._last_event['data']['id'], 'document1')
            self.assertEquals(
                service.service._last_log,
                (service.service._last_event['timestamp'], 'create',
                    '/plone/folder2/document1'))

            service.service._handle_event('update', self.document1)
            self.assertEquals(
                sorted(service.service._last_event.keys()),
                ['data', 'path', 'timestamp', 'type'])

            service.service._handle_event('delete', self.document1)
            self.assertEquals(
                sorted(service.service._last_event.keys()),
                ['path', 'timestamp', 'type'])
        finally:
            service.service.push_event = org_push_event
            service.service.log_event = org_log_event

    def test_push_event(self):
        org_post_data = service.service.post_data
        org_maxtries = service.service.maxtries
        @classmethod
        def post_data(cls, data):
            cls._posted_data = data
            return cls._statuses.pop(0)
        service.service.post_data = post_data
        service.service.maxtries = 3
        try:
            # this should only be executed until the status is 200/201/204
            service.service._statuses = [200, 500, 500]
            service.service.push_event({'foo': 1})
            self.assertEquals(service.service._posted_data, {'foo': 1})
            self.assertEquals(service.service._statuses, [500, 500])
            # but up to maxtries times if it's not
            service.service._statuses = [500, 500, 500]
            service.service.push_event({'foo': 1})
            self.assertEquals(service.service._statuses, [])
        finally:
            service.service.post_data = org_post_data
            service.service.maxtries = org_maxtries

    def test_log_event(self):
        tempdir = tempfile.mkdtemp()
        try:
            org_logdir = service.service.logdir
            service.service.logdir = tempdir
            try:
                service.service.log_event(0, 'foobar', '/foo/bar')
                logpath =  os.path.join(tempdir, 'changes-19700101.log')
                self.assertEquals(open(logpath).read(), '0 foobar /foo/bar\n')
            finally:
                service.service.logdir = org_logdir
        finally:
            shutil.rmtree(tempdir)

    def test_post_data(self):
        org_urlopen = urllib2.urlopen
        try:
            org_username = service.service.username
            org_password = service.service.password
            org_url = service.service.url
            try:
                requests = []
                def urlopen(request):
                    requests.append(request)
                    response = DummyObject(status=123)
                    return response
                urllib2.urlopen = urlopen

                # check if normal requests come through
                service.service.url = 'http://example.com/'
                service.service.username = None
                service.service.password = None
                status = service.service.post_data({'foo': 1})
                self.assertEquals(status, 123)
                request = requests.pop()
                self.assertEquals(
                    request.headers['Content-type'], 'application/json')
                self.assertEquals(request.headers.get('Authorization'), None)
                self.assertEquals(request.get_data(), '{"foo": 1}')

                # test basic auth
                service.service.username = 'johnny'
                service.service.password = 'foobar'
                service.service.post_data({'foo': 1})
                request = requests.pop()
                self.assertEquals(
                    request.headers.get('Authorization'),
                    'Basic: am9obm55OmZvb2Jhcg==')
            finally:
                service.service.username = org_username
                service.service.password = org_password
                service.service.url = org_url
        finally:
            urllib2.urlopen = org_urlopen


class EventsLayer(PloneSandboxLayer):
    defaultBases = (PLONE_INTEGRATION_TESTING,)

    def setUpZope(self, app, configurationContext):
        import pareto.jsonexport
        self.loadZCML('serializers.zcml', package=pareto.jsonexport)
        self.loadZCML('events.zcml', package=pareto.jsonexport)


class EventHandlerTestCase(TestCase):
    layer = EventsLayer()

    def setUp(self):
        self.portal = self.layer['portal']

        self.org_threaded = service.service.threaded
        service.service.threaded = False

        self.org_handle_event = service.service.handle_event
        self.events = events = []
        @classmethod
        def handle_event(self, _type, instance):
            print 'handling event', _type, service.service.threaded
            events.append((_type, instance))
            print 'events now:', events
        service.service.handle_event = handle_event

    def tearDown(self):
        service.service.threaded = self.org_threaded
        service.service.handle_event = self.org_handle_event

    def test_create(self):
        _createObjectByType(
            'Folder', self.portal, id='folder_create', title='Folder')
        try:
            transaction.commit()
            self.assertEquals(len(self.events), 1)
            self.assertEquals(self.events[0][0], 'create')
            self.assertEquals(self.events[0][1].id, 'folder_create')
        finally:
            self.portal.manage_delObjects(['folder_create'])

    def test_update(self):
        _createObjectByType(
            'Folder', self.portal, id='folder_update', title='Folder')
        try:
            transaction.commit()
            self.events[:] = []
            self.portal.folder_update.title = 'Folder renamed'
            transaction.commit()
            self.assertEquals(len(self.events), 1)
            self.assertEquals(self.events[0][0], 'update')
        finally:
            self.portal.manage_delObjects(['folder_update'])

    def test_delete(self):
        _createObjectByType(
            'Folder', self.portal, id='folder_delete', title='Folder')
        self.events[:] = []
        self.portal.manage_delObjects(['folder_delete'])
        print 'going to check'
        self.assertEquals(len(self.events), 1)
        self.assertEquals(self.events[0][0], 'delete')
