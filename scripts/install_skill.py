"""Install only this skill into the user's Agent Skills root. No dependency or config mutation."""
from pathlib import Path
import argparse,shutil,hashlib,json,sys
from core import write
def install(source=None):
    source=Path(source or Path(__file__).resolve().parents[1]).resolve()
    target=Path.home()/'.agents/skills/mechanism-to-cad'
    if target.exists():raise FileExistsError(f'{target} already exists; refusing to overwrite an installed skill')
    if not (source/'SKILL.md').is_file():raise FileNotFoundError('Source SKILL.md missing')
    target.parent.mkdir(parents=True,exist_ok=True)
    before={p.name:hashlib.sha256((p/'SKILL.md').read_bytes()).hexdigest() for p in target.parent.iterdir() if p.is_dir() and (p/'SKILL.md').is_file()}
    shutil.copytree(source,target,ignore=shutil.ignore_patterns('.git','.venv','venv','__pycache__','*.pyc','*.log','.pytest_cache','environment_detected.json','installation_report.json','discovery_report.json','projects','output'))
    files={str(p.relative_to(target)):hashlib.sha256(p.read_bytes()).hexdigest() for p in target.rglob('*') if p.is_file()}
    after={p.name:hashlib.sha256((p/'SKILL.md').read_bytes()).hexdigest() for p in target.parent.iterdir() if p.name!='mechanism-to-cad' and p.is_dir() and (p/'SKILL.md').is_file()}
    assert before==after,'An unrelated skill changed during installation; inspect concurrent writers'
    report={'installed':True,'path':str(target),'other_skill_manifests_unchanged':len(before),'files_sha256':files,'discovery':'requires separate Codex skills/list check; disk installation alone is not a discovery test'}
    write(source/'installation_report.json',report)
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source');a=p.parse_args();print(json.dumps(install(a.source),ensure_ascii=False,indent=2))
