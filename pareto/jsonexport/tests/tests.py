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

        # AT NewsItem with a reference to the other one
        _createObjectByType(
            'News Item', self.portal, id='newsitem2', title='News Item 2')
        self.newsitem2 = self.portal.newsitem2
        self.newsitem2.setDescription('<p>Description.</p>')
        self.newsitem2.setRelatedItems([self.newsitem1])

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
                'effectiveDate': None,
                'expirationDate': None,
                'language': 'en',
                'location': '',
                'creators': ('test_user_1_',),
                'contributors': (),
                'relatedItems': [],
                'rights': '',
            }.items())))

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
                'effectiveDate': None,
                'expirationDate': None,
                'language': 'en',
                'location': '',
                'creators': ('test_user_1_',),
                'contributors': (),
                'relatedItems': [],
                'tableContents': False,
                'presentation': False,
                'rights': '',
            }.items())))

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
                'effectiveDate': None,
                'expirationDate': None,
                'image': self.newsitem1.getImage(),
                'imageCaption': 'Image Caption 1',
                'language': 'en',
                'location': '',
                'creators': ('test_user_1_',),
                'contributors': (),
                'relatedItems': [],
                'rights': '',
            })

    def test_recursion(self):
        serializer = ISerializer(self.folder2)
        data = serializer.to_dict(recursive=True)
        self.assertEquals(len(data['_children']), 2)
        self.assertEquals(data['_children'][0]['id'], 'document1')
        self.assertEquals(data['_children'][1]['id'], 'newsitem1')

    def test_archetypes_reference_field(self):
        serializer = ISerializer(self.newsitem1)
        data = serializer.to_dict(recursive=True)
