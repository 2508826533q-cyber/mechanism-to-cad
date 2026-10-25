import argparse
from solidworks_backend import assembly
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('project');a=p.parse_args();assembly(a.project)
