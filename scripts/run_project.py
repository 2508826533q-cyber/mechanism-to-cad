"""Explicit, resumable stage orchestration. Failures never become completion records."""
import argparse,os,sys,traceback
from pathlib import Path
from core import *
def run(a):
    project=Path(a.project).resolve();os.environ['CADGEN_DAEMON']='0'
    stages=[x.strip() for x in a.stages.split(',')]
    for stage in stages:
        print('STAGE',stage,flush=True)
        try:
            if stage=='analyze':
                from analyze_mechanism import analyze
                analyze(project,a.parameters,a.reference,a.observations)
            elif stage=='solve':
                from solve_kinematics import solve
                solve(project)
            elif stage=='parts':
                from generate_parts import generate
                generate(project)
            elif stage=='assembly':
                from solidworks_backend import assembly
                assembly(project)
            elif stage=='animation':
                from generate_animation import render
                render(project,a.fps,a.width,a.height)
            elif stage=='validate':
                from validate_project import validate
                validate(project)
            else:raise ValueError('Unknown stage '+stage)
        except Exception as e:
            write(project/'reports'/('stage_'+stage+'.json'),{'stage':stage,'status':'failed','error':str(e)});raise
        write(project/'reports'/('stage_'+stage+'.json'),{'stage':stage,'status':'passed'})
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('project');p.add_argument('--parameters');p.add_argument('--reference');p.add_argument('--observations');p.add_argument('--stages',default='analyze,solve,parts,assembly,animation,validate');p.add_argument('--fps',type=int,default=30);p.add_argument('--width',type=int,default=1920);p.add_argument('--height',type=int,default=1080);run(p.parse_args())
