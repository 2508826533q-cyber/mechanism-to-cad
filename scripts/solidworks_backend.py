"""Native feature tree and seven real mates, plus saved and replay-verified Motion Analysis."""
import math,time,hashlib,os
from pathlib import Path
from types import SimpleNamespace
from core import *
PARTS=['Part_01_Frame','Part_02_Crank','Part_03_ConnectingRod','Part_04_Rocker']
def connect(project):
    import _native_helpers as n
    local=Path(__file__).resolve().parents[1]/'local_environment.json'
    env=read(local) if local.exists() else {}
    install=os.environ.get('MECHANISM_SW_INSTALL',env.get('solidworks_install',''))
    if not install or not (Path(install)/'sldworks.tlb').exists():raise RuntimeError('Set MECHANISM_SW_INSTALL to the installed SOLIDWORKS folder; run environment detection first')
    n.connect(install)
    config,f,_=parameters(read(Path(project)/'analysis/resolved_parameters.json'))
    dims=config['defaults_used']
    p=SimpleNamespace(AD=f.ground,AB=f.crank,BC=f.coupler,CD=f.rocker,HOLE_D=dims['hole_mm'],LINK_W=dims['width_mm'],
       FRAME_W=30.,FRAME_T=8.,CRANK_T=dims['thickness_mm'],ROD_T=dims['thickness_mm'],ROCKER_W=dims['rocker_width_mm'],
       ROCKER_T=dims['rocker_thickness_mm'],RPM=config['simulation']['rpm'],DURATION=config['simulation']['duration_s'],DIRECTION=config['simulation']['direction'])
    for name in ('FRAME_W','FRAME_T','LINK_W','CRANK_T','ROD_T','ROCKER_W','ROCKER_T','HOLE_D'):positive(getattr(p,name),name)
    if p.HOLE_D>=min(p.FRAME_W,p.LINK_W,p.ROCKER_W):raise ValueError('Hole must be smaller than link width')
    p.CRANK_Z=p.FRAME_T+4;p.ROD_Z=p.CRANK_Z+p.CRANK_T+4;p.ROCKER_Z=p.ROD_Z+p.ROD_T+4
    n.p=p;n.OUT=Path(project).resolve()/'parts'
    return n,config,f
def native_names(project):
    # Separate filename prefixes allow different projects to coexist in the same SW process.
    token=hashlib.sha256(str(Path(project).resolve()).encode()).hexdigest()[:8]
    return {name:'M'+token+'_'+name for name in PARTS}

def parts(project):
    project=Path(project).resolve();n,c,f=connect(project);names=native_names(project)
    original=n.app.GetUserPreferenceToggle(10);n.app.SetUserPreferenceToggle(10,False)
    try:
        for id,L,W,T in [(PARTS[0],f.ground,n.p.FRAME_W,n.p.FRAME_T),(PARTS[1],f.crank,n.p.LINK_W,n.p.CRANK_T),
                         (PARTS[2],f.coupler,n.p.LINK_W,n.p.ROD_T),(PARTS[3],f.rocker,n.p.ROCKER_W,n.p.ROCKER_T)]:
            doc=n.makepart(names[id],L,W,T)
            doc.ClearSelection2(True)
            n.save(doc,project/'export/STEP'/(id+'.step'));n.save(doc,project/'export/STL'/(id+'.stl'))
        write(project/'analysis/native_parts.json',{'backend':'solidworks','native_names':names,'parts':n.REPORT['parts'],'solidworks_revision':n.app.RevisionNumber()})
    finally:n.app.SetUserPreferenceToggle(10,original)

