echo -n "Please enter your StackStorm username: "
read ST2_USERNAME
export ST2_USERNAME=$ST2_USERNAME

echo -n "Please enter your StackStrom password: "
read -s ST2_PASSWORD
echo
export ST2_PASSWORD=$ST2_PASSWORD

export ST2_BASE_URL=http://127.0.0.1
export ST2_AUTH_URL=http://127.0.0.1:9100
export ST2_API_URL=http://127.0.0.1:9101/v1

TOKEN=`st2 auth $ST2_USERNAME -p $ST2_PASSWORD -j | jq '.token'`
export ST2_AUTH_TOKEN=`echo "$TOKEN" | sed -e 's/^"//'  -e 's/"$//'`
