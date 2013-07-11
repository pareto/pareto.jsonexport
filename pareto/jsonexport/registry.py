class _Registry(object):
    def __init__(self):
        self._items = {}

    def register(self, _type, exporter):
        if not isinstance(_type, type):
            raise TypeError(
                'registration must happen on class, not on instance')
        self._items[_type] = exporter

    def get(self, instance):
        if isinstance(instance, type):
            raise TypeError(
                'retrieving must happen on instance, not on class')
        if hasattr(instance, 'aq_base'):
            instance = instance.aq_base
        bases = [instance.__class__] + list(instance.__class__.__bases__)
        for base in bases:
            serializer = self._items.get(base)
            if serializer is not None:
                return serializer(instance)
        raise KeyError(instance.__class__.__name__)

registry = _Registry()
