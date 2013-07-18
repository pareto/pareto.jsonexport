from zope import interface
from OFS.SimpleItem import Item
from Products.CMFCore.utils import getToolByName

from Products.Archetypes.Field import ReferenceField

import interfaces


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

    def to_dict(self, recursive=False):
        # we find all of our own methods which are decorated using
        # serializer_for, then we know about the JSON key and know we can call
        # that method for the JSON value
        ret = {
            'type': self.instance.meta_type,
            'id': self.instance.getId(),
            'path': '/'.join(self.instance.getPhysicalPath()),
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


class ReferenceSerializer(Serializer):
    """ serialize an object as a reference

        used internally for ReferenceFields, etc.
    """
    def to_dict(self, recursive=False):
        return {
            'type': 'Reference',
            'subtype': self.instance.meta_type,
            'path': '/'.join(self.instance.getPhysicalPath()),
            'id': self.instance.getId(),
        }


class UnknownTypeSerializer(Serializer):
    """ serialize an unknown object with a small set of data

        used internally when an object for which there's no serializer
        registered is encountered as child of a serialized object
    """
    def to_dict(self, recursive=False):
        return {
            'type': 'UnknownType',
            'subtype': self.instance.meta_type,
            'path': '/'.join(self.instance.getPhysicalPath()),
            'id': self.instance.getId(),
        }


class ContentListingReference(Serializer):
    def to_dict(self, recursive=False):
        return {
            'type': 'Reference',
            'subtype': self.instance.meta_type,
            'path': self.instance.getPath(),
            'id': self.instance.getId(),
        }


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
        'allowDiscussion', 'acquireCriteria', 'constrainTypesMode',
        'customView', 'customViewFields',
        'description', 'excludeFromNav', 'immediatelyAddableTypes',
        'limit', 'limitNumber', 'locallyAllowedTypes', 'nextPreviousEnabled',
        'presentation', 'query', 'sort_on', 'sort_reversed', 'tableContents',
    )

    @serializer_for('description')
    def serialize_description(self):
        return self.instance.schema.get('description').getEditAccessor(
            self.instance)()

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
        ret['portal_type'] = self.instance.portal_type
        for field_id in self.instance.schema.keys():
            if field_id in self.skip_fields:
                continue
            field = self.instance.schema[field_id]
            value = self._get_from_schema(field_id)
            if isinstance(field, ReferenceField):
                value = [
                    ReferenceSerializer(item).to_dict() for item in value]
            elif isinstance(value, Item):
                serializer = interfaces.ISerializer(value)
                value = serializer.to_dict(recursive=True)
            ret[field_id] = value
        return ret

    def _get_from_schema(self, id):
        return self.instance.schema.get(id).getAccessor(self.instance)()


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
        return [ContentListingReference(item).to_dict() for item in items]


class ImageSerializer(Serializer):
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
