#!/bin/sh

REPO_DIR=/opt/stackstorm/repo

USER="vagrant:vagrant"

BASEDIR=`dirname ${0}`
CONTENT_FOLDER=`realpath ${BASEDIR}/../../content`

CONTENT_SETS="devel"

FORCE='false'

print_usage() {
    echo "usage: populate_stackstorm_repo.sh [--force]"
    echo ""
    echo "    --force    forcibly overwrite anything already in the repo"
    echo ""
    exit 1
}

if [ "$#" -ne "0" ]; then
    while [ "$#" -gt "0" ]
    do
        case $1 in

        --force)
                FORCE='true'
                shift
                ;;
        *)
                echo "error: unknown option '${1}' ... aborting"
                print_usage
                shift
                ;;
        esac
    done
fi


if [ -e ${REPO_DIR} ] && [ "${FORCE}" != "true" ]; then
    echo "error: repo already exists. Aborting population"
    exit 1
fi

echo "Creating repo folder: ${REPO_DIR}"
sudo mkdir -p ${REPO_DIR}
sudo chown -R ${USER} ${REPO_DIR}

echo "Copying content sets from ${CONTENT_FOLDER} to repo folder"

for set in ${CONTENT_SETS}; do
    echo "    copying content set: ${set}"
    cp -Rp ${CONTENT_FOLDER}/${set}/* ${REPO_DIR}
done


echo "Finished copying content"
echo "Repo is ready for use"
