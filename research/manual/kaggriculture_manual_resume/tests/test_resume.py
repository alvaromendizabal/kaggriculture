import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import resume as r

class FakeS3:
    def __init__(self, data=b'evidence', version='v1', length=None):
        self.data=data; self.version=version; self.length=length; self.calls=0
    def get_object(self, **kwargs):
        self.calls+=1
        self.kwargs=kwargs
        return {'Body':io.BytesIO(self.data),'VersionId':self.version,
                'ContentLength':len(self.data) if self.length is None else self.length}

def record(data=b'evidence'):
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
            'version_id':'v1','readback_verified':True}

class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.base=Path(self.tmp.name)
        self.patcher=patch.object(r,'STATE',self.base/'state'); self.patcher.start()
        r.DEADLINE=float('inf')
        self.manifest={'bucket':'private-test','prefix':'runs/test/'}
        self.relative='artifacts/staffing_episodes/a.json.gz'
    def tearDown(self):
        self.patcher.stop(); self.tmp.cleanup()
    def test_path_inside_root(self):
        self.assertEqual(r.safe_target(self.base,'reports/x.json'),self.base/'reports/x.json')
    def test_parent_escape_rejected(self):
        with self.assertRaises(ValueError):r.safe_target(self.base,'../x')
    def test_embedded_parent_escape_rejected(self):
        with self.assertRaises(ValueError):r.safe_target(self.base,'reports/../../x')
    def test_absolute_path_rejected(self):
        with self.assertRaises(ValueError):r.safe_target(self.base,'/etc/x')
    def test_backslash_rejected(self):
        with self.assertRaises(ValueError):r.safe_target(self.base,'reports\\x')
    def test_symlink_parent_rejected(self):
        (self.base/'reports').symlink_to(self.base/'outside')
        with self.assertRaises(ValueError):r.safe_target(self.base,'reports/x.json')
    def test_symlink_target_rejected(self):
        (self.base/'reports').mkdir(); (self.base/'reports/x').symlink_to(self.base/'other')
        with self.assertRaises(ValueError):r.safe_target(self.base,'reports/x')
    def test_hash_validation(self):
        item=self.base/'x';item.write_bytes(b'evidence')
        self.assertTrue(r.verified_file(item,record()))
        item.write_bytes(b'corrupt!'); self.assertFalse(r.verified_file(item,record()))
    def test_restore_exact_version(self):
        s=FakeS3(); outcome=r.restore_one(s,self.manifest,self.base,self.relative,record())
        self.assertEqual(s.kwargs['VersionId'],'v1')
        self.assertEqual(s.kwargs['Key'],'runs/test/'+self.relative)
        self.assertEqual(outcome['status'],'DOWNLOADED_VERSION_AND_HASH_VERIFIED')
    def test_resume_without_another_download(self):
        s=FakeS3();r.restore_one(s,self.manifest,self.base,self.relative,record())
        again=r.restore_one(s,self.manifest,self.base,self.relative,record())
        self.assertEqual(s.calls,1);self.assertEqual(again['status'],'REUSED_HASH_VERIFIED')
    def test_wrong_hash_never_published(self):
        with self.assertRaises(RuntimeError):
            r.restore_one(FakeS3(b'badbytes'),self.manifest,self.base,self.relative,record())
        self.assertFalse((self.base/self.relative).exists())
        self.assertEqual(len(list(self.base.rglob('*.partial'))),1)
    def test_wrong_version_rejected(self):
        with self.assertRaises(RuntimeError):
            r.restore_one(FakeS3(version='different'),self.manifest,self.base,self.relative,record())
        self.assertFalse((self.base/self.relative).exists())
    def test_wrong_size_rejected(self):
        with self.assertRaises(RuntimeError):
            r.restore_one(FakeS3(length=999),self.manifest,self.base,self.relative,record())
    def test_existing_corrupt_file_preserved(self):
        path=self.base/self.relative;path.parent.mkdir(parents=True);path.write_bytes(b'keep-me')
        s=FakeS3()
        with self.assertRaises(RuntimeError):r.restore_one(s,self.manifest,self.base,self.relative,record())
        self.assertEqual(path.read_bytes(),b'keep-me');self.assertEqual(s.calls,0)
    def test_unknown_manifest_family(self):
        with self.assertRaises(ValueError):r.validate_record('src/change.py',record())
    def test_unverified_manifest_rejected(self):
        obj=record();obj['readback_verified']=False
        with self.assertRaises(ValueError):r.validate_record(self.relative,obj)
    def test_oversize_manifest_rejected(self):
        obj=record();obj['bytes']=20_000_000
        with self.assertRaises(ValueError):r.validate_record(self.relative,obj)
    def test_atomic_json_valid(self):
        p=self.base/'report.json';r.atomic_json(p,{'value':1});r.atomic_json(p,{'value':2})
        self.assertEqual(json.loads(p.read_text()),{'value':2})
    def test_source_path_in_kernel_bootstrap_twice(self):
        doc=r.kernel_document(self.base/'new',self.base/'old/.venv/bin/python')
        self.assertEqual(doc['argv'][1:3],['-I','-B'])
        self.assertEqual(doc['argv'][4].count('sys.path[:]='),2)
        self.assertIn(str(self.base/'new/src'),doc['argv'][4])
    def test_runtime_code_compiles(self):
        compile(r.runtime_probe(self.base/'new'),'runtime-probe','exec')
    def test_supplied_manifest_valid(self):
        m=r.load_manifest();self.assertEqual(len(m['artifacts']),10)
        self.assertEqual(sum(p.startswith('artifacts/') for p in m['artifacts']),7)
    def test_command_failure_reports(self):
        with self.assertRaises(RuntimeError):
            r.run([sys.executable,'-c','raise SystemExit(7)'],seconds=5,label='expected-failure')
    def test_command_timeout_bounded(self):
        with self.assertRaises(TimeoutError):
            r.run([sys.executable,'-c','import time;time.sleep(30)'],seconds=.2,label='timeout-test')
    def test_clone_preserves_original_and_resumes(self):
        remote=self.base/'remote';old=self.base/'original';new=self.base/'new'
        remote.mkdir();old.mkdir();(old/'raw.zip').write_bytes(b'original-data')
        def cmd(*args):return subprocess.check_output(args,stderr=subprocess.STDOUT,text=True).strip()
        cmd('git','init','-b','main',str(remote))
        cmd('git','-C',str(remote),'config','user.email','test@example.invalid')
        cmd('git','-C',str(remote),'config','user.name','Local Test')
        (remote/'README.md').write_text('source')
        cmd('git','-C',str(remote),'add','README.md');cmd('git','-C',str(remote),'commit','-m','test')
        head=cmd('git','-C',str(remote),'rev-parse','HEAD')
        p={'old':old,'repo':new}
        r.sync_checkout(p,expected=head,remote=str(remote))
        r.sync_checkout(p,expected=head,remote=str(remote))
        self.assertEqual((old/'raw.zip').read_bytes(),b'original-data')
        (new/'local-notes.txt').write_text('preserve')
        with self.assertRaises(RuntimeError):r.sync_checkout(p,expected=head,remote=str(remote))
        self.assertEqual((new/'local-notes.txt').read_text(),'preserve')
    def test_refuses_original_as_destination(self):
        with self.assertRaises(RuntimeError):r.sync_checkout({'old':self.base,'repo':self.base})
    def test_reference_contains_no_metric_improvement_claim(self):
        e=json.loads((r.HERE/'verified_evidence.json').read_text())
        self.assertFalse(e['competition']['official_metric_measured_by_this_kit'])
        self.assertFalse(e['aws']['current_ebs_contents_directly_inspected'])

if __name__=='__main__':unittest.main(verbosity=2)
