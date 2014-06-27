import os
import logging


LOG = logging.getLogger(__name__)


def env(name, *args, **kwargs):
    """Returns the environment variable if exist otherwise returns default."""
    value = os.environ.get(name)
    return value if value else kwargs.get('default', '')
