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

json_serializers = [
    (datetime.datetime, datetime_to_json),
    (datetime.date, datetime_to_json),
    (DateTime, datetime_to_json),
]

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        for cls, serializer in json_serializers:
            if isinstance(obj, cls):
                return serializer(obj)
        return json.JSONEncoder.default(self, obj)

def to_json(data):
    return json.dumps(data, cls=JSONEncoder)
