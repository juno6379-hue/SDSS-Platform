"""Reusable GMAIS gate policies: proposed, not yet approved by consortium."""
STATUS_ORDER={'DRAFT','VALIDATED','APPROVED','DEPLOYED','RETIRED'}
UPDATE_ALLOWED={
 'trainable_ml': {'RETRAINING','CONFIG_UPDATE'},
 'calibrated_physical': {'RECALIBRATION','CONFIG_UPDATE'},
 'statistical': {'RETRAINING','CONFIG_UPDATE'},
 'inference_only': {'CONFIG_UPDATE','EXTERNAL_RELEASE'},
 'external_service': {'EXTERNAL_RELEASE','CONFIG_UPDATE'}
}
TRANSITIONS={
 'CREATED':{'VALIDATING','CANCELLED'},
 'VALIDATING':{'BLOCKED','QUEUED','FAILED','CANCELLED'},
 'QUEUED':{'RUNNING','FAILED','CANCELLED'},
 'RUNNING':{'SUCCEEDED','FAILED','CANCELLED'},
 'BLOCKED':set(),'SUCCEEDED':set(),'FAILED':set(),'CANCELLED':set()
}
def allowed_transition(old,new):return new in TRANSITIONS.get(old,set())
def validate_update(model_type, update_type, independent_test_ref, approval_ref=None, deployment=False):
 if update_type not in UPDATE_ALLOWED.get(model_type,set()):return False,'WRONG_UPDATE_METHOD'
 if not independent_test_ref:return False,'NO_INDEPENDENT_VALIDATION'
 if deployment and not approval_ref:return False,'UNAPPROVED_DEPLOYMENT'
 return True,'OK'
def acyclic(nodes):
 graph={x['node_id']:set(x.get('depends_on',[])) for x in nodes}
 if any(n not in graph for deps in graph.values() for n in deps):return False
 visited=set();visiting=set()
 def visit(n):
  if n in visiting:return False
  if n in visited:return True
  visiting.add(n)
  for p in graph[n]:
   if not visit(p):return False
  visiting.remove(n);visited.add(n);return True
 return all(visit(n) for n in graph)
