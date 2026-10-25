"""Deterministic planar four-bar synthesis and circle-intersection kinematics (mm/rad/s)."""
import csv,json,math
from pathlib import Path
from dataclasses import dataclass

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def delta(a,b):return (a-b+180)%360-180
def positive(value,label):
    if not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:raise ValueError(f'{label} must be finite and positive')
    return float(value)

@dataclass(frozen=True)
class FourBar:
    ground:float
    crank:float
    coupler:float
    rocker:float
    branch:int=1
    def __post_init__(self):
        for k in ('ground','crank','coupler','rocker'):positive(getattr(self,k),k)
        if self.branch not in (-1,1):raise ValueError('branch must be +1 or -1')
    def pose(self,q):
        q=math.radians(q);a,b,c,d=self.crank,self.coupler,self.rocker,self.ground
        A=(0.,0.);D=(d,0.);B=(a*math.cos(q),a*math.sin(q))
        dx,dy=B[0]-d,B[1];r=math.hypot(dx,dy)
        if r<1e-10:raise ValueError('Coincident circle centers: indeterminate configuration')
        u=(c*c-b*b+r*r)/(2*r);h2=c*c-u*u
        if h2 < -1e-7:raise ValueError(f'Cannot close at crank {math.degrees(q):.6f} deg')
        h=math.sqrt(max(0.,h2));s=self.branch
        C=(d+u*dx/r+s*h*dy/r,u*dy/r-s*h*dx/r)
        beta=math.atan2(C[1]-B[1],C[0]-B[0]);phi=math.atan2(C[1],C[0]-d)
        cosine=(b*b+c*c-r*r)/(2*b*c)
        mu=math.degrees(math.acos(max(-1,min(1,cosine))))
        return {'A':A,'B':B,'C':C,'D':D,'crank_deg':math.degrees(q),'rod_deg':math.degrees(beta),
                'rocker_deg':math.degrees(phi),'transmission_angle_deg':min(mu,180-mu),
                'closure_error_mm':max(abs(math.dist(A,B)-a),abs(math.dist(B,C)-b),abs(math.dist(C,D)-c)),
                'toggle':h<1e-6}
    def full_turn_margin(self):
        # B-D distance over a full turn is [|d-a|, d+a]. Compare circle-intersection limits.
        return min(abs(self.ground-self.crank)-abs(self.coupler-self.rocker),self.coupler+self.rocker-self.ground-self.crank)
    def audit(self,step=.25):
        positive(step,'step');count=max(4,math.ceil(360/step));poses=[]
        failed=[]
        for i in range(count+1):
            try:poses.append(self.pose(i*360/count))
            except ValueError:failed.append(i*360/count)
        if not poses:raise ValueError('No sampled input angle can close')
        jump=max(abs(delta(b['rocker_deg'],a['rocker_deg'])) for a,b in zip(poses,poses[1:]))
        return {'samples':len(poses),'full_turn_margin_mm':self.full_turn_margin(),
                'full_turn_possible':self.full_turn_margin()>=-1e-7 and not failed,'unreachable_input_angles_deg':failed,'toggle_count':sum(p['toggle'] for p in poses),
                'max_closure_error_mm':max(p['closure_error_mm'] for p in poses),
                'max_step_rocker_deg':jump,'min_transmission_angle_deg':min(p['transmission_angle_deg'] for p in poses),
                'planar_mobility':3*(4-1)-2*4,'revolute_joint_count':4,'independent_drives':1}
    def extrema(self):
        # Finite rocker extrema occur when input and coupler are collinear.
        out=[]
        for r in (self.coupler-self.crank,self.coupler+self.crank):
            if r<=0:raise ValueError('This extreme formula requires coupler > crank; use sampled ranges for other inversions')
            v=(self.ground**2+self.rocker**2-r*r)/(2*self.ground*self.rocker)
            if abs(v)>1+1e-10:raise ValueError('No two rocker extrema: different four-bar inversion')
            phi=180-math.degrees(math.acos(max(-1,min(1,v))))
            C=(self.ground+self.rocker*math.cos(math.radians(phi)),self.rocker*math.sin(math.radians(phi)))
            q=math.degrees(math.atan2(C[1],C[0]))+(180 if r==self.coupler-self.crank else 0)
            out.append((phi,q%360))
        angles=sorted(x[0] for x in out);minor=abs(delta(out[1][1],out[0][1]))
        if minor<1e-10:raise ValueError('Degenerate quick-return timing')
        return {'swing_deg':angles[1]-angles[0],'K':(360-minor)/minor,'theta_deg':180-minor,
                'rocker_upper_extremes_deg':angles,'extreme_crank_deg':[x[1] for x in out],
                'mirror_equivalent':True,'timing_definition':'K=longer/shorter crank-time interval at constant speed'}

