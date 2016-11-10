#!/bin/bash

if [[ -z $1 ]]; then
  echo "USAGE: file_touch FILENAME"
  exit 2
else
  DATE=`date +%s`
  echo "${DATE}" > $1
  if [ $? -ne 0 ]; then
    echo "Failed to write ${DATE} to ${1}"
    exit 2
  else
    echo "Successfully updated ${1}"
  fi
fi
