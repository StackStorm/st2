import os

from pkg_resources import get_distribution


class RequirementsValidator(object):

    @staticmethod
    def validate(requirements_file):
        if not os.path.exists(requirements_file):
            raise Exception('Requirements file %s not found.' % requirements_file)
        missing = []
        with open(requirements_file, 'r') as f:
            for line in f:
                rqmnt = line.strip()
                try:
                    get_distribution(rqmnt)
                except:
                    missing.append(rqmnt)
        return missing
