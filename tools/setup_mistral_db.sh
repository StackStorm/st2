#!/bin/bash
set -e

# This script lovingly "borrowed" from https://github.com/StackStorm/mistral_dev/blob/master/actions/setup_db.sh

MISTRAL_PATH=$1
MISTRAL_CONFIG=$2
DISTRO=$3
DB_TYPE=$4
DB_NAME=$5
DB_USER_NAME=$6
DB_USER_PASS=$7
DB_ROOT_PASS=$8

if [[ ! -e "${MISTRAL_CONFIG}" ]]; then
    >&2 echo "ERROR: ${MISTRAL_CONFIG} does not exist."
    exit 1
fi

if [[ ! -d "${MISTRAL_PATH}" ]]; then
    >&2 echo "ERROR: ${MISTRAL_PATH} does not exist."
    exit 1
fi

if [[ ! -d "${MISTRAL_PATH}/.venv" ]]; then
    >&2 echo "ERROR: ${MISTRAL_PATH}/.venv does not exist."
    exit 1
fi

if [[ "${DISTRO}" != "ubuntu" && "${DISTRO}" != "fedora" ]]; then
    >&2 echo "ERROR: ${DISTRO} is an unsupported Linux distribution."
    exit 1
fi

if [[ "${DB_TYPE}" != "postgresql" && "${DB_TYPE}" != "mysql" ]]; then
    >&2 echo "ERROR: ${DB_TYPE} is an unsupported database type."
    exit 1
fi

echo "Setup database in ${DB_TYPE} on ${DISTRO}..."

# Create the database and user. Restart DB server first in case of active user sessions.
if [ "${DB_TYPE}" == "mysql" ]; then
    sudo service mysql restart
    mysql -uroot -p${DB_ROOT_PASS} -e "DROP DATABASE IF EXISTS ${DB_NAME}"
    mysql -uroot -p${DB_ROOT_PASS} -e "CREATE DATABASE ${DB_NAME}"
    mysql -uroot -p${DB_ROOT_PASS} -e "GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER_NAME}'@'%' IDENTIFIED BY '${DB_USER_PASS}'"
    mysql -uroot -p${DB_ROOT_PASS} -e "FLUSH PRIVILEGES"
elif [ "${DB_TYPE}" == "postgresql" ]; then
    sudo service postgresql restart
    sudo -u postgres psql -c "DROP DATABASE IF EXISTS ${DB_NAME};"
    sudo -u postgres psql -c "DROP USER IF EXISTS ${DB_USER_NAME};"
    sudo -u postgres psql -c "CREATE USER ${DB_USER_NAME} WITH ENCRYPTED PASSWORD '${DB_USER_PASS}';"
    sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER_NAME};"
fi

# Install requirements for the client lib.
if [[ "${DISTRO}" == "ubuntu" && "${DB_TYPE}" == "postgresql" ]]; then
    echo "Installing requirement libpg-dev..."
    sudo apt-get install -y libpq-dev
elif [[ "${DISTRO}" == "fedora" && "${DB_TYPE}" == "postgresql" ]]; then
    echo "Installing requirement postgresql-devel..."
    sudo yum install -y postgresql-devel
elif [[ "${DISTRO}" == "ubuntu" && "${DB_TYPE}" == "mysql" ]]; then
    echo "Installing requirement libmysqlclient-dev..."
    sudo apt-get install -y libmysqlclient-dev
elif [[ "${DISTRO}" == "fedora" && "${DB_TYPE}" == "mysql" ]]; then
    echo "Installing requirement mysql-devel..."
    sudo yum install -y mysql-devel
fi

# Install the client lib.
echo "Installing client lib for ${DB_TYPE}..."
. ${MISTRAL_PATH}/.venv/bin/activate

if [ "${DB_TYPE}" == "mysql" ]; then
    pip install -q mysql-python
elif [ "${DB_TYPE}" == "postgresql" ]; then
    pip install -q psycopg2
fi

deactivate

echo "Creating tables..."
${MISTRAL_PATH}/.venv/bin/mistral-db-manage --config-file ${MISTRAL_CONFIG} upgrade head > /dev/null
echo "Populating tables..."
${MISTRAL_PATH}/.venv/bin/mistral-db-manage --config-file ${MISTRAL_CONFIG} populate > /dev/null
echo "========================"
echo "Database setup complete."
echo "========================"