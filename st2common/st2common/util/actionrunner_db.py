from mongoengine import ValidationError

from st2common import log as logging
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.persistence.actionrunner import (ActionType, LiveAction)
from st2common.models.api.actionrunner import (LiveActionAPI, ActionTypeAPI,
                                               )

LOG = logging.getLogger(__name__)


def get_actiontype_by_id(actiontype_id):
    """
        Get ActionType by id.

        On error, raise StackStormDBObjectNotFoundError
    """
    try:
        actiontype = ActionType.get_by_id(actiontype_id)
    except (ValueError, ValidationError) as e:
        LOG.warning('Database lookup for ActionType with id="%s" resulted in '
                    'exception: %s', actiontype_id, e)
        raise StackStormDBObjectNotFoundError('Unable to find ActionType with '
                                              'id="%s"' % actiontype_id)

    return actiontype


def get_actiontype_by_name(actiontype_name):
        """
            Get an ActionType by name.
            On error, raise ST2ObjectNotFoundError.
        """
        LOG.debug('Lookup for ActionType with name="%s"', actiontype_name)
        try:
            actiontypes = ActionType.query(name=actiontype_name)
        except (ValueError, ValidationError) as e:
            LOG.error('Database lookup for name="%s" resulted in exception: %s',
                      actiontype_name, e)
            raise StackStormDBObjectNotFoundError('Unable to find actiontype with name="%s"'
                                                  % actiontype_name)

        if not actiontypes:
            LOG.error('Database lookup for ActionType with name="%s" produced no results',
                      actiontype_name)
            raise StackStormDBObjectNotFoundError('Unable to find actiontype with name="%s"'
                                                  % actiontype_name)

        if len(actiontypes) > 1:
            LOG.warning('More than one ActionType returned from DB lookup by name. '
                        'Result list is: %s', actiontypes)

        return actiontypes[0]


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
