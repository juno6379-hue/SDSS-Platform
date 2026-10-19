"""Temporary actual checkpoint + two/six registry scenes; no execution."""
import copy
import hashlib
import json
import unittest
from unittest.mock import patch

from app.dataset_registry import canonical_manifest, version_key
from app.ml import pinned_annual_normalization as api
import test_pinned_scene_normalization as single_fixtures


def sha(raw):return hashlib.sha256(raw).hexdigest()


class PinnedAnnualNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.fixture=single_fixtures.PinnedSceneNormalizationTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups);self.store=self.fixture.store;self.root=self.fixture.root
        self.rows=[];self.paths=[]
        for year in range(2020,2026):
            directory=self.root/'annual'/str(year);directory.mkdir(parents=True)
            image=directory/'image.bin';image.write_bytes(f'TEMP NOT A VERIFIED RASTER {year}'.encode())
            metadata=directory/'metadata.xml';metadata.write_bytes(f'<fixture year="{year}"/>'.encode())
            evidence=directory/'evidence.json'
            doc=copy.deepcopy(self.fixture.scene.evidence)
            doc.update(product_id=f'SCENE_{year}',source_metadata_path=metadata.relative_to(self.root).as_posix(),source_metadata_sha256=sha(metadata.read_bytes()))
            evidence.write_text(json.dumps(doc),encoding='utf-8')
            refs=[{'id':f'{role}-{year}','version':'v1','sha256':sha(path.read_bytes())}
                  for role,path in zip(('image','evidence','metadata'),(image,evidence,metadata))]
            for index,(ref,path) in enumerate(zip(refs,(image,evidence,metadata))):
                manifest=copy.deepcopy(self.fixture.scene.manifests[index])
                manifest.update(dataset_id=ref['id'],version=ref['version'],sha256=ref['sha256'],artifact_uri=path.relative_to(self.root).as_posix())
                if index==0:manifest['source']['scene_id']=f'SCENE_{year}'
                elif index==1:manifest['lineage']=[{**refs[0],'role':'normalization_input_image'},{**refs[2],'role':'normalization_source_metadata'}]
                snapshot,digest=canonical_manifest(manifest)
                self.store.put('dataset_versions',{'id':version_key(ref['id'],ref['version']),'manifest':snapshot,'manifest_sha256':digest})
            self.rows.append({'year':year,'image_ref':refs[0],'evidence_ref':refs[1],'metadata_ref':refs[2]})
            self.paths.append((image,evidence,metadata))

    def inspect(self,**kwargs):
        args={'store':self.store,'model_ref':self.fixture.model_ref,'training_report_sha256':self.fixture.report_sha,'requested_years':self.rows[:2]}
        args.update(kwargs);return api.inspect_pinned_annual_normalization(**args)

    def test_actual_two_and_six_scene_integration_one_model_read_shared_actual_manifest(self):
        for size in (2,6):
            seen=[];reader=api.read_registered_per_scene_files
            def record_scene(store,manifest,*refs):seen.append(manifest);return reader(store,manifest,*refs)
            with (patch.object(api,'read_pinned_model_checkpoint_manifest',wraps=api.read_pinned_model_checkpoint_manifest) as model,
                  patch.object(api,'read_registered_per_scene_files',record_scene),patch.object(self.store,'get',wraps=self.store.get) as get):
                result=self.inspect(requested_years=self.rows[:size])
            self.assertEqual(len(result),24);self.assertEqual(result['status'],'PINNED_YEARS_MATCHED_UNVERIFIED');model.assert_called_once()
            self.assertEqual(get.call_count,1+3*size);self.assertTrue(all(v is result['model_observation']['checkpoint_manifest'] for v in seen))
            self.assertEqual(result['model_observation_calls'],1);self.assertEqual(result['scene_observation_calls'],size);self.assertEqual(result['checked_rows'],size)
            self.assertTrue(result['artifact_bytes_verified']);self.assertTrue(result['registry_references_verified'])
            self.assertTrue(all(row['status']=='MATCHED_UNVERIFIED' for row in result['rows']))
            self.assertFalse(result['temporal_year_verified'])

    def test_upfront_whole_batch_shape_year_bool_order_ref_and_duplicate_image_reject_no_store(self):
        invalid=[None,[],self.rows[:1],self.rows+[self.rows[0]],tuple(self.rows[:2]),list(reversed(self.rows[:2]))]
        for bad in (True,1899,2201,2020.,'2020'):
            rows=copy.deepcopy(self.rows[:2]);rows[0]['year']=bad;invalid.append(rows)
        for key,value in (('year',2020),('image_ref',None),('evidence_ref',{'id':'x','version':'latest','sha256':'0'*64})):
            rows=copy.deepcopy(self.rows[:2]);rows[1][key]=value;invalid.append(rows)
        rows=copy.deepcopy(self.rows[:2]);rows[1]['image_ref']=copy.deepcopy(rows[0]['image_ref']);invalid.append(rows)
        rows=copy.deepcopy(self.rows[:2]);rows[0]['extra']='private';invalid.append(rows)
        rows=copy.deepcopy(self.rows[:2]);rows[0]['metadata_ref']=copy.deepcopy(rows[0]['evidence_ref']);invalid.append(rows)
        with patch.object(self.store,'get',side_effect=AssertionError('I/O forbidden')):
            for rows in invalid:
                result=self.inspect(requested_years=rows)
                self.assertEqual(result['status'],'INVALID_INPUT');self.assertEqual(result['rows'],[])
                self.assertEqual(result['issue'],{'code':'INVALID_INPUT','field':'request','year':None})
                self.assertEqual(result['model_observation_calls'],0)
            self.assertEqual(self.inspect(model_ref={**self.fixture.model_ref,'id':'한글'})['status'],'INVALID_INPUT')
            self.assertEqual(self.inspect(training_report_sha256=True)['status'],'INVALID_INPUT')

    def test_model_failure_all_rows_not_checked_scene_zero_partial_model_flags(self):
        self.fixture.report_path.write_bytes(self.fixture.report_path.read_bytes()+b'changed')
        with patch.object(api,'read_registered_per_scene_files',side_effect=AssertionError('no scenes')) as scene:result=self.inspect()
        scene.assert_not_called();self.assertEqual(result['status'],'MODEL_BLOCKED')
        self.assertTrue(result['checkpoint_artifact_verified']);self.assertFalse(result['training_report_artifact_verified'])
        self.assertEqual(result['checked_rows'],0);self.assertTrue(all(row['status']=='NOT_CHECKED' for row in result['rows']))

    def test_global_valid_batch_reads_only_model_invalid_batch_is_io_zero(self):
        self.fixture.manifest['normalization_mode']='global';self.fixture.bind_model()
        with patch.object(api,'read_registered_per_scene_files',side_effect=AssertionError('no scenes')) as scene,patch.object(self.store,'get',wraps=self.store.get) as get:
            result=self.inspect()
        self.assertEqual(result['status'],'OUT_OF_SCOPE');scene.assert_not_called();self.assertEqual(get.call_count,1)
        self.assertEqual(result['scene_observation_calls'],0);self.assertTrue(all(r['status']=='NOT_CHECKED' for r in result['rows']))
        with patch.object(self.store,'get',side_effect=AssertionError('no I/O')):
            self.assertEqual(self.inspect(requested_years=[])['status'],'INVALID_INPUT')

    def test_middle_failure_failfast_first_issue_partial_rows_and_full_aggregate_false(self):
        self.paths[1][0].write_bytes(b'tampered')
        result=self.inspect(requested_years=self.rows[:3])
        self.assertEqual(result['status'],'SCENE_BLOCKED');self.assertEqual(result['issue'],{'code':'SCENE_OBSERVATION_BLOCKED','field':'scene','year':2021})
        self.assertEqual([row['status'] for row in result['rows']],['MATCHED_UNVERIFIED','BLOCKED','NOT_CHECKED'])
        self.assertEqual(result['checked_rows'],2);self.assertEqual(result['scene_observation_calls'],2)
        self.assertTrue(result['rows'][0]['scene_observation']['artifact_bytes_verified'])
        self.assertFalse(result['artifact_bytes_verified']);self.assertFalse(result['registry_references_verified'])
        self.assertIsNone(result['rows'][2]['scene_observation'])

    def test_first_scene_exception_fixed_issue_no_secret_and_later_reads_zero(self):
        with patch.object(api,'read_registered_per_scene_files',side_effect=RuntimeError('private root password')) as scene:
            result=self.inspect(requested_years=self.rows[:6])
        scene.assert_called_once();self.assertEqual(result['checked_rows'],1);self.assertNotIn('password',str(result))
        self.assertEqual([r['status'] for r in result['rows']],['BLOCKED']+['NOT_CHECKED']*5)

    def test_model_exception_counts_attempt_and_sanitizes_without_scene(self):
        with patch.object(api,'read_pinned_model_checkpoint_manifest',side_effect=RuntimeError('private path')),patch.object(api,'read_registered_per_scene_files') as scene:
            result=self.inspect()
        scene.assert_not_called();self.assertEqual(result['model_observation_calls'],1);self.assertIsNone(result['model_observation'])
        self.assertEqual(result['issue'],{'code':'MODEL_OBSERVATION_BLOCKED','field':'model','year':None})
        self.assertNotIn('private path',str(result))

    def test_requested_year_labels_do_not_prove_manifest_temporal_match(self):
        rows=copy.deepcopy(self.rows[:2]);rows[0]['year']=1900;rows[1]['year']=2200
        result=self.inspect(requested_years=rows)
        self.assertEqual(result['status'],'PINNED_YEARS_MATCHED_UNVERIFIED');self.assertFalse(result['temporal_year_verified'])
        self.assertEqual([r['year'] for r in result['rows']],[1900,2200])

    def test_inputs_db_files_unchanged_and_all_approval_flags_false(self):
        before=copy.deepcopy((self.fixture.model_ref,self.rows))
        files={p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with patch.object(self.store,'put',side_effect=AssertionError('no writes')):result=self.inspect()
        self.assertEqual(before,(self.fixture.model_ref,self.rows))
        self.assertEqual(files,{p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        for key in ('state_dict_verified','raster_header_verified','quality_report_verified','quality_mask_verified',
                    'source_authority_verified','access_authorization_verified','other_lineage_parents_verified',
                    'scientific_accuracy_validated','execution_authorized','workflow_supported','temporal_year_verified'):
            self.assertIs(result[key],False)


if __name__=='__main__':unittest.main()
