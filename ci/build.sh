#!/usr/bin/env bash
set -euo pipefail

: "${SOURCE_SHA:?}" "${SOURCE_VERSION:?}" "${SOURCE_REF:?}"
app='io.github.sqeezy_53.school-day'
root=$(realpath source)
output=$(realpath -m dist)
work="$RUNNER_TEMP/flatpak-work"
mkdir -p "$output"
python3 - "$root/packaging/flatpak/$app.json" "$app" <<'PY'
import json, sys
from pathlib import Path
manifest = json.loads(Path(sys.argv[1]).read_text())
assert manifest["app-id"] == sys.argv[2], "Unexpected Flatpak ID"
assert manifest["runtime-version"] == "51" and manifest["command"] == "school-day"
assert not any(arg.startswith("--filesystem=") for arg in manifest["finish-args"])
PY
appstreamcli validate --no-net "$root/packaging/$app.metainfo.xml"
if [[ -f "$root/packaging/flatpak/test-repository.sh" ]]; then
  bash "$root/packaging/flatpak/test-repository.sh"
else
  echo "The selected source predates the upstream signed migration test."
fi
python3 "$root/packaging/build-flatpak.py" --work-dir "$work" --output-dir "$output"
bundle="school-day-$SOURCE_VERSION-x86_64.flatpak"
stage=$(<"$work/latest-build.txt")
ref="app/$app/x86_64/master"
ostree fsck --repo="$stage/repo"
test -s "$output/$bundle"
ostree init --repo="$work/reimport" --mode=archive-z2
flatpak build-import-bundle "$work/reimport" "$output/$bundle"
commit=$(ostree rev-parse --repo="$stage/repo" "$ref")
test "$(ostree rev-parse --repo="$work/reimport" "$ref")" = "$commit"
ostree fsck --repo="$work/reimport"
(
  cd "$output"
  sha256sum -c SHA256SUMS
)
python3 - "$output/SOURCE.json" "$SOURCE_SHA" "$SOURCE_VERSION" "$app" <<'PY'
import json, sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text())
assert (data["base_commit"], data["version"], data["app_id"]) == tuple(sys.argv[2:])
assert data["working_tree_dirty"] is False
PY
tar -C "$stage" -cf "$output/school-day-ostree.tar" repo
printf '{"repository":"sqeezy-53/school-day","ref":"%s","sha":"%s","version":"%s","ostree_commit":"%s"}\n' \
  "$SOURCE_REF" "$SOURCE_SHA" "$SOURCE_VERSION" "$commit" >"$output/BUILD.json"
(
  cd "$output"
  sha256sum BUILD.json school-day-ostree.tar >> SHA256SUMS
  sha256sum -c SHA256SUMS
)
