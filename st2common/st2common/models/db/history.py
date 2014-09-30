from st2common.models.db import stormbase
from st2common import log as logging


LOG = logging.getLogger(__name__)


class ActionExecutionHistoryDB(stormbase.StormFoundationDB):
    trigger = stormbase.EscapedDictField(required=True)
    trigger_type = stormbase.EscapedDictField(required=True)
    trigger_instance = stormbase.EscapedDictField(required=True)
    rule = stormbase.EscapedDictField(required=True)
    action = stormbase.EscapedDictField(required=True)
    runner = stormbase.EscapedDictField(required=True)
    execution = stormbase.EscapedDictField(required=True)
