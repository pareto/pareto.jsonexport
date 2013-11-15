from zope import interface
from OFS.SimpleItem import Item
from Products.CMFCore.utils import getToolByName

from Products.Archetypes.Field import ReferenceField
from Products.Archetypes.Widget import RichWidget

from archetypes.schemaextender.extender import instanceSchemaFactory

import interfaces
import html

try:
    from pareto.jsonexport.config import BASE_URL 
except ImportError:  
    BASE_URL = ''

try:
    from pareto.jsonexport.config import DIMENSIONS 
except ImportError:  
    DIMENSIONS = [
        'full', 'large', 'preview', 'mini', 'thumb', 'tile', 'icon', 'listing', 
        'leadimage', 'sidebar', 'summary', 'client'
    ]

# base classes
def serializer_for(attrId):
    """ decorator to mark methods as serializers for a single field

        requires one argument, attrId, which is used as the key by which
        the serialized value is stored
    """
    def decorator(func):
        func.serializer_for = attrId
        return func
    return decorator


class Serializer(object):
    """ base class for serializers

        this supports a single method 'serialize' that generates JSON for
        an object

        subclasses should add methods marked with a special decorator
        'serializer_for' (see above) to the class, those methods are called
        for serialization of single fields
    """
    interface.implements(interfaces.ISerializer)

    def __init__(self, instance):
        self.instance = instance
        if getattr(instance, 'getObject', False):
            self.instance = instance.getObject()
        self.portal_url = self.instance.portal_url()

    def clean_path(self, obj):
        return [x for i, x in enumerate(obj.getPhysicalPath()) if i != 1]

    def clean_url(self, obj):
        return '/'.join(self.clean_path(obj))

    def url(self, obj):
        return BASE_URL + self.clean_url(obj)
    
    def dimensionize(self, obj, field_id=''):
        url = self.url(obj)
        if field_id:
            url = '/'.join([self.url(obj), field_id])
        return dict([(d, ('%s_%s' % (url, d)).rstrip('_full')) 
                     for d in DIMENSIONS])

    def to_dict(self, recursive=False):
        # we find all of our own methods which are decorated using
        # serializer_for, then we know about the JSON key and know we can call
        # that method for the JSON value
        ret = {
            'type': self.instance.meta_type,
            'id': self.instance.getId(),
            'path': self.url(self.instance),
        }
        for attrName in dir(self):
            if attrName.startswith('_'):
                continue
            attr = getattr(self, attrName)
            if (not callable(attr) or
                    not hasattr(attr, 'serializer_for')):
                continue
            key = attr.serializer_for
            value = attr()
            ret[key] = value
        if recursive:
            # _children is a magic marker for child contents
            children = ret.get('_children')
            if children is not None:
                children_data = []
                for childid in children:
                    child = getattr(self.instance, childid)
                    try:
                        serializer = interfaces.ISerializer(child)
                    except TypeError:
                        children_data.append(
                            UnknownTypeSerializer(child).to_dict())
                        continue
                    children_data.append(serializer.to_dict(recursive=True))
                ret['_children'] = children_data
        return ret

    @serializer_for('path')
    def serialize_path(self):
        return self.url(self.instance)


class SimpleSerializer(Serializer):
    """ serialize a simple object
    """
    @property
    def type(self):
        return 'Simple'

    def to_dict(self, recursive=False):
        return {
            'type': self.type,
            'subtype': self.instance.meta_type,
            'path': self.url(self.instance),
            'id': self.instance.getId(),
        }


class ReferenceSerializer(SimpleSerializer):
    """ serialize an object as a reference

        used internally for ReferenceFields, etc.
    """
    @property
    def type(self):
        return 'Reference'



class UnknownTypeSerializer(Serializer):
    """ serialize an unknown object with a small set of data

        used internally when an object for which there's no serializer
        registered is encountered as child of a serialized object
    """
    @property
    def type(self):
        return 'UnknownType'


