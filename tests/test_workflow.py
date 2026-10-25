import unittest,tempfile,sys,json,csv
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from core import *
from analyze_mechanism import analyze
from solve_kinematics import solve
class WorkflowTests(unittest.TestCase):
    def fixture(self,root):
        cfg=read(Path(__file__).resolve().parents[1]/'assets/templates/acceptance_short.json')
        cfg['simulation']['duration_s']=1.2
        file=root/'params.json';write(file,cfg);return file
    def test_text_only_analysis_is_not_image_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);file=self.fixture(root);a=analyze(root/'project',file)
            self.assertFalse(a['image_analysis_performed']);self.assertEqual(len(a['joints']),4)
            rows=solve(root/'project');self.assertLess(max(x['closure_error_mm'] for x in rows),1e-8)
            with self.assertRaises(FileExistsError):analyze(root/'project',file)
    def test_reference_and_observations(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);file=self.fixture(root);ref=root/'test.webp';Image.new('RGB',(32,32),'white').save(ref)
            obs=root/'obs.json';write(obs,{'confidence':.75,'unknowns':['hidden shaft'],'provenance':'test fixture, not machine vision'})
            result=analyze(root/'project',file,ref,obs)
            self.assertTrue(result['image_analysis_performed']);self.assertTrue((root/'project/input/reference.webp').exists())
    def test_unknown_backend_does_not_create_fake_file(self):
        from generate_parts import generate
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(NotImplementedError):generate(temp,'freecad')
            self.assertFalse(list(Path(temp).glob('**/*.FCStd')))
    def test_truncated_mesh_rejected(self):
        from validate_project import mesh_check
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'bad.stl';p.write_bytes(b'not a mesh')
            with self.assertRaises(ValueError):mesh_check(p)
if __name__=='__main__':unittest.main()
