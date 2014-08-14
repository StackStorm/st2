import os
import logging

from st2client import models


LOG = logging.getLogger(__name__)


class Client(object):

    def __init__(self, *args, **kwargs):

        # If API endpoints not provided, then try to get it from environment.
        self.endpoints = dict()
        self.endpoints['base'] = os.environ.get(
            'ST2_BASE_URL', kwargs.get('base_url', 'http://localhost'))
        self.endpoints['action'] = kwargs.get('action_url', None)
        if not self.endpoints['action']:
            self.endpoints['action'] = os.environ.get(
                'ST2_ACTION_URL', '%s:%s' % (self.endpoints['base'], 9101))
        self.endpoints['reactor'] = kwargs.get('reactor_url', None)
        if not self.endpoints['reactor']:
            self.endpoints['reactor'] = os.environ.get(
                'ST2_REACTOR_URL', '%s:%s' % (self.endpoints['base'], 9102))
        self.endpoints['datastore'] = kwargs.get('datastore_url', None)
        if not self.endpoints['datastore']:
            self.endpoints['datastore'] = os.environ.get(
                'ST2_DATASTORE_URL', '%s:%s' % (self.endpoints['base'], 9103))

        # Instantiate resource managers and assign appropriate API endpoint.
        self.managers = dict()
        self.managers['RunnerType'] = models.ResourceManager(
            models.RunnerType, self.endpoints['action'])
        self.managers['Action'] = models.ResourceManager(
            models.Action, self.endpoints['action'])
        self.managers['ActionExecution'] = models.ResourceManager(
            models.ActionExecution, self.endpoints['action'])
        self.managers['Rule'] = models.ResourceManager(
            models.Rule, self.endpoints['reactor'])
        self.managers['Trigger'] = models.ResourceManager(
            models.Trigger, self.endpoints['reactor'])
        self.managers['KeyValuePair'] = models.ResourceManager(
            models.KeyValuePair, self.endpoints['datastore'])

    @property
    def runners(self):
        return self.managers['RunnerType']

    @property
    def actions(self):
        return self.managers['Action']

    @property
    def executions(self):
        return self.managers['ActionExecution']

    @property
    def rules(self):
        return self.managers['Rule']

    @property
    def triggers(self):
        return self.managers['Trigger']

    @property
    def keys(self):
        return self.managers['KeyValuePair']
