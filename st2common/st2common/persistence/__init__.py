import abc
import six

from st2common import log as logging


LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class Access(object):

    @classmethod
    @abc.abstractmethod
    def _get_impl(kls):
        pass

    @classmethod
    @abc.abstractmethod
    def _get_publisher(kls):
        return None

    @classmethod
    def get_by_name(kls, value):
        return kls._get_impl().get_by_name(value)

    @classmethod
    def get_by_id(kls, value):
        return kls._get_impl().get_by_id(value)

    @classmethod
    def get(kls, *args, **kwargs):
        return kls._get_impl().get(*args, **kwargs)

    @classmethod
    def get_all(kls, *args, **kwargs):
        return kls._get_impl().get_all(*args, **kwargs)

    @classmethod
    def count(kls, *args, **kwargs):
        return kls._get_impl().count(*args, **kwargs)

    @classmethod
    def query(kls, *args, **kwargs):
        return kls._get_impl().query(*args, **kwargs)

    @classmethod
    def add_or_update(kls, model_object, publish=True):
        pre_persist_id = model_object.id
        model_object = kls._get_impl().add_or_update(model_object)
        publisher = kls._get_publisher()
        try:
            if publisher and publish:
                if str(pre_persist_id) == str(model_object.id):
                    publisher.publish_update(model_object)
                else:
                    publisher.publish_create(model_object)
        except:
            LOG.exception('publish failed.')
        return model_object

    @classmethod
    def delete(kls, model_object, publish=True):
        persisted_object = kls._get_impl().delete(model_object)
        publisher = kls._get_publisher()
        if publisher and publish:
            # using model_object.
            publisher.publish_delete(model_object)
        return persisted_object
