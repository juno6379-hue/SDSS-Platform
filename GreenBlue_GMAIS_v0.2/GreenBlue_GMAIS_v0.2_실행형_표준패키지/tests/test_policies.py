import unittest
from reference_adapter.policies import allowed_transition,validate_update,acyclic
class TestPolicies(unittest.TestCase):
 def test_state_machine_cannot_revive_terminal_job(self):
  self.assertTrue(allowed_transition('CREATED','VALIDATING'))
  self.assertFalse(allowed_transition('SUCCEEDED','RUNNING'))
  self.assertFalse(allowed_transition('BLOCKED','QUEUED'))
 def test_model_type_update_methods(self):
  self.assertTrue(validate_update('trainable_ml','RETRAINING','holdout-v1')[0])
  self.assertFalse(validate_update('calibrated_physical','RETRAINING','obs-v1')[0])
  self.assertTrue(validate_update('calibrated_physical','RECALIBRATION','independent-obs-v1')[0])
  self.assertFalse(validate_update('external_service','RECALIBRATION','provider-v1')[0])
 def test_independent_validation_and_approval_gate(self):
  self.assertEqual(validate_update('trainable_ml','RETRAINING',None)[1],'NO_INDEPENDENT_VALIDATION')
  self.assertEqual(validate_update('trainable_ml','RETRAINING','holdout',deployment=True)[1],'UNAPPROVED_DEPLOYMENT')
 def test_dag_cycle_and_unknown_dependency(self):
  self.assertTrue(acyclic([{'node_id':'a','depends_on':[]},{'node_id':'b','depends_on':['a']}]))
  self.assertFalse(acyclic([{'node_id':'a','depends_on':['b']},{'node_id':'b','depends_on':['a']}]))
  self.assertFalse(acyclic([{'node_id':'a','depends_on':['missing']}]))
if __name__=='__main__':unittest.main()
