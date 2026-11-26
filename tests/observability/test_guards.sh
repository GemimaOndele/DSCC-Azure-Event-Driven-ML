#!/usr/bin/env bash
# All Azure/curl calls are replaced by test doubles. No external traffic.
set -euo pipefail
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
export DSCC_TEST_LOG="$tmp/calls"
export PATH="$tmp:$PATH"
cat > "$tmp/az" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$DSCC_TEST_LOG"
case "$*" in
  'account show '*) echo test-sub ;;
  'monitor log-analytics workspace show '*"workspaceCapping.dailyQuotaGb"*) echo 0.2 ;;
  'monitor log-analytics workspace show '*) echo /test/workspace ;;
  'monitor app-insights component show '*"workspaceResourceId"*) echo "${DSCC_TEST_WORKSPACE:-/test/workspace}" ;;
  'monitor app-insights component show '*) echo /test/insights ;;
  'containerapp show '*) echo dscc-api ;;
  'functionapp show '*) echo dscc-function ;;
  'monitor action-group create '*) ;;
  'monitor action-group show '*) echo /test/action-group ;;
  'monitor scheduled-query create '*) ;;
  *) echo "Unexpected command: $*" >&2; exit 99 ;;
esac
MOCK
cat > "$tmp/curl" <<'MOCK'
#!/usr/bin/env bash
printf 'curl %s\n' "$*" >> "$DSCC_TEST_LOG"
case "$*" in
  *'/health') exit 0 ;;
  *'{"rows": []}'*) printf '%s' "${DSCC_TEST_INVALID_STATUS:-422}" ;;
  *'/predict/batch') printf '200' ;;
  *) exit 99 ;;
esac
MOCK
chmod +x "$tmp/az" "$tmp/curl"
: > "$DSCC_TEST_LOG"
unset DSCC_ALERT_APPROVAL DSCC_ALERT_TEST_APPROVAL || true
if bash infra/observability.sh; then exit 1; fi
if bash infra/trigger-alert.sh; then exit 1; fi
test ! -s "$DSCC_TEST_LOG"
export DSCC_ALERT_APPROVAL=APPROVED-DSCC-ALERT
export DSCC_SUBSCRIPTION=test-sub DSCC_RG=test-rg DSCC_FUNCTION=dscc-function ALERT_EMAIL=test@example.invalid
export DSCC_TEST_WORKSPACE=/wrong/workspace
if bash infra/observability.sh; then exit 1; fi
if grep -q 'action-group create\|scheduled-query create' "$DSCC_TEST_LOG"; then echo "Unexpected mutating operation" >&2; exit 1; fi
unset DSCC_TEST_WORKSPACE
: > "$DSCC_TEST_LOG"
bash infra/observability.sh
grep -q 'scheduled-query create' "$DSCC_TEST_LOG"
if grep -q 'workspace create\|component create\|containerapp update\|functionapp config appsettings set' "$DSCC_TEST_LOG"; then echo "Unexpected mutating operation" >&2; exit 1; fi
export DSCC_ALERT_TEST_APPROVAL=APPROVED-DSCC-SYNTHETIC-ALERT-TEST API_URL=https://test.azurecontainerapps.io
export DSCC_TEST_INVALID_STATUS=500
: > "$DSCC_TEST_LOG"
if bash infra/trigger-alert.sh; then exit 1; fi
test "$(grep -c 'curl ' "$DSCC_TEST_LOG")" = 2
unset DSCC_TEST_INVALID_STATUS
: > "$DSCC_TEST_LOG"
bash infra/trigger-alert.sh
test "$(grep -c 'curl ' "$DSCC_TEST_LOG")" = 36
echo 'Observability guard and status checks passed (mocked commands only).'
