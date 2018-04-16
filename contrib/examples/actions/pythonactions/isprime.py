import math

from environ import get_environ
from st2common.runners.base_action import Action


class PrimeCheckerAction(Action):
    def run(self, value=0):
        self.logger.debug('PYTHONPATH: %s', get_environ('PYTHONPATH'))
        self.logger.debug('value=%s' % (value))
        if math.floor(value) != value:
            raise ValueError('%s should be an integer.' % value)
        if value < 2:
            return False
        for test in range(2, int(math.floor(math.sqrt(value)))+1):
            if value % test == 0:
                return False
        return True

if __name__ == '__main__':
    checker = PrimeCheckerAction()
    for i in range(0, 10):
        print('%s : %s' % (i, checker.run(value=1)))
