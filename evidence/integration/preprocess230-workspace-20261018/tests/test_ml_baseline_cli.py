"""실자료 실행 CLI의 미확보 입력 처리와 읽기 전용 사전검사 시험."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import rasterio
from rasterio.transform import from_origin
from scripts.run_baseline import run, register_report
from backend.app.store import Store


class BaselineCliTests(unittest.TestCase):
    def test_manual_registration_preserves_pending_job_and_forces_draft(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            (root/'weights.pt').write_bytes(b'explicit-registration-fixture-not-real-model')
            (root/'manifest.json').write_text(json.dumps({'version':'fixture'}),encoding='utf-8')
            report={'status':'completed_functional_baseline','run_id':'fixture','synthetic':True,
                    'dataset':{'dataset_id':'dataset','manifest_path':'manifest.json'},
                    'training':{'model_id':'model','checkpoint_path':'weights.pt','dataset_version':'fixture',
                                'status':'Approved','independent_evaluation':True,'history':[{'epoch':1}]},'predictions':[]}
            path=root/'report.json'; path.write_text(json.dumps(report),encoding='utf-8')
            store=Store(root); store.put('jobs',{'id':'pending','status':'running'})
            receipt=register_report(path,root)
            self.assertEqual(receipt['status'],'registered')
            self.assertEqual(store.get('jobs','pending')['status'],'running')
            model=store.get('models','model')
            self.assertEqual(model['status'],'Draft')
            self.assertFalse(model['independent_evaluation'])
            self.assertEqual(model['training_history'],[{'epoch':1}])
            with self.assertRaisesRegex(ValueError,'이미 등록'):
                register_report(path,root)

    def test_missing_scenes_records_failure_without_fabricating_training(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            manifest=root/'inputs.json'; manifest.write_text('{"scenes":[]}',encoding='utf-8')
            args=SimpleNamespace(data_root=root,run_id='missing',manifest=manifest,check_only=True,scale=.0001,offset=0)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(run(args),2)
            report=json.loads((root/'results/missing/baseline-run.json').read_text(encoding='utf-8'))
            self.assertEqual(report['status'],'failed')
            self.assertNotIn('training',report)
            self.assertFalse((root/'models').exists())

    def test_preflight_three_explicit_synthetic_regions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); scenes=[]
            for index in range(3):
                profile={'driver':'GTiff','crs':'EPSG:32748','width':16,'height':16,'transform':from_origin(500000+index*10000,9000000,10,10),'nodata':0}
                with rasterio.open(root/f'i{index}.tif','w',**profile,count=3,dtype='uint16') as dst:
                    dst.write(np.full((3,16,16),1000,dtype='uint16'))
                with rasterio.open(root/f'l{index}.tif','w',**profile,count=1,dtype='uint8') as dst:
                    dst.write(np.full((1,16,16),10,dtype='uint8'))
                scenes.append({'image_path':f'i{index}.tif','label_path':f'l{index}.tif','group':f'g{index}','label_source':'worldcover','source':'synthetic-test'})
            manifest=root/'inputs.json'; manifest.write_text(json.dumps({'scenes':scenes,'synthetic':True}),encoding='utf-8')
            args=SimpleNamespace(data_root=root,run_id='check',manifest=manifest,check_only=True,scale=.0001,offset=0)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(run(args),0)
            report=json.loads((root/'results/check/baseline-run.json').read_text(encoding='utf-8'))
            self.assertTrue(report['synthetic'])
            self.assertEqual(len(report['quality']),3)
            self.assertEqual(report['status'],'preflight_passed_no_training')
            self.assertNotIn('training',report)


if __name__=='__main__':
    unittest.main()
