import eventlet
import oslo.config.cfg
import pymongo
import pymongo.errors
import six

from st2common import log as logging


INSERT = 'i'
UPDATE = 'u'
DELETE = 'd'
COMMAND = 'c'
DB_PRESENCE = 'db'
NOOP = 'n'

__watcher = None

LOG = logging.getLogger(__name__)


class OplogWatcher(object):
    def __init__(self, connection=None, poll_time=1):
        cfg = oslo.config.cfg
        self.connection = connection or pymongo.Connection(cfg.CONF.database.host,
                                                           cfg.CONF.database.port)
        self.__thread = None
        self.poll_time = poll_time

        self._handlers = {}

    @staticmethod
    def __format_ns(db, collection):
        return db + '.' + collection

    @staticmethod
    def __get_id(op):
        id = None
        o2 = op.get('o2')
        if o2 is not None:
            id = o2.get('_id')

        if id is None:
            id = op['o'].get('_id')

        return id

    def __watch(self):
        oplog = self.connection.local['oplog.rs']
        ts = oplog.find().sort('$natural', -1)[0]['ts']
        while True:
            # fetch only new documents
            filter = {'ts': {'$gt': ts}}
            try:
                cursor = oplog.find(filter, tailable=True)
                while True:
                    for op in cursor:
                        ts = op['ts']
                        id = self.__get_id(op)
                        key = (op['ns'], op['op'])

                        try:
                            func, model = self._handlers[key]
                            func(op['ns'], ts, op['op'], id, op['o'])
                        except KeyError:
                            pass

                    eventlet.sleep(self.poll_time)
                    if not cursor.alive:
                        break
            except pymongo.errors.AutoReconnect:
                eventlet.sleep(self.poll_time)

    def start(self):
        if not self.status():
            LOG.info('Starting to watch for changes in db')
            self.__thread = eventlet.spawn_n(self.__watch)
        else:
            raise Exception('Watcher is already started')  # Is there more suitable exception type?

    def stop(self):
        if self.status():
            self.__thread = eventlet.kill(self.__thread)
        else:
            raise Exception('Watcher has not been started yet')

    def status(self):
        return self.__thread is not None

    def watch(self, func, model, operation=(INSERT, UPDATE, DELETE)):
        ns = self.__format_ns(model._get_db().name, model._get_collection_name())

        if isinstance(operation, six.string_types):
            operation = (operation,)

        for op in operation:
            key = (ns, op)
            self._handlers[key] = (func, model)


def get_watcher(auto_start=True):
    global __watcher
    if not __watcher:
        __watcher = OplogWatcher()
        if auto_start:
            __watcher.start()
    return __watcher


def _clear_watcher():
    global __watcher
    try:
        if __watcher:
            __watcher.stop()
    except Exception:
        pass
    finally:
        __watcher = None
