"""SOLIDWORKS native sketch/feature/mate helpers, exercised with 2025 SP5.
COM initialization is explicit. Importing this module does not launch or change CAD.
"""
from pathlib import Path
import math,json,time
import pythoncom
import win32com.client as wc
from win32com.client import gencache
SW=CONST=MOTION=app=p=OUT=INSTALL=None
NONE=None
REPORT={"parts":{},"mates":[],"motion":{}}
def cast(obj,interface):
    if obj is None:raise RuntimeError('Missing '+interface.__name__)
    return interface(obj._oleobj_.QueryInterface(interface.CLSID,pythoncom.IID_IDispatch))
def connect(install):
    global SW,CONST,MOTION,app,INSTALL
    INSTALL=Path(install)
    def library(name):
        attrs=pythoncom.LoadTypeLib(str(INSTALL/name)).GetLibAttr()
        return gencache.EnsureModule(attrs[0],attrs[1],attrs[3],attrs[4])
    SW=library('sldworks.tlb');CONST=library('swconst.tlb');MOTION=library('swmotionstudy.tlb')
    app=cast(wc.Dispatch('SldWorks.Application'),SW.ISldWorks);app.Visible=True
    REPORT['version']=app.RevisionNumber()

def value(n): return format(float(n),'.16g')
def selection(doc,*objects,mark=0):
    doc.ClearSelection2(True)
    mgr=cast(doc.SelectionManager,SW.ISelectionMgr)
    data=cast(mgr.CreateSelectData(),SW.ISelectData)
    data.Mark=mark
    for i,obj in enumerate(objects):
        assert obj.Select4(bool(i),data),'Selection failed'

def equation(doc,name,rhs):
    mgr=cast(doc.GetEquationMgr(),SW.IEquationMgr)
    idx=mgr.Add2(-1,f'"{name}" = {rhs}',True)
    assert idx>=0,f'Equation rejected: {name} = {rhs}'

def global_param(doc,name,n): equation(doc,name,f'{value(n)}mm')

def relation(doc,kind,*entities):
    sk=cast(doc.GetActiveSketch2(),SW.ISketch)
    mgr=cast(sk.RelationManager,SW.ISketchRelationManager)
    array=wc.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,[obj for obj in entities])
    result=mgr.AddRelation(array,kind)
    assert result is not None,('Relation rejected',kind)

def drive(doc,display,expression):
    dd=cast(display,SW.IDisplayDimension)
    dim=cast(dd.GetDimension2(0),SW.IDimension)
    name='@'.join(dim.FullName.split('@')[:2])
    equation(doc,name,expression)

def begin(doc,name):
    doc.ClearSelection2(True)
    f=cast(doc.FirstFeature(),SW.IFeature)
    while f.GetTypeName2()!='RefPlane': f=cast(f.GetNextFeature(),SW.IFeature)
    assert f.Select2(False,0)
    sm=cast(doc.SketchManager,SW.ISketchManager)
    sm.InsertSketch(True)
    sk=cast(doc.GetActiveSketch2(),SW.ISketch)
    cast(doc.FeatureByPositionReverse(0),SW.IFeature).Name=name
    sm.AddToDB=True
    anchor=cast(sm.CreatePoint(0.,0.,0.),SW.ISketchPoint)
    selection(doc,anchor)
    relation(doc,17,anchor)
    return sm,anchor

def coordinate(doc,pt,anchor,x,y,xexpr,yexpr):
    selection(doc,pt,anchor)
    if abs(x)<1e-8 and abs(y)<1e-8:
        if pt._oleobj_!=anchor._oleobj_:relation(doc,9,pt,anchor)
        return
    if abs(x)<1e-8: relation(doc,26,pt,anchor)
    else: drive(doc,doc.AddHorizontalDimension2(x/2000,y/1000+.008,0),xexpr)
    selection(doc,pt,anchor)
    if abs(y)<1e-8: relation(doc,25,pt,anchor)
    else: drive(doc,doc.AddVerticalDimension2(x/1000+.008,y/2000,0),yexpr)

def polygon(doc,sm,anchor,vertices,exprs):
    lines=[]
    for i,xy in enumerate(vertices):
        nx,ny=vertices[(i+1)%len(vertices)]
        line=cast(sm.CreateLine(xy[0]/1000,xy[1]/1000,0,nx/1000,ny/1000,0),SW.ISketchLine)
        lines.append(line)
    for i,line in enumerate(lines):
        finish=cast(line.GetEndPoint2(),SW.ISketchPoint)
        start=cast(lines[(i+1)%len(lines)].GetStartPoint2(),SW.ISketchPoint)
        if finish._oleobj_!=start._oleobj_:
            relation(doc,9,finish,start)
    for line,(x,y),(xe,ye) in zip(lines,vertices,exprs):
        coordinate(doc,cast(line.GetStartPoint2(),SW.ISketchPoint),anchor,x,y,xe,ye)

