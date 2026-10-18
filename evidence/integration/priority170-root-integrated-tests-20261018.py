import unittest
names=['test_targeted_inventory','test_targeted_execution','test_targeted_scene_claims','test_targeted_asset_geometry','test_targeted_bare_plan','test_targeted_collection_hooks','test_targeted_live_guards','test_collect_targeted_bare','test_prepare_priority_candidate164','test_audit_priority_increment165']
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in names)
r=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not r.wasSuccessful())
