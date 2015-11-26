from st2actions.runners.pythonrunner import Action

__all__ = [
    'SkipMessageAction'
]


class SkipMessageAction(Action):
    def run(self):
        # That's a placeholder for format_result failure
        # to avoid failing action chain on aliases with 
        # disabled output.
        return 
