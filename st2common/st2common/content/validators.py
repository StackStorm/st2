from st2common.constants.content_pack import USER_PACK_NAME_BLACKLIST

__all__ = [
    'validate_content_pack_name'
]


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
