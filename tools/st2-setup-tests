#!/bin/bash

PACK=tests
PATH="/usr/share/stackstorm"

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

if [ -f ${PATH}/${PACK}/requirements.txt ]; then
    echo "Creating virtualenv for ${PACK}..."
    mkdir -p /opt/stackstorm/virtualenvs
    virtualenv --system-site-packages /opt/stackstorm/virtualenvs/${PACK}
    echo "Installing requirements.txt for ${PACK}..."
    pip install -r ${PATH}/${PACK}/requirements.txt -E /opt/stackstorm/virtualenvs/${PACK}
fi
