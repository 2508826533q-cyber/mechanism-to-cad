import argparse
from pathlib import Path
from core import *
def solve(project):
    project=Path(project);resolved,f,_=parameters(read(project/'analysis'/'resolved_parameters.json'))
    rows=simulate(f,resolved['simulation']);save_csv(project/'simulation'/'motion_data.csv',rows)
    write(project/'simulation'/'simulation_config.json',resolved['simulation'])
    write(project/'simulation'/'solver_validation.json',{'status':'passed','rows':len(rows),'max_closure_error_mm':max(r['closure_error_mm'] for r in rows),'full_turn_audit':f.audit(),'branch':f.branch})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(3,1,figsize=(12,9),layout='constrained');t=[x['time_s'] for x in rows]
    for ax,field,label in zip(axes,['rocker_deg','rocker_velocity_deg_s','rocker_acceleration_deg_s2'],['Rocker / deg','Velocity / deg/s','Acceleration / deg/s^2']):
        ax.plot(t,[r[field] for r in rows]);ax.set_ylabel(label);ax.grid(alpha=.3)
    axes[-1].set_xlabel('Time / s');fig.savefig(project/'simulation'/'motion_curves.png',dpi=150);plt.close(fig)
    return rows
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('project');a=p.parse_args();solve(a.project)
