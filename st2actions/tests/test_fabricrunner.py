import tests.config
tests.config.parse_args()

from st2actions.runners.fabricrunner import FabricRunner
from st2common.models.api.action import ACTIONEXEC_STATUS_SUCCEEDED, ACTIONEXEC_STATUS_FAILED
from unittest2 import TestCase


class TestFabricRunnerResultStatus(TestCase):

    def test_pf_ok_all_success(self):
        result = {
            '1': {'succeeded': True},
            '2': {'succeeded': True},
            '3': {'succeeded': True},
        }
        self.assertEquals(ACTIONEXEC_STATUS_SUCCEEDED,
                          FabricRunner._get_result_status(result, True))

    def test_pf_ok_some_success(self):
        result = {
            '1': {'succeeded': False},
            '2': {'succeeded': True},
            '3': {'succeeded': False},
        }
        self.assertEquals(ACTIONEXEC_STATUS_SUCCEEDED,
                          FabricRunner._get_result_status(result, True))

        result = {
            '1': {'succeeded': True},
            '2': {'succeeded': False},
            '3': {'succeeded': False},
        }
        self.assertEquals(ACTIONEXEC_STATUS_SUCCEEDED,
                          FabricRunner._get_result_status(result, True))

        result = {
            '1': {'succeeded': False},
            '2': {'succeeded': False},
            '3': {'succeeded': True},
        }
        self.assertEquals(ACTIONEXEC_STATUS_SUCCEEDED,
                          FabricRunner._get_result_status(result, True))

    def test_pf_ok_all_fail(self):
        result = {
            '1': {'succeeded': False},
            '2': {'succeeded': False},
            '3': {'succeeded': False},
        }
        self.assertEquals(ACTIONEXEC_STATUS_FAILED,
                          FabricRunner._get_result_status(result, True))

    def test_pf_not_ok_all_success(self):
        result = {
            '1': {'succeeded': True},
            '2': {'succeeded': True},
            '3': {'succeeded': True},
        }
        self.assertEquals(ACTIONEXEC_STATUS_SUCCEEDED,
                          FabricRunner._get_result_status(result, False))

    def test_pf_not_ok_some_success(self):
        result = {
            '1': {'succeeded': False},
            '2': {'succeeded': True},
            '3': {'succeeded': False},
        }
        self.assertEquals(ACTIONEXEC_STATUS_FAILED,
                          FabricRunner._get_result_status(result, False))

        result = {
            '1': {'succeeded': True},
            '2': {'succeeded': False},
            '3': {'succeeded': False},
        }
        self.assertEquals(ACTIONEXEC_STATUS_FAILED,
                          FabricRunner._get_result_status(result, False))

        result = {
            '1': {'succeeded': False},
            '2': {'succeeded': False},
            '3': {'succeeded': True},
        }
        self.assertEquals(ACTIONEXEC_STATUS_FAILED,
                          FabricRunner._get_result_status(result, False))

    def test_pf_not_ok_all_fail(self):
        result = {
            '1': {'succeeded': False},
            '2': {'succeeded': False},
            '3': {'succeeded': False},
        }
        self.assertEquals(ACTIONEXEC_STATUS_FAILED,
                          FabricRunner._get_result_status(result, False))
