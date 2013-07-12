try:
    import json
except ImportError:
    import simplejson as json
import datetime
from DateTime import DateTime
from OFS.Image import Image

def datetime_to_json(dt):
    if isinstance(dt, datetime.date):
        return dt.strftime('%Y%m%d')
    else:
        return dt.strftime('%Y%m%d-%H%M%S')

def image_to_json(image):
    # XXX should we add an explicit path, even though it can be implied from
    # the context?
    ret = {
        'width': image.width,
        'height': image.height,
        'size': image.size,
        'alt': image.alt,
    }
    return json.dumps(ret)

json_serializers = [
    (datetime.datetime, datetime_to_json),
    (datetime.date, datetime_to_json),
    (DateTime, datetime_to_json),
    (Image, image_to_json),
]

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        for cls, serializer in json_serializers:
            if isinstance(obj, cls):
                return serializer(obj)
        return json.JSONEncoder.default(self, obj)
