#!/bin/bash

if [ "$#" -ne 1 ] || ([ ${1} != "start" ] && [ ${1} != "stop" ]) ; then
  echo "Usage: $0 [start|stop]" >&2
  exit 1
fi

if [[ ${1} == "start" ]]; then

    echo "Starting all Stanley servers..."

    # Install screen if it is not installed
    if ! yum list installed | grep -qw screen; then
        echo "Installing the screen program..."
        sudo yum install screen
    fi

    # Determine where the stanley repo is located. Some assumption is made here
    # that this script is located under stanley/contrib/sandbox/scripts.

    COMMAND_PATH=${0%/*}
    CURRENT_DIR=`pwd`

    if [[ (${COMMAND_PATH} == /*) ]] ;
    then
        ST2_REPO=${COMMAND_PATH}/../../..
    else
        ST2_REPO=${CURRENT_DIR}/${COMMAND_PATH}/../../..
    fi

    # Change working directory to the root of the repo.
    ST2_REPO=`realpath ${ST2_REPO}`
    echo "Changing working directory to ${ST2_REPO}..."
    cd ${ST2_REPO}

    # Copy and overwrite the action contents
    mkdir -p /opt/stackstorm
    cp -Rp ./contrib/core/actions /opt/stackstorm 

    # activate virtualenv to set PYTHONPATH
    source ./virtualenv/bin/activate

    # Run the datastore API server
    echo 'Starting screen session st2-datastore...'
    screen -d -m -S st2-datastore ./virtualenv/bin/python \
        ./st2datastore/bin/datastore_controller \
        --config-file ./conf/stanley.conf

    # Run the action runner API server
    echo 'Starting screen session st2-actionrunner...'
    screen -d -m -S st2-actionrunner ./virtualenv/bin/python \
        ./st2actionrunnercontroller/bin/actionrunner_controller \
        --config-file ./conf/stanley.conf

    # Run the action API server
    echo 'Starting screen session st2-action...'
    screen -d -m -S st2-action ./virtualenv/bin/python \
        ./st2actioncontroller/bin/action_controller \
        --config-file ./conf/stanley.conf

    # Run the reactor server
    echo 'Starting screen session st2-reactor...'
    screen -d -m -S st2-reactor ./virtualenv/bin/python \
        ./st2reactor/bin/sensor_container \
        --config-file ./conf/stanley.conf

    # Run the reactor API server
    echo 'Starting screen session st2-reactorcontroller...'
    screen -d -m -S st2-reactorcontroller ./virtualenv/bin/python \
        ./st2reactorcontroller/bin/reactor_controller \
        --config-file ./conf/stanley.conf

elif [[ ${1} == "stop" ]]; then

    echo "Stopping all Stanley servers..."

    # Stop the reactor API server
    echo "Terminating the screen session for st2-reactorcontroller..."
    screen -X -S st2-reactorcontroller quit

    # Stop the reactor server
    echo "Terminating the screen session for st2-reactor..."
    screen -X -S st2-reactor quit

    # Stop the action API server
    echo "Terminating the screen session for st2-action..."
    screen -X -S st2-action quit

    # Stop the action runner API server
    echo "Terminating the screen session for st2-actionrunner..."
    screen -X -S st2-actionrunner quit

    # Stop the datastore API server
    echo "Terminating the screen session for st2-datastore..."
    screen -X -S st2-datastore quit
fi
