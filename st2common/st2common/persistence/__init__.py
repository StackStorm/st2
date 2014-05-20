import abc
import six

@six.add_metaclass(abc.ABCMeta)
class Access(object):

    @classmethod
    @abc.abstractmethod
    def _get_impl(cls):
        """ """

    @classmethod
    def get_by_name(cls, value):
        return cls._get_impl().get_by_name(value)

    @classmethod
    def get_by_id(cls, value):
        return cls._get_impl().get_by_id(value)

    @classmethod
    def get_all(cls):
        return cls._get_impl().get_all()

    @classmethod
    def query(cls, **query_args):
        return cls._get_impl().query(**query_args)

    @classmethod
    def add_or_update(cls, model_object):
        return cls._get_impl().add_or_update(model_object)

    @classmethod
    def delete(cls, model_object):
        return cls._get_impl().delete(model_object)
