from st2actionrunner.runners import ActionRunner


class RemoteRunner(ActionRunner):
    def pre_run(self):
        raise NotImplementedError()

    @abstractmethod
    def run(self, action_parameters):
        raise NotImplementedError()

    @abstractmethod
    def post_run(self):
        raise NotImplementedError()
