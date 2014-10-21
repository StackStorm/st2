__all__ = [
    'ResourceReference'
]

PACK_SEPARATOR = '.'


class ResourceReference(object):
    """
    Class used for referring to resources which belong to a content pack.
    """
    def __init__(self, pack=None, name=None):
        self.pack = self.validate_pack_name(pack=pack)
        self.name = name

        self.ref = self.to_string_reference(pack=pack, name=name)

    @staticmethod
    def from_string_reference(ref):
        pack = ResourceReference.get_pack(ref)
        name = ResourceReference.get_name(ref)

        return ResourceReference(pack=pack, name=name)

    @staticmethod
    def to_string_reference(pack=None, name=None):
        if pack and name:
            pack = ResourceReference.validate_pack_name(pack=pack)
            return PACK_SEPARATOR.join([pack, name])
        else:
            raise ValueError('Both pack and name needed for building ref. pack=%s, name=%s' %
                             (pack, name))

    @staticmethod
    def validate_pack_name(pack):
        if PACK_SEPARATOR in pack:
            raise ValueError('Pack name should not contain "%s"' % (PACK_SEPARATOR))

        return pack

    @staticmethod
    def get_pack(ref):
        return ref.split(PACK_SEPARATOR, 1)[0]

    @staticmethod
    def get_name(ref):
        return ref.split(PACK_SEPARATOR, 1)[1]

    def __repr__(self):
        return ('<ResourceReference pack=%s,name=%s,ref=%s>' %
                (self.pack, self.name, self.ref))
