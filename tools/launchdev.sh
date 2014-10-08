#!/bin/bash

runner_count=1
if [ "$#" -gt 1 ]; then
    runner_count=${2}
fi

function st2start(){
    echo "Starting all st2 servers..."

    # Determine where the stanley repo is located. Some assumption is made here
    # that this script is located under stanley/tools.

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

    # Change working directory to the root of the repo.
    ST2_REPO=`realpath ${ST2_REPO}`
    echo "Changing working directory to ${ST2_REPO}..."
    cd ${ST2_REPO}

    if [ -z "$ST2_CONF" ]; then
        ST2_CONF=${ST2_REPO}/conf/stanley.conf
    fi
    echo "Using st2 config file: $ST2_CONF"

    if [ ! -f "$ST2_CONF" ]; then
        echo "Config file $ST2_CONF does not exist."
        exit 1
    fi

    CONTENT_PACKS_BASE_DIR=$(grep 'content_packs_base_path' ${ST2_CONF} \
        | awk 'BEGIN {FS=" = "}; {print $2}')
    if [ -z $CONTENT_PACKS_BASE_DIR ]; then
        CONTENT_PACKS_BASE_DIR="/opt/stackstorm"
    fi
    echo "Using conent packs base dir: $CONTENT_PACKS_BASE_DIR"

    # Copy and overwrite the action contents
    if [ ! -d "/opt/stackstorm" ]; then
        echo "/opt/stackstorm doesn't exist. Creating..."
        sudo mkdir -p $CONTENT_PACKS_BASE_DIR
    fi

    sudo mkdir -p $CONTENT_PACKS_BASE_DIR/default/sensors/
    sudo mkdir -p $CONTENT_PACKS_BASE_DIR/default/actions/
    sudo mkdir -p $CONTENT_PACKS_BASE_DIR/default/rules/
    sudo chown -R ${CURRENT_USER}:${CURRENT_USER_GROUP} $CONTENT_PACKS_BASE_DIR
    cp -Rp ./contrib/core/ $CONTENT_PACKS_BASE_DIR

    # activate virtualenv to set PYTHONPATH
    source ./virtualenv/bin/activate

    # Kill existing st2 screens
    screen -ls | grep st2 &> /dev/null
    if [ $? == 0 ]; then
        echo 'Killing existing st2 screen sessions...'
        screen -ls | grep st2 | cut -d. -f1 | awk '{print $1}' | xargs kill
    fi

    # Run the history server
    echo 'Starting screen session st2-history...'
    screen -d -m -S st2-history ./virtualenv/bin/python \
        ./st2actions/bin/history \
        --config-file $ST2_CONF

    # Run the action runner server
    echo 'Starting screen session st2-actionrunner...'
    screen -d -m -S st2-actionrunner

    # start each runner in its own nested screen tab
    for i in $(seq 1 $runner_count)
    do
        # a screen for every runner
        screen -S st2-actionrunner -X screen -t runner-$i ./virtualenv/bin/python \
            ./st2actions/bin/actionrunner \
            --config-file $ST2_CONF
    done

    # Run the st2 API server
    echo 'Starting screen session st2-api...'
    screen -d -m -S st2-api ./virtualenv/bin/python \
        ./st2api/bin/st2api \
        --config-file $ST2_CONF

    # Run the reactor server
    echo 'Starting screen session st2-reactor...'
    screen -d -m -S st2-reactor ./virtualenv/bin/python \
        ./st2reactor/bin/sensor_container \
        --config-file $ST2_CONF

    # Check whether screen sessions are started
    screens=(
        "st2-api"
        "st2-history"
        "st2-actionrunner"
        "st2-reactor"
    )

    echo
    for s in "${screens[@]}"
    do
        screen -ls | grep "${s}[[:space:]]" &> /dev/null
        if [ $? != 0 ]; then
            echo "ERROR: Unable to start screen session for $s."
        fi
    done

    # List screen sessions
    screen -ls

    echo 'Registering actions and rules...'
    ./virtualenv/bin/python \
        ./st2common/bin/registercontent.py \
        --config-file $ST2_CONF --register-all
}

function st2stop(){
    screen -ls | grep st2 &> /dev/null
    if [ $? == 0 ]; then
        echo 'Killing existing st2 screen sessions...'
        screen -ls | grep st2 | cut -d. -f1 | awk '{print $1}' | xargs kill
    fi
}

function st2clean(){
    # clean mongo
    mongo st2 --eval "db.dropDatabase();"
    # start with clean logs
    LOGDIR=$(dirname $0)/../logs
    rm ${LOGDIR}/*
}

case ${1} in
start)
    st2start
    ;;
startclean)
    st2clean
    st2start
    ;;
stop)
    st2stop
    ;;
restart)
    st2stop
    sleep 1
    st2start
    ;;
*)
    echo "Usage: $0 [start|stop|restart|startclean]" >&2
    ;;
esac
