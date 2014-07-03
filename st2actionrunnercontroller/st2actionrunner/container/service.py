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
        self._exit_code = None
        self._output = []
        self._payload = {}

    def report_exit_code(self, code):
        self._exit_code = code

    def report_output(self, stream, output):
        self._output.append((stream, output))

    def report_payload(self, name, value):
        self._payload[name] = value

    def get_logger(self, name):
        pass

    def __str__(self):
        result = []
        result.append('RunnerContainerService@')
        result.append(str(id(self)))
        result.append('(')
        result.append('_container="%s", ' % self._container)
        result.append('_exit_code="%s", ' % self._exit_code)
        result.append('_output="%s", ' % self._output)
        result.append('_payload="%s", ' % self._payload)
        result.append(')')
        return ''.join(result)
