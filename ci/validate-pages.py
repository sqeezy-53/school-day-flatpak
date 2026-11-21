"""Validate a signed, cumulative OSTree release archive before hosting it."""
import configparser
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import tarfile

def require(value, message):
    if not value:
        raise SystemExit(message)

tag, expected, expected_url = sys.argv[1:]
archive = Path("incoming/school-day-ostree-signed.tar.gz")
metadata = json.loads(Path("incoming/BUILD.json").read_text())
require(metadata.get("sha") == expected and metadata.get("ref") == tag, "Source SHA or tag mismatch")
require(metadata.get("version") == tag[1:], "Version mismatch")
checksum_file = Path("incoming/SHA256SUMS").read_text()
hashes = re.findall(r"(?m)^([a-f0-9]{64}) [ *]school-day-ostree-signed\.tar\.gz$", checksum_file)
with archive.open("rb") as handle:
    require(len(hashes) == 1 and hashlib.file_digest(handle, "sha256").hexdigest() == hashes[0], "Archive digest mismatch")

with tarfile.open(archive, "r:gz") as file:
    files = file.getmembers()
    require(sum(m.size for m in files) <= 900_000_000, "Repository exceeds the Pages size budget")
    for member in files:
        path = PurePosixPath(member.name)
        require(not path.is_absolute() and ".." not in path.parts and path.parts[0] in
                {"repo", "school-day.flatpakref", "school-day.flatpakrepo"}, "Unexpected archive path")
        require(member.isfile() or member.isdir(), "Archive must contain files and directories only")
    file.extractall("site", members=files, filter="data")

repo = configparser.ConfigParser()
app = configparser.ConfigParser()
repo.read("site/school-day.flatpakrepo")
app.read("site/school-day.flatpakref")
require(repo["Flatpak Repo"]["Url"] == app["Flatpak Ref"]["Url"] == expected_url, "Flatpak URL mismatch")
require(repo["Flatpak Repo"]["GPGKey"] == app["Flatpak Ref"]["GPGKey"], "Flatpak key mismatch")
require(app["Flatpak Ref"]["Name"] == "io.github.sqeezy_53.school-day" and
        app["Flatpak Ref"]["Branch"] == "master", "Flatpak application ID or branch mismatch")
