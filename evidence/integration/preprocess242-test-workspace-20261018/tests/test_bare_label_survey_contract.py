"""220 순수 합성JSON 계약. 실제 파일·원장·raster·HTTP를 읽지 않는다."""
import copy
from dataclasses import FrozenInstanceError
import unittest
from unittest.mock import patch

from app.data import bare_label_survey_contract as subject
from app.data.references import esri_annual_plan


class BareLabelSurveyContractTests(unittest.TestCase):
    def setUp(self):
        ref=lambda p:{'path':p,'sha256':'a'*64}
        scene={'id':'S2A_MSIL2A_20240601T000000_N0510_R001_T51MXR_20240601T000000',
               'datetime':'2024-06-01T00:00:00Z','source_group':
               'southeast_sulawesi/S2A_MSIL2A_20240601T000000_N0510_R001_T51MXR_20240601T000000',
               'stac_ref':ref('data/selected/stac.json')}
        self.request={'schema_version':1,'kind':'BARE_LABEL_SURVEY_REQUEST','survey_id':'survey220-synthetic',
            'config_sha256':'b'*64,
            'current_manifest_ref':ref('data/source.json'),'boundary_ref':ref('data/boundary.json'),
            'ledger_ref':ref('data/ledger.json'),'base_config_ref':ref('configs/survey-base.json'),
            'seed':{'seed_id':'synthetic-seed','province':'southeast_sulawesi','fixed_split':'train',
                'year':2024,'bbox_wgs84':[122.0,-4.0,122.1,-3.9],
                'period_start':'2024-01-01T00:00:00Z','period_end':'2024-12-31T23:59:59Z',
                'justification_ref':ref('evidence/integration/synthetic-seed.json')},
            'selected_scene':scene,'policy':copy.deepcopy(subject.POLICY),
            'budget_snapshot':{'additional_maximum_bytes':subject.GLOBAL_BYTES,'new_charged_bytes':136314880,
                'preserved_pending_bytes':136314880,'rate_limit_active':False},
            'output_relative_path':'data/bare-label-surveys/survey220-synthetic','patches_materialized':0,
            **dict.fromkeys(subject.FALSE_FLAGS,False)}
        self.pin=subject.validate_survey_request(self.request).request_sha256
        grid={'crs':'EPSG:32751','transform':[10,0,400000,0,-10,9600000], 'width':2048,'height':2048}
        annual=esri_annual_plan(2024,scene['id'])
        self.receipt={'schema_version':1,'kind':'BARE_LABEL_SURVEY_RECEIPT','collection_purpose':'SURVEY_LABEL_ONLY',
            'survey_id':self.request['survey_id'],'request_sha256':self.pin,
            'batch_key':'bare-survey-'+self.request['survey_id']+'-'+self.pin[:12],
            'config_sha256':'b'*64,'selected_scene':copy.deepcopy(scene),
            'label':{'ref':ref(self.request['output_relative_path']+'/raw-esri_io.tif'),
                'label_source':'esri_io','label_year':2024,'source_url':annual['url'],'license':'CC-BY-4.0',
                'dataset_version':annual['version'],'grid':grid},
            'candidate_scl_refs':[{'ref':ref(self.request['output_relative_path']+'/qa-candidate-00-SCL.tif'),
                'scene_id':scene['id'],'role':'SCL_CANDIDATE_SUPPORT',
                'grid':{**grid,'width':1024,'height':1024}}],
            'accounting':{'state':'DECLARED_MEASURED_SETTLED','measurement_known':True,
                'reserved_bytes':subject.BATCH_BYTES,'charged_bytes':120,'metadata_body_bytes':20,
                'cog_body_bytes':100},'patches_materialized':0,**dict.fromkeys(subject.FALSE_FLAGS,False)}

    def assert_bad_request(self,edit,code=None):
        value=copy.deepcopy(self.request);edit(value)
        with self.assertRaises(subject.SurveyContractError) as caught:
            subject.validate_survey_request(value)
        if code:self.assertEqual(str(caught.exception),code)
        self.assertRegex(str(caught.exception),r'^SURVEY_[A-Z0-9_]+$')

    def assert_bad_receipt(self,edit,code=None):
        value=copy.deepcopy(self.receipt);edit(value)
        with self.assertRaises(subject.SurveyContractError) as caught:
            subject.validate_survey_receipt(value,self.request)
        if code:self.assertEqual(str(caught.exception),code)

    def test_valid_request_immutable_typed_copy_and_false_status(self):
        original=copy.deepcopy(self.request);checked=subject.validate_survey_request(self.request)
        self.assertIsInstance(checked,subject.ValidatedSurveyContract)
        self.assertFalse(checked.execution_supported);self.assertFalse(checked.provenance_verified)
        self.assertEqual(checked.status,'DECLARED_CONTRACT_VALID_EXECUTION_PLANNED')
        with self.assertRaises(FrozenInstanceError):checked.kind='other'
        checked.to_dict()['seed']['year']=2021
        self.assertEqual(checked.to_dict(),original);self.assertEqual(self.request,original)

    def test_receipt_validates_only_declared_facts_not_operational_truth(self):
        checked=subject.validate_survey_receipt(self.receipt,self.request)
        self.assertEqual(checked.request_sha256,self.pin)
        self.assertFalse(checked.provenance_verified);self.assertFalse(checked.execution_supported)
        self.assertEqual(checked.to_dict(),self.receipt)

    def test_no_io_for_request_or_receipt(self):
        with patch('builtins.open',side_effect=AssertionError('I/O forbidden')), \
             patch('pathlib.Path.open',side_effect=AssertionError('I/O forbidden')), \
             patch('socket.socket',side_effect=AssertionError('HTTP forbidden')):
            subject.validate_survey_request(self.request)
            subject.validate_survey_receipt(self.receipt,self.request)

    def test_exact_keys_types_and_unknown_execute_rejected(self):
        for edit in (lambda d:d.update(execute=True),lambda d:d.update(schema_version=True),
                     lambda d:d.update(kind='annual-window-report'),lambda d:d.pop('ledger_ref')):
            self.assert_bad_request(edit)

    def test_all_approval_and_training_flags_prohibited(self):
        for field in subject.FALSE_FLAGS:
            with self.subTest(field=field):
                self.assert_bad_request(lambda d:d.update({field:True}),'SURVEY_APPROVAL_PROHIBITED')
                self.assert_bad_receipt(lambda d:d.update({field:True}),'SURVEY_APPROVAL_PROHIBITED')
        self.assert_bad_request(lambda d:d.update(patches_materialized=True))
        self.assert_bad_receipt(lambda d:d.update(patches_materialized=1))

    def test_paths_are_lexical_local_and_canonical_only(self):
        for path in ('../secret','data/../secret','data//a','C:/secret','//server/share',
                     'data/a:secret','data/CON.json','data/COM¹.json','data/a.','data/a\\b','data/a\x00b'):
            with self.subTest(path=path):
                self.assert_bad_request(lambda d:d['ledger_ref'].update(path=path))

    def test_refs_sha_alias_and_nondata_operational_ref(self):
        for pin in ('A'*64,'f'*63,False):
            self.assert_bad_request(lambda d:d['ledger_ref'].update(sha256=pin))
        self.assert_bad_request(lambda d:d.update(boundary_ref=copy.deepcopy(d['current_manifest_ref'])))
        self.assert_bad_request(lambda d:d['ledger_ref'].update(path='evidence/integration/fake-ledger.json'))

    def test_output_is_separate_survey_only(self):
        for path in ('data/first-group-training-esri-v1','data/bare-label-surveys/other',
                     'data/model','data/bare-label-surveys/survey220-synthetic/'):
            self.assert_bad_request(lambda d:d.update(output_relative_path=path),'SURVEY_OUTPUT_INVALID')

    def test_fixed_province_split_year_and_scene(self):
        for edit in (lambda d:d['seed'].update(province='unknown'),
                     lambda d:d['seed'].update(fixed_split='test'),lambda d:d['seed'].update(year=True),
                     lambda d:d['seed'].update(year=2026),lambda d:d['selected_scene'].update(id='unfixed'),
                     lambda d:d['selected_scene'].update(source_group='west_java/other'),
                     lambda d:d['selected_scene'].update(id=d['selected_scene']['id'].replace('2024','2023')),
                     lambda d:d['selected_scene'].update(datetime='2023-06-01T00:00:00Z')):
            self.assert_bad_request(edit)

    def test_bbox_period_numeric_and_structure_failclosed(self):
        for bbox in ([122,-4,121,-3],[True,-4,123,-3],[float('nan'),-4,123,-3],[0,0,1,2**10000]):
            self.assert_bad_request(lambda d:d['seed'].update(bbox_wgs84=bbox))
        for edit in (lambda d:d['seed'].update(period_end='2024-02-31T00:00:00Z'),
                     lambda d:d['seed'].update(period_end='2024-01-01T00:00:00Z'),
                     lambda d:d['seed'].update(period_start='2024-06-02T00:00:00Z'),
                     lambda d:d.update(survey_id='a'*5000)):
            self.assert_bad_request(edit)
        nested=[];nested.append(nested)
        with self.assertRaises(subject.SurveyContractError):subject.validate_survey_request(nested)

    def test_exact_policy_cannot_increase_budget_or_relax_circuit(self):
        for key,value in (('maximum_cog_bytes',subject.COG_BYTES+1),('maximum_metadata_bytes',2**21),
                          ('maximum_batches',2),('maximum_label_side',4096),('request_spacing_seconds',1),
                          ('transient_asset_retries',1),('stop_on_first_429',False),('maximum_batches',True)):
            self.assert_bad_request(lambda d:d['policy'].update({key:value}),'SURVEY_POLICY_INVALID')

    def test_budget_is_existing_bound_not_new_authorization(self):
        for edit in (lambda d:d['budget_snapshot'].update(additional_maximum_bytes=subject.GLOBAL_BYTES+1),
                     lambda d:d['budget_snapshot'].update(new_charged_bytes=subject.GLOBAL_BYTES-subject.BATCH_BYTES+1),
                     lambda d:d['budget_snapshot'].update(preserved_pending_bytes=136314881),
                     lambda d:d['budget_snapshot'].update(rate_limit_active=True),
                     lambda d:d['budget_snapshot'].update(new_charged_bytes=True)):
            self.assert_bad_request(edit,'SURVEY_BUDGET_INVALID')
        self.request['budget_snapshot']['new_charged_bytes']=subject.GLOBAL_BYTES-subject.BATCH_BYTES
        self.assertFalse(subject.validate_survey_request(self.request).execution_supported)

    def test_receipt_request_and_scene_digest_binding(self):
        for edit in (lambda d:d.update(request_sha256='0'*64),lambda d:d.update(batch_key='other'),
                     lambda d:d.update(survey_id='other'),lambda d:d.update(config_sha256=True),
                     lambda d:d.update(config_sha256='c'*64),
                     lambda d:d['selected_scene'].update(datetime='2024-07-01T00:00:00Z')):
            self.assert_bad_receipt(edit)

    def test_esri_exact_scene_supercell_year_version_and_unsigned_url(self):
        for edit in (lambda d:d['label'].update(label_source='worldcover'),
                     lambda d:d['label'].update(label_year=2023),lambda d:d['label'].update(label_year=True),
                     lambda d:d['label'].update(source_url=d['label']['source_url']+'?sig=secret'),
                     lambda d:d['label'].update(source_url=d['label']['source_url'].replace('51M','50M')),
                     lambda d:d['label'].update(dataset_version='legacy'),
                     lambda d:d['label']['ref'].update(path='data/first-group-training-esri-v1/fake.tif')):
            self.assert_bad_receipt(edit)

    def test_label_and_scl_grid_shape_crs_contract(self):
        for edit in (lambda d:d['label']['grid'].update(crs='EPSG:4326'),
                     lambda d:d['label']['grid'].update(width=2049),
                     lambda d:d['label']['grid'].update(width=True),
                     lambda d:d['label']['grid'].update(transform=[20,0,400000,0,-20,9600000]),
                     lambda d:d['candidate_scl_refs'][0]['grid'].update(crs='EPSG:32750'),
                     lambda d:d['candidate_scl_refs'][0]['grid'].update(height=1025),
                     lambda d:d['candidate_scl_refs'][0]['grid'].update(transform=[10,1,1,0,-10,1])):
            self.assert_bad_receipt(edit)

    def test_scl_selected_scene_required_and_no_duplicate_alias(self):
        for edit in (lambda d:d.update(candidate_scl_refs=[]),
                     lambda d:d['candidate_scl_refs'][0].update(scene_id='other'),
                     lambda d:d['candidate_scl_refs'][0].update(role='REFERENCE_LABEL'),
                     lambda d:d['candidate_scl_refs'].append(copy.deepcopy(d['candidate_scl_refs'][0]))):
            self.assert_bad_receipt(edit)

    def test_declared_measured_accounting_exact_caps_and_sum(self):
        for edit in (lambda d:d['accounting'].update(charged_bytes=119),
                     lambda d:d['accounting'].update(metadata_body_bytes=subject.METADATA_BYTES+1),
                     lambda d:d['accounting'].update(cog_body_bytes=subject.COG_BYTES+1),
                     lambda d:d['accounting'].update(metadata_body_bytes=True),
                     lambda d:d['accounting'].update(measurement_known=False),
                     lambda d:d['accounting'].update(reserved_bytes=subject.BATCH_BYTES+1)):
            self.assert_bad_receipt(edit,'SURVEY_ACCOUNTING_INVALID')

    def test_unsettled_must_preserve_full_reservation_and_unknown_measurement(self):
        self.receipt['accounting'].update(state='UNSETTLED_FULL_RESERVATION',measurement_known=False,
            charged_bytes=subject.BATCH_BYTES,metadata_body_bytes=None,cog_body_bytes=None)
        out=subject.validate_survey_receipt(self.receipt,self.request)
        self.assertFalse(out.provenance_verified);self.assertFalse(out.execution_supported)
        for edit in (lambda d:d['accounting'].update(charged_bytes=0),
                     lambda d:d['accounting'].update(metadata_body_bytes=0),
                     lambda d:d['accounting'].update(state='AUTO_REFUNDED'),
                     lambda d:d['accounting'].update(measurement_known=True)):
            self.assert_bad_receipt(edit,'SURVEY_ACCOUNTING_INVALID')

    def replace_scene(self, value, identifier, timestamp=None):
        value['selected_scene'].update(id=identifier,
            source_group=value['seed']['province']+'/'+identifier)
        if timestamp is not None:value['selected_scene']['datetime']=timestamp

    def test_strict_full_scene_id_calendar_sensor_orbit_and_mgrs(self):
        original=self.request['selected_scene']['id']
        bad=[original.replace('20240601T000000','20249999T999999'),
             original.replace('20240601T000000','20240230T000000'),
             original.replace('20240601T000000','20240601T246000'),
             original.replace('S2A','S2D'),original.replace('MSIL2A','MSIL1C'),
             original.replace('R001','R000'),original.replace('R001','R144'),
             original.replace('T51MXR','T00MXR'),original.replace('T51MXR','T61MXR'),
             original.replace('T51MXR','T51IXR'),original.replace('T51MXR','T51MIR'),
             original.replace('T51MXR','T51MXZ'),original.replace('N0510','N051'),
             original+'_suffix','prefix_'+original,original+'.SAFE',original[:-1],
             'S2A_MSIL2A_20240601T000000_x_T51MXR_x']
        for identifier in bad:
            with self.subTest(identifier=identifier):
                self.assert_bad_request(lambda d:self.replace_scene(d,identifier),'SURVEY_SCENE_INVALID')

    def test_normal_sensors_and_orbit_boundaries_and_leap_calendar(self):
        original=self.request['selected_scene']['id']
        for sensor in ('S2A','S2B','S2C'):
            for orbit in ('001','143'):
                value=copy.deepcopy(self.request)
                identifier=original.replace('S2A',sensor).replace('R001','R'+orbit)
                self.replace_scene(value,identifier)
                self.assertFalse(subject.validate_survey_request(value).execution_supported)
        value=copy.deepcopy(self.request)
        identifier=original.replace('20240601T000000','20240229T000000')
        self.replace_scene(value,identifier,'2024-02-29T00:00:00Z')
        self.assertFalse(subject.validate_survey_request(value).execution_supported)

    def test_scene_datetime_exact_acquisition_and_production_calendar(self):
        self.assert_bad_request(lambda d:d['selected_scene'].update(datetime='2024-06-01T00:00:01Z'),
                                'SURVEY_SCENE_TIME_MISMATCH')
        self.assert_bad_request(lambda d:d['selected_scene'].update(datetime='2024-07-01T00:00:00Z'),
                                'SURVEY_SCENE_TIME_MISMATCH')
        original=self.request['selected_scene']['id']
        for production in ('20240230T000000','20240531T235959'):
            identifier=original.rsplit('_',1)[0]+'_'+production
            self.assert_bad_request(lambda d:self.replace_scene(d,identifier),'SURVEY_SCENE_INVALID')

    def test_fractional_utc_exact_zero_is_allowed_nonzero_or_precision_loss_rejected(self):
        for fraction in ('.0','.000','.000000'):
            value=copy.deepcopy(self.request);value['selected_scene']['datetime']='2024-06-01T00:00:00'+fraction+'Z'
            subject.validate_survey_request(value)
        for text in ('2024-06-01T00:00:00.000001Z','2024-06-01T00:00:00.123Z'):
            self.assert_bad_request(lambda d:d['selected_scene'].update(datetime=text),'SURVEY_SCENE_TIME_MISMATCH')
        for text in ('2024-06-01T00:00:00.0000000Z','2024-06-01T00:00:00+00:00'):
            self.assert_bad_request(lambda d:d['selected_scene'].update(datetime=text),'SURVEY_TIME_INVALID')

    def test_other_year_acquisition_and_period_boundary_never_use_declaration_only(self):
        identifier=self.request['selected_scene']['id'].replace('20240601T000000','20231231T235959')
        self.assert_bad_request(lambda d:self.replace_scene(d,identifier),'SURVEY_SCENE_INVALID')
        value=copy.deepcopy(self.request);value['seed'].update(period_start='2024-06-01T00:00:00.000000Z')
        subject.validate_survey_request(value)
        self.assert_bad_request(lambda d:d['seed'].update(period_start='2024-06-01T00:00:00.000001Z'),
                                'SURVEY_SCENE_INVALID')

    def test_lone_surrogate_value_and_key_return_fixed_code_without_leakage(self):
        for surrogate in ('\ud800','\udfff'):
            self.assert_bad_request(lambda d:d['seed']['justification_ref'].update(
                path='evidence/integration/private-token'+surrogate),'SURVEY_UTF8_INVALID')
            self.assert_bad_request(lambda d:d.update({'private-token'+surrogate:1}),'SURVEY_UTF8_INVALID')
            self.assert_bad_receipt(lambda d:d['label']['ref'].update(
                path='data/private-token'+surrogate),'SURVEY_UTF8_INVALID')
        checked=subject.validate_survey_request(self.request)
        self.assertFalse(checked.execution_supported)

    def test_dict_changed_during_copy_runtimeerror_becomes_fixed_error(self):
        original=subject._number;changed=[]
        def change(value):
            if not changed:
                changed.append(True);self.request['private-token-race']=1
            return original(value)
        with patch.object(subject,'_number',side_effect=change):
            with self.assertRaises(subject.SurveyContractError) as caught:
                subject.validate_survey_request(self.request)
        self.assertEqual(str(caught.exception),'SURVEY_INPUT_CHANGED')
        self.assertNotIn('private',str(caught.exception))
        del self.request['private-token-race']
        subject.validate_survey_request(self.request)

    def test_only_detached_checked_tree_is_serialized_after_caller_mutation(self):
        original=copy.deepcopy(self.request);canonical=subject._canonical;changed=[]
        def change(value):
            if not changed:
                changed.append(True)
                self.request['seed']['justification_ref']['path']='private-token\ud800'
                self.request['execute']=True
            return canonical(value)
        with patch.object(subject,'_canonical',side_effect=change):
            checked=subject.validate_survey_request(self.request)
        self.assertEqual(checked.to_dict(),original)
        self.assertNotIn('private-token',checked.canonical_json)

    def test_growth_during_copy_cannot_bypass_container_or_node_limits(self):
        data=[1];number=subject._number;changed=[]
        def grow(value):
            if not changed:
                changed.append(True);data.extend([1]*128)
            return number(value)
        with patch.object(subject,'_number',side_effect=grow):
            with self.assertRaises(subject.SurveyContractError) as caught:subject._copy(data)
        self.assertEqual(str(caught.exception),'SURVEY_STRUCTURE_LIMIT')
        # Shared values must be detached independently and still count each visit.
        huge=[[0]*100 for _ in range(101)]
        with self.assertRaisesRegex(subject.SurveyContractError,'SURVEY_STRUCTURE_LIMIT'):subject._copy(huge)

    def test_split_mapping_uses_canonical_values_without_shared_mutable_exposure(self):
        from app.data.readiness_connectivity_witness import FIXED_PROVINCE_SPLITS
        self.assertEqual(subject.SPLITS,FIXED_PROVINCE_SPLITS)
        with self.assertRaises(TypeError):subject.SPLITS['banten']='train'
        self.assertEqual(FIXED_PROVINCE_SPLITS['banten'],'val')

    def test_root_supplied_219_catalog_id_is_accepted_without_invented_baseline(self):
        # Only this supplied string is reused; no operating report/STAC is read.
        identifier='S2A_MSIL2A_20240619T021351_R060_T51MUR_20240619T061603'
        value=copy.deepcopy(self.request)
        self.replace_scene(value,identifier,'2024-06-19T02:13:51Z')
        checked=subject.validate_survey_request(value)
        self.assertEqual(checked.to_dict()['selected_scene']['id'],identifier)
        self.assertEqual(checked.to_dict()['selected_scene']['source_group'],'southeast_sulawesi/'+identifier)
        self.assertNotIn('_N0510_',checked.canonical_json)
        self.assertFalse(checked.provenance_verified);self.assertFalse(checked.execution_supported)
        receipt=copy.deepcopy(self.receipt)
        receipt.update(request_sha256=checked.request_sha256,
            batch_key='bare-survey-'+value['survey_id']+'-'+checked.request_sha256[:12],
            selected_scene=copy.deepcopy(value['selected_scene']))
        receipt['candidate_scl_refs'][0]['scene_id']=identifier
        self.assertFalse(subject.validate_survey_receipt(receipt,value).execution_supported)

    def test_two_complete_id_profiles_support_normal_sensors_and_remain_distinct(self):
        original=self.request['selected_scene']['id'];digests=[]
        for sensor in ('S2A','S2B'):
            for baseline in ('_N0510',''):
                identifier=original.replace('S2A',sensor).replace('_N0510',baseline)
                value=copy.deepcopy(self.request);self.replace_scene(value,identifier)
                checked=subject.validate_survey_request(value)
                self.assertEqual(checked.to_dict()['selected_scene']['id'],identifier)
                digests.append(checked.request_sha256)
        self.assertEqual(len(set(digests)),4)

    def test_catalog_profile_does_not_relax_full_grammar_calendar_or_baseline_tokens(self):
        catalog=self.request['selected_scene']['id'].replace('_N0510','')
        bad=[catalog+'_suffix',catalog+'.SAFE','prefix_'+catalog,catalog[:-1],
             catalog.replace('20240601T000000','20249999T999999'),
             catalog.replace('S2A','S2D'),catalog.replace('R001','R000'),
             catalog.replace('T51MXR','T61MXR'),catalog.replace('T51MXR','T51MIR'),
             catalog.replace('_R001','_N051_R001'),catalog.replace('_R001','_N05100_R001'),
             catalog.replace('_R001','_N_R001'),catalog.replace('_R001','_N0510_N0510_R001'),
             catalog.replace('_R001','_R001_N0510'),catalog.replace('_R001','_R001_R001')]
        for identifier in bad:
            with self.subTest(identifier=identifier):
                self.assert_bad_request(lambda d:self.replace_scene(d,identifier),'SURVEY_SCENE_INVALID')

    def test_catalog_source_group_and_datetime_cannot_be_enriched_or_aliased(self):
        catalog=self.request['selected_scene']['id'].replace('_N0510','')
        value=copy.deepcopy(self.request);self.replace_scene(value,catalog)
        value['selected_scene']['source_group']='southeast_sulawesi/'+self.request['selected_scene']['id']
        with self.assertRaisesRegex(subject.SurveyContractError,'SURVEY_SCENE_INVALID'):
            subject.validate_survey_request(value)
        value=copy.deepcopy(self.request);self.replace_scene(value,catalog,'2024-06-01T00:00:01Z')
        with self.assertRaisesRegex(subject.SurveyContractError,'SURVEY_SCENE_TIME_MISMATCH'):
            subject.validate_survey_request(value)


if __name__ == '__main__':unittest.main()