def synthesize(ground,rocker,swing,K):
    d=positive(ground,'ground');c=positive(rocker,'rocker');positive(swing,'swing');positive(K,'K')
    if not 0<swing<180 or K<=1:raise ValueError('Current crank-rocker synthesis requires 0<swing<180 and K>1; K=1 needs separate symmetry analysis')
    theta=180*(K-1)/(K+1);t=math.tan(math.radians(theta));h=math.radians(swing/2)
    candidates=[]
    for sign in (-1,1):
        den=2*d*c*(t*math.cos(h)-sign*math.sin(h))
        if abs(den)<1e-12:continue
        v=(sign*2*c*c*math.sin(h)*math.cos(h)-t*(d*d+c*c*math.cos(2*h)))/den
        if abs(v)>1+1e-10:continue
        m=math.acos(max(-1,min(1,v)))
        radii=[math.sqrt(d*d+c*c+2*d*c*math.cos(m+s*h)) for s in (-1,1)]
        a=(max(radii)-min(radii))/2;b=sum(radii)/2
        if a<=0:continue
        f=FourBar(d,a,b,c)
        try:ext=f.extrema();audit=f.audit()
        except ValueError:continue
        if abs(ext['swing_deg']-swing)>1e-6 or abs(ext['K']-K)>1e-6 or audit['full_turn_margin_mm']<=1e-7:continue
        if any(abs(a-x['crank'])<1e-7 and abs(b-x['coupler'])<1e-7 for x in candidates):continue
        candidates.append({'ground':d,'crank':a,'coupler':b,'rocker':c,'branch':1,'mid_rocker_deg':math.degrees(m),
                           'verification':ext,'full_turn_margin_mm':audit['full_turn_margin_mm']})
    if not candidates:raise ValueError('No nondegenerate crank-rocker satisfies the requested dimensions, swing and K')
    return {'theta_deg':theta,'candidates':candidates,'unique_lengths_within_examined_crank_rocker_family':len(candidates)==1,
            'other_assemblies':'Each candidate has upper/lower mirror branches; K alone does not say which stroke is faster. Ground orientation and mounting are not fixed.'}

