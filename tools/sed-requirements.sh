#!/usr/bin/env bash
if [[ -z "${GITLAB_TOKEN_U}" ]]; then
    echo "set GITLAB_TOKEN_U to user"
    exit 1
fi
if [[ -z "${GITLAB_TOKEN_K}" ]]; then
    echo "set GITLAB_TOKEN_K to PAC token"
    exit 1
fi


set -e
sed -i "s/GITLAB_TOKEN_USER/${GITLAB_TOKEN_U}/g" ./st2common/in-requirements.txt
sed -i "s/GITLAB_TOKEN_USER/${GITLAB_TOKEN_U}/g" ./st2actions/in-requirements.txt
sed -i "s/GITLAB_TOKEN_USER/${GITLAB_TOKEN_U}/g" ./st2auth/in-requirements.txt
sed -i "s/GITLAB_TOKEN_USER/${GITLAB_TOKEN_U}/g" requirements.txt
sed -i "s/GITLAB_TOKEN_KEY/${GITLAB_TOKEN_K}/g" ./st2common/in-requirements.txt
sed -i "s/GITLAB_TOKEN_KEY/${GITLAB_TOKEN_K}/g" ./st2actions/in-requirements.txt
sed -i "s/GITLAB_TOKEN_KEY/${GITLAB_TOKEN_K}/g" ./st2auth/in-requirements.txt
sed -i "s/GITLAB_TOKEN_KEY/${GITLAB_TOKEN_K}/g" requirements.txt
