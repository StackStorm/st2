from __future__ import absolute_import
import math


from st2common.runners.base_action import Action
from six.moves import range


class PascalRowAction(Action):
    def run(self, **kwargs):
        # We call list values to verify that log messages are not duplicated when
        # datastore service is used
        try:
            self.action_service.list_values()
        except Exception:
            pass

        self.logger.info('test info log message')
        self.logger.debug('test debug log message')
        self.logger.error('test error log message')
        return PascalRowAction._compute_pascal_row(**kwargs)

    @staticmethod
    def _compute_pascal_row(row_index=0):
        if row_index == 'a':
            return False, 'This is suppose to fail don\'t worry!!'
        elif row_index == 'b':
            return None
        elif row_index == 'complex_type':
            result = PascalRowAction()
            return (False, result)
        elif row_index == 'c':
            return False, None
        elif row_index == 'd':
            return 'succeeded', [1, 2, 3, 4]
        elif row_index == 'e':
            return [1, 2]
        elif row_index == 5:
            return [math.factorial(row_index) /
                    (math.factorial(i) * math.factorial(row_index - i))
                    for i in range(row_index + 1)]
        else:
            return True, [math.factorial(row_index) /
                          (math.factorial(i) * math.factorial(row_index - i))
                          for i in range(row_index + 1)]
