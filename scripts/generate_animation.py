import argparse,json,subprocess,sys,shutil,os
from pathlib import Path
from core import *
def render(project,fps=30,width=1920,height=1080,mode='engineering',camera=None):
    project=Path(project).resolve()
    if mode!='engineering':raise NotImplementedError('Product/Blender mode not implemented; select engineering rather than falsely claiming product rendering')
    if type(fps) is not int or not 1<=fps<=120:raise ValueError('FPS must be integer 1..120')
    if not (1<=width<=8192 and 1<=height<=8192):raise ValueError('Invalid output resolution')
    from cad_adapter import build_exchange
    step=build_exchange(project,fps);config=read(project/'analysis/resolved_parameters.json')
    cam=camera or {'direction':[-1,-1,2],'up':[0,1,0]}
    job={'input':str(step),'animation':{'clip':'motion'},'video':{'fps':fps,'seconds':config['simulation']['duration_s'],'quality':'review'},
         'outputs':[{'path':str(project/'animation/animation.mp4'),'camera':cam,'width':width,'height':height}]}
    write(project/'animation/render_job.json',job)
    env={**os.environ,'CADGEN_DAEMON':'0','PYTHONUTF8':'1'}
    subprocess.run([sys.executable,'-m','cadgen.cli','step','snapshot','--job',str(project/'animation/render_job.json')],check=True,env=env)
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg:raise RuntimeError('FFmpeg is required for MP4 extraction; see environment report')
    subprocess.run([ffmpeg,'-y','-v','error','-i',str(project/'animation/animation.mp4'),'-frames:v','1',str(project/'animation/preview.png')],check=True)
    write(project/'animation/render_settings.json',{'fps':fps,'width':width,'height':height,'mode':mode,'camera':cam,'pose_source':'motion_frames.csv; independently closed at each time sample'})
    jobs=[]
    from solidworks_backend import PARTS
    for id in PARTS:
        jobs.append({'input':str(project/'export/STEP'/(id+'.step')),'outputs':[{'path':str(project/'reports'/(id+'_review.png')),'camera':'iso'}],'output':{'sizeProfile':'simple'}})
    write(project/'reports'/'snapshot_jobs.json',jobs)
    subprocess.run([sys.executable,'-m','cadgen.cli','step','snapshot','--job',str(project/'reports/snapshot_jobs.json')],check=True,env=env)
    return project/'animation/animation.mp4'
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('project');p.add_argument('--fps',type=int,default=30);p.add_argument('--width',type=int,default=1920);p.add_argument('--height',type=int,default=1080);p.add_argument('--mode',default='engineering');p.add_argument('--camera-json');a=p.parse_args()
    render(a.project,a.fps,a.width,a.height,a.mode,json.loads(a.camera_json) if a.camera_json else None)
