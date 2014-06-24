
from mongoengine import ValidationError

from st2common import log as logging
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.persistence.action import (Action, ActionExecution)
from st2common.models.api.action import (ActionExecutionAPI, ACTIONEXEC_STATUS_INIT,
                                         ACTION_ID, ACTION_NAME
                                         )

LOG = logging.getLogger(__name__)


def get_action_by_id(action_id):
    """
        Get Action by id.
        
        On error, raise StackStormDBObjectNotFoundError
    """
    action = None

    try:
        action = Action.get_by_id(action_id)
    except (ValueError, ValidationError) as e:
        LOG.warning('Database lookup for action with id="%s" resulted in '
                    'exception: %s', action_id, e)
        raise StackStormDBObjectNotFoundError('Unable to find action with '
                                              'id="%s"' % action_id)

    return action


def get_action_by_name(action_name):
    """
        Get Action by name.
        
        On error, raise StackStormDBObjectNotFoundError
    """
    action = None

    try:
        action = Action.get_by_name(action_name)
    except (ValueError, ValidationError) as e:
        LOG.warning('Database lookup for action with name="%s" resulted in '
                    'exception: %s', action_name, e)
        raise StackStormDBObjectNotFoundError('Unable to find action with '
                                              'name="%s"' % action_name)

    return action


def get_actionexec_by_id(actionexec_id):
    """
        Get ActionExecution by id.
        
        On error, raise ST2DBObjectNotFoundError.
    """
    actionexec = None

    try:
        actionexec = ActionExecution.get_by_id(actionexec_id)
    except (ValidationError, ValueError) as e:
        LOG.error('Database lookup for actionexecution with id="%s" resulted in '
                  'exception: %s', actionexec_id, e)
        raise StackStormDBObjectNotFoundError('Unable to find actionexecution with '
                                              'id="%s"' % actionexec_id)

    return actionexec

def get_action_by_dict(action_dict):
    """
        Get Action object from DB based on action_dict values.

        action_dict is a dictionary that contains either an "id" field,
        a "name" field", or both fields.

        Returns:
            - Action object found in DB. (None on lookup failure.)
            - modified action_dict with "id" key removed if lookup by
                  id failed.
    """
    action = None

    if ACTION_ID in action_dict:
        action_id = action_dict[ACTION_ID]
        try:
            action = get_action_by_id(action_id)
        except StackStormDBObjectNotFoundError:
            LOG.info('Action not found by id, falling back to lookup by name and '
                     'removing action id from Action Execution.')
            del action_dict[ACTION_ID]
        else:
            return (action, action_dict)
    
    if ACTION_NAME in action_dict:
        action_name = action_dict[ACTION_NAME]
        try:
            action = get_action_by_name(action_name)
        except StackStormDBObjectNotFoundError:
            LOG.info('Action not found by name.')
        else:
            return (action, action_dict) 
        
    # No action found by identifiers in action_dict.
    return (None,{})
