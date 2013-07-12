try:
    import json
except ImportError:
    import simplejson as json

from zope import interface

import interfaces
import jsonutils


# base classes
def serializerFor(attrId):
    """ decorator to mark methods as serializers for a single field

        requires one argument, attrId, which is used as the key by which
        the serialized value is stored
    """
    def decorator(func):
        func.serializerFor = attrId
        return func
    return decorator


class Serializer(object):
    """ base class for serializers

        this supports a single method 'serialize' that generates JSON for
        an object

        subclasses should add methods marked with a special decorator
        'serializerFor' (see above) to the class, those methods are called
        for serialization of single fields
    """
    interface.implements(interfaces.ISerializer)

    def __init__(self, instance):
        self.instance = instance

    def serialize(self, recursive=False):
        return json.dumps(
            self._to_dict(recursive=recursive), cls=jsonutils.JSONEncoder)

    def _to_dict(self, recursive=False):
        # we find all of our own methods which are decorated using
        # serializerFor, then we know about the JSON key and know we can call
        # that method for the JSON value
        ret = {}
        for attrName in dir(self):
            if attrName.startswith('_'):
                continue
            attr = getattr(self, attrName)
            if (not callable(attr) or
                    not hasattr(attr, 'serializerFor')):
                continue
            key = attr.serializerFor
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
                    except KeyError:
                        children_data.append({'id': childid})
                        continue
                    children_data.append(serializer._to_dict(recursive=True))
                ret['_children'] = children_data
        return ret


class ATSerializer(Serializer):
    """ base class for ArcheTypes objects

        since this provides the base fields of all the AT content types,
        it can be used as concrete default ATCTContent serializer

        on serialization, this looks at a class-attribute called 'ATFieldIds'
        to find schema fields to serialize (in addition to the default
        behaviour of looking at marked methods)
    """
    ATFieldIds = (
        'id', 'title', 'subject', 'creation_date',
        'modification_date', 'creators', 'contributors',
    )

    @serializerFor('description')
    def serializeDescription(self):
        return self.instance.schema.get('description').getEditAccessor(
            self.instance)()

    def _to_dict(self, *args, **kwargs):
        ret = super(ATSerializer, self)._to_dict(*args, **kwargs)
        for fieldId in self.ATFieldIds:
            value = self._get_from_schema(fieldId)
            ret[fieldId] = value
        return ret

    def _get_from_schema(self, id):
        return self.instance.schema.get(id).getAccessor(self.instance)()


# actual serializer implementations
class EmptySerializer(Serializer):
    """ generates an empty dict as JSON result
    
        used as catch-all by default
    """
    def _to_dict(self, recursive=False):
        return {
            'error':
                'No serializer found for object %s' % (
                    self.instance.__class__,)}


class ItemSerializer(Serializer):
    """ the very basics, can be registered as a default handler
    """
    @serializerFor('id')
    def serializeId(self):
        _id = self.instance.id
        if callable(_id):
            _id = _id()
        return _id

    @serializerFor('title')
    def serializeTitle(self):
        return self.instance.title


class FolderSerializer(ItemSerializer):
    """ basic folder serializer
    
        provides an additional '_children' (marked with an underscore to
        prevent name clashes) value in the dict that contains the ids
        of the folder's children
    """
    @serializerFor('_children')
    def serializeItems(self):
        return self.instance.objectIds()


class ATFolderSerializer(ATSerializer):
    @serializerFor('_children')
    def serializeItems(self):
        return self.instance.objectIds()


class ATDocumentSerializer(ATSerializer):
    ATFieldIds = ATSerializer.ATFieldIds + ('text',)


class ATNewsItemSerializer(ATSerializer):
    ATFieldIds = ATSerializer.ATFieldIds + (
        'text', 'image', 'imageCaption', 
    )


class ATBlobSerializer(ATSerializer):
    pass
