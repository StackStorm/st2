from mongoengine import ValidationError

from st2common import log as logging
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.persistence.actionrunner import LiveAction


LOG = logging.getLogger(__name__)


def get_liveactions_by_actionexec_id(actionexec_id):
    """
        Get LiveAction by the actionexecution_id field.

        On error, raise ST2ObjectNotFoundError.
    """
    liveactions = None
    try:
        liveactions = LiveAction.query(actionexecution_id=actionexec_id)
    except (ValueError, ValidationError) as e:
        LOG.error('Database lookup for Live Actions with actionexecution_id="%s" resulted in '
                  'exception: %s', actionexec_id, e)
        raise StackStormDBObjectNotFoundError('Unable to find Live Actions with '
                                              'actionexecution_id="%s"' % actionexec_id)

    return liveactions


def get_liveaction_by_id(liveaction_id):
    """
        Get LiveAction by id.

        On error, raise ST2ObjectNotFoundError.
    """
    liveaction = None
    try:
        liveaction = LiveAction.get_by_id(liveaction_id)
    except (ValueError, ValidationError) as e:
        LOG.error('Database lookup for id="%s" resulted in '
                  'exception: %s', liveaction_id, e)
        raise StackStormDBObjectNotFoundError('Unable to find liveaction with '
                                              'id="%s"' % liveaction_id)

    return liveaction
