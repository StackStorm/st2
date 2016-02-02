#!/usr/bin/env bash

function usage() {
    echo "Usage: $0 [start|stop|restart|startclean] [-r runner_count] [-g] [-x] [-c]" >&2
}

subcommand=$1; shift
runner_count=1
use_gunicorn=true
copy_examples=false
load_content=true

while getopts ":r:gxc" o; do
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


    if [ -z "$ST2_CONF" ]; then
        ST2_CONF=${ST2_REPO}/conf/st2.dev.conf
    fi
    echo "Using st2 config file: $ST2_CONF"

    if [ ! -f "$ST2_CONF" ]; then
        echo "Config file $ST2_CONF does not exist."
        exit 1
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
    fi

    VIRTUALENVS_DIR=$ST2_BASE_DIR/virtualenvs

    sudo mkdir -p $PACKS_BASE_DIR/default/sensors/
    sudo mkdir -p $PACKS_BASE_DIR/default/actions/
    sudo mkdir -p $PACKS_BASE_DIR/default/rules/
    sudo mkdir -p $VIRTUALENVS_DIR
    sudo chown -R ${CURRENT_USER}:${CURRENT_USER_GROUP} $PACKS_BASE_DIR
    sudo chown -R ${CURRENT_USER}:${CURRENT_USER_GROUP} $VIRTUALENVS_DIR
    cp -Rp ./contrib/core/ $PACKS_BASE_DIR
    cp -Rp ./contrib/packs/ $PACKS_BASE_DIR

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

    # Run the st2 API server
    echo 'Starting screen session st2-api...'
    if [ "${use_gunicorn}" = true ]; then
        echo '  using guicorn to run st2-api...'
        export ST2_CONFIG_PATH=${ST2_CONF}
        screen -d -m -S st2-api ./virtualenv/bin/gunicorn_pecan \
            ./st2api/st2api/gunicorn_config.py -k eventlet -b 127.0.0.1:9101 --workers 1
    else
        screen -d -m -S st2-api ./virtualenv/bin/python \
            ./st2api/bin/st2api \
            --config-file $ST2_CONF
    fi

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
        echo '  using guicorn to run st2-auth...'
        export ST2_CONFIG_PATH=${ST2_CONF}
        screen -d -m -S st2-auth ./virtualenv/bin/gunicorn_pecan \
            ./st2auth/st2auth/gunicorn_config.py -k eventlet -b 127.0.0.1:9100 --workers 1
    else
        screen -d -m -S st2-auth ./virtualenv/bin/python \
        ./st2auth/bin/st2auth \
        --config-file $ST2_CONF
    fi

    if [ -n "$ST2_EXPORTER" ]; then
        EXPORTS_DIR=$(exportsdir)
        sudo mkdir -p $EXPORTS_DIR
        sudo chown -R ${CURRENT_USER}:${CURRENT_USER_GROUP} $EXPORTS_DIR
        echo 'Starting screen session st2-exporter...'
        screen -d -m -S st2-exporter ./virtualenv/bin/python \
            ./st2exporter/bin/st2exporter \
            --config-file $ST2_CONF
    fi

    # Check whether screen sessions are started
    SCREENS=(
        "st2-api"
        "${RUNNER_SCREENS[@]}"
        "st2-sensorcontainer"
        "st2-rulesengine"
        "st2-resultstracker"
        "st2-notifier"
        "st2-auth"
    )

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
        echo 'Registering sensors, actions, rules, aliases, and policies...'
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
}

function st2clean(){
    # clean mongo
    mongo st2 --eval "db.dropDatabase();"
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
