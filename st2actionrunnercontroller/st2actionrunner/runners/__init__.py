from abc import abstractmethod


class ActionRunner():
    """
        The interface that must be implemented by each StackStorm
        Action Runner implementation.
    """

    def __init__(self):
        self.container_service = None
        self.liveaction_id = None
        self.parameters = None

    def set_container_service(self, container_service):
        self.container_service = container_service

    def set_liveaction_id(self, liveaction_id):
        self.liveaction_id = liveaction_id

    # Consider making set_parameters abstract rather than
    # forcing a dict-model of parameters on ActionRunner developers.
    def set_parameters(self, parameters):
        self.parameters = parameters

    @abstractmethod
    def pre_run(self):
        raise NotImplementedError()

    # Run will need to take an action argument
    # Run may need result data argument
    @abstractmethod
    def run(self, action_parameters):
        raise NotImplementedError()

    @abstractmethod
    def post_run(self):
        raise NotImplementedError()

    def __str__(self):
        result = []
        result.append('ActionRunner@')
        result.append(str(id(self)))
        result.append('(')
        result.append('liveaction_id="%s", ' % self.liveaction_id)
        result.append('container_service="%s", ' % self.container_service)
        result.append('runner_parameters="%s"' % self.parameters)
        result.append(')')
        return ''.join(result)