class ATSerializer(Serializer):
    """ base class for ArcheTypes objects

        since this provides the base fields of all the AT content types,
        it can be used as concrete default ATCTContent serializer

        on serialization, this looks at a class-attribute called 'skip_fields'
        to find schema fields _not_ to serialize, the rest of the schema
        fields will be found by looking at the schema (in addition to the
        default behaviour of looking at marked methods)
    """

    skip_fields = (
        'allowDiscussion', 'acquireCriteria', 'constrainTypesMode', 'title', 
        'description', 'customView', 'customViewFields', 'excludeFromNav',
        'limit', 'limitNumber', 'locallyAllowedTypes', 'nextPreviousEnabled',
        'presentation', 'query', 'sort_on', 'sort_reversed', 'tableContents',
        'immediatelyAddableTypes',
    )

    def rich_text(self, value):
        return value

    @serializer_for('title')
    def serialize_title(self):
        return self._get_from_schema('title', self.instance.schema) 
    
    @serializer_for('description')
    def serialize_description(self):
        return self._get_from_schema('description', self.instance.schema) 

    @serializer_for('state')
    def serialize_workflow_state(self):
        wft = getToolByName(self.instance, 'portal_workflow')
        wfs = wft.getWorkflowsFor(self.instance)
        assert len(wfs) <= 1, (
            'Unexpected error: more than one workflow registered for %s' % (
                self.instance,))
        if not wfs:
            return None
        return wft.getStatusOf(wfs[0].id, self.instance)['review_state']

    def to_dict(self, *args, **kwargs):
        ret = super(ATSerializer, self).to_dict(*args, **kwargs)
        ret['portal_type'] = portal_type = self.instance.portal_type
        schema = instanceSchemaFactory(self.instance)
        for field_id in schema.keys():
            if field_id in self.skip_fields:
                continue
            field = schema[field_id]
            _schema = schema
            if field_id in self.instance.schema:
                _schema = self.instance.schema
            value = self._get_from_schema(field_id, _schema)
            if isinstance(field, ReferenceField):
                value = [
                    ReferenceSerializer(item).to_dict() for item in value]
            elif isinstance(field.widget, RichWidget):
                value = self.rich_text(value)
            elif isinstance(value, Item):
                serializer = interfaces.ISerializer(value)
                value = serializer.to_dict(recursive=True)
            elif field_id == 'image' and self.instance.portal_type == 'Image':
                continue
            elif field_id == 'leadImage':
                if value:
                    value = {
                        'dimensions': self.dimensionize(value, field_id),
                        'width': value.width,
                        'height': value.height,
                    }
                else:
                    value = ""
            elif hasattr(value, 'blob'):
                # file or image content, ignore
                continue
            ret[field_id] = value
        return ret

    def _get_from_schema(self, id, schema):
        return self.instance.getField(id).getAccessor(self.instance)()


# actual serializer implementations
class ItemSerializer(Serializer):
    """ the very basics, can be registered as a default handler
    """
    @serializer_for('id')
    def serialize_id(self):
        _id = self.instance.id
        if callable(_id):
            _id = _id()
        return _id

    @serializer_for('title')
    def serialize_title(self):
        return self.instance.title


class FolderSerializer(ItemSerializer):
    """ basic folder serializer

        provides an additional '_children' (marked with an underscore to
        prevent name clashes) value in the dict that contains the ids
        of the folder's children
    """
    @serializer_for('_children')
    def serialize_items(self):
        return self.instance.objectIds()


class ATFolderSerializer(ATSerializer):

    @serializer_for('_children')
    def serialize_items(self):
        return self.instance.objectIds()


class CollectionSerializer(ATSerializer):
    @serializer_for('results')
    def serialize_items(self):
        items = self.instance.results(batch=False)
        return [ReferenceSerializer(item).to_dict() for item in items]


class ImageSerializer(ItemSerializer):
    @serializer_for('width')
    def serialize_width(self):
        return self.instance.width

    @serializer_for('height')
    def serialize_height(self):
        return self.instance.height

    @serializer_for('size')
    def serialize_size(self):
        return self.instance.size

    @serializer_for('alt')
    def serialize_alt(self):
        return self.instance.alt
