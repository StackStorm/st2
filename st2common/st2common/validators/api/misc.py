from st2common.constants.pack import SYSTEM_PACK_NAME
from st2common.exceptions.apivalidation import ValueValidationException

__all__ = [
    'validate_not_part_of_system_pack'
]


def validate_not_part_of_system_pack(resource_db):
    """
    Validate that the provided resource database object doesn't belong to
    a system level pack.

    If it does, ValueValidationException is thrown.

    :param resource_db: Resource database object to check.
    :type resource_db: ``object``
    """
    pack = getattr(resource_db, 'pack', None)

    if pack == SYSTEM_PACK_NAME:
        msg = 'Resources belonging to system level packs can\'t be manipulated'
        raise ValueValidationException(msg)

    return resource_db
