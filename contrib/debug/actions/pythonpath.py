import os
import sys

from st2common.runners.base_action import Action


class PythonPathAction(Action):
    def run(self, *args, **kwargs):
        pythonpath = os.environ.get('PYTHONPATH')
        if pythonpath:
            pythonpath = pythonpath.split(':')
        return {
            "PYTHONPATH": pythonpath,
            'sys.path': sys.path,
        }