def parameters(data):
    if data.get('mechanism_type','four_bar')!='four_bar':raise NotImplementedError('Only planar four-bar is implemented in v1; do not substitute it for another mechanism')
    lengths=data.get('lengths',{})
    missing=[k for k in ('ground','crank','coupler','rocker') if k not in lengths]
    if missing:
        design=data.get('design',{})
        if all(k in lengths for k in ('ground','rocker')) and all(k in design for k in ('swing_deg','K')):
            synthesis=synthesize(lengths['ground'],lengths['rocker'],design['swing_deg'],design['K'])
            choice=design.get('candidate_index')
            if choice is None and len(synthesis['candidates'])!=1:raise ValueError('Multiple length solutions: ask the user to select a design candidate')
            if choice is None:choice=0
            if type(choice) is not int or not 0<=choice<len(synthesis['candidates']):raise ValueError('Invalid candidate_index')
            lengths={k:synthesis['candidates'][choice][k] for k in ('ground','crank','coupler','rocker')}
        else:raise ValueError(f'Missing dimensions {missing}; request dimensions/constraints; never measure scale from a photo')
    else:synthesis=None
    f=FourBar(**lengths,branch=data.get('branch',1))
    sim={'rpm':50.,'duration_s':30.,'dt_s':1/30,'initial_deg':45.,'direction':1,**data.get('simulation',{})}
    for k in ('rpm','duration_s','dt_s'):positive(sim[k],k)
    if not math.isfinite(sim['initial_deg']) or sim['direction'] not in (-1,1):raise ValueError('Invalid initial angle or direction')
    if sim['dt_s']*sim['rpm']*6>=90:raise ValueError('Time step too coarse: use <90 degrees per sample')
    resolved={**data,'mechanism_type':'four_bar','units':'mm','lengths':lengths,'branch':f.branch,'simulation':sim}
    resolved['defaults_used']={'width_mm':20.,'thickness_mm':8.,'rocker_width_mm':30.,'rocker_thickness_mm':10.,'hole_mm':10.,**data.get('part_defaults',{})}
    if data.get('units','mm')!='mm':raise ValueError('Convert input lengths to mm explicitly')
    audit=f.audit()
    if data.get('require_full_turn',True) and (not audit['full_turn_possible'] or f.full_turn_margin()<=1e-7):
        raise ValueError('Input link cannot complete a nonsingular 360-degree turn; revise dimensions or explicitly request restricted motion')
    if 'design' in data:
        ext=f.extrema()
        for key,actual in [('swing_deg',ext['swing_deg']),('K',ext['K'])]:
            if key in data['design'] and abs(actual-data['design'][key])>data.get('design_tolerance',1e-6):
                raise ValueError(f'Conflicting {key}: supplied lengths give {actual}, requested {data["design"][key]}')
    return resolved,f,synthesis

def simulate(f,sim):
    n=math.ceil(sim['duration_s']/sim['dt_s'])
    if n>1000000:raise ValueError('More than one million samples; choose a coarser dt')
    rows=[];prev=None;phi_unwrapped=0.;beta_unwrapped=0.
    for i in range(n+1):
        t=min(i*sim['dt_s'],sim['duration_s']);q=sim['initial_deg']+sim['direction']*t*sim['rpm']*6;s=f.pose(q)
        if s['toggle']:raise ValueError(f'Toggle singularity at {t}s; cannot guarantee branch continuation')
        if prev is None:phi_unwrapped=s['rocker_deg'];beta_unwrapped=s['rod_deg']
        else:
            dp=delta(s['rocker_deg'],prev['rocker_deg']);db=delta(s['rod_deg'],prev['rod_deg'])
            if max(abs(dp),abs(db))>90:raise ValueError('Ambiguous branch/large angular jump; refine dt or inspect singularity')
            phi_unwrapped+=dp;beta_unwrapped+=db
        rows.append({'time_s':t,'crank_deg':q,'coupler_deg':beta_unwrapped,'rocker_deg':phi_unwrapped,
                     'B_x_mm':s['B'][0],'B_y_mm':s['B'][1],'C_x_mm':s['C'][0],'C_y_mm':s['C'][1],
                     'closure_error_mm':s['closure_error_mm'],'transmission_angle_deg':s['transmission_angle_deg']})
        prev=s
    import numpy as np
    times=[r['time_s'] for r in rows]
    if len(rows)<3:raise ValueError('At least three simulation samples are required')
    for key in ('crank','coupler','rocker'):
        vel=np.gradient([r[key+'_deg'] for r in rows],times,edge_order=2);acc=np.gradient(vel,times,edge_order=2)
        for row,v,a in zip(rows,vel,acc):row[key+'_velocity_deg_s']=float(v);row[key+'_acceleration_deg_s2']=float(a)
    return rows

def save_csv(path,rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