def circle(doc,sm,anchor,x,d,expr):
    seg=sm.CreateCircleByRadius(x/1000,0,0,d/2000)
    arc=cast(seg,SW.ISketchArc)
    centre=cast(arc.GetCenterPoint2(),SW.ISketchPoint)
    coordinate(doc,centre,anchor,x,0,'"L"','0mm')
    selection(doc,cast(seg,SW.ISketchSegment))
    drive(doc,doc.AddDiameterDimension2(x/1000+d/1000,d/1000,0),expr)

def finish(doc,depth,name,depth_expr,cut=False):
    sm=cast(doc.SketchManager,SW.ISketchManager)
    sk=cast(doc.GetActiveSketch2(),SW.ISketch)
    skfeature=cast(doc.FeatureByPositionReverse(0),SW.IFeature)
    sm.AddToDB=False
    # Record native sketch solver status before closing.
    status=sk.GetConstrainedStatus()
    assert status==3,('Sketch is not fully defined',skfeature.Name,status)
    sm.InsertSketch(True)
    doc.ClearSelection2(True);assert skfeature.Select2(False,0)
    fm=cast(doc.FeatureManager,SW.IFeatureManager)
    if cut:
        f=fm.FeatureCut3(True,False,True,1,0,depth/1000,0,False,False,False,False,0,0,
                        False,False,False,False,False,True,True,False,False,False,0,0,False)
    else:
        f=fm.FeatureExtrusion3(True,False,False,0,0,depth/1000,0,False,False,False,False,0,0,
                              False,False,False,False,True,True,True,0,0,False)
    f=cast(f,SW.IFeature);f.Name=name
    if not cut: equation(doc,f'D1@{name}',depth_expr)
    print(' feature',name,'sketch status',status,flush=True)
    return f,status

def save(doc,path):
    ext=cast(doc.Extension,SW.IModelDocExtension)
    result=ext.SaveAs(str(path),0,1,NONE,0,0)
    # Generated COM signature returns (success, errors, warnings).
    print(' saved',path.name,result,flush=True)
    if isinstance(result,tuple): assert result[0] and result[1]==0,result
    else: assert result
    assert path.exists(),path

def makepart(name,L,W,T,pedal=False):
    path=OUT/(name+'.SLDPRT')
    if path.exists():
        raise FileExistsError(f'Refusing to overwrite native part {path}; choose another output folder')
    print('BUILD',name,flush=True)
    doc=cast(app.NewPart(),SW.IModelDoc2)
    for key,n in [('L',L),('W',W),('T',T),('Hole',p.HOLE_D)]: global_param(doc,key,n)
    sm,anchor=begin(doc,'Web_Profile')
    polygon(doc,sm,anchor,[(0,-W/2),(L,-W/2),(L,W/2),(0,W/2)],
            [('0mm','"W"/2'),('"L"','"W"/2'),('"L"','"W"/2'),('0mm','"W"/2')])
    statuses=[finish(doc,T,'Web_Extrude','"T"')[1]]
    for x,label in [(0,'End_A'),(L,'End_B')]:
        sm,anchor=begin(doc,label+'_Profile');circle(doc,sm,anchor,x,W,'"W"')
        statuses.append(finish(doc,T,label+'_Boss','"T"')[1])
    sm,anchor=begin(doc,'Pivot_Bores')
    circle(doc,sm,anchor,0,p.HOLE_D,'"Hole"');circle(doc,sm,anchor,L,p.HOLE_D,'"Hole"')
    statuses.append(finish(doc,T,'Hole_10_Through','"T"',True)[1])
    cast(doc.GetEquationMgr(),SW.IEquationMgr).EvaluateAll()
    assert doc.ForceRebuild3(False),'Rebuild failed'
    bodies=cast(doc,SW.IPartDoc).GetBodies2(0,True)
    assert len(bodies)==1,('Body count',len(bodies))
    mass=cast(bodies[0],SW.IBody2).GetMassProperties(1)
    REPORT['parts'][name]={'sketch_statuses':statuses,'body_count':len(bodies),'mass_properties':mass,
                         'equation_count':cast(doc.GetEquationMgr(),SW.IEquationMgr).GetCount()}
    doc.ShowNamedView2('',7);doc.ViewZoomtofit2()
    save(doc,path)
    # Independent neutral export for comparison with the text-to-CAD STEP.
    save(doc,OUT/(name+'.step'))
    return doc

