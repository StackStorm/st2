import os
import pipes

from oslo.config import cfg

__all__ = [
    'get_packs_base_path',
    'get_pack_base_path'
]


def get_packs_base_path():
    return cfg.CONF.content.packs_base_path


def get_pack_base_path(pack_name):
    """
    Return full absolute base path to the content pack directory.

    :param pack_name: Content pack name.
    :type pack_name: ``str``

    :rtype: ``str``
    """
    if not pack_name:
        return None

    packs_base_path = get_packs_base_path()
    pack_base_path = os.path.join(packs_base_path, pipes.quote(pack_name))
    pack_base_path = os.path.abspath(pack_base_path)
    return pack_base_path
