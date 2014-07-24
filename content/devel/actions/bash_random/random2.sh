#!/bin/bash

echo "count>>${count}<<"
if [[ ! $count ]]; then
    # count variable not set so default to 3
    RANDOM_COUNT=3
else
    RANDOM_COUNT=${count}
fi

for (( i=1; i <= ${RANDOM_COUNT}; i++ ))
do
 echo "Random number $i: $RANDOM"
done