def insert(doc,assy,name,xy,z,angle,fixed=False):
    comp=cast(assy.AddComponent5(str(OUT/(name+'.SLDPRT')),0,'',False,'',0,0,0),SW.IComponent2)
    doc.ClearSelection2(True);comp.Select4(False,NONE,False);assy.UnfixComponent()
    c=math.cos(math.radians(angle));s=math.sin(math.radians(angle))
    mu=cast(app.GetMathUtility(),SW.IMathUtility)
    arr=wc.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_R8,[c,s,0,-s,c,0,0,0,1,xy[0]/1000,xy[1]/1000,z/1000,1,0,0,0])
    comp.Transform2=mu.CreateTransform(arr)
    if fixed:
        doc.ClearSelection2(True);comp.Select4(False,NONE,False);assy.FixComponent()
    doc.ClearSelection2(True)
    return comp

def face(comp,x=None,bottom=False):
    part=cast(comp.GetModelDoc2(),SW.IPartDoc)
    bodies=part.GetBodies2(0,True)
    for obj in cast(bodies[0],SW.IBody2).GetFaces():
        f=cast(obj,SW.IFace2);surface=cast(f.GetSurface(),SW.ISurface)
        match=False
        if bottom and surface.IsPlane():
            box=f.GetBox();match=abs(box[2])<1e-7 and abs(box[5])<1e-7
        elif not bottom and surface.IsCylinder():
            v=surface.CylinderParams;match=abs(v[0]-x/1000)<1e-7 and abs(v[1])<1e-7 and abs(v[6]-p.HOLE_D/2000)<1e-7
        if match:return cast(comp.GetCorrespondingEntity(f),SW.IEntity)
    raise RuntimeError(f'No mate face: {comp.Name2} {x} {bottom}')

def mate(doc,assy,first,second,kind,distance=0,label=''):
    selection(doc,first,second,mark=1)
    d=abs(distance)/1000
    result=assy.AddMate5(kind,0,(kind==5 and distance>0),d,d,d,1,1,0,0,0,False,False,0,0)
    print(' mate',label,result,flush=True)
    if isinstance(result,tuple):m,status=result;assert m and status==CONST.constants.swAddMateError_NoError,(label,status)
    else:m=result;assert m
    REPORT['mates'].append({'name':label,'kind':kind,'distance_mm':distance,'created':True})
    doc.ClearSelection2(True)

def setup_study(doc,frame,crank,path=None):
    path=path or OUT/'Treadle_Assembly.SLDASM'
    ext=cast(doc.Extension,SW.IModelDocExtension)
    app.LoadAddIn(str(INSTALL/'cmotionsw.dll'))
    mgr=cast(ext.GetMotionStudyManager(),MOTION.IMotionStudyManager)
    existing=mgr.GetMotionStudy('Mechanism_Motion')
    study=cast(existing if existing is not None else mgr.CreateMotionStudy(),MOTION.IMotionStudy)
    study.Name='Mechanism_Motion';study.Activate();assert study.SetDuration(p.DURATION)
    supported_result=study.GetSupportedStudyTypes()
    supported=supported_result[1] if isinstance(supported_result,tuple) else supported_result
    REPORT['motion']['supported_types']=supported
    # Prefer Motion Analysis when installed; default Animation still solves driven mates.
    study.StudyType=1
    study.Activate()
    motor=cast(study.CreateDefinition(78),SW.ISimulationMotorFeatureData)
    ref=face(crank,0)
    motor.DirectionReference=ref;motor.Location=ref;motor.RelativeComponent=frame
    motor.LoadReferences=wc.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,[ref])
    # This installed API stores motor angular velocity in SI rad/s. Native pose
    # verification, rather than the help page's RPM label, is authoritative.
    motor.ConstantSpeedMotor(p.RPM*2*math.pi/60)
    motor.ReverseDirection=(p.DIRECTION>0)
    feature=cast(study.CreateFeature(motor),SW.IFeature);feature.Name=f'Input_{p.RPM:g}RPM'
    if supported & 4:
        study.StudyType=4
        study.Activate()
    REPORT['motion'].update(name=study.Name,rpm=p.RPM,duration_s=study.GetDuration(),study_type=study.StudyType,
                           motor_name=feature.Name)
    save(doc,path)
    print('CALCULATE',flush=True)
    calculated=study.Calculate()
    assert calculated,'Motion Analysis calculation failed'
    REPORT['motion']['calculate_return']=calculated
    save(doc,path)
