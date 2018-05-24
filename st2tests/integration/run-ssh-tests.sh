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
        ST2_CONF=${ST2_REPO}/st2tests/conf/st2.conf
    fi
    echo "Using st2 config file: $ST2_CONF"
    if [ ! -f "$ST2_CONF" ]; then
        echo "Config file $ST2_CONF does not exist."
        exit 1
    fi

    ## Setup config file

    # Use test SSH keys.
    ORIG_SSH_KEY_FILE=$(grep 'ssh_key_file' ${ST2_CONF} | awk 'BEGIN {FS=" = "}; {print $2}')

    # RISK. RISK. RISK. This key is avilable publicly. DO NOT CHANGE THIS AND USE A SECURE KEY.
    # https://github.com/mitchellh/vagrant/blob/master/keys/vagrant
    SSH_KEY_FILE=$ST2_REPO/st2tests/conf/vagrant.privkey.insecure
    echo "Swapping out SSH key: ${ORIG_SSH_KEY_FILE} with key: ${SSH_KEY_FILE}"
    sed -i "s|$ORIG_SSH_KEY_FILE|$SSH_KEY_FILE|g" ${ST2_CONF}

    # Use content packs in st2tests.
    CONTENT_PACK_BASE_DIR=$ST2_REPO/st2tests/testpacks/
    ORIG_CONTENT_PACK_BASE_DIR=$(grep 'packs_base_path' ${ST2_CONF} | awk 'BEGIN {FS=" = "}; {print $2}')
    if [ -z "$ORIG_CONTENT_PACK_BASE_DIR" ]; then
        echo "[content]\npacks_base_path = ${CONTENT_PACK_BASE_DIR}" >> ${ST2_CONF}
        ORIG_CONTENT_PACK_BASE_DIR='/opt/stackstorm/packs/'
    else
        echo "Swapping out packs_base_path: ${ORIG_CONTENT_PACK_BASE_DIR} with dir: ${CONTENT_PACK_BASE_DIR}"
        sed -i "s|$ORIG_CONTENT_PACK_BASE_DIR|$CONTENT_PACK_BASE_DIR|g" ${ST2_CONF}
    fi

    # cat $ST2_CONF

    ## Run st2 now...
    echo "Running st2..."
    ST2_CONF=${ST2_CONF} ${ST2_REPO}/tools/launchdev.sh startclean
    echo
    echo
    echo "Running SSH tests in a loop(count=$loop_count) ..."
    echo "Activating virtual environment..."
    # activate virtualenv to set PYTHONPATH
    if [[ "$(uname 2>/dev/null)" == "Darwin" ]]; then
        VIRTUALENV_DIR=virtualenv-osx
    else
        VIRTUALENV_DIR=virtualenv
    fi
    source ./${VIRTUALENV_DIR}/bin/activate

    # Run SSH commands test.
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

    # Run script test.
    for i in `seq 1 ${loop_count}`; do
        echo "Running test: $i"
        output=`st2 run check.loadavg period=all hosts=127.0.0.1 --json`
        # altoutput=`st2 run local date --json | python -mjson.tool`
        status=$(echo "$output" | grep -Po '"status":.*?[^\\]",' | awk '{print $2}' | cut -d ',' -f 1 | tr -d '"')
        if [ $status != "succeeded" ]; then
            echo "Test failed. Output: $output"
            exit 1
        fi
        ret=$(echo "$output" | grep -Po '"return_code":.*?[^\\]",')
        echo "Return code for script: ${ret}"
        echo $output
        echo "Success. $stdout"
    done

    ## Revert config files.
    echo "Swapping out SSH key: ${SSH_KEY_FILE} with key: ${ORIG_SSH_KEY_FILE}"
    sed -i "s|$SSH_KEY_FILE|$ORIG_SSH_KEY_FILE|g" $ST2_CONF

    echo "Swapping out packs_base_path: ${CONTENT_PACK_BASE_DIR} with ${ORIG_CONTENT_PACK_BASE_DIR}"
    sed -i "s|$CONTENT_PACK_BASE_DIR|$ORIG_CONTENT_PACK_BASE_DIR|g" $ST2_CONF

    ## Stop st2.
    echo "Stopping st2..."
    ST2_CONF=${ST2_CONF} ${ST2_REPO}/tools/launchdev.sh stop

    ## Cleanup core and default packs.
    rm -rf $ST2_REPO/st2tests/testpacks/core
    rm -rf $ST2_REPO/st2tests/testpacks/default

    ## git co ST2_CONF.
    git checkout ${ST2_CONF}
}

sshtest