def assembly(project):
    project=Path(project).resolve();n,c,f=connect(project);names=native_names(project)
    for name in names.values():
        opened=n.app.OpenDoc6(str(project/'parts'/(name+'.SLDPRT')),1,1,'',0,0)
        if opened[0] is None:raise RuntimeError(f'Could not resolve {name}: {opened[1:]}')
    doc=n.cast(n.app.NewAssembly(),n.SW.IModelDoc2);assy=n.cast(doc,n.SW.IAssemblyDoc)
    q=c['simulation']['initial_deg'];s=f.pose(q);p=n.p
    frame=n.insert(doc,assy,names[PARTS[0]],s['A'],0,0,True)
    crank=n.insert(doc,assy,names[PARTS[1]],s['A'],p.CRANK_Z,q)
    rod=n.insert(doc,assy,names[PARTS[2]],s['B'],p.ROD_Z,s['rod_deg'])
    rocker=n.insert(doc,assy,names[PARTS[3]],s['D'],p.ROCKER_Z,s['rocker_deg'])
    for a,xa,b,xb,label in [(frame,0,crank,0,'A'),(frame,p.AD,rocker,0,'D'),(crank,p.AB,rod,0,'B'),(rod,p.BC,rocker,p.CD,'C')]:
        n.mate(doc,assy,n.face(a,xa),n.face(b,xb),1,label='Revolute_'+label)
    for comp,z,label in [(crank,p.CRANK_Z,'Crank'),(rod,p.ROD_Z,'Rod'),(rocker,p.ROCKER_Z,'Rocker')]:
        n.mate(doc,assy,n.face(frame,bottom=True),n.face(comp,bottom=True),5,z,'Layer_'+label)
    assert doc.ForceRebuild3(False)
    path=project/'assembly'/(names[PARTS[0]].split('_Part_')[0]+'_Assembly.SLDASM')
    if path.exists():raise FileExistsError(path)
    doc.ShowNamedView2('',7);doc.ViewZoomtofit2();n.save(doc,path)
    n.setup_study(doc,frame,crank,path)
    mgr=n.cast(n.cast(doc.Extension,n.SW.IModelDocExtension).GetMotionStudyManager(),n.MOTION.IMotionStudyManager)
    study=n.cast(mgr.GetMotionStudy('Mechanism_Motion'),n.MOTION.IMotionStudy)
    # Names describe arbitrary motion settings in the project report; rename native features too.
    study.Name='Mechanism_Motion';study.SetTime(0)
    doc.ClearSelection2(True);n.save(doc,path);n.save(doc,project/'export/STEP'/'Assembly.step')
    mateinfo=[];obj=doc.FirstFeature()
    while obj:
        feat=n.cast(obj,n.SW.IFeature)
        if feat.GetTypeName2()=='MateGroup':
            sub=feat.GetFirstSubFeature()
            while sub:
                sub=n.cast(sub,n.SW.IFeature);mateinfo.append({'name':sub.Name,'type':sub.GetTypeName2(),'error':sub.GetErrorCode()});sub=sub.GetNextSubFeature()
        obj=feat.GetNextFeature()
    assert len(mateinfo)==7 and all(x['error']==0 for x in mateinfo)
    def sample(doc,study,t):
        study.SetTime(t);doc.GraphicsRedraw2();n.pythoncom.PumpWaitingMessages();time.sleep(.08)
        comps={n.cast(x,n.SW.IComponent2).Name2.rsplit('-',1)[0]:n.cast(x,n.SW.IComponent2) for x in n.cast(doc,n.SW.IAssemblyDoc).GetComponents(False)}
        def pt(key,x):
            T=n.cast(comps[names[key]].Transform2,n.SW.IMathTransform).ArrayData
            return (1000*T[9]+x*T[0],1000*T[10]+x*T[1],1000*T[11]+x*T[2])
        A=pt(PARTS[1],0);B=pt(PARTS[1],p.AB);B2=pt(PARTS[2],0);C=pt(PARTS[2],p.BC);C2=pt(PARTS[3],p.CD);D=pt(PARTS[3],0)
        expected=f.pose(q+c['simulation']['direction']*t*p.RPM*6)
        error=max(math.dist(A[:2],expected['A']),math.dist(D[:2],expected['D']),math.dist(B[:2],expected['B']),math.dist(C2[:2],expected['C']))
        close=max(math.dist(B[:2],B2[:2]),math.dist(C[:2],C2[:2]))
        assert error<.01 and close<.01,(t,error,close)
        return {'time_s':t,'crank_angle_deg':math.degrees(math.atan2(B[1]-A[1],B[0]-A[0])),
                'rocker_angle_deg':math.degrees(math.atan2(C2[1]-D[1],C2[0]-D[0])),
                'closure_error_mm':close,'analytic_error_mm':error}
    # Native cached grid defaults to 25 FPS. Sample first cycle at actual output times.
    times=sorted(set([round(i*.04,8) for i in range(min(31,int(p.DURATION/.04)+1))]+[p.DURATION]))
    results=[sample(doc,study,t) for t in times]
    measured=sum(delta(y['crank_angle_deg'],x['crank_angle_deg']) for x,y in zip(results[:30],results[1:31]))/(min(1.2,times[-1])*6)
    if len(times)>=31:assert abs(measured-c['simulation']['direction']*p.RPM)<1e-5
    study.SetTime(0);n.save(doc,path)
    n.app.CloseDoc(doc.GetTitle());opened=n.app.OpenDoc6(str(path),2,1,'',0,0)
    assert opened[0] and opened[1]==0,opened[1:]
    doc=n.cast(opened[0],n.SW.IModelDoc2)
    mgr=n.cast(n.cast(doc.Extension,n.SW.IModelDocExtension).GetMotionStudyManager(),n.MOTION.IMotionStudyManager)
    study=n.cast(mgr.GetMotionStudy('Mechanism_Motion'),n.MOTION.IMotionStudy);study.Activate()
    assert study.StudyType==4 and abs(study.GetDuration()-p.DURATION)<1e-6,'Motion Analysis unavailable or duration not saved'
    study.SetTime(.04);study.SetTime(0)
    last=max(0,(math.ceil(p.DURATION*25)-1)/25)
    replay=[sample(doc,study,t) for t in sorted(set([0.,min(.4,last),last]))]
    study.SetTime(0);doc.GraphicsRedraw2();n.save(doc,path)
    report={'status':'passed','backend':'solidworks','native_assembly':str(path),'fixed_component':names[PARTS[0]],'mates':mateinfo,
            'motion':n.REPORT['motion'],'sampled_native_results':results,'measured_rpm':measured,'reopened_cached_samples':replay,
            'reopen_errors':opened[1],'reopen_warnings':opened[2],'native_cache_fps':25,
            'study_name':'Mechanism_Motion','study_type':study.StudyType,'layer_z_mm':[0,p.CRANK_Z,p.ROD_Z,p.ROCKER_Z]}
    write(project/'reports'/'native_validation.json',report)
    (project/'reports'/'assembly_report.md').write_text('# Native assembly\n\nFour fixed-length links; four concentric + three axial-distance mates. Frame fixed.\n\n'+json.dumps(report,indent=2),encoding='utf-8')
    return report
