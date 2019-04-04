from st2actions.runners.pythonrunner import Action

__all__ = [
    'GetLibraryPathAction'
]


class GetLibraryPathAction(Action):
    def run(self, module):
        return __import__(module).__file__
