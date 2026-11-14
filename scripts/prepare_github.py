"""Create a source-only GitHub upload archive without local account data or secrets."""
from pathlib import Path
import fnmatch
import json
import zipfile
import os

ROOT=Path(__file__).resolve().parents[1]
SKIP_DIRS={'.git','.tools','node_modules','.next','.venv','__pycache__','.pytest_cache','coverage','output','tmp','.gradle','build','.agents','.codex','.aws'}
LOCAL_HELPERS={'build_project_report.py','expand_project_report.py','add_report_screenshots.py','add_screenshots_to_uploaded_pdf.py','align_report_cover.py'}
PATTERNS=['*.db','*.db-wal','*.db-shm','*.sqlite','*.sqlite3','*.pyc','*.tsbuildinfo','*.jks','*.keystore','*.pem','*.p12','*.log']

def eligible(path):
    rel=path.relative_to(ROOT)
    if any(part in SKIP_DIRS for part in rel.parts):return False
    if rel.parts[0]=='scripts' and path.name in LOCAL_HELPERS:return False
    if path.name=='.env' or (path.name.startswith('.env.') and path.name!='.env.example'):return False
    if rel.as_posix()=='android/local.properties':return False
    return not any(fnmatch.fnmatch(path.name,pattern) for pattern in PATTERNS)

def prepare():
    selected=[]
    for directory,dirs,files in os.walk(ROOT):
        dirs[:]=[name for name in dirs if name not in SKIP_DIRS]
        for name in files:
            path=Path(directory)/name
            if eligible(path):
                if path.stat().st_size>10_000_000:raise ValueError(f'Unexpected large source file: {path.relative_to(ROOT)}')
                selected.append(path)
    selected.sort()
    destination=ROOT/'.tools/SpendWise_GitHub_Ready.zip'
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in selected:archive.write(path,path.relative_to(ROOT).as_posix())
    manifest=[p.relative_to(ROOT).as_posix() for p in selected]
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist())==len(manifest)
        assert all(eligible(ROOT/name) for name in archive.namelist())
    required={'README.md','compose.yaml','backend/.env.example','frontend/.env.example','.env.example','frontend/package-lock.json','.github/workflows/checks.yml'}
    assert required.issubset(set(manifest))
    (ROOT/'.tools/github-upload-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(f'Prepared {len(manifest)} source/configuration files; archive integrity passed.')
    print(destination)
    print('Excluded local databases, sessions, environment secrets, report outputs, account screenshots and installed dependencies.')

if __name__=='__main__':prepare()
