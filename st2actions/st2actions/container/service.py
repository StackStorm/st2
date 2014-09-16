import json
import os
import pipes

from oslo.config import cfg

from st2common import log as logging

LOG = logging.getLogger(__name__)
STDOUT = 'stdout'
STDERR = 'stderr'


class RunnerContainerService():
    """
        The RunnerContainerService class implements the interface
        that ActionRunner implementations use to access services
        provided by the Action Runner Container.
    """

    def __init__(self, container):
        self._container = container
        self._status = None
        self._result = None
        self._payload = {}
        self._action_workingdir = None

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

    def get_content_packs_base_path(self):
        return cfg.CONF.content.content_packs_base_path

    def get_artifact_working_dir(self, pack=None, entry_point=None):
        wkdir = self.get_content_packs_base_path()
        entry_point_path = os.path.split(entry_point)[0]
        if not entry_point_path:
            return wkdir
        wkdir = os.path.join(wkdir, pack, 'actions', entry_point_path)
        return wkdir

    def get_entry_point_abs_path(self, pack=None, entry_point=None):
        if entry_point is not None:
            if os.path.isabs(entry_point):
                return entry_point
            return os.path.join(self.get_content_packs_base_path(), pipes.quote(pack),
                                'actions', pipes.quote(entry_point))
        else:
            return None

    def __str__(self):
        result = []
        result.append('RunnerContainerService@')
        result.append(str(id(self)))
        result.append('(')
        result.append('_container="%s", ' % self._container)
        result.append('_result="%s", ' % self._result)
        result.append('_payload="%s", ' % self._payload)
        result.append(')')
        return ''.join(result)
