import json
import os
import pipes

from oslo.config import cfg

from st2actions.constants import LIBS_DIR as ACTION_LIBS_DIR
from st2common import log as logging

LOG = logging.getLogger(__name__)
STDOUT = 'stdout'
STDERR = 'stderr'


class RunnerContainerService(object):
    """
        The RunnerContainerService class implements the interface
        that ActionRunner implementations use to access services
        provided by the Action Runner Container.
    """

    def __init__(self):
        self._status = None
        self._result = None
        self._payload = {}

    def report_status(self, status):
        self._status = status

    def report_result(self, result):
        try:
            self._result = json.loads(result)
        except:
            self._result = result

    def get_status(self):
        return self._status

    def get_result(self):
        return self._result

    def report_payload(self, name, value):
        self._payload[name] = value

    def get_logger(self, name):
        from st2common import log as logging
        logging.getLogger(__name__ + '.' + name)

    @staticmethod
    def get_content_packs_base_path():
        return cfg.CONF.content.content_packs_base_path

    @staticmethod
    def get_content_pack_base_path(pack_name):
        """
        Return full absolute base path to the content pack directory.

        :param pack_name: Content pack name.
        :type pack_name: ``str``

        :rtype: ``str``
        """
        packs_base_path = RunnerContainerService.get_content_packs_base_path()
        pack_base_path = os.path.join(packs_base_path, pipes.quote(pack_name))
        pack_base_path = os.path.abspath(pack_base_path)
        return pack_base_path

    @staticmethod
    def get_entry_point_abs_path(pack=None, entry_point=None):
        if entry_point is not None and len(entry_point) > 0:
            if os.path.isabs(entry_point):
                return entry_point
            return os.path.join(RunnerContainerService.get_content_packs_base_path(),
                                pipes.quote(pack), 'actions', pipes.quote(entry_point))
        else:
            return None

    @staticmethod
    def get_action_libs_abs_path(pack=None, entry_point=None):
        entry_point_abs_path = RunnerContainerService.get_entry_point_abs_path(
            pack=pack, entry_point=entry_point)
        if entry_point_abs_path is not None:
            return os.path.join(os.path.dirname(entry_point_abs_path), ACTION_LIBS_DIR)
        else:
            return None

    def __str__(self):
        result = []
        result.append('RunnerContainerService@')
        result.append(str(id(self)))
        result.append('(')
        result.append('_result="%s", ' % self._result)
        result.append('_payload="%s", ' % self._payload)
        result.append(')')
        return ''.join(result)
