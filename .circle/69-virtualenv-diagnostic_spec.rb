# Diagnostic test to check virtualenv bundled wheels integrity
describe "virtualenv bundled wheels diagnostic" do
  describe "Check virtualenv wheel integrity" do
    describe command("bash -c '
echo \"========================================\"
echo \"  VIRTUALENV BUNDLED WHEELS DIAGNOSTIC\"
echo \"========================================\"
echo \"\"

echo \"1. Virtualenv Version:\"
/opt/stackstorm/st2/bin/python -m virtualenv --version || echo \"  ERROR: Could not determine virtualenv version\"
echo \"\"

echo \"2. Virtualenv Package Location:\"
VENV_PKG=$(/opt/stackstorm/st2/bin/python -c \"import virtualenv; print(virtualenv.__file__)\" 2>/dev/null || echo \"\")
if [ -z \"$VENV_PKG\" ]; then
    echo \"  ERROR: Could not locate virtualenv package\"
    exit 1
fi
VENV_DIR=$(dirname \"$VENV_PKG\")
echo \"  Package dir:  $VENV_DIR\"
echo \"\"

echo \"3. Bundled Wheels Directory:\"
WHEELS_DIR=\"$VENV_DIR/seed/wheels/embed\"
if [ -d \"$WHEELS_DIR\" ]; then
    echo \"  Location: $WHEELS_DIR\"
    echo \"  Contents:\"
    ls -lh \"$WHEELS_DIR\" | grep -E \"\\.(whl|txt)$\" || echo \"  No .whl files found\"
else
    echo \"  ERROR: Wheels directory not found at $WHEELS_DIR\"
fi
echo \"\"

echo \"4. SHA256 Hashes of Key Bundled Wheels:\"
if [ -d \"$WHEELS_DIR\" ]; then
    for wheel in \"$WHEELS_DIR\"/pip-*.whl \"$WHEELS_DIR\"/setuptools-*.whl; do
        if [ -f \"$wheel\" ]; then
            BASENAME=$(basename \"$wheel\")
            echo \"  File: $BASENAME\"
            ACTUAL_HASH=$(sha256sum \"$wheel\" | awk \"{print \\$1}\")
            echo \"    Actual SHA256: $ACTUAL_HASH\"
            echo \"\"
        fi
    done
fi

echo \"5. Virtualenv Cache Status:\"
CACHE_DIR=\"/root/.cache/virtualenv\"
if [ -d \"$CACHE_DIR\" ]; then
    echo \"  Cache location: $CACHE_DIR\"
    CACHE_SIZE=$(du -sh \"$CACHE_DIR\" 2>/dev/null | awk \"{print \\$1}\")
    echo \"  Cache size: $CACHE_SIZE\"
else
    echo \"  No cache found at $CACHE_DIR\"
fi
echo \"\"

echo \"========================================\"
echo \"  DIAGNOSTIC COMPLETE\"
echo \"========================================\"
'") do
      its(:exit_status) { is_expected.to eq 0 }
      its(:stdout) { is_expected.to match(/DIAGNOSTIC COMPLETE/) }
    end
  end
end