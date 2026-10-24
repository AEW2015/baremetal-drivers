"""Exact artifact identity gates, without hardware access."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from check_artifacts import check
class ArtifactPair(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.sof=self.root/'test.sof';self.handoff=self.root/'handoff.bin';self.profile=self.root/'profile.json'
        self.sof.write_bytes(b'sof fixture');self.handoff.write_bytes(b'handoff fixture')
        self.data={'name':'fixture','device':'fixture-only','qualification':'recorded-bench-pass','sof_sha256':hashlib.sha256(self.sof.read_bytes()).hexdigest(),'handoff_sha256':hashlib.sha256(self.handoff.read_bytes()).hexdigest()};self.write()
    def write(self):self.profile.write_text(json.dumps(self.data))
    def test_exact_pair_matches(self):self.assertEqual(check(self.profile,self.sof,self.handoff)['status'],'match')
    def test_changed_handoff_is_unqualified(self):
        self.handoff.write_bytes(b'different');self.assertEqual(check(self.profile,self.sof,self.handoff)['status'],'unqualified')
    def test_changed_sof_is_unqualified(self):
        self.sof.write_bytes(b'different');self.assertEqual(check(self.profile,self.sof,self.handoff)['status'],'unqualified')
    def test_unqualified_profile_cannot_pass_on_hashes_alone(self):
        self.data['qualification']='not-tested';self.write();self.assertEqual(check(self.profile,self.sof,self.handoff)['status'],'unqualified')

    def test_invalid_profile_has_actionable_schema_error(self):
        self.profile.write_text('[]')
        with self.assertRaisesRegex(ValueError,'Profile must define'):check(self.profile,self.sof,self.handoff)
