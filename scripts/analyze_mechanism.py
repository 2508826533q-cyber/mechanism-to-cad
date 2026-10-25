"""Ingest explicit mechanical observations; vision stays with Codex, never guessed by Python."""
import argparse
from pathlib import Path
from core import *
def analyze(project,inputs,reference=None,observations=None):
    project=Path(project)
    if (project/'input'/'parameters.json').exists():raise FileExistsError('Existing project: choose a new folder instead of overwriting work')
    if reference:
        from PIL import Image
        import shutil
        reference=Path(reference)
        if reference.suffix.lower() not in ('.png','.jpg','.jpeg','.webp'):raise ValueError('Unsupported reference image')
        with Image.open(reference) as im:im.verify()
        target=project/'input'/('reference'+reference.suffix.lower());target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(reference,target)
    supplied=read(inputs);resolved,f,synthesis=parameters(supplied)
    if synthesis:write(project/'analysis'/'design_candidates.json',synthesis)
    for folder in ['input','analysis','parts','assembly','simulation','animation','export/STEP','export/STL','reports']:(project/folder).mkdir(parents=True,exist_ok=True)
    write(project/'input'/'parameters.json',supplied);write(project/'analysis'/'resolved_parameters.json',resolved)
    specs=[('Part_01_Frame','Fixed ground','ground'),('Part_02_Crank','Input crank','crank'),('Part_03_ConnectingRod','Coupler','coupler'),('Part_04_Rocker','Output rocker','rocker')]
    parts=[{'id':id,'name':name,'geometry':{'type':'two-pivot solid link','hole_center_distance_mm':resolved['lengths'][key]},'fixed':key=='ground'} for id,name,key in specs]
    joints=[{'id':key,'type':'revolute','parts':list(pair),'axis':[0,0,1]} for key,pair in [('A',('Part_01_Frame','Part_02_Crank')),('B',('Part_02_Crank','Part_03_ConnectingRod')),('C',('Part_03_ConnectingRod','Part_04_Rocker')),('D',('Part_01_Frame','Part_04_Rocker'))]]
    observation=read(observations) if observations else None
    analysis={'mechanism_type':'four_bar','parts':parts,'joints':joints,'fixed_parts':['Part_01_Frame'],'driver':'Part_02_Crank',
              'evidence':'explicit dimensions and topology supplied by user; image observations separate','vision_observations':observation,
              'image_analysis_performed':observation is not None,'confidence':{'topology':'user-supplied','image':None if observation is None else observation.get('confidence')},
              'uncertainties':['Hidden bearings, pins, clearances, loads and materials require separate information'],
              'assumptions':supplied.get('assumptions',[]),'status':'resolved'}
    write(project/'analysis'/'mechanism_analysis.json',analysis)
    audit=f.audit();ext=None
    try:ext=f.extrema()
    except ValueError:pass
    write(project/'analysis'/'kinematics_analysis.json',{'audit':audit,'extrema':ext})
    (project/'analysis'/'kinematics_report.md').write_text('# Kinematics\n\n'+json.dumps({'audit':audit,'extrema':ext,'synthesis':synthesis},ensure_ascii=False,indent=2),encoding='utf-8')
    return analysis
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('project');p.add_argument('--parameters',required=True);p.add_argument('--reference');p.add_argument('--observations');a=p.parse_args();analyze(a.project,a.parameters,a.reference,a.observations)
