try:
    import json
except ImportError:
    import simplejson as json

from unittest import TestCase, TestSuite
from plone.app.testing import PLONE_INTEGRATION_TESTING
from Products.CMFPlone.utils import _createObjectByType

from OFS import Folder
from Products.ATContentTypes.content.folder import ATFolder
from Products.ATContentTypes.content.document import ATDocument

import registry
import serializers
import service


class DummyZopeObject(object):
    pass


class DummyZopeObjectSubClass(DummyZopeObject):
    pass


class DummyZopeObjectSerializer(serializers.Serializer):
    pass


class RegistryTestCase(TestCase):
    def setUp(self):
        self.registry = registry._Registry()

    def test_register_retrieve(self):
        self.assertRaises(KeyError, self.registry.get, DummyZopeObject())
        self.assertRaises(
            TypeError, self.registry.register, DummyZopeObject(),
            DummyZopeObjectSerializer)
        self.registry.register(DummyZopeObject, DummyZopeObjectSerializer)
        self.assertEquals(
            type(self.registry.get(DummyZopeObject())),
            DummyZopeObjectSerializer)
        #self.assertEquals(
        #    TypeError, self.registry.get, DummyZopeObject)

    def test_retrieve_subclass(self):
        self.registry.register(DummyZopeObject, DummyZopeObjectSerializer)
        self.assertEquals(
            type(self.registry.get(DummyZopeObjectSubClass())),
            DummyZopeObjectSerializer)


class JsonSerializersTestCase(TestCase):
    layer = PLONE_INTEGRATION_TESTING

    def setUp(self):
        self.app = self.layer['app']
        self.portal = self.layer['portal']

        reg = self.registry = registry._Registry()
        reg.register(Folder.Folder, serializers.FolderSerializer)
        reg.register(ATFolder, serializers.ATFolderSerializer)
        reg.register(ATDocument, serializers.ATDocumentSerializer)

        # Zope has good old factory methods to create content
        self.app.manage_addFolder('folder1', title='Folder 1')
        self.folder1 = self.app.folder1

        # Plone does it a little different...
        _createObjectByType(
            'Folder', self.portal, id='folder2', title='Folder 2')
        self.folder2 = self.portal.folder2

        # AT document
        _createObjectByType(
            'Document', self.portal, id='document1', title='Document 1')
        self.document1 = self.portal.document1
        self.document1.setDescription('<p>Description.</p>')

    def test_non_archetypes_folder(self):
        serializer = self.registry.get(self.folder1)
        results = serializer._to_dict()
        self.assertEquals(
            results,
            {'id': 'folder1',
                'title': 'Folder 1',
                'items': []})

    def test_archetypes_folder(self):
        serializer = self.registry.get(self.folder2)
        results = serializer._to_dict()
        self.assertEquals(
            results,
            {'id': 'folder2',
                'title': 'Folder 2',
                'items': []})

    def test_archetypes_document(self):
        serializer = self.registry.get(self.document1)
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
            json.loads(result),
            {'id': 'document1',
                'title': 'Document 1',
                'description': '<p>Description.</p>',
                'text': '',
                'subject': [],
                'creation_date': self.document1.creation_date.strftime(
                    'datetime:%Y%m%d-%H%M%S'),
                'modification_date': self.document1.modification_date.strftime(
                    'datetime:%Y%m%d-%H%M%S'),
                'creators': ['test_user_1_'],
                'contributors': []})
