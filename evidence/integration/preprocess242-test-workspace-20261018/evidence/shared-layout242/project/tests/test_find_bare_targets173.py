"""Real tiny local GTiff discovery; no HTTP, image selection, or authorization."""
import hashlib,json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import copy
import types
from unittest.mock import patch
import numpy as np
import rasterio
from rasterio.transform import from_origin
from scripts import find_bare_targets173 as subject


class BareTargets173Tests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.data=self.root/'data';self.data.mkdir()
        self.source=self.data/'source.json';self.boundary=self.data/'boundary.geojson'
        self.geo={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'province_id':p},'geometry':{'type':'Polygon','coordinates':[[[-1,-1],[1,-1],[1,1],[-1,1],[-1,-1]]]}} for p in subject.SPLITS]}
        self.boundary.write_text(json.dumps(self.geo),encoding='utf8')
        self.crop=self.data/'label.tif';self.make_crop(self.crop,256)
        self.rows=[self.row(self.crop)]

    def digest(self,path):return hashlib.sha256(path.read_bytes()).hexdigest()

    def make_crop(self,path,bare,width=256):
        values=np.ones((256,width),dtype='uint8');values.reshape(-1)[:bare]=8
        with rasterio.open(path,'w',driver='GTiff',width=width,height=256,count=1,dtype='uint8',crs='EPSG:3857',transform=from_origin(0,2560,10,10)) as ds:ds.write(values,1)

    def row(self,path,province='banten',year=2020):
        url=f'https://example.invalid/lc{year}/51N_{year}0101-{year+1}0101.tif'
        return {'province':province,'year':year,'label_year':year,'label_source':'esri_io','label_source_url':url,'quality_status':'quality_insufficient','source_window':{'raw_source_crops':{'raw-esri_io.tif':{'path':str(path),'sha256':self.digest(path),'source':url}}}}

    def scan(self,limits=None,**options):
        self.source.write_text(json.dumps({'scenes':self.rows}),encoding='utf8')
        return subject.discover(self.root,self.source,self.digest(self.source),self.boundary,self.digest(self.boundary),limits=limits,**options)

    def test_native_threshold_and_false_approval(self):
        result=self.scan();self.assertEqual(result['qualified_dense_inside_windows'],1)
        candidate=result['ranked_windows'][0]
        self.assertEqual(candidate['declared_weak_label_bare_pixels'],256)
        self.assertEqual(candidate['local_window_xy'],[0,0])
        self.assertFalse(candidate['execution_supported']);self.assertFalse(candidate['actual_quality_eligible'])
        self.assertFalse(result['ready_for_training'])

    def test_below_threshold_is_not_dense(self):
        self.make_crop(self.crop,255);self.rows=[self.row(self.crop)]
        self.assertEqual(self.scan()['qualified_dense_inside_windows'],0)

    def test_year_mismatch_rejected(self):
        self.rows[0]['label_year']=2021
        with self.assertRaises(ValueError):self.scan()

    def test_stale_crop_pin_rejected(self):
        self.make_crop(self.crop,65536)
        with self.assertRaises(ValueError):self.scan()

    def test_duplicate_sha_window_excluded(self):
        other=self.data/'copy.tif';other.write_bytes(self.crop.read_bytes())
        self.rows.append(self.row(other))
        result=self.scan();self.assertEqual(result['qualified_dense_inside_windows'],1)
        self.assertEqual(result['duplicate_sha_windows_excluded'],1)

    def test_byte_and_window_caps_rejected(self):
        limits={**subject.LIMITS,'max_total_bytes':1}
        with self.assertRaises(ValueError):self.scan(limits)
        self.make_crop(self.crop,65536,width=512);self.rows=[self.row(self.crop)]
        with self.assertRaises(ValueError):self.scan({**subject.LIMITS,'max_windows':1})

    def test_inside_fraction_filters_and_missing_boundary_rejects(self):
        self.geo['features']=[{**f,'geometry':{'type':'Polygon','coordinates':[[[20,20],[21,20],[21,21],[20,21],[20,20]]]}} for f in self.geo['features']]
        self.boundary.write_text(json.dumps(self.geo),encoding='utf8')
        self.assertEqual(self.scan()['qualified_dense_inside_windows'],0)
        self.geo['features'].pop();self.boundary.write_text(json.dumps(self.geo),encoding='utf8')
        with self.assertRaises(ValueError):self.scan()

    def test_priority_gap_then_density_and_train_unconnected(self):
        dense=self.data/'dense.tif';self.make_crop(dense,65536)
        self.rows=[self.row(dense,'south_sulawesi'),self.row(self.crop,'banten')]
        # South Sulawesi's plan cell is already at28; Banten remains empty.
        self.rows += [{**self.row(dense,'south_sulawesi'),'quality_status':'quality_eligible'} for _ in range(28)]
        result=self.scan();self.assertEqual(result['ranked_windows'][0]['province'],'banten')
        train=next(r for r in result['ranked_windows'] if r['province']=='south_sulawesi')
        self.assertEqual(train['consumer_scope'],'PLANNED_CONSUMER_NOT_CONNECTED')

    def test_local_files_unchanged(self):
        # Collector's aggregate uses exact four-digit year strings.
        self.rows[0]['year']='2020'
        pins={p:self.digest(p) for p in (self.crop,self.boundary)}
        result=self.scan()
        self.assertEqual(result['network_requests'],0)
        self.assertEqual(pins,{p:self.digest(p) for p in pins})
        self.assertEqual(list(self.data.glob('*.aux.xml')),[])

    def test186_offset_finds_split_bare_patch_default_unchanged(self):
        values=np.ones((256,512),dtype='uint8');values[:4,206:306]=8
        with rasterio.open(self.crop,'w',driver='GTiff',width=512,height=256,count=1,dtype='uint8',crs='EPSG:3857',transform=from_origin(0,2560,10,10)) as ds:ds.write(values,1)
        self.rows=[self.row(self.crop,'west_java')]
        baseline=self.scan();self.assertEqual(baseline['qualified_dense_inside_windows'],0)
        self.assertEqual(baseline['windows_scanned'],2);self.assertNotIn('window_stride',baseline)
        shifted=self.scan(window_stride=128,provinces=['west_java'])
        self.assertEqual(shifted['windows_scanned'],3);self.assertEqual(shifted['qualified_dense_inside_windows'],1)
        self.assertEqual(shifted['ranked_windows'][0]['local_window_xy'],[128,0])
        self.assertEqual(shifted['ranked_windows'][0]['declared_weak_label_bare_pixels'],400)
        self.assertEqual(shifted['window_stride'],128);self.assertEqual(shifted['province_filter'],['west_java'])
        self.assertEqual(shifted['ranked_windows'][0]['consumer_scope'],'SIX_PROVINCE_175_176_REVALIDATION_REQUIRED')
        self.assertFalse(shifted['actual_quality_eligible']);self.assertEqual(shifted['network_requests'],0)

    def test186_filter_scope_invalid_stride_and_caps(self):
        other=self.data/'other.tif';self.make_crop(other,65536)
        self.rows=[self.row(self.crop,'gorontalo'),self.row(other,'west_java')]
        out=self.scan(window_stride=128,provinces=['gorontalo'])
        self.assertEqual(out['local_label_crops_read'],1);self.assertTrue(all(c['province']=='gorontalo' for c in out['ranked_windows']))
        for stride in (True,64,0,512,128.0):
            with self.assertRaises(ValueError):self.scan(window_stride=stride)
        for scope in ([],['x'],['gorontalo','gorontalo'],'gorontalo'):
            with self.assertRaises(ValueError):self.scan(provinces=scope)
        self.make_crop(self.crop,65536,width=512);self.rows=[self.row(self.crop)]
        with self.assertRaises(ValueError):self.scan({**subject.LIMITS,'max_windows':2},window_stride=128)

    def test186_offset_duplicate_sha_window_still_excluded(self):
        other=self.data/'copy.tif';other.write_bytes(self.crop.read_bytes());self.rows.append(self.row(other))
        out=self.scan(window_stride=128)
        self.assertEqual(out['qualified_dense_inside_windows'],1);self.assertEqual(out['duplicate_sha_windows_excluded'],1)

    def label_ref(self,path):
        return {'path':path.relative_to(self.root).as_posix(),'sha256':self.digest(path)}

    def test214_omitted_and_explicit_none_match_pinned_legacy_complete_output(self):
        baseline=subject.ROOT/'evidence/integration/bare214-before-source-20261018.py'
        raw_bytes=baseline.read_bytes()
        self.assertEqual(hashlib.sha256(raw_bytes).hexdigest(),'a8524dc457fd2945fe4845b69757af3b6ba2dd32be5248383175dca1fed964e0')
        raw=raw_bytes.decode('utf-8')
        legacy=types.ModuleType('legacy173_before214');legacy.__file__=subject.__file__
        exec(compile(raw,subject.__file__,'exec'),legacy.__dict__)
        self.source.write_text(json.dumps({'scenes':self.rows}),encoding='utf8')
        args=(self.root,self.source,self.digest(self.source),self.boundary,self.digest(self.boundary))
        for options in ({},{'window_stride':128,'provinces':['banten']}):
            old=legacy.discover(*args,**options)
            self.assertEqual(subject.discover(*args,**options),old)
            self.assertEqual(subject.discover(*args,label_refs=None,**options),old)
            self.assertNotIn('label_ref_filter',old)

    def test214_only_selected_crop_is_read_and_unselected_bad_bytes_are_ignored(self):
        other=self.data/'other.tif';self.make_crop(other,65536)
        self.rows.append(self.row(other))
        selected=self.label_ref(self.crop);other.write_bytes(b'unselected nonraster bytes')
        with patch.object(subject,'pin',wraps=subject.pin) as read:
            result=self.scan(label_refs=[selected])
        self.assertEqual(result['local_label_crops_read'],1)
        self.assertEqual(result['available_label_crops_in_province_scope'],2)
        self.assertEqual(result['label_crops_excluded_by_filter'],1)
        self.assertEqual(result['label_ref_filter'],[selected])
        self.assertEqual(result['label_filter_scope'],'ONLY_SELECTED_MANIFEST_LABEL_REFS')
        self.assertEqual(result['province_filter'],['banten'])
        self.assertEqual(result['requested_province_filter'],list(subject.SPLITS))
        self.assertFalse(any(call.args[1]==other for call in read.call_args_list))
        self.assertEqual(result['network_requests'],0);self.assertFalse(result['execution_supported'])

    def test214_entire_manifest_coverage_is_preserved_while_one_crop_is_scanned(self):
        other=self.data/'other.tif';self.make_crop(other,65536)
        self.rows[0]['quality_status']='quality_eligible'
        self.rows.extend([{**self.row(other),'quality_status':'quality_eligible'} for _ in range(27)])
        result=self.scan(label_refs=[self.label_ref(self.crop)])
        self.assertEqual(result['source_row_count'],28)
        self.assertEqual(result['ranked_windows'][0]['cell_eligible_at_snapshot'],28)
        self.assertEqual(result['ranked_windows'][0]['cell_deficit_to_28'],0)
        self.assertEqual(result['local_label_crops_read'],1)

    def test214_invalid_shape_duplicate_and_path_fail_before_any_pin_reads(self):
        ref=self.label_ref(self.crop)
        variants=[[],{},True,'x',[ref]*257,[ref,copy.deepcopy(ref)],
            [{'path':ref['path'],'sha256':True}], [{'path':ref['path'],'sha256':'A'*64}],
            [{**ref,'extra':0}],[{'path':'../outside.tif','sha256':ref['sha256']}],
            [{'path':str(self.crop),'sha256':ref['sha256']}],
            [ref,{'path':ref['path'].replace('/','\\'),'sha256':ref['sha256']}]]
        for value in variants:
            with self.subTest(value=value),patch.object(subject,'pin',side_effect=AssertionError('No file reads')) as read:
                with self.assertRaises(ValueError):self.scan(label_refs=value)
            read.assert_not_called()

    def test214_missing_ref_sha_mismatch_and_province_conflict_fail_before_raster_pin(self):
        missing=self.data/'missing-from-manifest.tif';self.make_crop(missing,65536)
        ref=self.label_ref(self.crop)
        variants=[([self.label_ref(missing)],{}),([{**ref,'sha256':'0'*64}],{}),
                  ([ref],{'provinces':['west_java']})]
        for refs,options in variants:
            with self.subTest(refs=refs,options=options),patch.object(subject,'pin',wraps=subject.pin) as read:
                with self.assertRaises(ValueError):self.scan(label_refs=refs,**options)
            self.assertFalse(any(call.args[1] in (self.crop,missing) for call in read.call_args_list))

    def test214_selected_actual_bytes_change_is_still_rejected(self):
        ref=self.label_ref(self.crop);self.make_crop(self.crop,65536)
        with self.assertRaises(ValueError):self.scan(label_refs=[ref])

    def test214_selected_file_byte_window_caps_and128_stride_remain_effective(self):
        other=self.data/'other.tif';self.make_crop(other,65536);self.rows.append(self.row(other))
        result=self.scan({**subject.LIMITS,'max_files':1},label_refs=[self.label_ref(self.crop)])
        self.assertEqual(result['local_label_crops_read'],1)
        with self.assertRaises(ValueError):self.scan({**subject.LIMITS,'max_files':1})
        with self.assertRaises(ValueError):self.scan({**subject.LIMITS,'max_total_bytes':1},label_refs=[self.label_ref(self.crop)])
        self.make_crop(self.crop,65536,width=512);self.rows=[self.row(self.crop)]
        ref=self.label_ref(self.crop)
        with self.assertRaises(ValueError):self.scan({**subject.LIMITS,'max_windows':2},label_refs=[ref],window_stride=128)
        out=self.scan(label_refs=[ref],window_stride=128)
        self.assertEqual(out['windows_scanned'],3)

    def test214_filter_does_not_override_year_lineage_or_mutate_inputs(self):
        refs=[self.label_ref(self.crop)];original=copy.deepcopy(refs)
        pins={p:p.read_bytes() for p in (self.crop,self.boundary)}
        self.scan(label_refs=refs)
        self.assertEqual(refs,original);self.assertEqual(pins,{p:p.read_bytes() for p in pins})
        self.rows[0]['label_year']=2021
        with self.assertRaises(ValueError):self.scan(label_refs=refs)


if __name__=='__main__':unittest.main()
