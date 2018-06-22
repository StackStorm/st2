#!/usr/bin/env bash

function usage() {
    echo "Usage: $0 [start|stop|restart|startclean] [-r runner_count] [-g] [-x] [-c] [-6] [-m]" >&2
}

subcommand=$1; shift
runner_count=1
use_gunicorn=true
copy_examples=false
load_content=true
use_ipv6=false
include_mistral=false

while getopts ":r:gxcu6m" o; do
    case "${o}" in
        r)
            runner_count=${OPTARG}
            ;;
        g)
            use_gunicorn=false
            ;;
        x)
            copy_examples=true
            ;;
        c)
            load_content=false
            ;;
        6)
            use_ipv6=true
            ;;
        m)
            include_mistral=true
            ;;
        \?)
            echo "Invalid option: -$OPTARG" >&2
            usage
            exit 2
            ;;
        :)
            echo "Option -$OPTARG requires an argument." >&2
            usage
            exit 2
            ;;
    esac
done

function init(){
    ST2_BASE_DIR="/opt/stackstorm"
    COMMAND_PATH=${0%/*}
    CURRENT_DIR=`pwd`
    CURRENT_USER=`whoami`
    CURRENT_USER_GROUP=`id -gn`

    if [[ (${COMMAND_PATH} == /*) ]] ;
    then
        ST2_REPO=${COMMAND_PATH}/..
    else
        ST2_REPO=${CURRENT_DIR}/${COMMAND_PATH}/..
    fi

    VENV=${ST2_REPO}/virtualenv
    PY=${VENV}/bin/python
    echo "Using virtualenv: ${VENV}"
    echo "Using python: ${PY}"

    if [ -z "$ST2_CONF" ]; then
        ST2_CONF=${ST2_REPO}/conf/st2.dev.conf
    fi
    echo "Using st2 config file: $ST2_CONF"

    if [ ! -f "$ST2_CONF" ]; then
        echo "Config file $ST2_CONF does not exist."
        exit 1
    fi

    # Optionally, initialize mistral
    if [ "${include_mistral}" = true ]; then
        init_mistral
    fi
}

function init_mistral(){

    echo "Initializing Mistral..."

    # Both the mistral and st2mistral repos must be present alongside the st2 repo
    MISTRAL_REPO="${ST2_REPO}/../mistral"
    ST2MISTRAL_REPO="${ST2_REPO}/../st2mistral"

    if [ ! -d "$MISTRAL_REPO" ] || [ ! -d "$ST2MISTRAL_REPO" ] ; then
        echo "You specified the Mistral option, but either the mistral or st2mistral directories were not found."
        echo "Please place a clone of both mistral and st2mistral repositories alongside the st2 repository."
        exit 1
    fi

    if [ -z "$MISTRAL_CONF" ]; then
        MISTRAL_CONF=${ST2_REPO}/conf/mistral.dev/mistral.dev.conf
    fi
    echo "Using mistral config file: $MISTRAL_CONF"

    if [ ! -f "$MISTRAL_CONF" ]; then
        echo "Config file $MISTRAL_CONF does not exist."
        exit 1
    fi

    # Create mistral virtualenv if doesn't exist
    if [[ ! -d "${MISTRAL_REPO}/.venv" ]]; then
        virtualenv ${MISTRAL_REPO}/.venv > /dev/null
    fi

    # Install Mistral and st2 plugins
    echo "Installing mistral, st2mistral, and all dependencies..."
    source "${MISTRAL_REPO}/.venv/bin/activate"
    cd "${MISTRAL_REPO}"

    # There's something funky going on with installation of Babel in mistral/requirements.txt
    # I noticed that the install script in mistral_dev is doing some replacements for Babel to set
    # the version but installation of Babel still fails for me even with that code. Only
    # thing I've managed to get working is manually installing pytz myself here.
    pip install pytz

    pip install -r requirements.txt > /dev/null
    python setup.py install > /dev/null
    cd "${ST2MISTRAL_REPO}"
    pip install -r requirements.txt > /dev/null
    python setup.py install > /dev/null
    deactivate

    MISTRAL_DB_COUNT=$(PGUSER=mistral PGPASSWORD=StackStorm PGDATABASE=mistral PGHOST=127.0.0.1 PGPORT=5432 psql mistral -c "select count(*) from action_definitions_v2" | grep -oP '\d{4}')
    if [ ! $? -eq 0 ]; then
        MISTRAL_DB_COUNT=0
    fi
    if [ "$MISTRAL_DB_COUNT" -lt 1200 ] ; then
      setup_mistral_db
    fi
}

function exportsdir(){
    local EXPORTS_DIR=$(grep 'dump_dir' ${ST2_CONF} | sed -e "s~^dump_dir[ ]*=[ ]*\(.*\)~\1~g")
    if [ -z $EXPORTS_DIR ]; then
        EXPORTS_DIR="/opt/stackstorm/exports"
    fi
    echo "$EXPORTS_DIR"
}

function st2start(){
    echo "Starting all st2 servers..."

    # Determine where the st2 repo is located. Some assumption is made here
    # that this script is located under st2/tools.

    # Change working directory to the root of the repo.
    echo "Changing working directory to ${ST2_REPO}..."
    cd ${ST2_REPO}
    RUNNERS_BASE_DIR=$(grep 'runners_base_path' ${ST2_CONF} \
        | awk 'BEGIN {FS=" = "}; {print $2}')
    if [ -z $RUNNERS_BASE_DIR ]; then
        RUNNERS_BASE_DIR="/opt/stackstorm/runners"
    fi
    echo "Using runners base dir: $RUNNERS_BASE_DIR"

    BASE_DIR=$(grep 'base_path' ${ST2_CONF} \
        | awk 'BEGIN {FS=" = "}; {print $2}')
    if [ -z BASE_DIR ]; then
        BASE_DIR="/opt/stackstorm"
    fi
    CONFIG_BASE_DIR="${BASE_DIR}/configs"
    echo "Using config base dir: $CONFIG_BASE_DIR"

    if [ ! -d "$CONFIG_BASE_DIR" ]; then
        echo "$CONFIG_BASE_DIR doesn't exist. Creating..."
        sudo mkdir -p $CONFIG_BASE_DIR
    fi

    PACKS_BASE_DIR=$(grep 'packs_base_path' ${ST2_CONF} \
        | awk 'BEGIN {FS=" = "}; {print $2}')
    if [ -z $PACKS_BASE_DIR ]; then
        PACKS_BASE_DIR="/opt/stackstorm/packs"
    fi
    echo "Using content packs base dir: $PACKS_BASE_DIR"

    # Copy and overwrite the action contents
    if [ ! -d "$ST2_BASE_DIR" ]; then
        echo "$ST2_BASE_DIR doesn't exist. Creating..."
        sudo mkdir -p $PACKS_BASE_DIR
        sudo mkdir -p $RUNNERS_BASE_DIR
    fi

    if [ "${use_ipv6}" = true ]; then
        echo '  using IPv6 bindings...'
        BINDING_ADDRESS="[::]"
    else
        BINDING_ADDRESS="0.0.0.0"
    fi
    
    VIRTUALENVS_DIR=$ST2_BASE_DIR/virtualenvs

    sudo mkdir -p $PACKS_BASE_DIR/default/sensors/
    sudo mkdir -p $PACKS_BASE_DIR/default/actions/
    sudo mkdir -p $PACKS_BASE_DIR/default/rules/
    sudo mkdir -p $VIRTUALENVS_DIR
    sudo mkdir -p $RUNNERS_BASE_DIR
    sudo chown -R ${CURRENT_USER}:${CURRENT_USER_GROUP} $PACKS_BASE_DIR
    sudo chown -R ${CURRENT_USER}:${CURRENT_USER_GROUP} $RUNNERS_BASE_DIR
    sudo chown -R ${CURRENT_USER}:${CURRENT_USER_GROUP} $VIRTUALENVS_DIR
    sudo chown -R ${CURRENT_USER}:${CURRENT_USER_GROUP} $CONFIG_BASE_DIR
    cp -Rp ./contrib/core/ $PACKS_BASE_DIR
    cp -Rp ./contrib/packs/ $PACKS_BASE_DIR
    cp -Rp ./contrib/runners/* $RUNNERS_BASE_DIR

    if [ "$copy_examples" = true ]; then
        echo "Copying examples from ./contrib/examples to $PACKS_BASE_DIR"
        cp -Rp ./contrib/examples $PACKS_BASE_DIR
    fi

    # activate virtualenv to set PYTHONPATH
    source ./virtualenv/bin/activate

    # Kill existing st2 screens
    screen -wipe
    screen -ls | grep st2 &> /dev/null
    if [ $? == 0 ]; then
        echo 'Killing existing st2 screen sessions...'
        screen -ls | grep st2 | cut -d. -f1 | awk '{print $1}' | xargs kill
    fi

    screen -ls | grep mistral &> /dev/null
    if [ $? == 0 ]; then
        echo 'Killing existing mistral screen sessions...'
        screen -ls | grep mistral | cut -d. -f1 | awk '{print $1}' | xargs kill
    fi

    # Run the st2 API server
    echo 'Starting screen session st2-api...'
    if [ "${use_gunicorn}" = true ]; then
        echo '  using gunicorn to run st2-api...'
        export ST2_CONFIG_PATH=${ST2_CONF}
        screen -d -m -S st2-api ./virtualenv/bin/gunicorn \
            st2api.wsgi:application -k eventlet -b "$BINDING_ADDRESS:9101" --workers 1
    else
        screen -d -m -S st2-api ./virtualenv/bin/python \
            ./st2api/bin/st2api \
            --config-file $ST2_CONF
    fi

    # Run st2stream API server
    if [ "${use_gunicorn}" = true ]; then
        echo '  using gunicorn to run st2-stream'
        export ST2_CONFIG_PATH=${ST2_CONF}
        screen -d -m -S st2-stream ./virtualenv/bin/gunicorn \
            st2stream.wsgi:application -k eventlet -b "$BINDING_ADDRESS:9102" --workers 1
    else
        screen -d -m -S st2-stream ./virtualenv/bin/python \
            ./st2stream/bin/st2stream \
            --config-file $ST2_CONF
    fi

    # Run the workflow engine server
    echo 'Starting screen session st2-workflow'
    screen -d -m -S st2-workflow ./virtualenv/bin/python \
        ./st2actions/bin/st2workflowengine \
        --config-file $ST2_CONF

    # Start a screen for every runner
    echo 'Starting screen sessions for st2-actionrunner(s)...'
    RUNNER_SCREENS=()
    for i in $(seq 1 $runner_count)
    do
        RUNNER_NAME=st2-actionrunner-$i
        RUNNER_SCREENS+=($RUNNER_NAME)
        echo '  starting '$RUNNER_NAME'...'
        screen -d -m -S $RUNNER_NAME ./virtualenv/bin/python \
            ./st2actions/bin/st2actionrunner \
            --config-file $ST2_CONF
    done

    # Run the sensor container server
    echo 'Starting screen session st2-sensorcontainer'
    screen -d -m -S st2-sensorcontainer ./virtualenv/bin/python \
        ./st2reactor/bin/st2sensorcontainer \
        --config-file $ST2_CONF

    # Run the rules engine server
    echo 'Starting screen session st2-rulesengine...'
    screen -d -m -S st2-rulesengine ./virtualenv/bin/python \
        ./st2reactor/bin/st2rulesengine \
        --config-file $ST2_CONF

    # Run the results tracker
    echo 'Starting screen session st2-resultstracker...'
    screen -d -m -S st2-resultstracker ./virtualenv/bin/python \
        ./st2actions/bin/st2resultstracker \
        --config-file $ST2_CONF

    # Run the actions notifier
    echo 'Starting screen session st2-notifier...'
    screen -d -m -S st2-notifier ./virtualenv/bin/python \
        ./st2actions/bin/st2notifier \
        --config-file $ST2_CONF

    # Run the auth API server
    echo 'Starting screen session st2-auth...'
    if [ "${use_gunicorn}" = true ]; then
        echo '  using gunicorn to run st2-auth...'
        export ST2_CONFIG_PATH=${ST2_CONF}
        screen -d -m -S st2-auth ./virtualenv/bin/gunicorn \
            st2auth.wsgi:application -k eventlet -b "$BINDING_ADDRESS:9100" --workers 1
    else
        screen -d -m -S st2-auth ./virtualenv/bin/python \
            ./st2auth/bin/st2auth \
            --config-file $ST2_CONF
    fi

    # Start Exporter
    if [ -n "$ST2_EXPORTER" ]; then
        EXPORTS_DIR=$(exportsdir)
        sudo mkdir -p $EXPORTS_DIR
        sudo chown -R ${CURRENT_USER}:${CURRENT_USER_GROUP} $EXPORTS_DIR
        echo 'Starting screen session st2-exporter...'
        screen -d -m -S st2-exporter ./virtualenv/bin/python \
            ./st2exporter/bin/st2exporter \
            --config-file $ST2_CONF
    fi

    if [ "${include_mistral}" = true ]; then

        LOGDIR=${ST2_REPO}/logs

        # Run mistral-server
        echo 'Starting screen session mistral-server...'
        screen -d -m -S mistral-server ${MISTRAL_REPO}/.venv/bin/python \
            ${MISTRAL_REPO}/.venv/bin/mistral-server \
            --server engine,executor \
            --config-file $MISTRAL_CONF \
            --log-file "$LOGDIR/mistral-server.log"

        # Run mistral-api
        echo 'Starting screen session mistral-api...'
        screen -d -m -S mistral-api ${MISTRAL_REPO}/.venv/bin/python \
            ${MISTRAL_REPO}/.venv/bin/mistral-server \
            --server api \
            --config-file $MISTRAL_CONF \
            --log-file "$LOGDIR/mistral-api.log"
    fi

    # Check whether screen sessions are started
    SCREENS=(
        "st2-api"
        "st2-workflow"
        "${RUNNER_SCREENS[@]}"
        "st2-sensorcontainer"
        "st2-rulesengine"
        "st2-resultstracker"
        "st2-notifier"
        "st2-auth"
    )

    if [ "${include_mistral}" = true ]; then
        SCREENS+=("mistral-server")
        SCREENS+=("mistral-api")
    fi

    echo
    for s in "${SCREENS[@]}"
    do
        screen -ls | grep "${s}[[:space:]]" &> /dev/null
        if [ $? != 0 ]; then
            echo "ERROR: Unable to start screen session for $s."
        fi
    done

    if [ "$load_content" = true ]; then
        # Register contents
        echo 'Registering sensors, runners, actions, rules, aliases, and policies...'
        ./virtualenv/bin/python \
            ./st2common/bin/st2-register-content \
            --config-file $ST2_CONF --register-all
    fi

    # List screen sessions
    screen -ls || exit 0
}

function st2stop(){
    screen -ls | grep st2 &> /dev/null
    if [ $? == 0 ]; then
        echo 'Killing existing st2 screen sessions...'
        screen -ls | grep st2 | cut -d. -f1 | awk '{print $1}' | xargs -L 1 pkill -P
    fi

    screen -ls | grep mistral &> /dev/null
    if [ $? == 0 ]; then
        echo 'Killing existing mistral screen sessions...'
        screen -ls | grep mistral | cut -d. -f1 | awk '{print $1}' | xargs -L 1 pkill -9 -P
    fi

    if [ "${use_gunicorn}" = true ]; then
        pids=`ps -ef | grep "gunicorn_config.py" | awk '{print $2}'`
        if [ -n "$pids" ]; then
            echo "Killing gunicorn processes"
            # true ensures that any failure to kill a process which does not exist will not lead
            # to failure. for loop to ensure all processes are killed even if some are missing
            # assuming kill will fail-fast.
            for pid in ${pids}; do
                echo ${pid} | xargs -L 1 kill -9 || true
            done
        fi
    fi
}

function st2clean(){
    # clean mongo
    . ${VENV}/bin/activate
    python ${ST2_REPO}/st2common/bin/st2-cleanup-db --config-file $ST2_CONF
    deactivate

    # start with clean logs
    LOGDIR=$(dirname $0)/../logs
    if [ -d ${LOGDIR} ]; then
        rm ${LOGDIR}/*
    fi
    if [ -n "$ST2_EXPORTER" ]; then
        EXPORTS_DIR=$(exportsdir)
        echo "Removing $EXPORTS_DIR..."
        rm -rf ${EXPORTS_DIR}
    fi

    setup_mistral_db
}

function setup_mistral_db(){
    # Ensure services are stopped, so DB script will work
    st2stop

    if [ -f /etc/lsb-release ]; then
        DISTRO="ubuntu"
    else
        DISTRO="fedora"
    fi

    ${ST2_REPO}/tools/setup_mistral_db.sh \
        "${MISTRAL_REPO}" \
        "${MISTRAL_CONF}" \
        "${DISTRO}" \
        postgresql \
        mistral \
        mistral \
        StackStorm \
        StackStorm
}

case ${subcommand} in
start)
    init
    st2start
    ;;
startclean)
    init
    st2clean
    st2start
    ;;
stop)
    st2stop
    ;;
restart)
    st2stop
    sleep 1
    init
    st2start
    ;;
*)
    usage
    ;;
esac
