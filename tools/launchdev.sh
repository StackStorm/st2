#!/usr/bin/env bash

function usage() {
    echo "Usage: $0 [start|stop|restart|startclean] [-r runner_count] [-s scheduler_count] [-w workflow_engine_count] [-g] [-x] [-c] [-6] [-m]" >&2
}

subcommand=$1; shift
runner_count=1
scheduler_count=1
workflow_engine_count=1
use_gunicorn=true
copy_test_packs=false
load_content=true
use_ipv6=false

while getopts ":r:s:w:gxcu6" o; do
    case "${o}" in
        r)
            runner_count=${OPTARG}
            ;;
        s)
            scheduler_count=${OPTARG}
            ;;
        w)
            workflow_engine_count=${OPTARG}
            ;;
        g)
            use_gunicorn=false
            ;;
        x)
            copy_test_packs=true
            ;;
        c)
            load_content=false
            ;;
        6)
            use_ipv6=true
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
    echo "Current user:group = ${CURRENT_USER}:${CURRENT_USER_GROUP}"

    if [[ (${COMMAND_PATH} == /*) ]] ;
    then
        ST2_REPO=${COMMAND_PATH}/..
    else
        ST2_REPO=${CURRENT_DIR}/${COMMAND_PATH}/..
    fi

    VIRTUALENV=${VIRTUALENV_DIR:-${ST2_REPO}/virtualenv}
    VIRTUALENV=$(readlink -f ${VIRTUALENV})
    PY=${VIRTUALENV}/bin/python
    PYTHON_VERSION=$(${PY} --version 2>&1)

    echo "Using virtualenv: ${VIRTUALENV}"
    echo "Using python: ${PY} (${PYTHON_VERSION})"

    if [ -z "$ST2_CONF" ]; then
        ST2_CONF=${ST2_REPO}/conf/st2.dev.conf
    fi

    ST2_CONF=$(readlink -f ${ST2_CONF})
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
    echo "Changing working directory to ${ST2_REPO}"
    cd ${ST2_REPO}

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
    sudo chown -R ${CURRENT_USER}:${CURRENT_USER_GROUP} $PACKS_BASE_DIR
    sudo chown -R ${CURRENT_USER}:${CURRENT_USER_GROUP} $VIRTUALENVS_DIR
    sudo chown -R ${CURRENT_USER}:${CURRENT_USER_GROUP} $CONFIG_BASE_DIR
    cp -Rp ./contrib/core/ $PACKS_BASE_DIR
    cp -Rp ./contrib/packs/ $PACKS_BASE_DIR

    if [ "$copy_test_packs" = true ]; then
        echo "Copying test packs examples and fixtures to $PACKS_BASE_DIR"
        cp -Rp ./contrib/examples $PACKS_BASE_DIR
        # Clone st2tests in /tmp directory.
        pushd /tmp
        echo Cloning https://github.com/StackStorm/st2tests.git
        # -q = no progress reporting (better for CI). Errors will still print.
        git clone -q https://github.com/StackStorm/st2tests.git
        ret=$?
        if [ ${ret} -eq 0 ]; then
            cp -Rp ./st2tests/packs/fixtures $PACKS_BASE_DIR
            rm -R st2tests/
        else
            echo "Failed to clone st2tests repo"
        fi
        popd
    fi

    # activate virtualenv to set PYTHONPATH
    source ${VIRTUALENV}/bin/activate

    # Kill existing st2 screens
    screen -wipe
    screen -ls | grep st2 &> /dev/null
    if [ $? == 0 ]; then
        echo 'Killing existing st2 screen sessions...'
        screen -ls | grep st2 | cut -d. -f1 | awk '{print $1}' | xargs kill
    fi

    # NOTE: We can't rely on latest version of screen with "-Logfile path"
    # option so we need to use screen config file per screen window

    # Run the st2 API server
    echo 'Starting screen session st2-api...'
    if [ "${use_gunicorn}" = true ]; then
        echo '  using gunicorn to run st2-api...'
        export ST2_CONFIG_PATH=${ST2_CONF}
        screen -L -c tools/screen-configs/st2api.conf -d -m -S st2-api ${VIRTUALENV}/bin/gunicorn \
            st2api.wsgi:application -k eventlet -b "$BINDING_ADDRESS:9101" --workers 1
    else
        screen -L -c tools/screen-configs/st2api.conf -d -m -S st2-api ${VIRTUALENV}/bin/python \
            ./st2api/bin/st2api \
            --config-file $ST2_CONF
    fi

    # Run st2stream API server
    if [ "${use_gunicorn}" = true ]; then
        echo '  using gunicorn to run st2-stream'
        export ST2_CONFIG_PATH=${ST2_CONF}
        screen -L -c tools/screen-configs/st2stream.conf -d -m -S st2-stream ${VIRTUALENV}/bin/gunicorn \
            st2stream.wsgi:application -k eventlet -b "$BINDING_ADDRESS:9102" --workers 1
    else
        screen -L -c tools/screen-configs/st2stream.conf -d -m -S st2-stream ${VIRTUALENV}/bin/python \
            ./st2stream/bin/st2stream \
            --config-file $ST2_CONF
    fi

    # Run the workflow engine server
    echo 'Starting screen session st2-workflow(s)'
    WORKFLOW_ENGINE_SCREENS=()
    for i in $(seq 1 $workflow_engine_count)
    do
        WORKFLOW_ENGINE_NAME=st2-workflow-$i
        WORKFLOW_ENGINE_SCREENS+=($WORKFLOW_ENGINE_NAME)
        echo '  starting '$WORKFLOW_ENGINE_NAME'...'
        screen -L -c tools/screen-configs/st2workflowengine.conf -d -m -S $WORKFLOW_ENGINE_NAME ${VIRTUALENV}/bin/python \
            ./st2actions/bin/st2workflowengine \
            --config-file $ST2_CONF
    done

    # Start a screen for every runner
    echo 'Starting screen sessions for st2-actionrunner(s)'
    RUNNER_SCREENS=()
    for i in $(seq 1 $runner_count)
    do
        RUNNER_NAME=st2-actionrunner-$i
        RUNNER_SCREENS+=($RUNNER_NAME)
        echo '  starting '$RUNNER_NAME'...'
        screen -L -c tools/screen-configs/st2actionrunner.conf -d -m -S $RUNNER_NAME ${VIRTUALENV}/bin/python \
            ./st2actions/bin/st2actionrunner \
            --config-file $ST2_CONF
    done

    # Run the garbage collector service
    echo 'Starting screen session st2-garbagecollector'
    screen -L -c tools/screen-configs/st2garbagecollector.conf -d -m -S st2-garbagecollector ${VIRTUALENV}/bin/python \
        ./st2reactor/bin/st2garbagecollector \
        --config-file $ST2_CONF

    # Run the scheduler server
    echo 'Starting screen session st2-scheduler(s)'
    SCHEDULER_SCREENS=()
    for i in $(seq 1 $scheduler_count)
    do
        SCHEDULER_NAME=st2-scheduler-$i
        SCHEDULER_SCREENS+=($SCHEDULER_NAME)
        echo '  starting '$SCHEDULER_NAME'...'
        screen -L -c tools/screen-configs/st2scheduler.conf -d -m -S $SCHEDULER_NAME ${VIRTUALENV}/bin/python \
            ./st2actions/bin/st2scheduler \
            --config-file $ST2_CONF
    done

    # Run the sensor container server
    echo 'Starting screen session st2-sensorcontainer'
    screen -L -c tools/screen-configs/st2sensorcontainer.conf -d -m -S st2-sensorcontainer ${VIRTUALENV}/bin/python \
        ./st2reactor/bin/st2sensorcontainer \
        --config-file $ST2_CONF

    # Run the rules engine server
    echo 'Starting screen session st2-rulesengine...'
    screen -L -c tools/screen-configs/st2rulesengine.conf -d -m -S st2-rulesengine ${VIRTUALENV}/bin/python \
        ./st2reactor/bin/st2rulesengine \
        --config-file $ST2_CONF

    # Run the timer engine server
    echo 'Starting screen session st2-timersengine...'
    screen -L -c tools/screen-configs/st2timersengine.conf -d -m -S st2-timersengine ${VIRTUALENV}/bin/python \
        ./st2reactor/bin/st2timersengine \
        --config-file $ST2_CONF

    # Run the actions notifier
    echo 'Starting screen session st2-notifier...'
    screen -L -c tools/screen-configs/st2notifier.conf -d -m -S st2-notifier ${VIRTUALENV}/bin/python \
        ./st2actions/bin/st2notifier \
        --config-file $ST2_CONF

    # Run the auth API server
    echo 'Starting screen session st2-auth...'
    if [ "${use_gunicorn}" = true ]; then
        echo '  using gunicorn to run st2-auth...'
        export ST2_CONFIG_PATH=${ST2_CONF}
        screen -L -c tools/screen-configs/st2auth.conf -d -m -S st2-auth ${VIRTUALENV}/bin/gunicorn \
            st2auth.wsgi:application -k eventlet -b "$BINDING_ADDRESS:9100" --workers 1
    else
        screen -L -c tools/screen-configs/st2auth.conf -d -m -S st2-auth ${VIRTUALENV}/bin/python \
            ./st2auth/bin/st2auth \
            --config-file $ST2_CONF
    fi

    # Start Exporter
    if [ -n "$ST2_EXPORTER" ]; then
        EXPORTS_DIR=$(exportsdir)
        sudo mkdir -p $EXPORTS_DIR
        sudo chown -R ${CURRENT_USER}:${CURRENT_USER_GROUP} $EXPORTS_DIR
        echo 'Starting screen session st2-exporter...'
        screen -L -d -m -S st2-exporter ${VIRTUALENV}/bin/python \
            ./st2exporter/bin/st2exporter \
            --config-file $ST2_CONF
    fi

    # Check whether screen sessions are started
    SCREENS=(
        "st2-api"
        "${WORKFLOW_ENGINE_SCREENS[@]}"
        "${SCHEDULER_SCREENS[@]}"
        "${RUNNER_SCREENS[@]}"
        "st2-sensorcontainer"
        "st2-rulesengine"
        "st2-notifier"
        "st2-auth"
        "st2-timersengine"
        "st2-garbagecollector"
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
        echo 'Registering sensors, runners, actions, rules, aliases, and policies...'
        ${VIRTUALENV}/bin/python \
            ./st2common/bin/st2-register-content \
            --config-file $ST2_CONF --register-all
    fi

    if [ "$copy_test_packs" = true ]; then
        st2 run packs.setup_virtualenv packs=fixtures
        if [ $? != 0 ]; then
            echo "Warning: Unable to setup virtualenv for the \"tests\" pack. Please setup virtualenv for the \"tests\" pack before running integration tests"
        fi
    fi

    # Print default creds to the screen
    echo "The default creds are testu:testp"

    # List screen sessions
    screen -ls || exit 0
}

function st2stop(){
    screen -ls | grep st2 &> /dev/null
    if [ $? == 0 ]; then
        echo 'Killing existing st2 screen sessions...'
        screen -ls | grep st2 | cut -d. -f1 | awk '{print $1}' | xargs -L 1 pkill -P
    fi

    if [ "${use_gunicorn}" = true ]; then
        pids=`ps -ef | grep "wsgi:application" | grep -v "grep" | awk '{print $2}'`
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
    . ${VIRTUALENV}/bin/activate
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
