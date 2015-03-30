#!/bin/bash

PACK=$1
if [[ "$PACK" == "examples" ]]; then
    PATH="/usr/share/doc/st2"
elif [[ "$PACK" == "tests" ]]; then
    PATH="/usr/share/stackstorm"
else
    echo "Invalid pack: ${PACK}"
    exit 2
fi

echo -e "Adding packs_base_paths for ${PATH}/${PACK}..."
grep packs_base_path /etc/st2/st2.conf || echo -e "\n[content]\npacks_base_paths = ${PATH}/${PACK}" >> /etc/st2/st2.conf

if [[ $? -ne 0 ]]; then
    echo "Failed to add pack path!"
    exit 2
else
    echo -e "Restarting St2 for new path to take affect..."
    st2ctl restart
    echo -e "Reloading St2 content..."
    st2ctl reload
fi

virtualenv --system-site-packages /opt/stackstorm/virtualenvs/${PACK}
pip install -r /opt/stackstorm/virtualenvs/${PACK}/requirements.txt -E /opt/stackstorm/virtualenvs/${PACK}
