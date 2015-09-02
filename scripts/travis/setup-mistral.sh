#!/usr/bin/env bash
set -e

if [ "$(whoami)" != 'root' ]; then
    echo 'Please run with sudo'
    exit 2
fi

MISTRAL_STABLE_BRANCH="master"
STANCONF="${PWD}/conf/st2.dev.conf"
TYPE="debs"

setup_mistral_st2_config()
{
  echo "" >> ${STANCONF}
  echo "[mistral]" >> ${STANCONF}
  echo "v2_base_url = http://127.0.0.1:8989/v2" >> ${STANCONF}
}

setup_postgresql() {
  # Setup the postgresql service on fedora. Ubuntu is already setup by default.
  if [[ "$TYPE" == "rpms" ]]; then
    echo "Configuring PostgreSQL for Fedora..."
    systemctl enable postgresql
    sudo postgresql-setup initdb
    pg_hba_config=/var/lib/pgsql/data/pg_hba.conf
    sed -i 's/^local\s\+all\s\+all\s\+peer/local all all trust/g' ${pg_hba_config}
    sed -i 's/^local\s\+all\s\+all\s\+ident/local all all trust/g' ${pg_hba_config}
    sed -i 's/^host\s\+all\s\+all\s\+127.0.0.1\/32\s\+ident/host all all 127.0.0.1\/32 md5/g' ${pg_hba_config}
    sed -i 's/^host\s\+all\s\+all\s\+::1\/128\s\+ident/host all all ::1\/128 md5/g' ${pg_hba_config}
    systemctl start postgresql
  fi

  echo "Changing max connections for PostgreSQL..."
  config=`sudo -u postgres psql -c "SHOW config_file;" | grep postgresql.conf`
  sed -i 's/max_connections = 100/max_connections = 500/' ${config}
  service postgresql restart
}

setup_mistral_config()
{
config=/etc/mistral/mistral.conf
echo "Writing Mistral configuration file to $config..."
if [ -e "$config" ]; then
  rm $config
fi
touch $config
cat <<mistral_config >$config
[database]
connection=postgresql://mistral:StackStorm@localhost/mistral
max_pool_size=50

[pecan]
auth_enable=false
mistral_config
}

setup_mistral_log_config()
{
log_config=/etc/mistral/wf_trace_logging.conf
echo "Writing Mistral log configuration file to $log_config..."
if [ -e "$log_config" ]; then
    rm $log_config
fi
cp /opt/openstack/mistral/etc/wf_trace_logging.conf.sample $log_config
sed -i "s~tmp~var/log~g" $log_config
}

setup_mistral_db()
{
  echo "Setting up Mistral DB in PostgreSQL..."
  sudo -u postgres psql -c "DROP DATABASE IF EXISTS mistral;"
  sudo -u postgres psql -c "DROP USER IF EXISTS mistral;"
  sudo -u postgres psql -c "CREATE USER mistral WITH ENCRYPTED PASSWORD 'StackStorm';"
  sudo -u postgres psql -c "CREATE DATABASE mistral OWNER mistral;"

  echo "Creating and populating DB tables for Mistral..."
  config=/etc/mistral/mistral.conf
  cd /opt/openstack/mistral
  /opt/openstack/mistral/.venv/bin/python ./tools/sync_db.py --config-file ${config}
}

setup_mistral_upstart()
{
echo "Setting up upstart for Mistral..."
upstart=/etc/init/mistral.conf
if [ -e "$upstart" ]; then
    rm $upstart
fi
touch $upstart
cat <<mistral_upstart >$upstart
description "Mistral Workflow Service"

start on runlevel [2345]
stop on runlevel [016]
respawn

exec /opt/openstack/mistral/.venv/bin/python /opt/openstack/mistral/mistral/cmd/launch.py --config-file /etc/mistral/mistral.conf --log-config-append /etc/mistral/wf_trace_logging.conf
mistral_upstart
}

setup_mistral() {
  echo "###########################################################################################"
  echo "# Setting up Mistral"

  # Clone mistral from github.
  mkdir -p /opt/openstack
  cd /opt/openstack
  if [ -d "/opt/openstack/mistral" ]; then
    rm -r /opt/openstack/mistral
  fi
  echo "Cloning Mistral branch: ${MISTRAL_STABLE_BRANCH}..."
  git clone -b ${MISTRAL_STABLE_BRANCH} https://github.com/StackStorm/mistral.git

  # Setup virtualenv for running mistral.
  cd /opt/openstack/mistral
  virtualenv --no-site-packages .venv
  . /opt/openstack/mistral/.venv/bin/activate
  pip install -q -r requirements.txt
  pip install -q psycopg2
  python setup.py install

  # Setup plugins for actions.
  mkdir -p /etc/mistral/actions
  if [ -d "/etc/mistral/actions/st2mistral" ]; then
    rm -r /etc/mistral/actions/st2mistral
  fi
  echo "Cloning St2mistral branch: ${MISTRAL_STABLE_BRANCH}..."
  cd /etc/mistral/actions
  git clone -b ${MISTRAL_STABLE_BRANCH} https://github.com/StackStorm/st2mistral.git
  cd /etc/mistral/actions/st2mistral
  python setup.py install

  # Create configuration files.
  mkdir -p /etc/mistral
  setup_mistral_config
  setup_mistral_log_config
  setup_mistral_st2_config

  # Setup database.
  setup_postgresql
  setup_mistral_db

  # Setup service.
  if [[ "$TYPE" == "debs" ]]; then
    setup_mistral_upstart
  elif [[ "$TYPE" == "rpms" ]]; then
    setup_mistral_systemd
  fi

  # Deactivate venv.
  deactivate

  # Setup mistral client.
  pip install -q -U git+https://github.com/StackStorm/python-mistralclient.git@${MISTRAL_STABLE_BRANCH}
}

setup_mistral

start mistral

echo 'Done!'
