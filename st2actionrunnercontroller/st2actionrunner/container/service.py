import json
import os
import tempfile

# TODO: fix st2common.log so that it supports all of the python logging API
import logging as pylogging

from oslo.config import cfg

from st2common import log as logging


LOG = logging.getLogger(__name__)


STDOUT = 'stdout'
STDERR = 'stderr'


CLEAN_UP_TEMPDIR = False


class RunnerContainerService():
    """
        The RunnerContainerService class implements the interface
        that ActionRunner implementations use to access services
        provided by the Action Runner Container.
    """

    def __init__(self, container):
        self._container = container
        self._result = None
        self._payload = {}
        self._action_workingdir = None

    def report_result(self, result):
        self._result = result

    def get_result(self):
        return self._result

    def get_result_json(self):
        return json.dumps(self._result)

    def report_payload(self, name, value):
        self._payload[name] = value

    def get_logger(self, name):
        from st2common import log as logging
        logging.getLogger(__name__ + '.' + name)

    def get_artifact_repo_path(self):
        return cfg.CONF.action_runner.artifact_repo_path

    def get_artifact_working_dir_path(self, entry_point):
        paths = entry_point.rsplit('/', 1)
        wkdir = (self.get_artifact_repo_path() + '/actions' +
                 ('/%s' % paths[0] if len(paths) == 2 else ''))
        if not os.path.isdir(wkdir):
            os.makedirs(wkdir)
        return wkdir

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
