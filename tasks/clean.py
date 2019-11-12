import glob
import os

from invoke import task


@task
def pycs(ctx):
    print("Removing all .pyc files")
    for pycfile in glob.glob('**/*.pyc', recursive=True):
        os.remove(pycfile)


@task
def mongodb(ctx):
    print("==================== cleanmongodb ====================")
    print("----- Dropping all MongoDB databases -----")
    ctx.sudo("pkill -9 mongod")
    ctx.sudo("rm -rf /var/lib/mongodb/*")
    ctx.sudo("chown -R mongodb:mongodb /var/lib/mongodb/")
    ctx.sudo("service mongodb start")
    run("sleep 15")
    run("mongo --eval \"rs.initiate()\"")
    run("sleep 15")


@task
def mysql(ctx):
    print("==================== cleanmysql ====================")
    print("----- Dropping all Mistral MYSQL databases -----")
    run("mysql -uroot -pStackStorm -e \"DROP DATABASE IF EXISTS mistral\"")
    run("mysql -uroot -pStackStorm -e \"CREATE DATABASE mistral\"")
    run("mysql -uroot -pStackStorm -e \"GRANT ALL PRIVILEGES ON mistral.* TO 'mistral'@'127.0.0.1' IDENTIFIED BY 'StackStorm'\"")
    run("mysql -uroot -pStackStorm -e \"FLUSH PRIVILEGES\"")
    run("/opt/openstack/mistral/.venv/bin/python /opt/openstack/mistral/tools/sync_db.py --config-file /etc/mistral/mistral.conf")


@task
def rabbitmq(ctx):
    print("==================== cleanrabbitmq ====================")
    print("Deleting all RabbitMQ queue and exchanges")
    ctx.sudo("rabbitmqctl stop_app")
    ctx.sudo("rabbitmqctl reset")
    ctx.sudo("rabbitmqctl start_app")


@task
def coverage(ctx):
    print("==================== cleancoverage ====================")
    print("Removing all coverage results directories")
    print("")
    run("rm -rf .coverage")


@task(pycs, default=True)
def clean(ctx):
    pass
