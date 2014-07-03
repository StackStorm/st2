from abc import abstractmethod

from st2actionrunner import RunnerBase


class StackRunner(stackstorm.stackrunner.StackRunnerBase):
    """
        Defines the interface that must be implemented by each
        StackStorm action runner implementation.
    """

    def __init__(self, action_id, action_name, runner_parameters, action_parameters):
        st2actionrunnerRunnerBase.__init__(self, action_id, action_name,
                                           runner_parameters, action_parameters)

    @abstractmethod
    def get_help_message(self):
        raise NotImplementedError()

    def get_param_names(self):
        return []

    @abstractmethod
    def get_run_type(self):
        raise NotImplementedError()

    def pre_run(self, target=None, params=None):
        pass

    @abstractmethod
    def run(self, target=None, params=None):
        raise NotImplementedError()

    def post_run(self, target=None, params=None):
        pass


def get_runner(action, target, args):
    raise NotImplementedError()
