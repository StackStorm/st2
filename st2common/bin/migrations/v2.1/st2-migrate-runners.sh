#! /bin/bash


ST2CTL_BIN='/usr/bin/st2ctl'

register_runners() {
    ${ST2CTL_BIN} reload --register-runners --register-fail-on-failure
    if [[ $? == 0 ]];then
        echo "Registered runners successfully."
        exit 0
    else
        echo "Failed registering runners."
        exit 1
    fi
}

register_runners
