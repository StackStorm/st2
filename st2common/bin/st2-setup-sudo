#!/bin/bash
# Generates sudo configuration for ST2 based on security mode
# Copyright 2020 The StackStorm Authors.

set -e

ST2_CONF="${ST2_CONF:-/etc/st2/st2.conf}"
SUDOERS_FILE="/etc/sudoers.d/st2"

# Function to read config value from st2.conf
get_config_value() {
    local section="$1"
    local key="$2"
    local default="$3"

    # Try to read from config file
    if [ -f "$ST2_CONF" ]; then
        # Look for the section and key
        value=$(awk -v section="$section" -v key="$key" '
            /^\[/ { in_section=0 }
            $0 == "["section"]" { in_section=1; next }
            in_section && $0 ~ "^"key" *= *" {
                sub("^"key" *= *", "");
                gsub(/^[ \t]+|[ \t]+$/, "");
                print;
                exit
            }
        ' "$ST2_CONF")

        if [ -n "$value" ]; then
            echo "$value"
            return
        fi
    fi

    # Return default if not found
    echo "$default"
}

# Read security mode from config (defaults to legacy)
SECURITY_MODE=$(get_config_value "system_security" "security_mode" "legacy")

echo "Configuring ST2 sudo access in ${SECURITY_MODE} mode..."

case "$SECURITY_MODE" in
    restricted)
        cat > "$SUDOERS_FILE" << 'EOF'
# ST2 Restricted Security Mode
# ST2 service can only execute commands from /opt/stackstorm
# This provides enhanced security by limiting the scope of sudo access

# Allow execution of pack actions, sensors, and ST2 scripts
Cmnd_Alias ST2_COMMANDS = /opt/stackstorm/packs/*/actions/*, \
                           /opt/stackstorm/packs/*/sensors/*, \
                           /opt/stackstorm/st2/bin/*, \
                           /usr/bin/bash -c /opt/stackstorm/*, \
                           /bin/bash -c /opt/stackstorm/*

# Allow st2 to run commands as stanley and root users
# Only commands from ST2_COMMANDS alias are allowed
st2 ALL=(stanley) NOPASSWD: ST2_COMMANDS
st2 ALL=(root) NOPASSWD: ST2_COMMANDS

# Explicitly deny dangerous security-related commands
Cmnd_Alias DANGEROUS = /usr/bin/passwd, \
                       /usr/sbin/visudo, \
                       /bin/su, \
                       /usr/bin/sudo

st2 ALL=(ALL) !DANGEROUS
EOF
        ;;

    legacy|*)
        cat > "$SUDOERS_FILE" << 'EOF'
# ST2 Legacy Security Mode (backward compatible)
# ST2 service has broad sudo access to maintain compatibility with existing actions
# This is the default mode to ensure smooth upgrades

# Allow st2 to run as stanley and root users with full sudo access
st2 ALL=(stanley,root) NOPASSWD: ALL

# Still explicitly deny changing security settings to prevent privilege escalation
Cmnd_Alias DANGEROUS = /usr/bin/passwd root, \
                       /usr/sbin/visudo

st2 ALL=(ALL) !DANGEROUS
EOF
        ;;
esac

# Set correct permissions on sudoers file
chmod 0440 "$SUDOERS_FILE"

# Validate the sudoers file
if command -v visudo >/dev/null 2>&1; then
    if visudo -c -f "$SUDOERS_FILE" >/dev/null 2>&1; then
        echo "✓ Sudo configuration validated and updated: $SUDOERS_FILE"
    else
        echo "✗ ERROR: Generated sudoers file has syntax errors!"
        echo "  Removing invalid file to prevent system issues..."
        rm -f "$SUDOERS_FILE"
        exit 1
    fi
else
    echo "⚠ Warning: visudo not found, skipping validation"
    echo "  Sudo configuration updated: $SUDOERS_FILE"
fi

exit 0