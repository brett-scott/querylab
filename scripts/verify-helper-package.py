"""Independent standard-library verification for the public helper ZIP."""
import hashlib
import io
import json
import pathlib
import re
import zipfile


root = pathlib.Path(__file__).resolve().parents[1]
downloads = root / "frontend" / "public" / "downloads"
manifest = json.loads((downloads / "querylab-helper-windows.json").read_text())
assert manifest["filename"] == "querylab-helper-windows.zip"
payload = (downloads / manifest["filename"]).read_bytes()
assert len(payload) == manifest["bytes"]
assert hashlib.sha256(payload).hexdigest() == manifest["sha256"]
with zipfile.ZipFile(io.BytesIO(payload)) as package:
    assert package.testzip() is None
    names = package.namelist()
    assert sorted(names) == sorted(manifest["files"])
    assert len(set(names)) == len(names)
    expected = {
        "Start-QueryLab-Helper.cmd", "scripts/launch-helper.ps1",
        "scripts/setup-helper.ps1", "scripts/start-helper.ps1",
        "scripts/show-helper-code.ps1", "backend/Dockerfile",
        "backend/requirements.txt", "backend/app/main.py", "helper.env.example",
        "compose.helper.yaml", "README.txt", "VERSION.txt",
        "backend/app/content/online_expansion.py",
        "backend/app/content/online_expansion_fixtures.py",
        "backend/app/content/inventory_expansion.py",
        "backend/app/content/inventory_expansion_fixtures.py",
        "backend/app/content/inventory_procedures.py",
        "backend/app/content/inventory_procedure_fixtures.py",
    }
    assert expected <= {name.removeprefix("QueryLab-Helper/") for name in names}
    for name in names:
        path = pathlib.PurePosixPath(name)
        assert path.parts[0] == "QueryLab-Helper"
        assert not path.is_absolute() and ".." not in path.parts and "\\" not in name
        assert not any(part in {".git", ".codex", "node_modules", "__pycache__", ".env.helper", "qa"} for part in path.parts)
        assert path.suffix.lower() in {".py", ".ps1", ".cmd", ".txt", ".yaml", ".example"} or path.name in {"Dockerfile", ".dockerignore"}
    contents = b"\n".join(package.read(name) for name in names)
    for env_name in (".env", ".env.helper"):
        private_path = root / env_name
        if private_path.exists():
            for line in private_path.read_text().splitlines():
                match = re.match(r"(?:QUERYLAB_PAIRING_TOKEN|MYSQL_ROOT_PASSWORD)=(.+)", line)
                if match:
                    assert match[1].encode() not in contents, "Local credential entered the public archive"
    compose = package.read("QueryLab-Helper/compose.helper.yaml").decode()
    assert "  website:" not in compose and "./frontend" not in compose
    assert '127.0.0.1:${QUERYLAB_HELPER_PORT' in compose
    assert package.read("QueryLab-Helper/VERSION.txt").decode().strip() == manifest["version"]
print(f"PASS: ZIP integrity, {len(names)} allowlisted files, manifest checksum, standalone Compose and credential exclusion.")
