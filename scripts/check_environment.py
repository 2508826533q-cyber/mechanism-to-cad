"""Read-only capability detection. Never installs software or starts CAD by default."""
import argparse,importlib.metadata as meta,json,os,shutil,sys,subprocess
from pathlib import Path
from core import write
def check():
    roots=[Path(os.environ.get(k,'')) for k in ('ProgramFiles','ProgramFiles(x86)','LOCALAPPDATA') if os.environ.get(k)]
    roots+=[Path('D:/Program Files'),Path('D:/Program Files (x86)'),Path('D:/SW2025')]
    packages={}
    for name in ('cadgen','build123d','numpy','scipy','Pillow','matplotlib','pywin32','PyYAML'):
        try:packages[name]=meta.version(name)
        except meta.PackageNotFoundError:packages[name]=None
    def find(program,patterns):
        found=set()
        if shutil.which(program):found.add(shutil.which(program))
        for root in roots:
            if root.exists():
                for pattern in patterns:
                    for path in root.glob(pattern):
                        if path.is_file():found.add(str(path))
        return sorted(found)
    cad_skill=[]
    for root in [Path.home()/'.agents/skills',Path.home()/'.codex/skills',Path.home()/'.codex/plugins/cache/openai-curated-remote/text-to-cad']:
        if root.exists():cad_skill.extend(str(p) for p in root.glob('**/cad/SKILL.md'))
    sw=[]
    if os.name=='nt':
        import winreg
        for cls in ('SldWorks.Application','SldWorks.Application.33'):
            try:
                with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT,cls+'\\CLSID') as key:sw.append({'progid':cls,'clsid':winreg.QueryValue(key,None)})
            except OSError:pass
    programs={'codex':find('codex.exe',['OpenAI/Codex/bin/*/codex.exe']),
              'freecad':find('FreeCADCmd.exe',['FreeCAD*/bin/FreeCADCmd.exe','Programs/FreeCAD*/bin/FreeCADCmd.exe']),
              'blender':find('blender.exe',['Blender Foundation/Blender*/blender.exe','Programs/Blender*/blender.exe']),
              'solidworks':find('SLDWORKS.exe',['SOLIDWORKS/SLDWORKS.exe','SOLIDWORKS Corp/SOLIDWORKS/SLDWORKS.exe']),
              'ffmpeg':find('ffmpeg.exe',['Microsoft/WinGet/Links/ffmpeg.exe']),
              'ffprobe':find('ffprobe.exe',['Microsoft/WinGet/Links/ffprobe.exe'])}
    versions={}
    for key,args in [('codex',['--version']),('ffmpeg',['-version']),('ffprobe',['-version']),('blender',['--version']),('freecad',['--version'])]:
        if programs[key]:
            try:versions[key]=subprocess.run([programs[key][0],*args],capture_output=True,text=True,timeout=20).stdout.splitlines()[:2]
            except Exception as e:versions[key]={'error':str(e)}
    return {'python':{'executable':sys.executable,'version':sys.version},'packages':packages,'programs':programs,'versions':versions,
            'solidworks_registered':sw,'text_to_cad_skill_candidates':cad_skill,'codex_user_skill_dir':str(Path.home()/'.agents/skills'),
            'preferred_implemented_backend':'solidworks' if sw else 'cadgen_geometry_only',
            'not_implemented':['FreeCAD native joints adapter','Blender renderer','gears','cams','slider_crank','robot_arm'],
            'cadgen_geometry_is_not_native_assembly':True}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();report=check();write(a.out,report);print(json.dumps(report,ensure_ascii=False,indent=2))
