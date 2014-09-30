import mongoengine as me

from st2common.models.db import stormbase
from st2common import log as logging


LOG = logging.getLogger(__name__)


class ActionExecutionHistoryDB(stormbase.StormFoundationDB):
    trigger = me.DictField(required=True)
    trigger_type = me.DictField(required=True)
    trigger_instance = me.DictField(required=True)
    rule = me.DictField(required=True)
    action = me.DictField(required=True)
    runner_type = me.DictField(required=True)
    execution = me.DictField(required=True)
