#!/usr/bin/env bash

set +x

# Default TERM to "ansi" when it is empty.
export TERM="${TERM:-ansi}"
# TERM is 'unknown' when run in github actions which causes tmux to fail, so force it to "ansi".
test "$TERM" = "unknown" && export TERM="ansi"

function usage() {
    cat<<EOF >&2
    Usage: $0 [start|stop|restart|startclean] [-r runner_count] [-s scheduler_count] [-w workflow_engine_count] [-g] [-x] [-c] [-6]
     -r : the number of st2runner instances start
     -s : the numer of st2scheduler instances to start
     -w : the numer of st2workflow-engine instances to start
     -g : disable gunicorn
     -x : enable copy test packs
     -c : disable load content
     -6 : enable use of ipv6
EOF
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

# Colour echo
function cecho()
{
    if [[ "$1" == "-n" ]]; then
        # No carrage return
        NCR="$1"; shift
    else
        NCR=""
    fi
    C="$1"; shift
    MSG="$1"
    echo $NCR -e "\e[${C}m${MSG}\e[0m"
}

function heading()
{
    MSG="$1"
    cecho "34;7" "$MSG"
}
function iecho()
{
    MSG="$1"
    cecho "37;1" "$MSG"
}
function wecho()
{
    MSG="$1"
    cecho "33;1" "$MSG"
}
function eecho()
{
    MSG="$1"
    cecho "31;1" "$MSG"
}
function init()
{
    heading "Initialising system variables ..."
    # Capture list of exported vars before adding any others
    ST2VARS=(${!ST2_@})

    ST2_BASE_DIR="/opt/stackstorm"
    COMMAND_PATH=${0%/*}
    CURRENT_DIR=$(pwd)
    CURRENT_USER=$(whoami)
    CURRENT_USER_GROUP=$(id -gn)
    echo -n "Current user:group = "; iecho "${CURRENT_USER}:${CURRENT_USER_GROUP}"

    if [[ (${COMMAND_PATH} == /*) ]] ;
    then
        ST2_REPO=${COMMAND_PATH}/..
    else
        ST2_REPO=${CURRENT_DIR}/${COMMAND_PATH}/..
    fi
    ST2_REPO=$(readlink -f ${ST2_REPO})
    ST2_LOGS="${ST2_REPO}/logs"
    # ST2_REPO/virtualenv is the Makefile managed dir.
    # The workflow should set this to use a pants exported or other venv instead.
    VIRTUALENV=${VIRTUALENV_DIR:-${ST2_REPO}/virtualenv}
    VIRTUALENV=$(readlink -f ${VIRTUALENV})
    PY=${VIRTUALENV}/bin/python
    if [ ! -f "${PY}" ]; then
        eecho "${PY} does not exist"
        exit 1
    fi
    PYTHON_VERSION=$(${PY} --version 2>&1)

    echo -n "Using virtualenv: "; iecho "${VIRTUALENV}"
    echo -n "Using python: "; iecho "${PY} (${PYTHON_VERSION})"
    echo -n "Log file location: "; iecho "${ST2_LOGS}"
    echo -n "Using tmux: "; iecho "$(tmux -V)"

    if [ -z "$ST2_CONF" ]; then
        ST2_CONF=${ST2_REPO}/conf/st2.dev.conf
    fi
    # ST2_* vars directly override conf vars using oslo_config's env var feature.
    # The ST2TESTS_* vars are only for tests, and take precedence over ST2_* vars.
    if [ -n "${ST2TESTS_SYSTEM_USER}" ]; then
        export ST2_SYSTEM_USER__USER="${ST2TESTS_SYSTEM_USER}"
        ST2VARS+=("ST2_SYSTEM_USER__USER")
    fi
    if [ -n "${ST2TESTS_REDIS_HOST}" ] && [ -n "${ST2TESTS_REDIS_PORT}" ]; then
        export ST2_COORDINATION__URL="redis://${ST2TESTS_REDIS_HOST}:${ST2TESTS_REDIS_PORT}?namespace=_st2_dev"
        ST2VARS+=("ST2_COORDINATION__URL")
    fi

    ST2_CONF=$(readlink -f ${ST2_CONF})
    echo -n "Using st2 config file: "; iecho "$ST2_CONF"

    if [ ! -f "$ST2_CONF" ]; then
        eecho "Config file $ST2_CONF does not exist."
        exit 1
    fi

}

function exportsdir()
{
    local EXPORTS_DIR=$(grep 'dump_dir' ${ST2_CONF} | sed -e "s~^dump_dir[ ]*=[ ]*\(.*\)~\1~g")
    if [ -z $EXPORTS_DIR ]; then
        EXPORTS_DIR="/opt/stackstorm/exports"
    fi
    echo -n "Export directories: "; iecho "$EXPORTS_DIR"
}

function st2start()
{
    heading "Starting all st2 servers ..."

    # Determine where the st2 repo is located. Some assumption is made here
    # that this script is located under st2/tools.

    # Change working directory to the root of the repo.
    echo -n "Changing working directory to "; iecho "${ST2_REPO}"
    cd ${ST2_REPO}

    BASE_DIR=$(grep 'base_path' ${ST2_CONF} | awk 'BEGIN {FS=" = "}; {print $2}')
    if [ -z BASE_DIR ]; then
        BASE_DIR="/opt/stackstorm"
    fi
    CONFIG_BASE_DIR="${BASE_DIR}/configs"
    echo -n "Using config base dir: "; iecho "$CONFIG_BASE_DIR"

    if [ ! -d "$CONFIG_BASE_DIR" ]; then
        wecho "$CONFIG_BASE_DIR doesn't exist. Creating ..."
        sudo mkdir -p $CONFIG_BASE_DIR
    fi

    PACKS_BASE_DIR=$(grep 'packs_base_path' ${ST2_CONF} | awk 'BEGIN {FS=" = "}; {print $2}')
    if [ -z $PACKS_BASE_DIR ]; then
        PACKS_BASE_DIR="/opt/stackstorm/packs"
    fi
    echo -n "Using content packs base dir: "; iecho "$PACKS_BASE_DIR"

    # Copy and overwrite the action contents
    if [ ! -d "$ST2_BASE_DIR" ]; then
        wecho "$ST2_BASE_DIR doesn't exist. Creating ..."
        sudo mkdir -p $PACKS_BASE_DIR
    fi

    if [ "${use_ipv6}" = true ]; then
        echo '  using IPv6 bindings ...'
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
        echo -n "Copying test packs examples and fixtures to "; iecho "$PACKS_BASE_DIR"
        cp -Rp ./contrib/examples $PACKS_BASE_DIR
        # Clone st2tests in a tmp directory.
        CLONE_TMP_DIR=$(mktemp -d)
        pushd "${CLONE_TMP_DIR}"
        echo Cloning https://github.com/StackStorm/st2tests.git
        # -q = no progress reporting (better for CI). Errors will still print.
        git clone -q https://github.com/StackStorm/st2tests.git
        ret=$?
        if [ ${ret} -eq 0 ]; then
            cp -Rp ./st2tests/packs/fixtures $PACKS_BASE_DIR
        else
            eecho "Failed to clone st2tests repo"
        fi
        popd
        rm -Rf "${CLONE_TMP_DIR}"
    fi

    # activate virtualenv to set PYTHONPATH
    source "${VIRTUALENV}/bin/activate"
    # set configuration file location.
    export ST2_CONFIG_PATH="${ST2_CONF}"

    # Kill existing st2 terminal multiplexor sessions
    for tmux_session in $(tmux ls 2>/dev/null | awk -F: '/^st2-/ {print $1}')
    do
        echo "Kill existing session $tmux_session"
        tmux kill-session -t $tmux_session
    done

    local PRE_SCRIPT_VARS=()
    for var_name in "${ST2VARS[@]}"; do
      PRE_SCRIPT_VARS+=("${var_name}=${!var_name}")
    done
    PRE_SCRIPT_VARS+=("ST2_CONFIG_PATH=${ST2_CONF}")

    # PRE_SCRIPT should not end with ';' so that using it is clear.
    local PRE_SCRIPT="export ${PRE_SCRIPT_VARS[@]}; source ${VIRTUALENV}/bin/activate"

    # Run the st2 API server
    if [ "${use_gunicorn}" = true ]; then
        echo 'Starting st2-api using gunicorn ...'
        tmux new-session -d -s st2-api "${PRE_SCRIPT}; ${VIRTUALENV}/bin/gunicorn st2api.wsgi:application -k eventlet -b $BINDING_ADDRESS:9101 --workers 1 2>&1 | tee -a ${ST2_LOGS}/st2-api.log"
    else
        echo 'Starting st2-api ...'
        tmux new-session -d -s st2-api "${PRE_SCRIPT}; ${VIRTUALENV}/bin/python ./st2api/bin/st2api --config-file $ST2_CONF 2>&1 | tee -a ${ST2_LOGS}/st2-api.log"
    fi

    # Run st2stream API server
    if [ "${use_gunicorn}" = true ]; then
        echo 'Starting st2-stream using gunicorn ...'
        tmux new-session -d -s st2-stream "${PRE_SCRIPT}; ${VIRTUALENV}/bin/gunicorn st2stream.wsgi:application -k eventlet -b $BINDING_ADDRESS:9102 --workers 1 2>&1 | tee -a ${ST2_LOGS}/st2-stream.log"
    else
        echo 'Starting st2-stream ...'
        tmux new-session -d -s st2-stream "${PRE_SCRIPT}; ${VIRTUALENV}/bin/python ./st2stream/bin/st2stream --config-file $ST2_CONF 2>&1 | tee -a ${ST2_LOGS}/st2-stream.log"
    fi

    # give st2stream time to startup and load things into database
    sleep 10

    # Run the workflow engine server
    echo 'Starting st2-workflow engine(s):'
    WORKFLOW_ENGINE_SESSIONS=()
    for i in $(seq 1 $workflow_engine_count)
    do
        WORKFLOW_ENGINE_NAME=st2-workflow-$i
        WORKFLOW_ENGINE_SESSIONS+=($WORKFLOW_ENGINE_NAME)
        echo "   $WORKFLOW_ENGINE_NAME ..."
        tmux new-session -d -s $WORKFLOW_ENGINE_NAME "${PRE_SCRIPT}; ${VIRTUALENV}/bin/python ./st2actions/bin/st2workflowengine --config-file $ST2_CONF 2>&1 | tee -a ${ST2_LOGS}/${WORKFLOW_ENGINE_NAME}.log"
    done

    # Start a session for every runner
    echo 'Starting st2-actionrunner(s):'
    RUNNER_SESSIONS=()
    for i in $(seq 1 $runner_count)
    do
        RUNNER_NAME=st2-actionrunner-$i
        RUNNER_SESSIONS+=($RUNNER_NAME)
        echo "   $RUNNER_NAME ..."
        tmux new-session -d -s $RUNNER_NAME "${PRE_SCRIPT}; ${VIRTUALENV}/bin/python ./st2actions/bin/st2actionrunner --config-file $ST2_CONF 2>&1 | tee -a ${ST2_LOGS}/${RUNNER_NAME}.log"
    done

    # Run the garbage collector service
    echo 'Starting st2-garbagecollector ...'
    tmux new-session -d -s st2-garbagecollector "${PRE_SCRIPT}; ${VIRTUALENV}/bin/python ./st2reactor/bin/st2garbagecollector --config-file $ST2_CONF 2>&1 | tee -a ${ST2_LOGS}/st2-garbagecollector.log"

    # Run the scheduler server
    echo 'Starting st2-scheduler(s):'
    SCHEDULER_SESSIONS=()
    for i in $(seq 1 $scheduler_count)
    do
        SCHEDULER_NAME=st2-scheduler-$i
        SCHEDULER_SESSIONS+=($SCHEDULER_NAME)
        echo "   $SCHEDULER_NAME ..."
        tmux new-session -d -s $SCHEDULER_NAME "${PRE_SCRIPT}; ${VIRTUALENV}/bin/python ./st2actions/bin/st2scheduler --config-file $ST2_CONF 2>&1 | tee -a ${ST2_LOGS}/${SCHEDULER_NAME}.log"
    done

    # Run the sensor container server
    echo 'Starting st2-sensorcontainer ...'
    tmux new-session -d -s st2-sensorcontainer "${PRE_SCRIPT}; ${VIRTUALENV}/bin/python ./st2reactor/bin/st2sensorcontainer --config-file $ST2_CONF 2>&1 | tee -a ${ST2_LOGS}/st2-sensorcontainer.log"

    # Run the rules engine server
    echo 'Starting st2-rulesengine ...'
    tmux new-session -d -s st2-rulesengine "${PRE_SCRIPT}; ${VIRTUALENV}/bin/python ./st2reactor/bin/st2rulesengine --config-file $ST2_CONF 2>&1 | tee -a ${ST2_LOGS}/st2-rulesengine.log"

    # Run the timer engine server
    echo 'Starting st2-timersengine ...'
    tmux new-session -d -s st2-timersengine "${PRE_SCRIPT}; ${VIRTUALENV}/bin/python ./st2reactor/bin/st2timersengine --config-file $ST2_CONF 2>&1 | tee -a ${ST2_LOGS}/st2-timersengine.log"

    # Run the actions notifier
    echo 'Starting st2-notifier ...'
    tmux new-session -d -s st2-notifier "${PRE_SCRIPT}; ${VIRTUALENV}/bin/python ./st2actions/bin/st2notifier --config-file $ST2_CONF 2>&1 | tee -a ${ST2_LOGS}/st2-notifier.log"

    # Run the auth API server
    if [ "${use_gunicorn}" = true ]; then
        echo 'Starting st2-auth using gunicorn ...'
        tmux new-session -d -s st2-auth "${PRE_SCRIPT}; ${VIRTUALENV}/bin/gunicorn st2auth.wsgi:application -k eventlet -b $BINDING_ADDRESS:9100 --workers 1 2>&1 | tee -a ${ST2_LOGS}/st2-auth.log"
    else
        echo 'Starting st2-auth ...'
        tmux new-session -d -s st2-auth "${PRE_SCRIPT}; ${VIRTUALENV}/bin/python ./st2auth/bin/st2auth --config-file $ST2_CONF 2>&1 | tee -a ${ST2_LOGS}/st2-auth.log"
    fi

    # Check whether tmux sessions are started
    SESSIONS=(
        "st2-api"
        "${WORKFLOW_ENGINE_SESSIONS[@]}"
        "${SCHEDULER_SESSIONS[@]}"
        "${RUNNER_SESSIONS[@]}"
        "st2-sensorcontainer"
        "st2-rulesengine"
        "st2-notifier"
        "st2-auth"
        "st2-timersengine"
        "st2-garbagecollector"
    )

    echo
    for s in "${SESSIONS[@]}"
    do
        tmux ls | grep "^${s}:\?[[:space:]]" &> /dev/null
        if [ $? != 0 ]; then
            eecho "ERROR: terminal multiplex session for $s failed to start."
        fi
    done

    if [ "$load_content" = true ]; then
        # Register contents
        echo 'Registering sensors, runners, actions, rules, aliases, and policies ...'
        ${VIRTUALENV}/bin/python ./st2common/bin/st2-register-content --config-file $ST2_CONF --register-all
    fi

    if [ "$copy_test_packs" = true ]; then
        st2 run packs.setup_virtualenv packs=fixtures
        if [ $? != 0 ]; then
            wecho "WARNING: Unable to setup virtualenv for the \"tests\" pack. Please setup virtualenv for the \"tests\" pack before running integration tests"
        fi
    fi

    # Display default credentials to the multiplexor session
    echo "The default credentials are testu:testp"

    # List sessions
    tmux ls || exit 0
}

function st2stop()
{
    for tmux_session in $(tmux ls 2>/dev/null | awk -F: '/^st2-/ {print $1}')
    do
        echo "Kill existing session $tmux_session"
        tmux kill-session -t $tmux_session
    done

    if [ "${use_gunicorn}" = true ]; then
        pids=$(ps -ef | grep "wsgi:application" | grep -v "grep" | awk '{print $2}')
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

function st2clean()
{
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
        echo "Removing $EXPORTS_DIR ..."
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
