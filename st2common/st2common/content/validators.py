import os
from pkg_resources import get_distribution

from st2common.constants.content_pack import USER_PACK_NAME_BLACKLIST

__all__ = [
    'RequirementsValidator',
    'validate_content_pack_name'
]


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


def validate_content_pack_name(name):
    """
    Validate the content pack name.

    Throws Exception on invalid name.

    :param name: Content pack name to validate.
    :type name: ``str``

    :rtype: ``str``
    """
    if not name:
        raise ValueError('Content pack name cannot be empty')

    if name.lower() in USER_PACK_NAME_BLACKLIST:
        raise ValueError('Name "%s" is blacklisted and can\'t be used' %
                         (name.lower()))

    return name
