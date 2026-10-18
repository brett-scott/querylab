"""Grade every challenge from the actual downloadable archive using real MySQL.

Run inside the configured backend/helper container with this repository mounted.
The bundle supplies runtime code; the container supplies Python dependencies.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import sys

with TemporaryDirectory(prefix='querylab-package-') as temporary:
    root = Path(__file__).resolve().parents[1]
    with ZipFile(root / 'frontend/public/downloads/querylab-helper-windows.zip') as archive:
        archive.extractall(temporary)
    packaged_backend = Path(temporary) / 'QueryLab-Helper' / 'backend'
    sys.path.insert(0, str(packaged_backend))
    import app
    assert Path(app.__file__).resolve().is_relative_to(packaged_backend.resolve())
    from app.content.challenges import CHALLENGES
    from app.engine import Job, grade
    from app.sql import validate_script
    assert len(CHALLENGES) == 12 and all(c['ready'] for c in CHALLENGES)
    for challenge in CHALLENGES:
        result = grade(challenge, validate_script(challenge['solution'], grading_type=challenge['type']),
                       Job('archive-smoke', 'owner', challenge['id'], 'submit'))
        assert result['passed'], (challenge['id'], result)
        print(f"PASS packaged {challenge['id']}: {len(result['checks'])} grading checks", flush=True)
    print('PASS: all twelve challenges grade from the extracted Windows download.', flush=True)
