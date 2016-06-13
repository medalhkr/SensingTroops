import hashlib

class InformationObject(object):
    def _props(self):
        return filter(lambda key:
                      key[0] != '.' and
                      key[0] != '_' and
                      not callable(getattr(self, key)),
                      dir(self))

    def to_dict(self):
        res_dict = {}
        for key in self._props():
            value = getattr(self, key)
            if isinstance(value, InformationObject):
                value = value.to_dict()
            if isinstance(value, list):
                first = value[0] if len(value) > 0 else None
                if isinstance(first, InformationObject):
                    value = [v.to_dict() for v in value]
            if isinstance(value, list):
                try:
                    value = sorted(value)
                except TypeError:
                    pass

            res_dict[key] = value
        return res_dict

    def hash(self):
        m = hashlib.md5()
        m.update(str(self.to_dict()).encode())
        return m.hexdigest()

    def __str__(self):
        return str(self.to_dict())

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
        for key in self._props():
            if getattr(self, key) != getattr(other, key):
                return False
        return True
