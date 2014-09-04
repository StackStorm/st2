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
        self.endpoints['api'] = kwargs.get('api_url', None)
        if not self.endpoints['api']:
            self.endpoints['api'] = os.environ.get(
                'ST2_API_URL', '%s:%s' % (self.endpoints['base'], 9101))

        # Instantiate resource managers and assign appropriate API endpoint.
        self.managers = dict()
        self.managers['RunnerType'] = models.ResourceManager(
            models.RunnerType, self.endpoints['api'])
        self.managers['Action'] = models.ResourceManager(
            models.Action, self.endpoints['api'])
        self.managers['ActionExecution'] = models.ResourceManager(
            models.ActionExecution, self.endpoints['api'])
        self.managers['Rule'] = models.ResourceManager(
            models.Rule, self.endpoints['api'])
        self.managers['Trigger'] = models.ResourceManager(
            models.Trigger, self.endpoints['api'])
        self.managers['KeyValuePair'] = models.ResourceManager(
            models.KeyValuePair, self.endpoints['api'])

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
