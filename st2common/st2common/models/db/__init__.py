import logging
from mongoengine import connect, disconnect
from oslo.config import cfg

LOG = logging.getLogger('st2common.models.db')


def setup(db_name=cfg.CONF.database.db_name, db_host=cfg.CONF.database.host,
          db_port=cfg.CONF.database.port):
    LOG.info('Database details - dbname:{}, host:{}, port:{}'.format(
        db_name, db_host, db_port))
    connect(db_name, host=db_host, port=db_port)


def teardown():
    disconnect()
