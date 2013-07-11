try:
    import json
except ImportError:
    import simplejson as json

import jsonutils

def serializerFor(attrId):
    def decorator(func):
        func.serializerFor = attrId
        return func
    return decorator

class Serializer(object):
    """ base class for serializers
    """
    def __init__(self, instance):
        self.instance = instance

    def serialize(self):
        return json.dumps(self._to_dict(), cls=jsonutils.JSONEncoder)

    def _to_dict(self):
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
        return ret


class ATSerializer(Serializer):
    def _to_dict(self):
        ret = super(ATSerializer, self)._to_dict()
        for fieldId in self.ATFieldIds:
            value = self._get_from_schema(fieldId)
            ret[fieldId] = value
        return ret

    def _get_from_schema(self, id):
        return self.instance.schema.get(id).getAccessor(self.instance)()


class FolderSerializer(Serializer):
    @serializerFor('id')
    def serializeId(self):
        return self.instance.id

    @serializerFor('title')
    def serializeTitle(self):
        return self.instance.title

    @serializerFor('items')
    def serializeItems(self):
        return self.instance.objectIds()


class ATFolderSerializer(ATSerializer):
    ATFieldIds = ('id', 'title')

    @serializerFor('items')
    def serializeItems(self):
        return self.instance.objectIds()


class ATDocumentSerializer(ATSerializer):
    ATFieldIds = (
        'id', 'title', 'description', 'text', 'subject', 'creation_date',
        'modification_date', 'creators', 'contributors')
