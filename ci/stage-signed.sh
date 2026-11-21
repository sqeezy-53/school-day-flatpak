#!/usr/bin/env bash
# Run on the maintainer's machine with an existing GPG signing key.
set -euo pipefail
if [[ $# != 6 ]]; then
  echo "Usage: bash ci/stage-signed.sh ARTIFACT_DIR REVIEWED_SOURCE STAGING HTTPS_REPO GNUPGHOME FINGERPRINT" >&2
  exit 2
fi
artifact=$(realpath "$1")
source_dir=$(realpath "$2")
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
(cd "$artifact" && sha256sum -c SHA256SUMS)
expected=$(git -C "$source_dir" rev-parse HEAD)
test -z "$(git -C "$source_dir" status --porcelain)"
helper="$source_dir/packaging/flatpak/prepare-repository.py"
test -f "$helper"
python3 - "$artifact" "$expected" "$scratch" <<'PY'
import json, sys, tarfile
from pathlib import Path
archive = Path(sys.argv[1])
provenance = json.loads((archive / "BUILD.json").read_text())
assert provenance["repository"] == "sqeezy-53/school-day"
assert provenance["sha"] == sys.argv[2], "Source commit mismatch"
assert provenance["ref"] == "v" + provenance["version"], "A tag build is required"
with tarfile.open(archive / "school-day-ostree.tar") as file:
    file.extractall(sys.argv[3], filter="data")
PY
ostree fsck --repo="$scratch/repo"
python3 "$helper" --source "$scratch/repo" --destination "$3" --url "$4" \
  --keyring "$5" --fingerprint "$6"
