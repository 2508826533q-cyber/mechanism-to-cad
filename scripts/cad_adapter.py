"""Adapter to the installed text-to-CAD cadgen package: no replacement CAD engine."""
from pathlib import Path
import json,csv,math,sys,subprocess,os
from core import *
from solidworks_backend import PARTS
def assembly_shape(project):
    from cadgen import read_step,build123d as bd,srgb
    project=Path(project).resolve();config,f,_=parameters(read(project/'analysis/resolved_parameters.json'))
    dims=config['defaults_used'];z=[0,12,12+dims['thickness_mm']+4,12+2*dims['thickness_mm']+8]
    # Matches native frame8 + gap4; native report is authoritative when available.
    native=project/'reports/native_validation.json'
    if native.exists():z=read(native)['layer_z_mm']
    shapes=[]
    for id,color in zip(PARTS,['#647586','#DD7636','#2B8DB0','#65A76B']):
        shape=read_step(project/'export/STEP'/(id+'.step'));shape.label=id;shape.color=srgb(color);shapes.append(shape)
    q=config['simulation']['initial_deg'];rest=f.pose(q)
    placements=[(rest['A'],0),(rest['A'],q),(rest['B'],rest['rod_deg']),(rest['D'],rest['rocker_deg'])]
    placed=[shape.moved(bd.Location((*xy,zz),(0,0,angle))) for shape,(xy,angle),zz in zip(shapes,placements,z)]
    return bd.Compound(children=placed,label='Mechanism_Assembly')

def build_exchange(project,fps=30):
    project=Path(project).resolve();config,f,_=parameters(read(project/'analysis/resolved_parameters.json'))
    q=config['simulation']['initial_deg'];rest=f.pose(q)
    rows=simulate(f,{**config['simulation'],'dt_s':1/fps})
    save_csv(project/'animation'/'motion_frames.csv',rows)
    table=[[r[k] for k in ['crank_deg','coupler_deg','rocker_deg','B_x_mm','B_y_mm']] for r in rows]
    js='''const poses=$TABLE;
export const clips={motion:{label:"Solved four-bar motion",duration:$DURATION,loop:false,update(t,m){
 const s=poses[Math.min(poses.length-1,Math.max(0,Math.floor(t*$FPS+1e-7)))];
 m.get("Part_02_Crank").rotate([0,0,1],s[0]-$Q,[0,0,0]);
 m.get("Part_03_ConnectingRod").rotate([0,0,1],s[1]-$BETA,[$BX,$BY,0]).translate([s[3]-$BX,s[4]-$BY,0]);
 m.get("Part_04_Rocker").rotate([0,0,1],s[2]-$PHI,[$GROUND,0,0]);
}}};'''
    for key,val in {'TABLE':table,'DURATION':config['simulation']['duration_s'],'FPS':fps,'Q':q,'BETA':rest['rod_deg'],
                    'PHI':rest['rocker_deg'],'BX':rest['B'][0],'BY':rest['B'][1],'GROUND':f.ground}.items():js=js.replace('$'+key,'('+json.dumps(val,separators=(',',':'))+')')
    # cadgen owns saving animation sidecars and model metadata. Native STEP input is a distinct file.
    output=project/'assembly'/'Viewer_Assembly.step'
    (project/'animation/motion.js').write_text(js,encoding='utf-8')
    # A module-level decorated entrypoint preserves cadgen's model/source contract.
    source='''from pathlib import Path
import sys
sys.path.insert(0, SCRIPTS)
from cadgen import step
from cad_adapter import assembly_shape
PROJECT=Path(__file__).resolve().parent.parent
@step(out="Viewer_Assembly.step", animation=(PROJECT/"animation/motion.js").read_text(encoding="utf-8"))
def Viewer_Assembly():
    return assembly_shape(PROJECT)
if __name__=="__main__":Viewer_Assembly()
'''.replace('SCRIPTS',repr(str(Path(__file__).resolve().parent)))
    script=project/'assembly/Viewer_Assembly.py';script.write_text(source,encoding='utf-8')
    subprocess.run([sys.executable,str(script)],check=True,env={**os.environ,'CADGEN_DAEMON':'0','PYTHONUTF8':'1'})
    return output
