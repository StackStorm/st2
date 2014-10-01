import mongoengine as me

from st2common.models.db import stormbase
from st2common import log as logging


LOG = logging.getLogger(__name__)


class ActionExecutionHistoryDB(stormbase.StormFoundationDB):
    trigger = stormbase.EscapedDictField()
    trigger_type = stormbase.EscapedDictField()
    trigger_instance = stormbase.EscapedDictField()
    rule = stormbase.EscapedDictField()
    action = stormbase.EscapedDictField(required=True)
    runner = stormbase.EscapedDictField(required=True)
    executions = me.ListField(field=stormbase.EscapedDictField(required=True))
