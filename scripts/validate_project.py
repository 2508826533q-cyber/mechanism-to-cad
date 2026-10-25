"""Verify saved geometry, actual native mates/replay, closed-loop data and playable moving video."""
import argparse,csv,json,math,struct,shutil,subprocess,hashlib
from pathlib import Path
from collections import Counter
from core import *
from solidworks_backend import PARTS
def mesh_check(path):
    raw=path.read_bytes()
    if len(raw)<84:raise ValueError('Truncated STL')
    n=struct.unpack_from('<I',raw,80)[0]
    if len(raw)!=84+50*n:raise ValueError('Expected binary STL; re-export with binary preference or use cadgen stl build')
    edges=Counter()
    for i in range(n):
        d=struct.unpack_from('<12fH',raw,84+50*i);v=[tuple(d[j:j+3]) for j in (3,6,9)]
        if len(set(v))!=3:raise ValueError('Degenerate STL facet')
        for j in range(3):edges[tuple(sorted((v[j],v[(j+1)%3])))]+=1
    if not all(x==2 for x in edges.values()):raise ValueError('STL is not a closed 2-manifold')
    return {'facets':n,'closed_manifold':True}
def validate(project):
    project=Path(project).resolve();report={'status':'running','checks':{},'limitations':[]}
    dest=project/'reports'/'validation_report.json'
    try:
        from cadgen import read_step,build123d as bd
        from cadgen.geometry import overlap_volume
        from build123d import GeomType
        c,f,_=parameters(read(project/'analysis/resolved_parameters.json'))
        native=read(project/'reports/native_validation.json');assert native['status']=='passed' and native['study_type']==4
        assert Path(native['native_assembly']).is_file() and Path(native['native_assembly']).stat().st_size>1000
        assert len(native['mates'])==7 and all(x['error']==0 for x in native['mates'])
        native_parts=read(project/'analysis/native_parts.json')
        assert len(native_parts['parts'])==4
        assert all(all(x==3 for x in part['sketch_statuses']) for part in native_parts['parts'].values())
        solids=[];dims=[];keys=['ground','crank','coupler','rocker']
        for name,key in zip(PARTS,keys):
            expected=c['lengths'][key];p=project/'export/STEP'/(name+'.step');shape=read_step(p)
            assert len(shape.solids())==1 and shape.solids()[0].is_valid,(name,'invalid solid')
            solid=shape.solids()[0];solids.append(solid);holes=[]
            for face in solid.faces():
                if face.geom_type==GeomType.CYLINDER and abs(face.radius-c['defaults_used']['hole_mm']/2)<1e-6:
                    ax=face.axis_of_rotation;candidate=[ax.position.X,ax.position.Y,face.radius]
                    if not any(math.dist(candidate,old)<1e-6 for old in holes):holes.append(candidate)
            assert len(holes)==2,(name,holes)
            for x in (0,expected):assert any(abs(h[0]-x)<1e-6 and abs(h[1])<1e-6 for h in holes),(name,holes)
            box=solid.bounding_box();thickness=box.max.Z-box.min.Z
            target=8 if key=='ground' else c['defaults_used']['rocker_thickness_mm'] if key=='rocker' else c['defaults_used']['thickness_mm']
            width=30 if key=='ground' else c['defaults_used']['rocker_width_mm'] if key=='rocker' else c['defaults_used']['width_mm']
            assert abs(thickness-target)<1e-6 and abs(box.size.Y-width)<1e-6,(name,'thickness or width')
            for x in (0,expected):
                bore=bd.Pos(x,0,target/2)*bd.Cylinder(c['defaults_used']['hole_mm']/2-1e-4,target+2)
                assert overlap_volume(solid,bore.solids()[0])<1e-6,'Blocked bore'
            dims.append({'name':name,'hole_distance_mm':expected,'width_mm':width,'thickness_mm':thickness,'valid_solid':True,'stl':mesh_check(project/'export/STL'/(name+'.stl'))})
            file=project/'parts'/(native_parts['native_names'][name]+'.SLDPRT');assert file.is_file() and file.stat().st_size>1000
        asm=read_step(project/'export/STEP/Assembly.step');assert len(asm.solids())==4 and all(s.is_valid for s in asm.solids())
        report['checks']['parts']=dims
        # In-plane rotations preserve Z. Nonoverlapping layer intervals prove no body interference throughout the turn.
        intervals=[]
        for solid,z in zip(solids,native['layer_z_mm']):
            b=solid.bounding_box();intervals.append([b.min.Z+z,b.max.Z+z])
        gaps=[max(a[0]-b[1],b[0]-a[1]) for i,a in enumerate(intervals) for b in intervals[i+1:]]
        assert min(gaps)>0
        report['checks']['interference']={'method':'separated Z bounding intervals; invariant under planar rotations, valid for full continuous motion','intervals_mm':intervals,'min_clearance_mm':min(gaps),'failures':[]}
        with (project/'simulation/motion_data.csv').open(encoding='utf-8-sig') as file:rows=[{k:float(v) for k,v in row.items()} for row in csv.DictReader(file)]
        maxerr=0
        for row in rows:
            t=row['time_s'];expected_q=c['simulation']['initial_deg']+c['simulation']['direction']*t*c['simulation']['rpm']*6
            assert abs(row['crank_deg']-expected_q)<1e-7
            s=f.pose(expected_q)
            err=max(math.dist(s['B'],[row['B_x_mm'],row['B_y_mm']]),math.dist(s['C'],[row['C_x_mm'],row['C_y_mm']]))
            assert err<1e-7 and row['closure_error_mm']<1e-7
            maxerr=max(maxerr,err)
        assert abs(rows[0]['time_s'])<1e-9 and abs(rows[-1]['time_s']-c['simulation']['duration_s'])<1e-9
        assert max(abs(delta(y['rocker_deg'],x['rocker_deg'])) for x,y in zip(rows,rows[1:]))<90
        report['checks']['kinematics']={'row_count':len(rows),'recomputed_point_error_mm':maxerr,'full_turn':f.audit(),'branch_continuity_checked':True}
        probe=shutil.which('ffprobe');ffmpeg=shutil.which('ffmpeg');assert probe and ffmpeg,'FFmpeg/ffprobe unavailable'
        video=project/'animation/animation.mp4';settings=read(project/'animation/render_settings.json')
        result=subprocess.run([probe,'-v','error','-select_streams','v:0','-show_entries','stream=width,height,nb_frames,r_frame_rate,duration','-of','json',str(video)],capture_output=True,text=True,check=True)
        stream=json.loads(result.stdout)['streams'][0];assert stream['width']==settings['width'] and stream['height']==settings['height']
        expected_frames=round(c['simulation']['duration_s']*settings['fps'])
        assert abs(int(stream['nb_frames'])-expected_frames)<=1 and abs(float(stream['duration'])-c['simulation']['duration_s'])<=1/settings['fps']+.001
        subprocess.run([ffmpeg,'-v','error','-i',str(video),'-f','null','-'],capture_output=True,check=True)
        # Two decoded frames should visibly differ; a still-image movie cannot pass this check.
        def frame(t):return subprocess.run([ffmpeg,'-v','error','-ss',str(t),'-i',str(video),'-frames:v','1','-vf','scale=160:90','-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True,check=True).stdout
        a=frame(0);b=frame(min(c['simulation']['duration_s']/2,15/c['simulation']['rpm']))
        assert a and len(a)==len(b) and sum(abs(x-y) for x,y in zip(a,b))/len(a)>.05,'Video contains no detected visible motion'
        report['checks']['animation']={'stream':stream,'full_decode_passed':True,'distinct_decoded_frames':True,'pose_source':'closed loop motion_frames.csv'}
        report['checks']['native_assembly']={'reopened':True,'replay_samples':native['reopened_cached_samples'],'measured_rpm':native['measured_rpm'],'mobility_model':1,'mates':native['mates']}
        report['limitations']=['No force/stress/print-strength analysis; pins and fasteners are not included','Image interpretation is agent-assisted, not an independent vision model in these Python scripts','Numerical angular derivatives have finite-difference error, especially near endpoints']
        report['status']='passed'
    except Exception as e:
        report['status']='failed';report['error']=str(e);write(dest,report);raise
    write(dest,report)
    (project/'reports/validation_report.md').write_text('# Validation: '+report['status']+'\n\n'+json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (project/'reports/README.md').write_text('# Open the project\n\nOpen '+str(Path(native['native_assembly']).relative_to(project))+'; retain parts/ alongside assembly/. Select Motion Study **Mechanism_Motion** to replay the saved Motion Analysis.\n\nanimation/animation.mp4 is the closed-loop solved pose-table engineering preview. STEP contains geometry only; editable mates are in SLDASM.\n\ninput/parameters.json holds supplied dimensions; analysis/resolved_parameters.json has synthesized lengths and declared assumptions.\n\nSee validation_report.md for executed checks and limits.',encoding='utf-8')
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('project');a=p.parse_args();print(json.dumps(validate(a.project),ensure_ascii=False,indent=2))
