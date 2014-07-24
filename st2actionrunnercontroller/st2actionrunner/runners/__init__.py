from abc import abstractmethod


class ActionRunner(object):
    """
        The interface that must be implemented by each StackStorm
        Action Runner implementation.
    """

    def __init__(self):
        self.container_service = None
        self.liveaction_id = None
        self.runner_parameters = None
        self.action_name = None
        self.entry_point = None
        self.artifact_paths = None

    def set_container_service(self, container_service):
        self.container_service = container_service

    def set_liveaction_id(self, liveaction_id):
        self.liveaction_id = liveaction_id

    def set_action_name(self, action_name):
        self.action_name = action_name

    # Consider making set_runner_parameters abstract rather than
    # forcing a dict-model of runner_parameters on ActionRunner developers.
    def set_runner_parameters(self, parameters):
        self.runner_parameters = parameters

    def set_artifact_paths(self, paths):
        self.artifact_paths = paths

    def set_entry_point(self, entry_point):
        self.entry_point = entry_point

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
        result.append('runner_parameters="%s", ' % self.runner_parameters)
        result.append('artifact_paths="%s", ' % self.artifact_paths)
        result.append('entry_point="%s"' % self.entry_point)
        result.append(')')
        return ''.join(result)
