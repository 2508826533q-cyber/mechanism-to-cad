"""Route native parts to the exercised backend, then use existing cadgen for exchange/viewer artifacts."""
import argparse
from pathlib import Path
from core import *
from solidworks_backend import PARTS
def generate(project,backend='solidworks'):
    if backend!='solidworks':raise NotImplementedError('Only SolidWorks native feature backend is implemented; FreeCAD not silently substituted')
    from solidworks_backend import parts
    parts(project)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('project');p.add_argument('--backend',default='solidworks');a=p.parse_args();generate(a.project,a.backend)
