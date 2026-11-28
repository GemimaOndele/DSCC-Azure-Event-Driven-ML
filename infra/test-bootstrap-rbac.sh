#!/usr/bin/env bash
# Tests hors ligne : aucune connexion Azure, aucune opération réelle.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export DSCC_SUBSCRIPTION=00000000-0000-0000-0000-000000000001
export DSCC_RG=rg-test DSCC_REGION=francecentral DSCC_STORAGE=dsccmock DSCC_COSMOS=dscc-mock DSCC_BACKEND=cosmosFreeTier
export MOCK_SCOPE="/subscriptions/$DSCC_SUBSCRIPTION/resourceGroups/$DSCC_RG"
export MOCK_OUT="$TMP/arguments"
cat > "$TMP/az" <<'PY'
#!/usr/bin/env python3
import json, os, sys
args=sys.argv[1:]
mode=os.environ["MOCK_MODE"]
scope=os.environ["MOCK_SCOPE"]
principal="00000000-0000-0000-0000-000000000002"
name="00000000-0000-0000-0000-000000000003"
role="/providers/Microsoft.Authorization/roleDefinitions/b24988ac-6180-42a0-ab88-20f7382dd24c"
if args[:2]==["account","show"]: print(os.environ["DSCC_SUBSCRIPTION"])
elif args[:2]==["group","exists"]: print("true")
elif args[:2]==["group","show"]: print(scope)
elif args[:2]==["identity","list"]: print(json.dumps([] if mode=="fresh" else [{"name":"dscc-github-mi","principalId":principal}]))
elif args[:3]==["role","assignment","list"]:
    if mode=="error": sys.exit(1)
    row={"name":name,"principalId":principal,"scope":scope.upper(),"roleDefinitionId":role}
    rows=[dict(row,scope=scope+"/providers/fake"),dict(row,principalId="other"),dict(row,roleDefinitionId="/reader")]
    if mode in ("existing","ambiguous"): rows.append(row)
    if mode=="ambiguous": rows.append(dict(row,name="00000000-0000-0000-0000-000000000004"))
    print(json.dumps(rows))
elif args[:3]==["deployment","group","what-if"]:
    with open(os.environ["MOCK_OUT"],"w") as f: f.write("\n".join(args))
else: sys.exit("Unexpected command: "+repr(args))
PY
chmod +x "$TMP/az"
export PATH="$TMP:$PATH"
for MOCK_MODE in fresh existing none; do
  export MOCK_MODE
  rm -f "$MOCK_OUT"
  bash "$ROOT/bootstrap.sh" plan-base
  if [[ "$MOCK_MODE" == existing ]]; then
    grep -Fx 'githubRoleAssignmentName=00000000-0000-0000-0000-000000000003' "$MOCK_OUT"
  else
    grep -Fx 'githubRoleAssignmentName=' "$MOCK_OUT"
  fi
done
for MOCK_MODE in ambiguous error; do
  export MOCK_MODE
  rm -f "$MOCK_OUT"
  if bash "$ROOT/bootstrap.sh" plan-base; then
    echo "Expected lookup failure" >&2
    exit 1
  fi
  test ! -e "$MOCK_OUT"
done
echo "5 scénarios RBAC simulés réussis."
