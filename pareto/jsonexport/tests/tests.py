import os
import unittest

try:
    import json
except ImportError:
    import simplejson as json

from plone.app.testing import PloneSandboxLayer
from plone.testing import z2
from zope.configuration import xmlconfig
from plone.app.testing import PLONE_INTEGRATION_TESTING
from Products.CMFPlone.utils import _createObjectByType

from .. import serializers
from .. import service
from ..interfaces import ISerializer

here = os.path.abspath(os.path.dirname(__file__))


class TestCase(unittest.TestCase):
    def assertEquals(self, one, other):
        if isinstance(one, dict) and isinstance(other, dict):
            if sorted(one.keys()) != sorted(other.keys()):
                raise AssertionError(
                    'keys of dicts do not match! (%r, %r)' % (
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
        results = serializer._to_dict()
        self.assertEquals(
            results, {
                'id': 'folder1',
                'title': 'Folder 1',
                '_children': []})

    def test_archetypes_folder(self):
        serializer = ISerializer(self.folder2)
        results = serializer._to_dict()
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
        results = dict(sorted(serializer._to_dict().items()))
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

        # test json serialization (since there's some DateTime objects in
        # there that don't serialize by default)
        result = serializer.serialize()
        self.assertEquals(
            json.loads(result), {
                'id': 'document1',
                'title': 'Document 1',
                'description': '<p>Description.</p>',
                'text': '',
                'subject': [],
                'creation_date': self.document1.creation_date.strftime(
                    '%Y%m%d-%H%M%S'),
                'modification_date': self.document1.modification_date.strftime(
                    '%Y%m%d-%H%M%S'),
                'creators': ['test_user_1_'],
                'contributors': []})

    def test_archetypes_newsitem(self):
        serializer = ISerializer(self.newsitem1)
        jsonresult = serializer.serialize()
        result = json.loads(jsonresult)
        result['image'] = json.loads(result['image'])
        self.assertEquals(
            result, {
                'id': 'newsitem1',
                'title': 'News Item 1',
                'description': '<p>Description.</p>',
                'text': '',
                'subject': [],
                'creation_date': self.newsitem1.creation_date.strftime(
                    '%Y%m%d-%H%M%S'),
                'modification_date': self.newsitem1.modification_date.strftime(
                    '%Y%m%d-%H%M%S'),
                'image': {
                    'width': 2,
                    'height': 2,
                    'size': 79,
                    'alt': 'News Item 1',
                },
                'imageCaption': 'Image Caption 1',
                'creators': ['test_user_1_'],
                'contributors': []})

    def test_recursion(self):
        serializer = ISerializer(self.folder2)
        data = serializer._to_dict(recursive=True)
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

    def testRender(self):
        jsonresult = service.service.render(self.document1)
        ret = json.loads(jsonresult)
        self.assertEquals(ret['id'], 'document1')

    def testDataForEvent(self):
        data = service.service.data_for_event('create', self.document1)
        self.assertEquals(len(data.keys()), 3)
        self.assertEquals(data['type'], 'create')
        self.assertEquals(data['path'], '/plone/folder2/document1')

