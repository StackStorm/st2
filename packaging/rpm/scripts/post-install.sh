set -e

# make sure that our socket generators run
systemctl daemon-reload >/dev/null 2>&1 || true
