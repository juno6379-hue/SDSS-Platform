"""246: 저장한 합성 STAC bytes만 검증. 운영자료·HTTP·영상을 쓰지 않는다."""
import copy
from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.data import bare_survey_stac_binding as subject
from app.data import bare_label_survey_contract as legacy
import test_bare_label_survey_contract as legacy_fixture


class SurveyStacBindingTests(unittest.TestCase):
    def setUp(self):
        fixture = legacy_fixture.BareLabelSurveyContractTests(); fixture.setUp()
        self.request = copy.deepcopy(fixture.request)
        self.identifier = 'S2A_MSIL2A_20240619T021351_R060_T51MUR_20240619T061603'
        self.product = 'S2A_MSIL2A_20240619T021351_N0510_R060_T51MUR_20240619T061603.SAFE'
        self.request['selected_scene'].update(id=self.identifier, datetime='2024-06-19T02:13:51Z',
            source_group='southeast_sulawesi/'+self.identifier)
        self.href = ('https://sentinel2l2a01.blob.core.windows.net/sentinel2-l2/51/M/UR/2024/06/19/'
                     + self.product + '/GRANULE/L2A_T51MUR_A047000_20240619T021351/IMG_DATA/R20m/'
                     'T51MUR_20240619T021351_SCL_20m.tif')
        self.document = {'type': 'Feature', 'stac_version': '1.0.0', 'id': self.identifier,
            'collection': 'sentinel-2-l2a', 'properties': {'datetime': '2024-06-19T02:13:51.000Z',
                's2:product_uri': self.product, 's2:processing_baseline': '05.10'},
            'assets': {'SCL': {'href': self.href}},
            'links': [{'rel': 'self', 'href': subject.CATALOG+'/collections/sentinel-2-l2a/items/'+self.identifier}]}
        self.selected = {'key': 'SCL', 'source_url': self.href, 'product_uri': self.product}

    def raw(self, document=None):
        return json.dumps(self.document if document is None else document, ensure_ascii=False).encode('utf-8')

    def verify(self, raw=None, request=None, selected=None):
        raw = self.raw() if raw is None else raw
        request = copy.deepcopy(self.request if request is None else request)
        request['selected_scene']['stac_ref']['sha256'] = hashlib.sha256(raw).hexdigest()
        return subject.validate_survey_stac_binding(request, raw, self.selected if selected is None else selected)

    def bad(self, mutate, code=None):
        doc = copy.deepcopy(self.document); mutate(doc)
        with self.assertRaises(subject.SurveyStacBindingError) as caught: self.verify(self.raw(doc))
        if code: self.assertEqual(str(caught.exception), code)
        self.assertRegex(str(caught.exception), r'^SURVEY_STAC_[A-Z0-9_]+$')

    def test_valid_temp_bytes_preserved_and_all_operating_claims_false(self):
        raw = self.raw()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'synthetic-stac.json'; path.write_bytes(raw)
            payload = path.read_bytes()
        checked = self.verify(payload); value = checked.to_dict()
        self.assertEqual(checked.raw_stac_sha256, hashlib.sha256(raw).hexdigest())
        self.assertTrue(value['metadata_consistency_verified'])
        self.assertEqual(value['selected_scene']['id'], self.identifier)
        self.assertEqual(value['raw_stac_datetime'], '2024-06-19T02:13:51.000Z')
        self.assertEqual(value['selected_scene']['datetime'], '2024-06-19T02:13:51Z')
        for key in ('source_authenticity_verified', 'remote_asset_verified', 'raster_header_verified',
                    'quality_eligible', 'independent_ground_truth', 'scientific_accuracy_validated',
                    'execution_supported', 'collection_executed', 'ledger_verified', 'training_ready',
                    'registry_connected', 'target_consumer_connected'):
            self.assertIs(value[key], False)
        with self.assertRaises(FrozenInstanceError): checked.status = 'approved'

    def test_no_io_or_network_and_input_output_aliases_detached(self):
        raw = self.raw(); request = copy.deepcopy(self.request)
        request['selected_scene']['stac_ref']['sha256'] = hashlib.sha256(raw).hexdigest()
        before = copy.deepcopy(request); selected = copy.deepcopy(self.selected)
        with patch('builtins.open', side_effect=AssertionError('I/O forbidden')), \
             patch('pathlib.Path.open', side_effect=AssertionError('I/O forbidden')), \
             patch('socket.socket', side_effect=AssertionError('HTTP forbidden')):
            checked = subject.validate_survey_stac_binding(request, raw, selected)
        self.assertEqual(request, before); self.assertEqual(selected, self.selected)
        request['selected_scene']['id'] = 'mutated'; selected['source_url'] = 'mutated'
        checked.to_dict()['selected_asset']['source_url'] = 'mutated'
        self.assertEqual(checked.to_dict()['selected_asset']['source_url'], self.href)

    def test_existing226_request_output_is_unchanged(self):
        raw = self.raw(); request = copy.deepcopy(self.request)
        request['selected_scene']['stac_ref']['sha256'] = hashlib.sha256(raw).hexdigest()
        old = legacy.validate_survey_request(request)
        bound = subject.validate_survey_stac_binding(request, raw, self.selected)
        self.assertEqual(old.to_dict(), request); self.assertEqual(old.request_sha256, bound.request_sha256)
        self.assertNotIn('_N0510_', bound.to_dict()['selected_scene']['id'])

    def test_baseline_catalog_profile_and_both_official_sentinel_hosts(self):
        for host in subject.ASSET_HOSTS:
            doc = copy.deepcopy(self.document)
            doc['id'] = self.product.removesuffix('.SAFE')
            doc['links'][0]['href'] = subject.CATALOG+'/collections/sentinel-2-l2a/items/'+doc['id']
            doc['assets']['SCL']['href'] = self.href.replace('sentinel2l2a01.blob.core.windows.net', host)
            request = copy.deepcopy(self.request)
            request['selected_scene'].update(id=doc['id'], source_group='southeast_sulawesi/'+doc['id'])
            selected = {**self.selected, 'source_url': doc['assets']['SCL']['href']}
            self.assertEqual(self.verify(self.raw(doc), request, selected).to_dict()['selected_scene']['id'], doc['id'])

    def test_pin_mismatch_rejected_before_parser(self):
        with patch.object(subject, '_document', side_effect=AssertionError('must not parse')), \
             self.assertRaisesRegex(subject.SurveyStacBindingError, 'PIN_MISMATCH'):
            subject.validate_survey_stac_binding(self.request, self.raw(), self.selected)

    def test_raw_fractional_nonzero_is_blocked_without_rounding(self):
        for value in ('2024-06-19T02:13:51.024Z', '2024-06-19T02:13:52Z'):
            self.bad(lambda d: d['properties'].update(datetime=value), 'SURVEY_STAC_TIME_MISMATCH')
        for value in ('2024-02-30T02:13:51Z', '2024-06-19T02:13:51+00:00', '2024-06-19T02:13:51.0000000Z'):
            self.bad(lambda d: d['properties'].update(datetime=value), 'SURVEY_STAC_TIME_INVALID')

    def test_catalog_scene_and_full_product_components_must_match(self):
        for edit in (lambda d: d.update(id=self.identifier+'_alias'),
                     lambda d: d.update(collection='landsat-c2-l2'),
                     lambda d: d.update(type='FeatureCollection'),
                     lambda d: d.update(stac_version='unknown')): self.bad(edit)
        for old, new in [('S2A', 'S2B'), ('R060', 'R061'), ('T51MUR', 'T51MUS'),
                         ('20240619T061603', '20240619T061604')]:
            doc = copy.deepcopy(self.document); product = self.product.replace(old, new)
            doc['properties']['s2:product_uri'] = product
            selected = {**self.selected, 'product_uri': product}
            with self.assertRaisesRegex(subject.SurveyStacBindingError, 'PRODUCT_MISMATCH'):
                self.verify(self.raw(doc), selected=selected)
        self.bad(lambda d: d['properties'].update({'s2:processing_baseline': '04.00'}), 'SURVEY_STAC_PRODUCT_MISMATCH')

    def test_existing_baseline_is_not_aliased_to_other_baseline(self):
        doc = copy.deepcopy(self.document); identifier = self.product.removesuffix('.SAFE').replace('N0510', 'N0400')
        doc['id'] = identifier
        request = copy.deepcopy(self.request); request['selected_scene'].update(id=identifier, source_group='southeast_sulawesi/'+identifier)
        with self.assertRaisesRegex(subject.SurveyStacBindingError, 'PRODUCT_MISMATCH'): self.verify(self.raw(doc), request)

    def test_self_link_exact_and_no_duplicate_aliases(self):
        for edit in (lambda d: d['links'].append(copy.deepcopy(d['links'][0])),
                     lambda d: d['links'].clear(),
                     lambda d: d['links'][0].update(href=d['links'][0]['href']+'?token=secret'),
                     lambda d: d['links'][0].update(href=d['links'][0]['href'].replace('planetarycomputer.microsoft.com', 'evil.invalid'))):
            self.bad(edit, 'SURVEY_STAC_SELF_INVALID')

    def test_source_url_exact_key_product_and_layout(self):
        self.bad(lambda d: d['assets'].update(SCL={'href': self.href+'?sig=secret'}), 'SURVEY_STAC_ASSET_MISMATCH')
        self.bad(lambda d: d['assets'].update(scl=d['assets'].pop('SCL')), 'SURVEY_STAC_ASSET_MISMATCH')
        variants = [self.href.replace('2024/06/19', '2023/06/19'), self.href.replace('R20m', 'R10m'),
                    self.href.replace('_SCL_20m.tif', '_B02_10m.tif'),
                    self.href.replace('L2A_T51MUR', 'L2A_T51MUS'),
                    self.href.replace('A047000_20240619', 'A047000_20240230')]
        for href in variants:
            doc = copy.deepcopy(self.document); doc['assets']['SCL']['href'] = href
            with self.assertRaisesRegex(subject.SurveyStacBindingError, 'LAYOUT_UNSUPPORTED'):
                self.verify(self.raw(doc), selected={**self.selected, 'source_url': href})

    def test_url_aliases_credentials_signed_queries_and_nonofficial_hosts(self):
        variants = [self.href.replace('https:', 'http:'), self.href.replace('https://', 'https://user:pass@'),
                    self.href.replace('.net/', '.net:443/'), self.href.replace('.net/', '.net.evil.invalid/'),
                    self.href.replace('/51/', '/%35%31/'), self.href.replace('/51/', '//51/'),
                    self.href.replace('/51/', '/./51/'), self.href.replace('/51/', '/../51/'),
                    self.href+'?', self.href+'#fragment', self.href+'?sig=secret',
                    self.href.replace('sentinel2l2a01', 'landsateuwest'), self.href+'\n']
        for href in variants:
            doc = copy.deepcopy(self.document); doc['assets']['SCL']['href'] = href
            with self.assertRaises(subject.SurveyStacBindingError) as caught:
                self.verify(self.raw(doc), selected={**self.selected, 'source_url': href})
            self.assertNotIn('secret', str(caught.exception)); self.assertEqual(str(caught.exception), 'SURVEY_STAC_URL_INVALID')

    def test_bytes_size_depth_nodes_and_strict_json(self):
        for raw, code in [(b'x'*(subject.MAX_BYTES+1), 'BYTE_LIMIT'),
                          (b'['*33+b'0'+b']'*33, 'DEPTH_LIMIT'),
                          (b'{"x":[0,0],"x":1}', 'DUPLICATE_KEY'),
                          (b'{"x":NaN}', 'NUMBER_INVALID'), (b'{"x":1e999}', 'NUMBER_INVALID'),
                          (b'{"x":"\\ud800"}', 'UTF8_INVALID'), (b'\xef\xbb\xbf{}', 'UTF8_INVALID'),
                          (b'\xff\xff', 'UTF8_INVALID'), (b'{', 'BYTE_LIMIT')]:
            with self.assertRaisesRegex(subject.SurveyStacBindingError, code): self.verify(raw)
        doc = {'large': [0]*subject.MAX_NODES}
        with self.assertRaisesRegex(subject.SurveyStacBindingError, 'NODE_LIMIT'): self.verify(self.raw(doc))
        for raw in (bytearray(self.raw()), memoryview(self.raw()), '{}'):
            with self.assertRaisesRegex(subject.SurveyStacBindingError, 'BYTE_LIMIT'):
                subject.validate_survey_stac_binding(self.request, raw, self.selected)

    def test_ref_alias_declaration_unknown_fields_and_old_approval_false(self):
        request = copy.deepcopy(self.request)
        request['selected_scene']['stac_ref']['path'] = request['current_manifest_ref']['path'].upper()
        # Keep lexical root valid while exercising case-insensitive alias check.
        request['selected_scene']['stac_ref']['path'] = 'data/SOURCE.JSON'
        with self.assertRaisesRegex(subject.SurveyStacBindingError, 'REFERENCE_ALIAS'): self.verify(request=request)
        for selected in (True, {**self.selected, 'execute': True}, {**self.selected, 'key': 'scl'}):
            with self.assertRaisesRegex(subject.SurveyStacBindingError, 'DECLARATION_INVALID'): self.verify(selected=selected)
        request = copy.deepcopy(self.request); request['execution_supported'] = True
        with self.assertRaisesRegex(subject.SurveyStacBindingError, 'REQUEST_INVALID'): self.verify(request=request)


if __name__ == '__main__': unittest.main()
