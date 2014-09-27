#!/bin/bash

loop_count=${1}
if [ -z $loop_count ]; then
    loop_count=10
fi

function sshtest(){
    COMMAND_PATH=${0%/*}
    CURRENT_DIR=`pwd`
    CURRENT_USER=`whoami`
    CURRENT_USER_GROUP=`id -gn`

    if [[ (${COMMAND_PATH} == /*) ]] ;
    then
        ST2_REPO=${COMMAND_PATH}/../../
    else
        ST2_REPO=${CURRENT_DIR}/${COMMAND_PATH}/../../
    fi

    # Change working directory to the root of the repo.
    ST2_REPO=`realpath ${ST2_REPO}`
    echo "Changing working directory to ${ST2_REPO}..."
    cd ${ST2_REPO}

    if [ -z "$ST2_CONF" ]; then
        ST2_CONF=${ST2_REPO}/st2tests/conf/stanley.conf
    fi
    echo "Using st2 config file: $ST2_CONF"
    if [ ! -f "$ST2_CONF" ]; then
        echo "Config file $ST2_CONF does not exist."
        exit 1
    fi

    ORIG_SSH_KEY_FILE=$(grep 'ssh_key_file' ${ST2_CONF} | awk 'BEGIN {FS=" = "}; {print $2}')

    # RISK. RISK. RISK. This key is avilable publicly. DO NOT CHANGE THIS AND USE A SECURE KEY.
    # https://github.com/mitchellh/vagrant/blob/master/keys/vagrant
    SSH_KEY_FILE=$ST2_REPO/st2tests/conf/vagrant.privkey.insecure
    echo "Swapping out SSH key: ${ORIG_SSH_KEY_FILE} with key: ${SSH_KEY_FILE}"
    sed -i "s|$ORIG_SSH_KEY_FILE|$SSH_KEY_FILE|g" ${ST2_CONF}
    # cat $ST2_CONF
    echo "Running st2..."
    ST2_CONF=${ST2_CONF} ${ST2_REPO}/tools/launchdev.sh startclean
    echo
    echo
    echo "Running SSH tests in a loop(count=$loop_count) ..."
    echo "Activating virtual environment..."
    # activate virtualenv to set PYTHONPATH
    source ./virtualenv/bin/activate
    for i in `seq 1 ${loop_count}`; do
        echo "Running test: $i"
        output=`st2 run local date --json`
        # altoutput=`st2 run local date --json | python -mjson.tool`
        status=$(echo "$output" | grep -Po '"status":.*?[^\\]",' | awk '{print $2}' | cut -d ',' -f 1 | tr -d '"')
        if [ $status != "succeeded" ]; then
            echo "Test failed. Output: $output"
            exit 1
        fi
        echo $output
        echo "Success. $stdout"
    done
    echo "Swapping out SSH key: ${SSH_KEY_FILE} with key: ${ORIG_SSH_KEY_FILE}"
    sed -i "s|$SSH_KEY_FILE|$ORIG_SSH_KEY_FILE|g" $ST2_CONF
}

sshtest
