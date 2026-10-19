"""실제 임시 GeoTIFF와 고정 launch 감사. 네트워크/수집/Store 없음."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import rasterio
from rasterio.transform import from_origin
from scripts import audit_priority_increment165 as audit


class PriorityIncrement165Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.output = self.root / "first-group-training-esri-v1"
        self.output.mkdir()
        self.launch_path = self.root / "launch.json"
        self.boundary = self.root / "boundary.json"
        self.write(self.boundary, {"features": [{"properties": {"province_id": "east_java"}, "geometry":
            {"type": "Polygon", "coordinates": [[[104,-8],[106,-8],[106,-5],[104,-5],[104,-8]]]}}]})
        self.rows = []
        self.ledger = {"batches": {"old-a": {"status":"pending", "reserved_bytes":68157440},
                                    "old-b": {"status":"pending", "reserved_bytes":68157440}}}
        self.launch = {"manifest_before_rows":0,"old_rows_canonical_sha256":audit.canonical([]),
                       "pending_before":copy.deepcopy(self.ledger["batches"]),"selected_jobs":[]}
        for number in range(2):
            key = "test-job-" + str(number)
            folder = self.output / "sources" / key
            folder.mkdir(parents=True)
            config = {"fixture":number}
            pin = audit.canonical(config)
            job = {"key":key,"province":"east_java","year":2024,"split":"train","config_sha256":pin}
            self.launch["selected_jobs"].append(job)
            report_path = folder / "annual-window-report.json"
            self.write(folder / "config.json", config)
            self.write(report_path,{"scenes":[{"status":"rgb_window_downloaded","label_status":"esri_io_aligned_weak_labels"}]})
            self.write(folder / "window-state.json",{"config_sha256":pin,"http_body_bytes":9})
            self.write(folder / "worker-result.json",{"key":key,"report_path":str(report_path),"charged_bytes":10,
                "cog_charged_bytes":9,"metadata_budget":{"charged_bytes":1},"circuit":None})
            self.ledger["batches"][key] = {"status":"settled","config_sha256":pin,"charged_bytes":10,"report_path":str(report_path)}
            row = {"patch_id":key+"-r0-c0","province":"east_java","year":"2024","split":"train",
                   "quality_status":"quality_eligible","valid_pixel_ratio":1.0,"province_inside_fraction":1.0,
                   "sample_class_coverage":{"8":65536},"patch_sha256":{},"scene_id":"scene-"+str(number),
                   "source_window":{"boundary_path":str(self.boundary),"boundary_sha256":audit.sha(self.boundary.read_bytes())}}
            for role in ("image","label","quality"):
                path = folder / (role+".tif")
                count = 6 if role == "image" else 1
                dtype = "float32" if role == "image" else "uint8"
                values = np.full((count,256,256), 20 if role == "image" else 8 if role == "label" else 1, dtype=dtype)
                with rasterio.open(path,"w",driver="GTiff",count=count,width=256,height=256,dtype=dtype,
                                   crs="EPSG:4326",transform=from_origin(105,-6,.0001,.0001),nodata=0) as dst:
                    dst.write(values)
                row["quality_mask_path" if role == "quality" else role+"_path"] = str(path)
                row["patch_sha256"][role] = audit.sha(path.read_bytes())
            self.rows.append(row)
        self.save()

    @staticmethod
    def write(path,value):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(value),encoding="utf-8")

    def save(self):
        self.write(self.launch_path,self.launch)
        self.write(self.output/"annual-window-report.json",{"scenes":self.rows})
        self.write(self.root/"first-group-training-budget/global-ledger.json",self.ledger)

    def run_audit(self):
        return audit.audit_increment(self.root,self.launch_path,self.boundary)

    def test_actual_native_two_patches_and_all_files_unchanged(self):
        before = {str(p):audit.sha(p.read_bytes()) for p in self.root.rglob("*") if p.is_file()}
        result = self.run_audit()
        self.assertEqual(result["status"],"COMPLETED_NATIVE_CHECKED",result)
        self.assertEqual(result["native_patches_checked"],2)
        self.assertEqual(result["native_eligible_patches"],2)
        self.assertEqual(result["eligible_bare_pixels"],131072)
        self.assertTrue(result["native_validation_complete"])
        self.assertTrue(result["batches"][0]["patches"][0]["maximum_class_fraction_over_90_percent"])
        self.assertEqual(result["pending_reserved_bytes"],136314880)
        self.assertEqual(result["source_or_ledger_writes"],0)
        self.assertFalse(result["learning_ready"])
        self.assertEqual(before,{str(p):audit.sha(p.read_bytes()) for p in self.root.rglob("*") if p.is_file()})

    def test_pending_and_missing_terminal_are_incomplete_no_native(self):
        key = self.launch["selected_jobs"][0]["key"]
        self.ledger["batches"][key]["status"] = "pending"
        self.save()
        with patch.object(audit,"native_patch",side_effect=AssertionError("must not read native")):
            self.assertEqual(self.run_audit()["issue"],"SELECTED_BATCH_NOT_SETTLED")
        self.ledger["batches"][key]["status"]="settled"; self.save()
        (self.output/"sources"/key/"worker-result.json").unlink()
        self.assertEqual(self.run_audit()["issue"],"TERMINAL_OR_REPORT_MISSING")

    def test_old_prefix_pending_and_config_pins_fail_closed(self):
        self.launch["manifest_before_rows"]=1
        self.launch["old_rows_canonical_sha256"]=audit.canonical(self.rows[:1]); self.save()
        self.rows[0]["year"]="2023"; self.save()
        self.assertEqual(self.run_audit()["issue"],"OLD_ROWS_CHANGED")
        self.rows[0]["year"]="2024"; self.ledger["batches"]["old-a"]["reserved_bytes"]-=1;self.save()
        self.assertEqual(self.run_audit()["issue"],"PENDING_CHANGED")
        self.ledger["batches"]["old-a"]["reserved_bytes"]+=1;self.save()
        key=self.launch["selected_jobs"][0]["key"]
        self.write(self.output/"sources"/key/"config.json",{"changed":True})
        self.assertEqual(self.run_audit()["issue"],"CONFIG_PIN_MISMATCH")

    def test_sha_grid_ratio_and_histogram_reject_including_bool(self):
        row=self.rows[0]
        original=copy.deepcopy(row)
        for field,value,code in [("valid_pixel_ratio",True,"PATCH_RATIO_MISMATCH"),
                                 ("sample_class_coverage",{"8":65535},"CLASS_HISTOGRAM_MISMATCH")]:
            row[field]=value;self.save();self.assertEqual(self.run_audit()["issue"],code)
            row.clear();row.update(copy.deepcopy(original))
        row["patch_sha256"]["label"]="0"*64;self.save()
        self.assertEqual(self.run_audit()["issue"],"PATCH_SHA_MISMATCH")
        row.clear();row.update(copy.deepcopy(original))
        with rasterio.open(row["quality_mask_path"],"r+") as dst:
            dst.transform=from_origin(105.1,-6,.0001,.0001)
        row["patch_sha256"]["quality"]=audit.sha(Path(row["quality_mask_path"]).read_bytes());self.save()
        self.assertEqual(self.run_audit()["issue"],"PATCH_GRID_MISMATCH")

    def test_nonfinite_pixels_and_nonbinary_support_do_not_pass(self):
        row=self.rows[0]
        with rasterio.open(row["image_path"],"r+") as dst:
            values=dst.read();values[0,0,0]=np.nan;dst.write(values)
        row["patch_sha256"]["image"]=audit.sha(Path(row["image_path"]).read_bytes());self.save()
        self.assertEqual(self.run_audit()["issue"],"MASK_SUPPORT_MISMATCH")
        with rasterio.open(row["quality_mask_path"],"r+") as dst:
            values=dst.read();values[0,0,0]=255;dst.write(values)
        row["patch_sha256"]["quality"]=audit.sha(Path(row["quality_mask_path"]).read_bytes());self.save()
        self.assertEqual(self.run_audit()["issue"],"MASK_NONBINARY")

    def test_settled_zero_patch_and_scene_failure_not_success(self):
        self.rows=[];self.save()
        key=self.launch["selected_jobs"][0]["key"]
        report=self.output/"sources"/key/"annual-window-report.json"
        self.write(report,{"scenes":[{"status":"failed","error":{"category":"fixture"}}]})
        result=self.run_audit()
        self.assertEqual(result["status"],"COMPLETED_ZERO_PATCHES")
        self.assertEqual(result["batches"][0]["scene_failure_count"],1)
        self.assertEqual(result["batches"][0]["data_outcome"],"ZERO_PATCHES")
        self.assertEqual(result["native_eligible_patches"],0)

    def test_worker_error_and_scene_error_are_separate(self):
        key=self.launch["selected_jobs"][0]["key"]
        path=self.output/"sources"/key/"worker-result.json"
        worker=json.loads(path.read_text());worker["error"]={"category":"fixture"};self.write(path,worker)
        self.write(path.parent/"annual-window-report.json",{"scenes":[{"status":"failed"}]})
        result=self.run_audit()
        self.assertEqual(result["status"],"COMPLETED_WITH_SOURCE_FAILURES")
        self.assertTrue(result["batches"][0]["worker_error"])
        self.assertEqual(result["batches"][0]["scene_failure_count"],1)

    def test_selected_file_recheck_detects_change_and_paths_never_fetch(self):
        original=audit.native_patch
        changed=False
        def mutate(root,row,geometry,checked):
            nonlocal changed
            result=original(root,row,geometry,checked)
            if not changed:
                Path(row["label_path"]).write_bytes(b"changed-after-read")
                changed=True
            return result
        with patch.object(audit,"native_patch",side_effect=mutate):
            self.assertEqual(self.run_audit()["issue"],"SELECTED_FILE_CHANGED_DURING_AUDIT")
        self.rows[0]["image_path"]="https://invalid.example/not-accessed";self.save()
        self.assertEqual(self.run_audit()["issue"],"PATH_INVALID")

    def test_stored_and_effective_config_pin_scopes_remain_distinct(self):
        job=self.launch["selected_jobs"][0];folder=self.output/"sources"/job["key"]
        config={"years":[2024],"season_start":"05-01","season_end":"08-31"}
        expected=copy.deepcopy(config);expected["periods"]={"2024":{"start_date":"2024-05-01","end_date":"2024-08-31"}}
        self.assertEqual(audit.effective_config(config),expected)
        self.assertNotIn("periods",config)
        job["config_sha256"]=audit.canonical(config)
        self.ledger["batches"][job["key"]]["config_sha256"]=job["config_sha256"]
        self.write(folder/"config.json",config)
        self.write(folder/"window-state.json",{"config_sha256":audit.canonical(expected),"http_body_bytes":9})
        self.save()
        result=self.run_audit();self.assertEqual(result["status"],"COMPLETED_NATIVE_CHECKED",result)
        self.assertNotEqual(result["batches"][0]["stored_config_sha256"],result["batches"][0]["effective_config_sha256"])
        self.write(folder/"window-state.json",{"config_sha256":audit.canonical(config),"http_body_bytes":9})
        self.assertEqual(self.run_audit()["issue"],"EFFECTIVE_CONFIG_PIN_MISMATCH")

    def test_malformed_worker_error_is_fixed_blocked_before_native(self):
        key=self.launch["selected_jobs"][0]["key"]
        path=self.output/"sources"/key/"worker-result.json"
        original=json.loads(path.read_text(encoding="utf-8"))
        for bad in ("untrusted error string",None,False,[],1):
            worker=copy.deepcopy(original);worker["error"]=bad;self.write(path,worker)
            with patch.object(audit,"native_patch",side_effect=AssertionError("must block before native")):
                result=self.run_audit()
            self.assertEqual(result["status"],"INTEGRITY_BLOCKED")
            self.assertEqual(result["issue"],"WORKER_ERROR_SHAPE")
            self.assertEqual(result["native_patches_checked"],0)

    def test_strict_json_and_bound(self):
        self.launch_path.write_text('{"selected_jobs":[],"selected_jobs":[]}',encoding="utf-8")
        self.assertEqual(self.run_audit()["issue"],"DUPLICATE_JSON_KEY")
        self.launch_path.write_bytes(b"x"*((1<<20)+1))
        self.assertEqual(self.run_audit()["issue"],"FILE_LIMIT")


if __name__ == "__main__":
    unittest.main()
