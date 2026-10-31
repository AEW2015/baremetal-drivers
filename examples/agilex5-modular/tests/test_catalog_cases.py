"""A bundled platform PASS must include every required recorded case."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('example_catalog',ROOT/'catalog.py')
catalog=importlib.util.module_from_spec(spec);spec.loader.exec_module(catalog)

class CatalogCases(unittest.TestCase):
    def check_bundle(self,tests,cases):
        data=copy.deepcopy(json.loads((ROOT/'catalog.json').read_text()))
        # Keep real inventory/source checks; only replace this isolated evidence.
        for row in data['examples']:
            for result in row['platforms'].values():
                if result.get('evidence'):result['evidence']=str(ROOT/result['evidence'])
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);evidence=base/'bundle.json'
            evidence.write_text(json.dumps({'tests':tests}))
            data['examples'].append({'id':'test/bundle','title':'Bundle guard','family':'Test',
                'source':'examples/agilex5-modular/memory-labs/fabric-ddr','scope':'Fixture',
                'platforms':{'qemu':{'status':'not-supported'},'hardware':{'status':'not-run'},
                    'simics':{'status':'pass','evidence':str(evidence),'cases':cases}}})
            (base/'catalog.json').write_text(json.dumps(data))
            with patch.object(catalog,'ROOT',base):return catalog.load()

    def test_all_required_cases_must_pass(self):
        tests=[{'name':'transfer','status':'pass'},{'name':'fault','status':'fail'}]
        with self.assertRaisesRegex(ValueError,'contradicts evidence'):
            self.check_bundle(tests,['transfer','fault'])
        tests[1]['status']='pass'
        self.assertTrue(self.check_bundle(tests,['transfer','fault']))

    def test_missing_or_duplicate_cases_rejected(self):
        with self.assertRaisesRegex(ValueError,'Missing/ambiguous'):
            self.check_bundle([{'name':'transfer','status':'pass'}],['transfer','fault'])
        with self.assertRaisesRegex(ValueError,'distinct list'):
            self.check_bundle([{'name':'transfer','status':'pass'}],['transfer','transfer'])

if __name__=='__main__':unittest.main()
