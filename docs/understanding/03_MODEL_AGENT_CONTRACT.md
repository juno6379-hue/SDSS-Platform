# 03 여섯 모델의 공통 계약

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-18 04:37:16 KST — 134 최종 관련·독립·Temp 연차 연결·보존 반영 |
| source_commit | 기준 c8ce70a082705fe270806515efbea94a9f4ed07c + 134 작업파일 SHA (미커밋); 실행 gate 변경 없음 |
| evidence_paths | `backend/app/gmais_api.py`; `backend/app/sdss_results.py`; `contracts/upstream/GMAIS-v0.2/README.md`; `evidence/integration/resume-tests-script-20261017.log`; `docs/implementation/25_ml_split_repair_plan.md`; `evidence/integration/ml-split-repair-plan-20261017.json`; `docs/implementation/26_dataset_version_registry_core.md`; `evidence/integration/dataset-versions-tests-20261017.log`; `backend/app/job_inputs.py`; `backend/app/gmais_api.py`; `docs/implementation/27_job_input_resolution.md`; `evidence/integration/job-input-core-tests-20261017.log`; `evidence/integration/job-input-api-tests-20261017.log`; `evidence/integration/job-input-full-tests-20261017.log`; `docs/implementation/28_workflow_input_resolution.md`; `backend/app/gmais_api.py`; `tests/test_gmais_workflow_extension.py`; `evidence/integration/workflow-input-tests-20261017.log`; `evidence/integration/workflow-input-full-tests-20261017.log`; `backend/app/workflow_policy.py`; `docs/implementation/29_workflow_blocking_policy.md`; `evidence/integration/workflow-policy-core-tests-20261017.log`; `evidence/integration/workflow-policy-api-tests-20261017.log`; `evidence/integration/workflow-policy-full-tests-20261017.log`; `backend/app/job_snapshot.py`; `docs/implementation/31_job_input_snapshot_read.md`; `docs/implementation/32_job_snapshot_ui.md`; `evidence/integration/job-snapshot-tests-20261017.log`; `evidence/integration/job-snapshot-full-tests-20261017.log`; `evidence/integration/job-snapshot-ui-build-20261017.log`; `evidence/integration/job-snapshot-live-ui-20261017.json`; `backend/app/dataset_lineage.py`; `docs/implementation/35_dataset_lineage_verification.md`; `evidence/integration/dataset-lineage-tests-20261017.log`; `evidence/integration/dataset-lineage-full-tests-20261017.log`; `evidence/integration/dataset-lineage-synthetic-20261017.json`; `backend/app/dataset_lineage_api.py`; `docs/implementation/36_dataset_lineage_api_plan.md`; `docs/implementation/37_dataset_lineage_ui.md`; `evidence/integration/dataset-lineage-api-independent-tests-20261017.log`; `evidence/integration/dataset-lineage-api-full-tests-20261017.log`; `evidence/integration/dataset-lineage-ui-build-20261017.log`; `evidence/integration/dataset-lineage-api-live-20261017.json`; `backend/app/job_lineage.py`; `backend/app/job_lineage_api.py`; `docs/implementation/38_job_lineage_validation.md`; `docs/implementation/39_job_lineage_ui.md`; `evidence/integration/job-lineage-tests-20261017.log`; `evidence/integration/job-lineage-full-tests-20261017.log`; `evidence/integration/job-lineage-ui-build-20261017.log`; `evidence/integration/job-lineage-live-20261017.json`; `backend/app/workflow_lineage.py`; `backend/app/workflow_lineage_api.py`; `backend/app/lineage_batch.py`; `docs/implementation/40_workflow_lineage_validation.md`; `docs/implementation/41_workflow_lineage_ui.md`; `evidence/integration/workflow-lineage-independent-tests-20261017.log`; `evidence/integration/workflow-lineage-full-tests-20261017.log`; `evidence/integration/workflow-lineage-ui-build-20261017.log`; `evidence/integration/workflow-lineage-live-20261017.json`; `docs/implementation/43_catalog_insight_data_contract.md`; `docs/implementation/42_catalog_insights_navigation.md`; `backend/app/readiness_source_identity_api.py`; `backend/app/main.py`; `tests/test_readiness_source_identity_api.py`; `frontend/src/AgentCenter.tsx`; `frontend/src/ReadinessSourceIdentityDiagnostics.tsx`; `frontend/src/readinessSourceIdentityAdapter.ts`; `frontend/src/readinessSourceIdentityAdapter.test.mjs`; `frontend/src/readiness-source-identity.css`; `docs/implementation/67_readiness_source_identity_api.md`; `docs/implementation/68_readiness_source_identity_ui.md`; `evidence/integration/readiness-source-identity-api-related-20261017.log`; `evidence/integration/readiness-source-identity-api-independent-20261017.log`; `evidence/integration/readiness-source-identity-api-live-20261017.json`; `evidence/integration/readiness-source-identity-api-ui-full-tests-20261017.log`; `evidence/integration/readiness-source-identity-ui-adapter-20261017.log`; `evidence/integration/readiness-source-identity-ui-tests-20261017.log`; `evidence/integration/readiness-source-identity-ui-build-20261017.log`; `evidence/integration/readiness-source-identity-ui-independent-20261017.log`; `evidence/integration/readiness-source-identity-ui-live-20261017.json`; `evidence/integration/readiness-source-identity-ui-console-20261017.json`; `evidence/integration/readiness-source-identity-api-ui-live-integrity-20261017.json`; `backend/app/ml/candidate_qa_comparison.py`; `backend/app/candidate_qa_comparison_api.py`; `tests/test_candidate_qa_comparison.py`; `frontend/src/CandidateQaComparisonDiagnostics.tsx`; `frontend/src/candidateQaComparisonAdapter.ts`; `frontend/src/candidateQaComparisonAdapter.test.mjs`; `frontend/src/candidate-qa-comparison.css`; `docs/implementation/74_candidate_qa_comparison_api.md`; `docs/implementation/75_candidate_qa_comparison_ui.md`; `evidence/integration/candidate-qa-comparison-related-20261017.log`; `evidence/integration/candidate-qa-comparison-independent-20261017.log`; `evidence/integration/candidate-qa-comparison-ui-adapter-20261017.log`; `evidence/integration/candidate-qa-comparison-ui-tests-20261017.log`; `evidence/integration/candidate-qa-comparison-ui-build-20261017.log`; `evidence/integration/candidate-qa-comparison-ui-independent-20261017.log`; `evidence/integration/candidate-qa-comparison-live-http-20261017.json`; `evidence/integration/candidate-qa-comparison-ui-live-20261017.json`; `evidence/integration/candidate-qa-comparison-ui-console-before-fix-20261017.json`; `evidence/integration/candidate-qa-comparison-ui-console-after-fix-20261017.json`; `evidence/integration/candidate-qa-comparison-full-tests-20261017.log`; `evidence/integration/candidate-qa-comparison-live-integrity-20261017.json`; `backend/app/execution_input_binding.py`; `tests/test_execution_input_binding.py`; `docs/implementation/77_execution_input_binding.md`; `evidence/integration/execution-input-binding-related-20261017.log`; `evidence/integration/execution-input-binding-independent-20261017.log`; `evidence/integration/execution-input-binding-live-validation-20261017.json`; `evidence/integration/execution-input-binding-live-replay-20261017.py`; `evidence/integration/execution-input-binding-full-tests-20261017.log`; `evidence/integration/execution-input-binding-live-integrity-20261017.json`; `backend/app/execution_binding_capture.py`; `tests/test_execution_binding_capture.py`; `docs/implementation/78_submission_binding_capture.md`; `evidence/integration/submission-binding-capture-related-20261017.log`; `evidence/integration/submission-binding-capture-independent-20261017.log`; `evidence/integration/submission-binding-capture-compat-before-20261017.json`; `evidence/integration/submission-binding-capture-compat-after-20261017.json`; `evidence/integration/submission-binding-capture-compat-runner-20261017.py`; `evidence/integration/submission-binding-capture-live-legacy-20261017.json`; `evidence/integration/submission-binding-capture-full-tests-20261017.log`; `evidence/integration/submission-binding-capture-live-integrity-20261017.json`; `backend/app/job_execution_binding_capture.py`; `backend/app/job_execution_binding_capture_api.py`; `tests/test_job_execution_binding_capture.py`; `frontend/src/StoredExecutionBindingCapture.tsx`; `frontend/src/storedExecutionBindingCaptureAdapter.ts`; `frontend/src/storedExecutionBindingCaptureAdapter.test.mjs`; `frontend/src/stored-execution-binding-capture.css`; `docs/implementation/79_stored_binding_capture_api.md`; `docs/implementation/80_stored_binding_capture_ui.md`; `evidence/integration/stored-binding-capture-related-20261017.log`; `evidence/integration/stored-binding-capture-live-api-20261017.json`; `evidence/integration/stored-binding-capture-live-ui-20261017.json`; `evidence/integration/stored-binding-capture-ui-adapter-20261017.log`; `evidence/integration/stored-binding-capture-ui-tests-20261017.log`; `evidence/integration/stored-binding-capture-ui-build-20261017.log`; `evidence/integration/job-execution-binding-capture-independent-20261017.log`; `evidence/integration/stored-execution-binding-capture-ui-independent-20261017.log`; `evidence/integration/stored-binding-capture-full-tests-20261017.log`; `evidence/integration/stored-binding-capture-live-integrity-20261017.json`; `backend/app/stored_job_binding_handoff.py`; `tests/test_stored_job_binding_handoff.py`; `docs/implementation/81_stored_job_binding_handoff.md`; `evidence/integration/stored-job-binding-handoff-related-20261017.log`; `evidence/integration/stored-binding-handoff-independent-20261017.log`; `evidence/integration/stored-binding-handoff-live-validation-20261017.json`; `evidence/integration/stored-binding-handoff-live-replay-20261017.py`; `evidence/integration/stored-binding-handoff-full-tests-20261017.log`; `evidence/integration/stored-binding-handoff-live-integrity-20261017.json`; `backend/app/stored_job_binding_handoff_store.py`; `tests/test_stored_job_binding_handoff_store.py`; `docs/implementation/82_stored_job_binding_handoff_store.md`; `evidence/integration/stored-binding-store-adapter-related-20261017.log`; `evidence/integration/stored-binding-store-adapter-independent-20261017.log`; `evidence/integration/stored-binding-store-adapter-live-validation-20261017.json`; `evidence/integration/stored-binding-store-adapter-live-check-20261017.py`; `evidence/integration/stored-binding-store-adapter-full-tests-20261017.log`; `evidence/integration/stored-binding-store-adapter-live-integrity-20261017.json`; `backend/app/stored_current_binding_preflight.py`; `tests/test_stored_current_binding_preflight.py`; `docs/implementation/83_stored_current_binding_preflight.md`; `evidence/integration/stored-current-binding-preflight-related-20261017.log`; `evidence/integration/stored-current-binding-independent-20261017.log`; `evidence/integration/stored-current-binding-live-validation-20261017.json`; `evidence/integration/stored-current-binding-live-check-20261017.py`; `evidence/integration/stored-current-binding-full-tests-20261017.log`; `evidence/integration/stored-current-binding-live-integrity-20261017.json`; `backend/app/stored_current_binding_preflight_api.py`; `tests/test_stored_current_binding_preflight_api.py`; `docs/implementation/84_current_input_preflight_api.md`; `docs/implementation/85_current_input_preflight_ui.md`; `frontend/src/CurrentInputPreflight.tsx`; `frontend/src/currentInputPreflightAdapter.ts`; `frontend/src/currentInputPreflightAdapter.test.mjs`; `frontend/src/current-input-preflight.css`; `evidence/integration/current-input-preflight-api-related-20261017.log`; `evidence/integration/stored-current-binding-api-independent-20261017.log`; `evidence/integration/current-input-preflight-live-api-20261017.json`; `evidence/integration/current-input-preflight-live-ui-20261017.json`; `evidence/integration/current-input-preflight-ui-desktop-20261017.jpg`; `evidence/integration/current-input-preflight-ui-adapter-20261017.log`; `evidence/integration/current-input-preflight-ui-tests-20261017.log`; `evidence/integration/current-input-preflight-ui-independent-20261017.log`; `evidence/integration/current-input-preflight-ui-build-20261017.log`; `evidence/integration/current-input-preflight-full-tests-20261017.log`; `evidence/integration/current-input-preflight-live-integrity-20261017.json`; `backend/app/workflow_node_input_handoff.py`; `tests/test_workflow_node_input_handoff.py`; `docs/implementation/86_workflow_node_input_handoff.md`; `evidence/integration/workflow-node-handoff-related-20261017.log`; `evidence/integration/workflow-node-handoff-independent-20261017.log`; `evidence/integration/workflow-node-handoff-full-tests-20261017.log`; `evidence/integration/workflow-node-handoff-live-integrity-20261017.json`; `evidence/integration/workflow-node-handoff-catalog-observation-20261017.json`; `evidence/integration/workflow-node-handoff-runtime-start-20261017.json`; `evidence/integration/workflow-node-handoff-full-interrupted-before-final-freeze-20261017.log`; `backend/app/workflow_node_input_handoff_api.py`; `tests/test_workflow_node_input_handoff_api.py`; `docs/implementation/87_workflow_node_handoff_api.md`; `docs/implementation/88_workflow_node_handoff_ui.md`; `frontend/src/WorkflowNodeHandoff.tsx`; `frontend/src/workflowNodeHandoffAdapter.ts`; `frontend/src/workflowNodeHandoffAdapter.test.mjs`; `frontend/src/workflow-node-handoff.css`; `frontend/src/GeoQuery.tsx`; `evidence/integration/workflow-node-handoff-canonical-fixture-20261017.json`; `evidence/integration/workflow-node-handoff-api-related-20261017.log`; `evidence/integration/workflow-node-handoff-api-independent-20261017.log`; `evidence/integration/workflow-node-handoff-api-live-api-20261017.json`; `evidence/integration/workflow-node-handoff-api-live-ui-20261017.json`; `evidence/integration/workflow-node-handoff-api-full-tests-20261017.log`; `evidence/integration/workflow-node-handoff-api-live-integrity-20261017.json`; `evidence/integration/workflow-node-handoff-ui-adapter-20261017.log`; `evidence/integration/workflow-node-handoff-ui-tests-20261017.log`; `evidence/integration/workflow-node-handoff-ui-independent-20261017.log`; `evidence/integration/workflow-node-handoff-ui-build-20261017.log`; `evidence/integration/workflow-node-handoff-ui-desktop-20261017.jpg`; `backend/app/workflow_job_request_handoff.py`; `tests/test_workflow_job_request_handoff.py`; `docs/implementation/89_workflow_job_request_handoff.md`; `evidence/integration/full-job-handoff-related-20261017.log`; `evidence/integration/full-job-handoff-independent-20261017.log`; `evidence/integration/full-job-handoff-initial-format-gap-20261017.log`; `evidence/integration/full-job-handoff-full-tests-20261017.log`; `evidence/integration/full-job-handoff-live-integrity-20261017.json`; `evidence/integration/full-job-handoff-catalog-observation-20261017.json`; `evidence/integration/full-job-handoff-runtime-start-20261017.json`; `backend/app/workflow_job_request_handoff_api.py`; `tests/test_workflow_job_request_handoff_api.py`; `docs/implementation/90_full_job_handoff_api.md`; `docs/implementation/91_full_job_handoff_ui.md`; `frontend/src/FullJobHandoff.tsx`; `frontend/src/fullJobHandoffAdapter.ts`; `frontend/src/fullJobHandoffAdapter.test.mjs`; `frontend/src/full-job-handoff.css`; `evidence/integration/full-job-handoff-api-related-20261017.log`; `evidence/integration/full-job-handoff-api-independent-20261017.log`; `evidence/integration/full-job-handoff-api-live-api-20261017.json`; `evidence/integration/full-job-handoff-api-live-ui-20261017.json`; `evidence/integration/full-job-handoff-api-full-tests-20261017.log`; `evidence/integration/full-job-handoff-api-live-integrity-20261017.json`; `evidence/integration/full-job-handoff-ui-adapter-20261017.log`; `evidence/integration/full-job-handoff-ui-tests-20261017.log`; `evidence/integration/full-job-handoff-ui-independent-20261017.log`; `evidence/integration/full-job-handoff-ui-build-20261017.log`; `evidence/integration/full-job-handoff-ui-desktop-20261017.jpg`; `backend/app/schema_formats.py`; `tests/test_schema_formats.py`; `docs/implementation/92_common_datetime_validation.md`; `evidence/integration/common-datetime-related-20261017.log`; `evidence/integration/common-datetime-independent-20261017.log`; `evidence/integration/common-datetime-source-runtime-20261017.json`; `evidence/integration/common-datetime-catalog-observation-20261017.json`; `evidence/integration/common-datetime-next-review-20261017.json`; `evidence/integration/common-datetime-full-tests-20261017.log`; `evidence/integration/common-datetime-live-integrity-20261017.json`; `backend/app/agent_capability_contract.py`; `tests/test_agent_capability_contract.py`; `docs/implementation/93_agent_capability_contract.md`; `evidence/integration/agent-capability-original-gmais-20261017.py`; `evidence/integration/agent-capability-related-20261017.log`; `evidence/integration/agent-capability-independent-20261017.log`; `evidence/integration/agent-capability-source-runtime-20261017.json`; `evidence/integration/agent-capability-next-review-20261017.json`; `evidence/integration/agent-capability-full-tests-20261017.log`; `evidence/integration/agent-capability-live-integrity-20261017.json`; `backend/app/workflow_job_registration_handoff.py`; `tests/test_workflow_job_registration_handoff.py`; `tests/test_workflow_job_registration_handoff_api.py`; `docs/implementation/94_full_job_registration_api.md`; `docs/implementation/95_full_job_registration_ui.md`; `frontend/src/fullJobRegistrationAdapter.ts`; `frontend/src/fullJobRegistrationAdapter.test.mjs`; `evidence/integration/full-job-registration-api-related-20261017.log`; `evidence/integration/full-job-registration-api-independent-20261017.log`; `evidence/integration/full-job-registration-api-live-api-20261017.json`; `evidence/integration/full-job-registration-api-live-ui-20261017.json`; `evidence/integration/full-job-registration-api-full-tests-20261017.log`; `evidence/integration/full-job-registration-api-live-integrity-20261017.json`; `evidence/integration/full-job-registration-api-original-20261017.py`; `evidence/integration/full-job-registration-ui-related-20261017.log`; `evidence/integration/full-job-registration-ui-tests-20261017.log`; `evidence/integration/full-job-registration-ui-independent-20261017.log`; `evidence/integration/full-job-registration-ui-build-20261017.log`; `evidence/integration/full-job-registration-ui-desktop-20261017.png`; `evidence/integration/full-job-registration-ui-blocked-20261017.png`; `backend/app/model_reference_contract.py`; `tests/test_model_reference_contract.py`; `docs/implementation/96_model_reference_contract.md`; `evidence/integration/model-ref-related-20261017.log`; `evidence/integration/model-ref-independent-20261017.log`; `evidence/integration/model-ref-source-runtime-20261017.json`; `evidence/integration/model-ref-full-tests-20261017.log`; `evidence/integration/model-ref-live-integrity-20261017.json`; `evidence/integration/model-ref-next-review-20261017.json`; `evidence/integration/model-ref-original-gmais-20261017.py`; `evidence/integration/model-ref-original-handoff-20261017.py`; `backend/app/experiment_registry.py`; `tests/test_model_version_declaration.py`; `docs/implementation/97_model_version_declaration.md`; `evidence/integration/model-version-related-20261017.log`; `evidence/integration/model-version-independent-20261017.log`; `evidence/integration/model-version-catalog-observation-20261017.json`; `evidence/integration/model-version-original-registry-20261017.py`; `evidence/integration/model-version-initial-tests-20261017.log`; `evidence/integration/model-version-full-tests-20261017.log`; `evidence/integration/model-version-live-integrity-20261017.json`; `evidence/integration/model-version-next-review-20261017.json`; `frontend/src/ModelReview.tsx`; `frontend/src/modelVersionRegistrationAdapter.ts`; `frontend/src/modelVersionRegistrationAdapter.test.mjs`; `frontend/src/model-version-registration.css`; `docs/implementation/98_model_version_registration_api.md`; `docs/implementation/99_model_version_registration_ui.md`; `evidence/integration/model-version-api-related-20261017.log`; `evidence/integration/model-version-api-independent-20261017.log`; `evidence/integration/model-version-api-live-api-20261017.json`; `evidence/integration/model-version-api-live-ui-20261017.json`; `evidence/integration/model-version-api-full-tests-20261017.log`; `evidence/integration/model-version-api-full-tests-corrected-20261017.log`; `evidence/integration/model-version-api-live-integrity-20261017.json`; `evidence/integration/model-version-api-original-main-20261017.py`; `evidence/integration/model-version-api-original-ui-20261017.tsx`; `evidence/integration/model-version-api-next-review-20261017.json`; `evidence/integration/model-version-ui-related-20261017.log`; `evidence/integration/model-version-ui-tests-20261017.log`; `evidence/integration/model-version-ui-independent-20261017.log`; `evidence/integration/model-version-ui-build-20261017.log`; `evidence/integration/model-version-ui-related-layout-20261017.log`; `evidence/integration/model-version-ui-tests-layout-20261017.log`; `evidence/integration/model-version-ui-build-layout-20261017.log`; `evidence/integration/model-version-ui-desktop-final-20261017.png`; `backend/app/model_registration_provenance.py`; `tests/test_model_registration_provenance.py`; `docs/implementation/100_model_registration_provenance_observation.md`; `evidence/integration/model-provenance-focused-20261017.log`; `evidence/integration/model-provenance-related-20261017.log`; `evidence/integration/model-provenance-independent-20261017.log`; `evidence/integration/model-provenance-catalog-observation-20261017.json`; `evidence/integration/model-provenance-live-integrity-20261017.json`; `tests/test_model_registration_provenance_api.py`; `docs/implementation/101_model_registration_provenance_api.md`; `docs/implementation/102_model_registration_provenance_ui.md`; `frontend/src/ModelRegistrationProvenance.tsx`; `frontend/src/modelRegistrationProvenanceAdapter.ts`; `frontend/src/modelRegistrationProvenanceAdapter.test.mjs`; `frontend/src/model-registration-provenance.css`; `evidence/integration/model-provenance-api-focused-20261017.log`; `evidence/integration/model-provenance-api-focused-corrected-20261017.log`; `evidence/integration/model-provenance-api-focused-final-20261017.log`; `evidence/integration/model-provenance-api-related-20261017.log`; `evidence/integration/model-provenance-api-independent-20261017.log`; `evidence/integration/model-provenance-api-live-api-20261017.json`; `evidence/integration/model-provenance-api-live-ui-20261017.json`; `evidence/integration/model-provenance-api-full-tests-20261017.log`; `evidence/integration/model-provenance-api-live-integrity-20261017.json`; `evidence/integration/model-provenance-api-next-review-20261017.json`; `evidence/integration/model-provenance-ui-related-20261017.log`; `evidence/integration/model-provenance-ui-tests-20261017.log`; `evidence/integration/model-provenance-ui-independent-20261017.log`; `evidence/integration/model-provenance-ui-build-20261017.log`; `evidence/integration/model-provenance-ui-desktop-20261017.png`; `backend/app/model_reference_record_comparison.py`; `tests/test_model_reference_record_comparison.py`; `docs/implementation/103_model_reference_record_comparison.md`; `evidence/integration/model-reference-record-focused-20261017.log`; `evidence/integration/model-reference-record-related-20261017.log`; `evidence/integration/model-reference-record-independent-20261017.log`; `evidence/integration/model-reference-record-catalog-observation-20261017.json`; `evidence/integration/model-reference-record-live-integrity-20261017.json`; `backend/app/workflow_job_model_record_handoff.py`; `tests/test_workflow_job_model_record_handoff.py`; `docs/implementation/104_workflow_job_model_record_handoff.md`; `evidence/integration/workflow-model-record-focused-20261017.log`; `evidence/integration/workflow-model-record-related-20261017.log`; `evidence/integration/workflow-model-record-independent-20261017.log`; `evidence/integration/workflow-model-record-catalog-observation-20261017.json`; `evidence/integration/workflow-model-record-live-integrity-20261017.json`; `backend/app/workflow_job_model_record_handoff_api.py`; `tests/test_workflow_job_model_record_handoff_api.py`; `docs/implementation/105_workflow_job_model_record_handoff_api.md`; `docs/implementation/106_workflow_model_record_handoff_ui.md`; `frontend/src/WorkflowModelRecordHandoff.tsx`; `frontend/src/workflowModelRecordHandoffAdapter.ts`; `frontend/src/workflowModelRecordHandoffAdapter.test.mjs`; `frontend/src/workflow-model-record-handoff.css`; `evidence/integration/workflow-model-record-api-focused-20261017.log`; `evidence/integration/workflow-model-record-api-related-20261017.log`; `evidence/integration/workflow-model-record-api-independent-20261017.log`; `evidence/integration/workflow-model-record-api-full-tests-20261017.log`; `evidence/integration/workflow-model-record-api-full-tests-final-20261017.log`; `evidence/integration/workflow-model-record-api-live-api-20261017.json`; `evidence/integration/workflow-model-record-api-live-ui-20261017.json`; `evidence/integration/workflow-model-record-api-live-integrity-20261017.json`; `evidence/integration/workflow-model-record-api-test-compat-baseline-20261017.json`; `evidence/integration/workflow-model-record-api-test-compat-focused-20261017.log`; `evidence/integration/workflow-model-record-api-test-compat-original-20261017.py`; `evidence/integration/workflow-model-record-api-test-compat-result-20261017.json`; `evidence/integration/workflow-model-record-api-next-queue-review-20261017.json`; `evidence/integration/workflow-model-record-ui-related-initial-failure-20261017.log`; `evidence/integration/workflow-model-record-ui-related-20261017.log`; `evidence/integration/workflow-model-record-ui-independent-20261017.log`; `evidence/integration/workflow-model-record-ui-tests-20261017.log`; `evidence/integration/workflow-model-record-ui-build-20261017.log`; `evidence/integration/workflow-model-record-ui-desktop-20261017.png`; `backend/app/workflow_dependency_order.py`; `tests/test_workflow_dependency_order.py`; `docs/implementation/107_workflow_dependency_order.md`; `evidence/integration/workflow-dependency-order-focused-20261017.log`; `evidence/integration/workflow-dependency-order-focused-final-20261017.log`; `evidence/integration/workflow-dependency-order-related-20261017.log`; `evidence/integration/workflow-dependency-order-independent-20261017.log`; `evidence/integration/workflow-dependency-order-independent-review-20261017.json`; `evidence/integration/workflow-dependency-order-full-tests-20261017.log`; `evidence/integration/workflow-dependency-order-live-integrity-20261017.json`; `evidence/integration/workflow-dependency-order-preflight-20261017.json`; `evidence/integration/workflow-dependency-order-original-gmais_api-20261017.py`; `evidence/integration/workflow-dependency-order-original-workflow_lineage-20261017.py`; `evidence/integration/workflow-dependency-order-original-workflow_policy-20261017.py`; `backend/app/data/recovery_commit_contract.py`; `tests/test_recovery_commit_contract.py`; `docs/implementation/109_area_completion_audit.md`; `docs/implementation/110_recovery_commit_contract.md`; `scripts/collect_training_parallel.py`; `backend/app/data/budget.py`; `evidence/integration/recovery-commit-contract-focused-20261017.log`; `evidence/integration/recovery-commit-contract-focused-final-20261017.log`; `evidence/integration/recovery-commit-contract-focused-final2-20261017.log`; `evidence/integration/recovery-commit-contract-related-20261017.log`; `evidence/integration/recovery-commit-contract-related-final-20261017.log`; `evidence/integration/recovery-commit-contract-related-final2-20261017.log`; `evidence/integration/recovery-commit-contract-independent-before-key-guard-20261017.log`; `evidence/integration/recovery-commit-contract-independent-20261017.log`; `evidence/integration/recovery-commit-contract-independent-final3-20261017.log`; `evidence/integration/recovery-commit-contract-preflight-20261017.json`; `evidence/integration/recovery-commit-contract-live-integrity-20261017.json`; `evidence/integration/recovery-commit-contract-external-dependencies-20261017.json`; `backend/app/lcluc_workflow_api.py`; `tests/test_lcluc_workflow_api.py`; `frontend/src/LclucWorkflowPanel.tsx`; `frontend/src/lclucWorkflowAdapter.ts`; `frontend/src/lclucWorkflowClient.ts`; `frontend/src/lcluc-workflow.css`; `frontend/src/ModelAnalysisWorkspace.tsx`; `docs/implementation/116_lcluc_workflow_api.md`; `docs/implementation/117_lcluc_workflow_ui.md`; `evidence/integration/lcluc-workflow-api-focused-final2-20261018.log`; `evidence/integration/lcluc-workflow-api-independent-tests-20261018.log`; `evidence/integration/lcluc-workflow-api-route-preservation-tests-20261018.log`; `evidence/integration/lcluc-workflow-ui-related-final-20261018.log`; `evidence/integration/lcluc-workflow-ui-tests-final-20261018.log`; `evidence/integration/lcluc-workflow-ui-build-final-20261018.log`; `evidence/integration/lcluc-workflow-ui-browser-20261018.json`; `evidence/integration/lcluc-workflow-api-live-integrity-20261018.json`; `evidence/integration/lcluc-workflow-api-live-route-20261018.json`; `evidence/integration/lcluc-workflow-ui-related-final3-20261018.log`; `evidence/integration/lcluc-workflow-ui-tests-final2-20261018.log`; `evidence/integration/lcluc-workflow-ui-build-final2-20261018.log`; `evidence/integration/lcluc-workflow-api-full-tests-20261018.log`; `evidence/integration/lcluc-workflow-api-related-20261018.log`; `evidence/integration/lcluc-workflow-ui-build-final3-20261018.log`; `evidence/integration/lcluc-workflow-ui-synthetic-desktop-final2-20261018.png`; `frontend/src/lclucChangeMapAdapter.ts`; `frontend/src/LclucWorkflowChangeMap.tsx`; `backend/app/lcluc_workflow.py`; `tests/test_lcluc_workflow.py`; `docs/implementation/118_lcluc_workflow_change_map.md`; `evidence/integration/lcluc-change-map-adapter-focused-20261018.log`; `evidence/integration/lcluc-change-map-ui-related-final-20261018.log`; `evidence/integration/lcluc-change-map-generated-fixture-20261018.json`; `evidence/integration/lcluc-change-map-independent-20261018.log`; `evidence/integration/lcluc-change-map-core-focused-20261018.log`; `evidence/integration/lcluc-change-map-core-api-final-20261018.log`; `evidence/integration/lcluc-change-map-nonempty-initial-diagnostic-20261018.log`; `evidence/integration/lcluc-change-map-ui-tests-20261018.log`; `evidence/integration/lcluc-change-map-ui-build-20261018.log`; `evidence/integration/lcluc-change-map-full-backend-20261018.log`; `evidence/integration/lcluc-change-map-live-integrity-20261018.json`; `evidence/integration/lcluc-change-map-browser-20261018.json`; `evidence/integration/lcluc-change-map-nonempty-20261018.png`; `evidence/integration/lcluc-change-map-empty-20261018.png`; `frontend/src/lclucTransitionAdapter.ts`; `frontend/src/LclucTransitionSummary.tsx`; `evidence/integration/lcluc-transition-adapter-focused-final-20261018.log`; `evidence/integration/lcluc-transition-ui-related-20261018.log`; `evidence/integration/lcluc-transition-independent-20261018.log`; `evidence/integration/lcluc-transition-generated-fixture-20261018.json`; `docs/implementation/119_lcluc_transition_matrix.md`; `evidence/integration/lcluc-transition-ui-tests-20261018.log`; `evidence/integration/lcluc-transition-ui-build-20261018.log`; `evidence/integration/lcluc-transition-ui-build-initial-20261018.log`; `evidence/integration/lcluc-transition-browser-20261018.json`; `evidence/integration/lcluc-transition-live-integrity-20261018.json`; `evidence/integration/lcluc-transition-matrix-final-20261018.png`; `evidence/integration/lcluc-transition-class-map-20261018.png`; `backend/app/model_error_analysis_api.py`; `tests/test_model_error_analysis_api.py`; `backend/app/ml/error_analysis.py`; `docs/implementation/120_model_error_analysis_read.md`; `evidence/integration/model-error-analysis-api-focused-final-20261018.log`; `evidence/integration/model-error-analysis-api-related-20261018.log`; `evidence/integration/model-error-read-route-guards-20261018.log`; `frontend/src/ModelErrorAnalysis.tsx`; `frontend/src/modelErrorAnalysisAdapter.ts`; `frontend/src/modelErrorAnalysisClient.ts`; `frontend/src/model-error-analysis.css`; `docs/implementation/121_model_error_analysis_ui.md`; `evidence/integration/model-error-analysis-ui-related-final2-20261018.log`; `evidence/integration/model-error-analysis-ui-tests-final-20261018.log`; `evidence/integration/model-error-analysis-ui-build-final-20261018.log`; `evidence/integration/model-error-read-independent-20261018.json`; `evidence/integration/model-error-read-browser-20261018.json`; `evidence/integration/model-error-read-live-integrity-20261018.json`; `evidence/integration/model-error-read-backend-all-20261018.log`; `backend/app/ml/per_scene_normalization_contract.py`; `tests/test_per_scene_normalization_contract.py`; `backend/app/ml/normalization.py`; `evidence/integration/per-scene-contract-focused-20261018.log`; `evidence/integration/per-scene-contract-existing-boundaries-20261018.log`; `docs/implementation/122_per_scene_normalization_contract.md`; `evidence/integration/per-scene-contract-independent-20261018.json`; `evidence/integration/per-scene-contract-independent-20261018.log`; `evidence/integration/per-scene-contract-runtime-boundary-20261018.json`; `evidence/integration/per-scene-contract-runtime-boundary-20261018.log`; `evidence/integration/per-scene-contract-live-integrity-20261018.json`; `backend/app/ml/per_scene_normalization_files.py`; `tests/test_per_scene_normalization_files.py`; `evidence/integration/per-scene-files-focused-final-20261018.log`; `evidence/integration/per-scene-files-related-20261018.log`; `evidence/integration/per-scene-files-runtime-comparison-20261018.json`; `evidence/integration/per-scene-files-live-integrity-20261018.json`; `docs/implementation/123_per_scene_normalization_files.md`; `evidence/integration/per-scene-files-independent-20261018.json`; `evidence/integration/per-scene-files-independent-20261018.log`; `evidence/integration/per-scene-files-independent-initial-20261018.json`; `evidence/integration/per-scene-files-independent-initial-20261018.log`; `backend/app/ml/model_checkpoint_manifest.py`; `tests/test_model_checkpoint_manifest.py`; `evidence/integration/model-manifest-read-agent-focused-final-20261018.log`; `evidence/integration/model-manifest-read-root-related-20261018.log`; `evidence/integration/model-manifest-read-runtime-20261018.json`; `evidence/integration/model-manifest-read-live-integrity-20261018.json`; `docs/implementation/124_model_checkpoint_manifest.md`; `evidence/integration/model-manifest-read-independent-20261018.json`; `evidence/integration/model-manifest-read-independent-20261018.log`; `evidence/integration/model-manifest-read-agent-focused-20261018.log`; `backend/app/ml/registered_per_scene_files.py`; `tests/test_registered_per_scene_files.py`; `docs/implementation/125_registered_per_scene_files.md`; `backend/app/dataset_registry.py`; `evidence/integration/registry-normalization-agent-focused-20261018.log`; `evidence/integration/registry-normalization-root-related-20261018.log`; `evidence/integration/registry-normalization-runtime-20261018.json`; `evidence/integration/registry-normalization-live-integrity-20261018.json`; `evidence/integration/registry-normalization-independent-20261018.json`; `evidence/integration/registry-normalization-independent-20261018.log`; `backend/app/ml/pinned_scene_normalization.py`; `tests/test_pinned_scene_normalization.py`; `evidence/integration/pinned-scene-agent-20261018-focused.log`; `evidence/integration/pinned-scene-runtime-20261018.json`; `evidence/integration/pinned-scene-operating-inventory-20261018.json`; `docs/implementation/126_pinned_scene_normalization.md`; `evidence/integration/pinned-scene-root-related-20261018.log`; `evidence/integration/pinned-scene-runtime-initial-20261018.log`; `evidence/integration/pinned-scene-live-integrity-20261018.json`; `evidence/integration/pinned-scene-independent-20261018.json`; `evidence/integration/pinned-scene-independent-20261018.log`; `backend/app/ml/pinned_annual_normalization.py`; `tests/test_pinned_annual_normalization.py`; `evidence/integration/annual-normalization-agent-20261018-focused.log`; `evidence/integration/annual-normalization-operating-inventory-20261018.json`; `docs/implementation/127_pinned_annual_normalization.md`; `evidence/integration/annual-normalization-root-related-20261018.log`; `evidence/integration/annual-normalization-runtime-20261018.json`; `evidence/integration/annual-normalization-live-integrity-20261018.json`; `evidence/integration/annual-normalization-independent-20261018.json`; `evidence/integration/annual-normalization-independent-20261018.log`; `backend/app/ml/registry_temporal_normalization.py`; `tests/test_registry_temporal_normalization.py`; `evidence/integration/temporal-normalization-agent-20261018-focused-final.log`; `evidence/integration/temporal-normalization-agent-20261018-focused.log`; `evidence/integration/temporal-normalization-live-integrity-20261018.json`; `evidence/integration/temporal-normalization-operating-inventory-20261018.json`; `docs/implementation/128_registry_temporal_normalization.md`; `evidence/integration/temporal-normalization-root-related-20261018.log`; `evidence/integration/temporal-normalization-runtime-20261018.json`; `evidence/integration/temporal-normalization-independent-20261018.json`; `evidence/integration/temporal-normalization-independent-20261018.log`; `backend/app/ml/registry_raster_grid_normalization.py`; `tests/test_registry_raster_grid_normalization.py`; `evidence/integration/raster-grid-agent-20261018-focused-final.log`; `evidence/integration/raster-grid-agent-20261018-focused.log`; `evidence/integration/raster-grid-live-integrity-20261018.json`; `evidence/integration/raster-grid-operating-inventory-20261018.json`; `docs/implementation/129_registry_raster_grid_normalization.md`; `evidence/integration/raster-grid-root-related-20261018.log`; `evidence/integration/raster-grid-runtime-20261018.json`; `evidence/integration/raster-grid-independent-20261018.json`; `evidence/integration/raster-grid-independent-20261018.log`; `backend/app/ml/registry_spatial_normalization.py`; `tests/test_registry_spatial_normalization.py`; `evidence/integration/registry-spatial-agent-20261018-focused.log`; `evidence/integration/registry-spatial-live-integrity-20261018.json`; `evidence/integration/registry-spatial-operating-inventory-20261018.json`; `docs/implementation/130_registry_spatial_normalization.md`; `evidence/integration/registry-spatial-root-related-20261018.log`; `evidence/integration/registry-spatial-runtime-20261018.json`; `evidence/integration/registry-spatial-independent-20261018.json`; `evidence/integration/registry-spatial-independent-20261018.log`; `backend/app/ml/registered_quality_mask_files.py`; `tests/test_registered_quality_mask_files.py`; `evidence/integration/quality-mask-agent-20261018-focused.log`; `evidence/integration/quality-mask-operating-inventory-20261018.json`; `docs/implementation/131_registered_quality_mask_files.md`; `evidence/integration/quality-mask-agent-20261018-focused-final.log`; `evidence/integration/quality-mask-root-related-20261018.log`; `evidence/integration/quality-mask-runtime-20261018.json`; `evidence/integration/quality-mask-live-integrity-20261018.json`; `evidence/integration/quality-mask-independent-20261018.json`; `evidence/integration/quality-mask-independent-20261018.log`; `backend/app/ml/registered_quality_mask_grid.py`; `tests/test_registered_quality_mask_grid.py`; `docs/implementation/132_registered_quality_mask_grid.md`; `evidence/integration/mask-grid-agent-20261018-focused.log`; `evidence/integration/mask-grid-independent-20261018.json`; `evidence/integration/mask-grid-independent-20261018.log`; `evidence/integration/mask-grid-operating-inventory-20261018.json`; `evidence/integration/mask-grid-root-related-final-20261018.log`; `evidence/integration/mask-grid-root-related-20261018.log`; `evidence/integration/mask-grid-runtime-20261018.json`; `evidence/integration/mask-grid-live-integrity-20261018.json`; `backend/app/ml/registered_binary_mask_values.py`; `tests/test_registered_binary_mask_values.py`; `evidence/integration/binary-mask-agent-20261018-focused.log`; `docs/implementation/133_registered_binary_mask_values.md`; `evidence/integration/binary-mask-root-related-20261018.log`; `evidence/integration/binary-mask-runtime-20261018.json`; `evidence/integration/binary-mask-live-integrity-20261018.json`; `evidence/integration/binary-mask-operating-inventory-20261018.json`; `evidence/integration/binary-mask-independent-20261018.json`; `evidence/integration/binary-mask-independent-20261018.log`; `backend/app/ml/annual_quality_mask_diagnostics.py`; `tests/test_annual_quality_mask_diagnostics.py`; `docs/implementation/134_annual_quality_mask_diagnostics.md`; `evidence/integration/annual-mask-agent-20261018-focused-final.log`; `evidence/integration/annual-mask-agent-20261018-focused.log`; `evidence/integration/annual-mask-root-related-20261018.log`; `evidence/integration/annual-mask-runtime-20261018.json`; `evidence/integration/annual-mask-live-integrity-20261018.json`; `evidence/integration/annual-mask-operating-inventory-20261018.json`; `evidence/integration/annual-mask-independent-20261018.json`; `evidence/integration/annual-mask-independent-20261018.log` |
| confidence | 완료 소스·집중9/관련28/독립7·실제 Temp7시나리오·보존 확인; 연차 진단 연결과 품질/실행 승인 구분 |
| status | TESTED_SYNTHETIC 연차 공간·이진 마스크 관측 결합; 품질·기관·과학·실행 승인 BLOCKED |

> 이번 작성은 읽기와 문서화다. 아래 시험 결과는 2026-10-17 보존 로그의 역사적 기록이며 재실행 결과가 아니다. 상태는 각 범위에 한정한다.

## 1분: 서로 다른 장비의 공통 접수증

기관별 모델은 서로 다른 분석 장비다. 접수증의 지역·기간·자료 버전과 결과표의 작업 ID를 통일하면 장비가 달라도 요청과 결과를 추적할 수 있다. 접수증 시험에 합격했다고 장비의 과학 정확도가 검증되는 것은 아니다.

## 5분: 계약 흐름과 현재 상태

Registry에서 Agent의 capability(기능)와 readiness(준비도)를 조회하고 실제 input ID·version·SHA를 지정하여 Job을 제출한다. Job/Trace/Result의 신원, 모델과 자료 버전이 이어져야 같은 실행의 산출물이라고 말할 수 있다. 같은 요청의 반복은 멱등 키로 중복을 막는다. 동일 키에 다른 요청을 섞으면 충돌로 다룬다.

| Agent | 현재 사실 |
|---|---|
| LCLUC | `lcluc-agent`, `landcover.change_detection`; 코드 경로 존재, 모델 DRAFT·실행 BLOCKED |
| Climate Downscaling | `climate-downscaling-agent`; 외부 실행기 NOT_IMPLEMENTED |
| Net Carbon Footprint | `net-carbon-footprint-agent`; 외부 실행기 NOT_IMPLEMENTED |
| Biodiversity | `biodiversity-agent`; 외부 실행기 NOT_IMPLEMENTED |
| Sea Level & Subsidence | `sea-level-subsidence-agent`; 외부 실행기 NOT_IMPLEMENTED |
| Flood & Drought | `flood-drought-agent`; 외부 실행기 NOT_IMPLEMENTED |

모두 같은 학습형 신경망이라고 가정하지 않는다. 외부 수치·통계·물리 모델은 해당 유형의 보정·검증·배포 절차가 필요하다.

```mermaid
flowchart LR
 A[등록 기능·준비도 조회] --> B[Job Request·멱등 키]
 B --> C[Schema·고정 입력 검사]
 C --> D[현재 BLOCKED Job·Trace]
 D -. 실행기·승인 연결 후 .-> E[Result Manifest]
 E -. 검증 통과 .-> F[SDSS Layer·Report]
```

## 실제 코드·입출력

`backend/app/gmais_api.py:_agent_manifests`, `_validate_job`, `create_router`가 실제 위치다. `GET /v1/agents`, `/v1/agents/{agent_id}/capabilities`, `/readiness`, `POST /v1/agents/{agent_id}/jobs`, `GET /v1/jobs/{job_id}`가 연결된다. 결과는 `/v1/jobs/{job_id}/results`, `/v1/results/{result_id}`다. JSON Schema 원문은 `contracts/upstream/GMAIS-v0.2/schemas/`에 있다.

Result→SDSS는 `backend/app/sdss_results.py:project_result`, `download_snapshot`과 `/v1/results/{result_id}/sdss`, `/assets/{asset_index}` RFC 확장이다. Job/Trace/모델·입력 일치, 독립검증·승인, 자산 SHA를 검사한다. 원격/UNC/경로탈출 자산을 임의 다운로드하지 않는다. 복사된 같은 snapshot을 전달하여 검사 뒤 파일 변경 위험도 다룬다.

## 시험·한계

`TESTED_SYNTHETIC`: 기존 197 PASS 로그의 `test_gmais_api.py`, `test_sdss_results.py`는 malformed schema, 신원 불일치, MOCK/DEVELOPMENT 게시 차단, 자산 변경·경로탈출 차단 등을 포함한다. 이 시험은 운영 Registry에 승인 성공 Result가 생겼다는 증거가 아니다. 과학 성능·외부기관 납품·기관 R&R은 미확인/미완료다. GMAIS v0.2는 내부 제안이며 BIG 승인 표준으로 부르지 않는다.

## 10분 확장·발표·Q&A

5분 흐름 뒤 2분은 잘못된 Job/Result 연결 사례, 2분은 멱등성과 snapshot 해시, 1분은 기관별 납품·독립 검증을 설명한다. 대안인 모델마다 다른 응답은 초기에는 빠르지만 화면·보고서마다 해석이 달라져 공통 계약을 사용했다.

30초: “여섯 분야에 같은 접수·추적·결과 규칙을 적용했습니다. LCLUC는 자료·승인 gate에서 차단되고 외부 다섯 모델은 실행기 연결 전입니다. 계약시험과 과학검증은 따로 보고합니다.”

슬라이드: 공통 접수증 / 기능과 실행 자격 / 결과 신원 / 기관 인수.

Q. 6개 화면이 6개 AI인가? A. 화면·계약 6개와 실행 가능한 승인 모델 수는 다르다.

Q. 다른 파일을 같은 Result로 열면? A. SHA·신원·분류조건이 맞지 않으면 게시를 차단하도록 검사한다.

Q. 다음 Gate는? A. 외부기관의 실제 납품 package·실행기·평가 근거가 들어오면 Agent별 상태와 발표표를 갱신한다.

## 2026-10-17 후속: 고정 Dataset 버전 코어의 계약상 의미

`backend/app/dataset_registry.py:register_version`, `resolve_version`은 Dataset ID·명시적 version·artifact SHA를 묶는 내부 코어다. 원문 GMAIS Dataset schema를 검사하고 manifest를 별도 SHA로 저장한다. 같은 버전의 내용 교체를 막고 조회 시 자산을 재확인한다. 임시 fixture10 PASS는 `TESTED_SYNTHETIC`이며 HTTP/기관 ACL/기존 dataset projection/실자료 등록/Job input resolver 연결은 아직 없다. lineage 버전 형식 검사는 부모 버전이 실제 존재한다는 검증과 다르다.

Q. 이제 모든 Job 입력이 불변 Registry로 연결됐나? A. 아니다. 연결 전 코어 단위이며 LCLUC readiness와 science/deployment 승인을 바꾸지 않는다. 1분은 “자료 버전 접수증”, 5분은 등록·조회·미연결 경계, 10분은 동시성·자산 변조 시험을 설명한다.

### Registry 독립 검토 후 보완

`resolve_version`에 요청 dataset ID/version과 저장 manifest의 ID/version·저장 key를 비교하는 검사를 추가했다. 다른 버전의 유효 manifest가 잘못된 요청의 결과로 해석되는 문제를 막기 위한 수정이다. `tests/test_dataset_registry_versions.py:test_valid_manifest_from_other_version_cannot_replace_requested_identity`가 추가되어 시험 정의는11개다. 앞서 기록한10 PASS는 수정 전 시험 이력이며, 수정 후 `dataset-versions-tests-20261017.log`를 읽어11 PASS/1.335초를 확인했다. 최종 전체 통합 실행 결과는 별도 인계 대기다.

## 최신 후속: Job 제출시점의 입력 무결성 진단 RFC

`resolve_job_inputs(store,input_refs)`가 Dataset 코어의 `resolve_version`을 호출한다. schema·Agent/capability·멱등성 검사를 통과한 새 요청에서 진단하고 Job record의 `input_resolution`, 기존409오류의 `error.details.input_resolution`에 저장한다. 확장은 `greenblue.job-input-resolution.rfc1`/`INTERNAL_REVIEW`이며 원문 JobStatus schema에는 필드를 추가하지 않는다. 기존 BLOCKED409/Location/JobID/Trace와 결과 미생성은 유지한다.

같은 자료ID의 서로 다른 고정version은 T1/T2입력으로 허용하고 동일(id,version)의 다른SHA만 충돌한다. 같은 참조의 다른role 반복도 허용한다. `input_integrity_verified=true`여도 품질/ACL blocker가 있을 수 있어 전체status와blockers를 함께 읽는다. `authorization_verified=false`, `ready_for_execution=false`, `scientific_approval=false`는 유지한다. PUBLIC+VALIDATED도 기관권한·모델성능·배포 승인이 아니다.

동일멱등key·동일본문 재생은 최초 저장진단을 반환한다. `evaluated_at`과 `SUBMISSION_SNAPSHOT_NOT_EXECUTION_AUTHORIZATION` 범위는 제출시점의 기록이며 재생시점의 파일 재인증이 아니다. 실제 executor는 실행직전에 다시 검사해야 한다. 제한자료 경로·URI·manifest와내부예외는 반환하지 않는다. 기관ACL·등록API·실행기·의미적입력검증은 후속이며 Workflow plan의 입력바인딩 해석은 이번범위 밖이다.

관련임시시험은 코어10 PASS/API12 PASS, 최신전체240건 중239 PASS·1 SKIP다. 이전225건224 PASS·1 SKIP와197 PASS는 이력으로 남기며 더하지 않는다. Q. 입력VERIFIED면Job이실행되나? A. 아니다. 제출진단일뿐 기존 실행·과학·승인차단은 그대로다.

## Workflow 노드 진단 RFC와 공통 오류 분류

`gmais_api.py:plan_workflow`가 유효한 각 노드의 `input_bindings`를 기존 입력 진단 코어로 전달한다. 요청 schema는 유지하고 응답 `nodes[].input_resolution`에 `greenblue.workflow-input-resolution.rfc1`/`INTERNAL_REVIEW`, 이번 검사 시각 `evaluated_at`, 범위 `PLAN_REQUEST_SNAPSHOT_NOT_EXECUTION_AUTHORIZATION`을 추가한다.

노드 blocker는 표준 분류를 유지하면서 `detail_code`와 `input_index`로 원인을 좁힌다. 누락/빈 입력은 DATA_MISSING, ACL 미연결은 FORBIDDEN, Registry 장애는 RESOURCE_UNAVAILABLE, 참조·URI 충돌은 SCHEMA_MISMATCH, 나머지 무결성·품질 오류는 DATA_QUALITY로 연결한다. 상세 진단은 제한자료의 경로·URI·원문 manifest·내부 예외를 노출하지 않는다.

정상 입력의 DATA_MISSING 제거는 모델 실행 자격을 뜻하지 않는다. node `execution_authorized=false`, 전역 `can_execute=false`, `execution_started=false`, PLAN_ONLY·BLOCKED를 유지한다. 요청마다 현재 파일을 검사하며 Job의 최초 snapshot 재생과 다르다. 계획 영속 저장·Job/Result/Trace 생성·실자료 카탈로그 쓰기는 하지 않는다. 실제 실행기와 동적 출력→입력 연결은 후속이다.

### Workflow 입력 연결 후 최종 전체시험

`workflow-input-full-tests-20261017.log`를 읽어 `scripts/test.ps1`의247건/139.318초/OK(skipped=1), 즉 **246 PASS·1 SKIP**를 확인했다. SKIP은 기존 실제 OS symlink 생성권한 부족이며 대체 mock 경계시험은 통과했다. 관련 Workflow14 PASS·3.910초는 이 전체시험에 포함된 부분이며 이전240건·225건·197건에 산술 합산하지 않는다. 이해 에이전트가 재실행한 것이 아니라 개발팀의 완료 로그를 읽은 근거다. 이전 전체시험 수치는 개발 이력이고 현재 판정은 이 절이 우선한다.

실제 API 프로세스 재시작·실자료 수집/학습·Job/Result 실행은 하지 않았다. 고정 입력 진단은 PLAN_ONLY·BLOCKED 범위이고 과학·기관·운영 승인 및 실제 DAG 실행 gate는 유지한다.

## Workflow 차단 사유의 계약 확장

계획 응답에 `policy_resolution`과 `nodes[].dependency_resolution`을 추가했다. 내부 확장 `greenblue.workflow-blocking-policy.rfc1`은 자신의 입력/Agent 문제(local), 실제 선행 노드 문제(upstream), FAIL_ALL 정책의 선행이 아닌 다른 노드 문제(policy)를 구분한다. 기존 `node.blockers`와 status는 그대로 둔다. 상세 필드는 [의존성 차단 Gate](gate-notes/GATE_WORKFLOW_POLICY_20261017.md)를 따른다.

STOP_DEPENDENTS는 실제 ancestor의 local blocker만 전달하고, FAIL_ALL은 실제 upstream과 구분해 실제 선행이 아닌 다른 노드의 local blocker를 추가한다. 자기 local 원인은 upstream/policy에 중복하지 않고 diamond 경로도 중복 원인을 만들지 않는다. 원인 없음 진단은 READY가 아니며 모든 실행 허가는 false다. 관련 API20 PASS·코어9 PASS, 최신 전체262건 중261 PASS·1 SKIP는 모의 계약시험 근거다. 실제 정책 실행·취소·재시도나 운영 승인은 아니다.

## 저장된 Job 제출 입력 기록의 companion 조회

새 `GET /v1/jobs/{job_id}/input-resolution`은 원문 Job Status를 바꾸지 않는 별도 읽기 응답이다. `backend/app/job_snapshot.py:project_job_input_snapshot`이 Job/Trace/Agent/요청 input_refs 연결과 저장 진단의 내부 일관성을 검사하고 allowlist 필드만 반환한다. 현재 Registry나 파일을 재검사하지 않고 제출 시점의 기록을 읽는다.

`RECORDED_SNAPSHOT`은 저장 기록, `LEGACY_SNAPSHOT_NOT_RECORDED`는 과거 기록 부재, `SNAPSHOT_INVALID`는 형식·연결 불일치다. 뒤의 둘은 HTTP200/available=false/snapshot=null이고, Job 자체가 없으면 JOB_NOT_FOUND/HTTP404다. legacy를 현재 파일로 재생성하지 않는다. 품질/ACL blocker가 빠진 모순이나 무결성/상태의 불가능한 조합은 invalid로 막는다. 원문 예외·경로·URI·자격정보는 노출하지 않고 current_files_revalidated/execution_authorized/scientific_approval는 false다. 이는 서명 감사나 과학적 사실 인증도 아니다.

관련 임시 시험12 PASS/6.726초, 전체274건 중273 PASS·1 SKIP/70.655초다. 저장기록 성공 경로는 fixture에서만 확인했다. 실제 브라우저는 기존2개 Job의 LEGACY, 없는 ID404, ID변경 시 이전 표시 제거를 확인했고 신규Job/Result/Trace는0이다. 기관ACL·실행직전 재검증·실제executor는 후속이다.

## 고정 부모 참조의 현재 계보 검사 코어

이전 “lineage 부모 존재 검증 후속”의 일부를 내부 읽기 함수 `dataset_lineage.py:verify_dataset_lineage`로 구현했다. root와 전이적 부모의 고정 ID/version/artifact SHA·현재 자산·그래프를 확인한다. Registry 등록이나 Job/Workflow 요청에 자동 연결한 것은 아니며 새 HTTP endpoint도 없다. 해당 호출의 순차 시점 검사이고 그래프 전체의 원자적 snapshot이나 출처 서명 증명이 아니다.

합성공개계보의 통과와 제한계보의 ACL차단을 시험했지만 `authorization_verified`, `execution_authorized`, `scientific_approval`는 false다. 제한노드는 상위조상까지 확장하지 않고 내부경로·URI·예외도 반환하지 않는다. current_assets_revalidated는 resolve시도 여부이며 모든 조상의 무결성 성공이 아니다. 기존API/응답계약을 바꾸지 않아 이 코어 단위의 UI 직접 변경은 없으며 HTTP/실행 연계는 후속이다.

## 현재 계보 검사의 내부 HTTP RFC

새 경로는 `greenblue.dataset-lineage-verification.rfc1`/INTERNAL_REVIEW이며 `present_in_upstream_openapi=false`다. 원문 GMAIS OpenAPI와 Dataset schema를 바꾸지 않는다. 입력은 root_ref의 고정 id/version/artifact SHA와 깊이/노드 한도뿐이다. URI·raw manifest·자격정보를 받지 않고 미지 필드·bool 한도·잘못된 형태는 자료 조회 전에400으로 거부한다.

미등록/불일치/계보 차단은200/BLOCKED의 진단이며, 예측하지 못한 자원 오류나 모순된 코어 응답은503/RESOURCE_UNAVAILABLE로 닫는다. 기존 app token 경계를 상속하지만 공용 token은 기관 자료 권한이 아니다. 제한노드의 더 위 조상·경로·URI·원문예외를 노출하지 않으며 존재/등급 자체의 운영 노출정책은 여전히 후속이다.

요청마다 현재 자산을 다시 검사하고 UTC 시작·종료를 검사구간으로 기록한다. no-store로 과거 성공 캐시를 현재 결과로 재생하지 않는다. 여러 파일의 순차검사이며 원자적 전체snapshot·실행직전 불변성을 보증하지 않는다. current_assets_revalidated는 시도여부, 전체성공은별도진단이며 권한/실행/과학승인false다. Job의 제출당시 기록조회와도 다르다. 계보API11시험·전체298건297 PASS/1SKIP는 코드계약, 실제 성공운영계보 검증은미수행이다.

## Job companion의 두 시점

| 경로 | 읽는 것 | 현재성의 범위 |
|---|---|---|
| `/v1/jobs/{id}/input-resolution` | 제출 당시 저장 snapshot | 현재 자산을 재검사하지 않음 |
| `/v1/jobs/{id}/lineage-validation` | 저장 원 요청의 고정 refs로 현재 전이 계보 | 명시 요청 때 현재 순차검사; 제출 snapshot은 불변 |

새 GET의 내부 확장은 `greenblue.job-lineage-validation.rfc1`, 범위는 `CURRENT_TRANSITIVE_LINEAGE_NOT_SUBMISSION_SNAPSHOT`이다. 원문 Status/schema와 저장Job상태를 바꾸지 않고 no-store·thread pool을 사용한다. 원 요청 없음은 LEGACY_REQUEST_NOT_RECORDED, 손상은 JOB_REQUEST_INVALID, 한도는 CHECK_LIMIT_REACHED, 현재진단은 CURRENT_LINEAGE_CHECKED로 구분한다. 없는Job404와 내부오류503도 구분한다.

available=true는 보고서가 있다는 뜻이며 성공이 아니다. 부분검사·상충SHA는 checked=false/진단없음이어도 차단보고서가 유효할 수 있다. 입력→고유진단 index/root 연결을 확인하고 현재 시도flag·모든binding 판정과 blocker를 함께 읽는다. 같은 자료의 다른 고정version은 허용하고 동일ID/version의 상충SHA는 해시 전 차단한다. 권한·실행·과학승인false, 네트워크·쓰기0이며 현재무결성이맞아도 기존BLOCKED Job을 READY로 바꾸지 않는다.

원문 URI/role/parameters·snapshot·자격정보를 응답에 포함하지 않는다. 제한자료의 상위계보는 기존코어 정책대로 숨기지만 기관ACL·정보노출운영정책·불변snapshot·실제실행 승인은 후속이다.

## Workflow 계획과 현재 전이 계보 companion의 계약

| 경로 | 이번 역할 | 실행과의 경계 |
|---|---|---|
| `/v1/workflows/plan` | 기존 입력·Agent·정책 계획진단 | 기존 응답/실행 gate 유지 |
| `/v1/workflows/lineage-validation` | 전체 Workflow 고정refs의 현재 전이계보 | 공유예산·cache, raw본문신원; 실행요건전체검사아님 |

새확장은greenblue.workflow-lineage-validation.rfc1/INTERNAL_REVIEW/upstream:false, scope는CURRENT_WORKFLOW_TRANSITIVE_LINEAGE_PLAN_ONLY다. schema/DAG오류·NaN/Infinity 등비표준JSON은400, 내부검사불가는503, 자료차단/한도는200보고서이며no-store·thread pool을사용한다. 원문schema/OpenAPI·기존plan응답·Job저장snapshot은변경하지않는다.

request_sha256는서버가실제로받은HTTP본문bytes의SHA다. UI는전송body인JSON.stringify(parsedPayload)를TextEncoderUTF8로해시해비교한다. 키정렬canonical이나textarea의들여쓰기원문hash가아니다. WorkflowID·Trace·이SHA가맞고현재본문/요청세대가같아야표시한다.

개별진단INTEGRITY_VERIFIED·전체lineage_integrity_verified=true도Workflow실행승인이아니다. 항상modePLAN_ONLY/statusBLOCKED·execution_started/can_execute/권한/실행/과학false다. checked/available/시도flag와부분검사를성공으로채우지않는다. 제한원문·URI/path·자격정보·내부예외를반환하지않고기관ACL·운영노출정책·과학/실행승인은후속이다.

## 카탈로그 인사이트의 선택 문맥과 실행 계약 구분

신규인사이트는기존읽기API의명시metadata를사용하며새backend계약이나실행권한을만들지않는다. 전역7개메뉴와별도로카탈로그검색+5개세부목적을두고,명시DatasetID또는유효한선택1개의문맥만전달한다.0개/복수선택에서대표자료를임의추정하지않으며Workspace열기는자동자료주입·호환성판정·Job실행과다르다.

독립자료계약문서43에따라legacy6행과불변버전0행을구분한다. 계보API는완전한고정root_ref가필요하고기존6행에없는version/SHA를생성하지않는다. SEE_COLLECTION_TERMS는이용조건검토지시이며공개다운로드/재배포권한승인이아니다. 기존LCLUC Draft·외부5 interface-only와학습blocker5개·readyfalse도유지한다.

출처/원문자격정보·URI/path를화면/CSV에노출하지않고메타데이터내보내기와원본자산다운로드를구분한다. 모델별입력매핑·공식AOI/기간의미적합성·기관ACL·독립과학/운영승인은후속이다. 이변경은backend수정이없어직전전체321건회귀를다시실행한것처럼보고하지않는다.

## 저장 출처 대조의 명시 읽기 API·UI — 67/68

[저장 진단 API·UI Gate](gate-notes/GATE_SOURCE_IDENTITY_API_UI_20261017.md)는66 저장 보고서의12계수·핀/token SHA·8비승인false만 반환하는 읽기 API와 Agent Center 수동 조회 카드다. POST /v1/diagnostics/readiness-source-identity에 report_sha256·manifest_sha256·token을 명시한다. 원본 경로·행index·token원문·큰JSON을 반환하지 않고8KiB본문·threadpool/process-local 단일worker·429·no-store를 적용한다. HTTP200도BLOCKED이며 저장 관측 조회이지 현재 영상/라벨 재hash·assess·학습 시작이 아니다.

프론트는 명시 버튼만 호출하고 핀/token SHA·정확한 응답키/상태·12계수·8false/교차모순을 검사한다. 입력·Agent/모델/Job선택·Registry/메뉴 변경 때 이전 결과를 지우고 세대/입력key/hash가 맞는 응답만 표시한다. 넓은400연결과 별도28유일선언회원·0patch3·patch25·기존차단5를 분리한다. 기대 숫자를 고정 성공으로 만들지 않는다. singleton≠원본 인증·누출해결·과학승인이다. 완료 빌드와 실제 실행서버/브라우저 검증은 별도이며 최종 근거 뒤 확정한다.

### 67/68 실제 연결·최종 시험 근거

최종 backend 전체는652건 중651 PASS·1 SKIP/258.461초/종료0이다. 기존 Windows symlink 생성권한 제약1개를 건너뛰었고 deterministic 경계 시험은 통과했다. API 관련14 PASS/6.055초·독립14 PASS/4.934초, UI 신규10 PASS/302.8698ms·독립10 PASS/447.0061ms·전체59 PASS/1317.2334ms와 build72modules/16.95초는 각 검증 범위를 구분하며 전체652에 더하지 않는다.

Root 실제 API8002는200·1,065bytes/18.797초·no-store였고 badbool400/틀린핀409/본문초과413은 안전한 오류를 반환했다. GET405는 프레임워크 기본 응답으로 별도다. UI5174의 #/view/24?model=lcluc&tab=evidence에서 명시조회28회원/400넓은연결/28유일선언회원/0patch3/patch25·장면/완전선언1384·저장차단5, 입력clear·409안내·허브 back/forward 이전결과폐기를 확인했다. 모바일 요청390×844에서 client/scroll375/375·수평넘침없음/console error0·viewport복원까지 확인했다. 기존5173/8000/8001의 새 기능 적용 검증으로 확대하지 않는다.

### 67/68 최종 보존·다음 계획

최종 보존은134참조·25기존 계약SHA와 카탈로그14기록(기존 gmais_jobs2개 포함)의 canonical records SHA불변을 확인했다. 이전에 추적한 코드/데이터/프론트 중 바뀐 것은 의도한 main 배선과 AgentCenter 두 파일이며 신규 파일을 포함한 전체 workspace 변경이2개뿐이라는 뜻은 아니다. main은 두 배선 줄을 제외하면 raw baseline과 같았다. 새 source assess·Job·학습·수집/다운로드를 실행하지 않았고 저장5차단·패치628/233/250·원본 분할·모델·예약136,314,880B·환불0을 유지했다. 보존 검사는 원자적 snapshot이나 전체workspace inventory 보장이 아니다.

다음 PLANNED 단위는 원본을 보존하는 신규 Dataset 버전 후보 계획에 기존 split repair plan과 최신 진단 핀을 연결하고 클래스 부족을 명시하는 내부 작업이다. 후보계획일 뿐 발행·원본삭제·분할/gate변경·다운로드·훈련·자료준비완료가 아니다. 이번 저장조회 UI 완성과 전체 ML/프로젝트 완료를 구분한다.

## 원본·후보저장QA의명시비교 — 74/75

[후보QA비교 Gate](gate-notes/GATE_CANDIDATE_QA_COMPARISON_20261017.md)는old/newQA·qaReceipt/stageReceipt 네고정JSON/외부4SHA만읽어최소비교projection/API와LCLUConly수동카드를연결한변경이다.2KiB본문·report16MiB/receipt64KiB·깊이32/finalpins·no-store/process-localworker1을사용하며source/candidate거대manifest/raster/assess/Registry는호출하지않는다.

원본1111/5차단→후보1095/4차단, class7코드빈도3+val209부족1과나지1418/209/1025·기여patch0을함께표시한다. oldphysicalnull NOT_PERSISTED·stage선언1384/1368·후보QA캡처1368은각출처를구분한다. 공유항목후보미관측≠완전누출해소/독립승인이며10false권한을유지한다. 입력/선택/hash/popstate/세대는이전결과를무효화하고표시중단은서버취소가아니다. 실제API/브라우저근거전에는실행서버반영완료로주장하지않는다.

### 74/75최종실제적용·회귀/보존

Root실제API8002는200/2161bytes·no-store로1111→1095/5→4·코드빈도3·bareval209/기여patch각0·oldphysicalnull/선언1384→1368/후보캡처1368·10false를대조했다.409/400/413과GET405프레임워크별도/경로비노출도확인했다. UI5174 LCLUC evidence에서명시조회·입력clear/409·허브왕복/back-forward-back이전결과제거/수동재조회를확인했다. desktop1449×1087에서수평넘침0이며이번모바일실측은없다. 기존5173적용검증으로확대하지않는다.

초기React형제카드중복key로console오류6건과header정렬문제를발견해candidate-qa:namespace/React siblingkey회귀·scopedflex-start로수정했다. 수정후reload/수동조회·경합흐름을재확인했고2026-10-17T08:24:15UTC이후새console오류0이다. 이전6건은별도보존하며수정전UI12/전체71/build17.63초·독립12/804.0825ms와최종13/72/build18.69초·독립13/382.2987ms를시점별구분한다.

최종backend전체는 **761건 중760 PASS·1 SKIP/398.767초/종료0**다. 기존Windows symlink생성권한 제약1개를 건너뛰었고 deterministic경계시험은통과했다. 관련17 PASS/14.400초·독립17 PASS/17.124초와 최종신규UI13 PASS/460.2888ms·독립최종13 PASS/382.2987ms·전체UI72 PASS/1137.5072ms·build75modules/18.69초는범위를분리해backend761에합산하지않는다. 보호141참조·32기존코어SHA와카탈로그14기록canonicalSHA가불변이며이전추적코드/데이터/프론트중의도한main배선/AgentCenter두파일만변경됐다. 신규파일/문서/evidence도있어전체workspace변경2개라는뜻이아니고원자snapshot보장도아니다.

다음76은PLANNED다. 고정후보QA보고서·정책에서분할별나지요구픽셀/기여patch부족을산출하는읽기전용후속데이터요구계약을검토한다. 실제이를충족할새영상/라벨/장면목록은없으며최소추가량만으로준비완료를보장하지않는다. 현재설계대기·미구현이고새수집/학습은없다.

## 실행전달ordered binding 순수대조 — 77

[입력전달binding Gate](gate-notes/GATE_EXECUTION_INPUT_BINDING_20261017.md)는Job/Agent/Trace+orderedbindings 두선언을순수비교하는내부RFCv1이다. id/version/assetSHA/index·optionalrole/manifestSHA를strict대조하고BLOCKED>UNKNOWN>MATCH를사용한다. expectedmanifestpin미기록은supplied추가나row간소급전파로채우지않는다. bindings만canonicalhash하며Jobidentity전체hash아니다.

Registry등록/resolve·제출snapshot·현재lineage를호출하거나복제하지않고12approvalfalse/IO5종0·입력불변이다. 실제legacy2Job의선택선언로컬8replay는UNKNOWN4/BLOCKED4로실제executorcapture/MATCH/실행연결증거가아니다. trustedexpectedadapter·현재resolver/bytes·ACL/READYgate가후속이며URI/AOI/model/params/전체request는scope밖이다. 새API/UI/CLI없는내부pure라직접화면/프론트/브라우저변경검사는없다.

### 77혼합근거·회귀/보존과후속capture계획

Root는readonlySQLite의실제legacyJob2건에서선택선언을읽고로컬replay8관측을만들었다. 각기록은request ref1개·제출snapshot/manifestpin미기록이고expected/supplied모두신뢰된제출/실행capture가아니다. 동일선언과suppliedfakepin추가는UNKNOWN·version/trace변조는BLOCKED로합계UNKNOWN4/BLOCKED4이며실제MATCH/실행연결성공을주장하지않는다. Rootharness의DB읽기와helper의database_calls0을구분한다. 실제executor/Job쓰기·asset/manifestbytes검증·새QA/학습은없다.

최종 전체 scripts/test.ps1은 **789건 중788 PASS·1 SKIP/346.172초/종료0**다. 기존Windows symlink생성권한 제약1개를 건너뛰었고 deterministic경계시험은통과했다. 관련14 PASS/0.037초·독립14 PASS/0.014초, 별도oracle648조합과Root로컬replay8관측은전체789에합산하지않는다. 보호141참조·35기존코어SHA와카탈로그14기록canonicalSHA/기존Job body가불변이고이전snapshot추적code/data/tests/frontend변경은0이다. 신규코드/문서/evidence는있으므로전체workspace변경0/원자snapshot보장이아니다.

다음78은PLANNED다. 기존resolver응답을유지하며같은resolve_version검증pass의record로비공개capture를함께생성하는내부pair/privatepass와새Job에만versioned execution_input_binding_capture확장을저장하는방안을검토한다. legacy/동일멱등replay재조회·역채움/추가Registry조회는하지않고초과/해석실패captureUNAVAILABLE로기존gate를유지하는방향이다. 정확schema/원문연결은78에서검증하며현재코드/route/저장변경은없다.77은실제executor미연결이고MATCH도실행승인이아니다.

## 새Job의선택적samepass binding capture — 78

[제출binding capture Gate](gate-notes/GATE_SUBMISSION_BINDING_CAPTURE_20261017.md)는기존resolver의같은resolve_version반환record에서선택pin을얻어새Job의내부execution_input_binding_capture에같은put으로저장한다. 기존wrapper/HTTP/JobStatus/input_resolution/schema는그대로이고legacy·동일멱등replay는재조회/역채움없다. 새pair/commonprivatepass·purebuilder를분리하며additionalRegistry/자산읽기/DB쓰기0은기존전체resolverIO0이아니다.

전체rows가integritytrue면quality/ACL차단중에도RECORDED가능하지만12approvalfalse/실행미연결이다. 선택오류/import/builder만UNAVAILABLE로격리하고기존unexpectederror/processExit는전파한다. selfcompareMATCH는shape검증이며실제executorsupplied대조아니다. 내부에는선택id/pin/role를저장하되URI/경로/manifest원문을제외하며공개응답/화면변경이없어직접UI/브라우저시험은없다.

### 78합성새capture/실제legacy호환·회귀/보존

새capture의RECORDED/UNAVAILABLE생성은신규16시험·TempStore3사례검증범위다. before/after전체HTTP/기존resolver/JobStatus·capture제외저장Job·resolve각1/put2·멱등추가조회/쓰기없음이deepEqual이었다. 실제API8002의기존legacyJob2건에는status/input-resolution GET총4회200만수행했고기존BLOCKED원문·LEGACY_SNAPSHOT_NOT_RECORDED/availablefalse·capture부재를유지했다. 운영POST/새productioncapture생성·executor연결·새QA/학습은0이다. 실제GET호환을새capture실자료생성성공으로확대하지않는다.

최종 전체 scripts/test.ps1은 **805건 중804 PASS·1 SKIP/327.813초/종료0**다. 기존Windows symlink생성권한 제약1개를 건너뛰었고 deterministic경계시험은통과했다. 관련50 PASS/15.440초(신규16+기존34)·독립신규16 PASS/6.243초·TempStore3호환사례/실제GET4회를전체805에중복합산하지않는다. 종료후보호141참조·36기존코어SHA·카탈로그14기록canonicalSHA/기존Jobbody불변을재확인했다. 이전추적코드/데이터/프론트중의도한job_inputs.py/gmais_api.py두파일만변경됐고신규파일도있으므로전체workspace변경2개/원자snapshot보장은아니다.

다음79는PLANNED다. storedcapture의exact형식/hash/Job-request연결을검사하는safeprojection/API와같은단위의수동UI를검토한다. RECORDED/UNAVAILABLE/LEGACY/INVALID를구분하고raw식별자/manifestpin/URI를노출하지않으며현재Registry/bytes/executor승인을부여하지않는다. RECORDED시각은timezoneaware필수·UNAVAILABLEfallbackNone허용을설계때검증한다. 현재79코드/API/UI는미구현이다.

## 저장capture안전조회API·UI — 79/80완료

[저장binding capture Gate](gate-notes/GATE_STORED_BINDING_CAPTURE_20261017.md)는Job/request/capture형식·선택신원연결·canonical배열hash를대조해26키최소projection/GET /v1/jobs/{job_id}/execution-input-binding을제공한다. RECORDED/UNAVAILABLE/LEGACY/INVALID·nullablecount를구분하고raw식별자/manifestpin/URI/경로/원문을노출하지않는다. 유효Job get1·잘못된literal DB0/INVALID·404/503·no-store/기존인증을유지한다.

12승인+current_files_revalidated/executor_bindings_comparedfalse이며저장내부일치가현재Registry/파일/executor검증은아니다. 실제legacy2/총8GET호환은확인했고RECORDED생성은합성검증이다. 80UI는코드/프론트·실제legacy수동조회를확인했으며나머지상태/강제late/mobile실환경은별도범위다. 운영POST/역채움/새QA학습은없다.

### 79/80실제안전조회·회귀/보존과후속설계

Root실제API8002의기존legacy2와oldstatus/inputresolution·없는404/257자INVALID 총8GET은기존응답/카탈로그보존을확인했다. UI5174표준Job카드에서명시GET·LEGACY/request1/capture·manifestnull의미기록표시·emptydisabled/inputalone결과없음·변경clear/404안전·공백literaldisabled/trim없음·허브back-forward-back Job/결과clear·Agent변경clear·복귀재조회성공을관측했다. desktop1449×1087문서/카드넘침0·consoleerror목록[]이다. 기존5173의적용검증으로확대하지않는다.

RECORDED생성/UNAVAILABLE·INVALID상태·강제late경합은합성검증범위이고실제운영RECORDED/나머지상태렌더·강제late/mobile실환경은이번검사하지않았다. 실제POST/새Job/capture역채움·현재Registry/자산bytes검증·executor비교/새QA·학습은0이다. 저장내부일치와14false·null≠0을유지하고표시중단을서버취소로설명하지않는다.

최종backend전체는 **819건 중818 PASS·1 SKIP/394.315초/종료0**다. 기존Windows symlink생성권한 제약1개를 건너뛰었고 deterministic경계시험은통과했다. backend관련14 PASS/0.594초·독립14 PASS/0.330초와신규UI14 PASS/544.6393ms·독립UI14 PASS/960.7704ms·전체UI86 PASS/1546.3622ms·build78modules/19.77초는범위를분리해backend819에합산하지않는다. 시험후보호141참조·39기존코어SHA와카탈로그14기록canonicalSHA/기존Job body불변을재확인했다. 이전추적code/data/tests/frontend중의도한main.py/AgentCenter.tsx두파일만변경됐고신규파일도있으므로전체workspace변경2개/원자snapshot보장은아니다.

후속은PLANNED다. compare_stored_job_binding_handoff(job, requested_job_id, supplied_envelope) 순수경계로79저장검증을통과한RECORDED expected만77과비교하는방향이다. caller임의expected/Registry역채움없이유효legacy/unavailableUNKNOWN·malformedJob/capture/suppliedBLOCKED·일치도승인false/실제executor미연결을유지한다. 현재후속guard/API/UI는미구현이다.

## 저장expected 기반순수handoff대조 — 81

[저장binding handoff Gate](gate-notes/GATE_STORED_BINDING_HANDOFF_20261017.md)는79projection으로저장Job/capture를검증한뒤RECORDEDexpected만77과비교한다. caller별도expected인자는없고legacy/unavailable도visibleJob/request/suppliedmismatch면BLOCKED·미기록만남으면UNKNOWN이다. malformedstored/supplied우선차단·Registry역채움없음/배열hashscope·15false7IO0을유지한다.

passedJob출처/현재files·실제executorsupplied는검증하지않는다. 실제legacy2기록의local8replay는UNKNOWN4/BLOCKED4이며실제MATCH/실행연결아니다. API/UI/executor/DB경로미연결pure라직접화면/프론트/브라우저변경검사는없고79/80카드의executorfalse를유지한다.

### 81혼합근거·최종회귀/보존과다음adapter

Root는실제저장legacyJob2개의선택선언을읽어supplied를로컬복사/변조한8replay에서UNKNOWN4/BLOCKED4를확인했다. 실제executor전달capture나실자료MATCH는없다. storedJob참조와local suppliedreplay의혼합근거이며guard의7IO0과Rootharness의DB읽기를구분한다. 실제POST/DBJob쓰기·역채움/새QA·학습/executor연결은0이다. caller의passedJoborigin을guard가인증하지않아15flags는모두false다.

최종backend전체는 **832건 중831 PASS·1 SKIP/344.500초/종료0**다. 기존Windows symlink생성권한 제약1개를 건너뛰었고 deterministic경계시험은통과했다. 관련13 PASS/0.057초·독립13 PASS/0.056초와legacy로컬8replay관측을전체832에합산하지않는다. 종료후보호141참조·42기존코어SHA와카탈로그14기록canonicalSHA/원Jobbody불변을재확인했고이전snapshot추적code/data/tests/frontend변경은0이다. 신규코드/문서/evidence가있어전체workspace변경0/원자snapshot보장은아니다.

후속은PLANNED다. configured Store에서유효Jobliteralget1회→81guard를호출하는내부readonlyadapter를검토한다. callerJob/expected인자없음·invalidliteralget0·실행체인미연결·기존Job/Workflow BLOCKED/PLAN_ONLY를유지하는방향이다. store_read_observed는읽기관측이지origin인증아니고stored_job_origin_verifiedfalse는유지한다. Store.get의전체bodyjson.loads가남으므로boundedDBparser/전체RAM하드상한보장은없다. 현재새adapter/API/UI는미구현이다.

## configuredStore get1→81대조 adapter — 82

[Store binding adapter Gate](gate-notes/GATE_STORED_BINDING_STORE_20261017.md)는callerJob/expected를받지않고validliteral에서configuredStore.get1회→81guard를연결한다. invalidget0·lookup네상태/attempted/observed/calls와innercomparison을분리하며malformed반환도OBSERVED/innerBLOCKED다. wrapper15false·inner15false/7IO0과adapterDBget1을구분한다.

get자원오류만safe분류하고programmer/comparison/BaseException은전파한다. Store.get전체JSON파싱/신뢰구성은남아boundedDBparser/RAM·origin인증/실제executor/현재files/TOCTOU보장은없다. 실제readonlylegacy2/local8replay UNKNOWN4/BLOCKED4·missing1/invalid0/get총9는운영MATCH/실행근거아니다. 새공개API/UI/executor미연결내부adapter라직접화면/프론트/브라우저변경검사는없다.


## 83 저장 기준과 현재 직접 입력의 대조

[비실행 preflight Gate](gate-notes/GATE_STORED_CURRENT_BINDING_20261017.md)는 저장 capture의 유효성, 현재 resolver의 integrity·quality/PUBLIC 진단, 저장 대비 현재 선언을 분리한다. caller supplied를 받지 않고 같은 resolver pass의 current capture를 81에 넘긴다. quality/RESTRICTED 차단은 pin MATCH로 덮지 않는다. manifest metadata와 digest만 달라도 저장 pin 대조는 차단된다. legacy는 현재 Registry로 역채우지 않고 UNKNOWN/NOT_RUN이다. 직접 참조만 대상이며 전이 계보·기관/모델/과학 승인·실행기 연결은 없다.


## 84/85 현재 입력 preflight 조회

[통합 Gate](gate-notes/GATE_CURRENT_INPUT_PREFLIGHT_UI_20261017.md)는 저장 capture 조회와 현재 직접 입력 재검증을 구분한다. GET /v1/jobs/{job_id}/input-preflight는 83 exact payload를 검증해 전달한다. 저장·현재 진단·선언 일치가 별개이며 legacy UNKNOWN/null을 0으로 채우지 않는다. quality 차단은 pin MATCH로 해제하지 않는다. UI85의 수동 버튼과 실제 legacy 조회를 확인했다. 현재 positive/busy는 합성 검증이며 실행 승인은 아니다.


## 86 Workflow 선택 노드의 제안 입력 대조

[전달 선언 Gate](gate-notes/GATE_WORKFLOW_NODE_HANDOFF_20261017.md)는 caller-pinned 전체 Workflow에서 선택 노드의 agent/capability/trace와 ordered refs를 제안 metadata와 비교한다. role/URI의 부재와 값도 구분한다. 완성 Job·AOI·output·선행 Result를 만들거나 추정하지 않는다. MATCH는 선언 동등성만이며 DAG·실제 파일·원본 인증·실행 승인은 아니다. 내부 pure 함수로 공개 API/UI는 불변이다.


## 87/88 원문 Workflow 전달 비교 API·UI

[원문 비교 Gate](gate-notes/GATE_WORKFLOW_HANDOFF_API_UI_20261017.md)는 Workflow·제안 metadata 원문 두 개를 strict parse해86과 대조한다. caller canonical pin과 실제 outer raw요청 SHA를 분리한다. 원문2개를 객체로 재구성하지 않아 중복키를 숨기지 않는다. MATCH도 caller동일성일뿐 원본인증·DAG·완성Job·파일·실행 승인은 아니다. UI88의 수동 원문 비교와 실제 로컬 합성 선언 표시를 확인했다. 운영 Workflow 전달·실행은 검증하지 않았다.


## 89 전체 Job 초안의 양식과 입력 대조

[full Job Gate](gate-notes/GATE_FULL_JOB_HANDOFF_20261017.md)는 사용자가 작성한 전체 초안을 원 schema로 확인한 뒤 metadata만 추출해86을한번호출한다. AOI소수·bbox수치순서·날짜지원범위를검사해도실제AOI/output/model/capability/과학/실행승인은아니다. 전체초안hash는관측값이고fullJobpin검증은false다. API/UI미연결로87/88metadata화면과구분한다.


## 90/91 full Job 수동 검사 통로

[full Job API/UI Gate](gate-notes/GATE_FULL_JOB_HANDOFF_API_UI_20261017.md)는89를별도수동POST로연결한다. Workflow는87정수규약,fullJob은strictdecimal/finite/int53을지원한다. outerrawSHA로응답을결속하고Python전체초안hash는관측값으로구분한다. schemaINVALID200BLOCKED와resource503을나누며24false/schemaIO미계측null을보존한다. UI91 수동 접는 child와 실제 합성 초안 시연을 확인했다. 운영 제출·실행은 없다.


## 92 공통 날짜 형식 검사

[공통 날짜 Gate](gate-notes/GATE_COMMON_DATETIME_20261017.md)는공통Job/Workflow validator생성과89wrapper가새detachedfactory를재사용한다. 이전checker/cache/class전역과원schema는바꾸지않는다. 기존제출400·fullJob진단200BLOCKED를유지하며날짜형식과기간순서·과학·실행승인을구분한다. 운영서버적용은source검증과별도다.


## 93 Agent-capability 등록관계 공통화

[등록관계 Gate](gate-notes/GATE_AGENT_CAPABILITY_20261017.md)는선택manifest존재와기존capability목록membership만pure공유한다. Job첫일치/Workflow마지막일치·오류·Store/멱등순서는그대로다. 실제구현·모델·권한·과학승인이나89~91의새검증축은아니며agent_capability_verified=false를유지한다.


## 94/95 fullJob RFC2 선택형 등록관계 관측

[등록관계 API/UI Gate](gate-notes/GATE_FULL_JOB_REGISTRATION_20261017.md)는RFC1/89결과·24false를보존하고exactint contract_version2 opt-in에서로컬명부관계를별도표시한다. innerMATCH때만inmemory관측2회,innerBLOCKED는NOT_RUN0회다. REGISTERED/checked는실능력·readiness·기관/과학/실행승인이아니다. 최종UI13check·966건전체회귀·보존을확인했으며운영capability실지원은미검증이다.


## 96 고정 model_ref 문자 선언

[모델 선언 Gate](gate-notes/GATE_MODEL_REFERENCE_20261017.md)는89문자규칙을pure공유하고GMAIS의원schema/SHA뒤Store전거부를추가한다. 허용입력축소이며동등refactor가아니다. helperNone과명시nullschema거부·생략허용을구분한다. 실제modelversion권위부재로resolverBLOCKED·dataset_version대체/역채움금지·model_verifiedfalse를유지한다.


## 97 내부 등록의 선택 model_version 선언

[버전 메모 Gate](gate-notes/GATE_MODEL_VERSION_DECLARATION_20261017.md)는keyword-only옵션의명시version만기존checkpoint/reportSHA와modelrecordexact5에연결한다. 생략은원rawrecord/응답/put순서동일이고shape/source만으로명시호출생성을인증할수없다. caller선언≠권위/승인·실제resolverBLOCKED이며UI/API옵션은미연결이다.


## 98/99 선택 모델 버전 등록 전달

[등록 API/UI Gate](gate-notes/GATE_MODEL_VERSION_REGISTRATION_UI_20261017.md)는기존route에키존재시에만옵션을원형전달한다. absence는기존호출·null은명시값이며201/422/auth/lock을유지한다. 성공은격리TempStore/mock근거이고운영성공등록은없다. caller메모와권위/승인·부분실패한계를유지한다.


## 100 모델 등록메모 metadata 관측

[출처 진단 Gate](gate-notes/GATE_MODEL_PROVENANCE_20261017.md)는record내선언/부모의부재·형식·충돌·일관미검증을나눈다. exact10의4false는이번진단미검증범위이며기존모델평가값을바꾸거나false로확정하지않는다. shape/source·일관성은권위/실파일인증이아니고실제resolver/API/UI미연결이다.


## 101/102 모델 등록메모 수동 관측 API/UI

[수동 출처관측 Gate](gate-notes/GATE_MODEL_PROVENANCE_API_UI_20261017.md)는기존Store모델get1뒤100exact10을그대로반환한다. 다섯상태200/기존auth404/safe503을나누고4false는이진단범위로표시한다. responseIDwrapper없어client세대는신원인증이아니며실파일/등록권위/과학·실행승인은없다.


## 103 명시 identity와 제공 레코드의 별도 계약

참조는 전체 model_ref가 아닌 exact3 id/version/sha256다. 호출자가 role·URI와 전체 요청을 검증하고 명시 추출해야 한다. None 참조는 형식 오류, None 카드는 RECORD_NOT_PROVIDED이며 실제 조회 부재가 아니다. ID 불일치는100 미호출, 같은 ID는100 정확1회이며 자체 CONSISTENT_UNVERIFIED일 때만 버전·지문을 모두 비교한다. 대표 오류는 버전 우선이다. 고정12키/6상태의 최고 결과도 MATCH_UNVERIFIED다. 다섯 false 축은 진단 미검증 범위이며 기존 모델값 변경이 아니다. 기존89/94 연결과 resolver는 없고 dataset_version 추정도 없다.



## 104 원 검토 보존과 별도 모델 관측

기존89를 원 네 인자로1회 호출하고 반환 객체를 그대로 embed한다. 차단이면 wrapper 추가 참조/후보 접근과103 호출0, MATCH·참조 키 부재면 ABSENT/0, 참조가 있으면 exact3 명시 추출과103 원형 후보 전달1회다. 고정12키/바깥3상태는 흐름이며 OBSERVED가 안쪽 MATCH나 승인을 뜻하지 않는다. None 후보는 미제공이지 DB 미발견이 아니다. 원24false와 바깥5false는 그대로다. 기존 role 문자와 URI 문자열 계약을 유지하며 URI 실체·원격 정책은 검증하지 않는다.



## 105/106 별도 수동 모델 카드 관측 계약

별도 POST는 기존 네 문자열과 선택 model_record_json 문자열만 받는다. 키 생략·문자열 null은 카드 미제공, transport null·공백 JSON은400이다. 기존 RFC1/RFC2는 그대로다. 세 원문 각512KiB·body1MiB이며 record도89 gate 전에 strict 파싱한다. 생산104 1회 뒤 원89 safe 검증과103 추가 재산출1회로 타입·흐름·nested100을 검증한다. 응답 카운터는 생산 범위다. 바깥 OBSERVED와 안쪽 오류/충돌/일치 미검증을 분리하고 다섯 false는 기존 모델값 변경이 아닌 관측 범위로 표시한다.



## 107 의존 순서 공통화의 계약 범위

세 호출자가 이미 검증한 dependency map을 공통 topological_order에 전달한다. schema·중복·없는 간선·자기 의존의 검사는 기존 호출자에 남긴다. 준비된 모든 노드를 계층별 sorted로 처리하는 순서와 기존 오류/응답을 유지한다. 새 API·입력 계약·resolver·동적 predecessor binding·승인은 추가하지 않았다. 다른 노드/전체 Job 관측의 dag_validated=false와 미검증 축도 그대로다.



## 사용자 확인 — 외부5개 실행 자료 미제공·미연결

climate_downscaling·net_carbon_footprint·biodiversity·sea_level_subsidence·flood_drought의 API/SDK/실행 코드는 별도로 준비되지 않았다는 사용자 확인을 반영한다. 현재 미제공·미연결이며 계약/화면 존재를 과학 실행 구현이나 운영 지원으로 표현하지 않는다. 독립 정확도 검증라벨도 미제공이다. 기존약한라벨입력은별도로보존한다. 외부구현/검증은BLOCKED이고내부계약·진단·설명개발은계속한다.



## 116/117 — LCLUC 수동 실행·조회 API와 화면

새 /v1/lcluc/workflows는 LOCAL_LCLUC_WORKFLOW_ONLY 확장이다. scientific_accuracy_validated와 standard_gmais_result는 항상false다. generic GMAIS Job/Result나 외부5개 실행기 연결로 승격하지 않는다. preclaim BLOCKED409는 미저장, claimed RUNNING/FAILED/SUCCEEDED200과 historical GET은 별도 계약이다.


## 118 — 검증된 선택 변화쌍 지도

새 지도는 기존 local receipt/report와 인증 index GET 계약을 소비한다. 새 endpoint나 GMAIS Result를 발행하지 않는다. 같은 trace·실행·checkpoint·변화쌍·unique artifact SHA를 결합해도 출처 기관 권위나 과학 인증을 추가하지 않는다. standard_gmais_result/scientific_accuracy_validated는 false 의미를 유지한다.


## 119 — 전체 래스터 전이행렬·범례·단위

report와 pair의 class_names는 실제9개 원문/순서가 같아야 한다. 같은 이름도 ID로 구분한다. ID별 palette는 표시색일 뿐 새 taxonomy나 과학 검증 claim이 아니다. 기존 receipt·API·standard_gmais_result/scientific_accuracy_validated 의미는 그대로다.


## 120/121 — 고정 모델의 오류분석 읽기

새 읽기 API는 exact3 pins와 exact10 응답의 AVAILABLE/UNAVAILABLE을 구분한다. UNAVAILABLE은analysis null·artifacts[]이며0점이 아니다. fixed index0/1/2 다운로드도 같은 pins를 재검증한다. local 읽기 scope와 scientific_accuracy_validated/standard_gmais_result false를 유지한다.


## 122 — per_scene 정규화 선언 계약

122의5상태는 INVALID/INCOMPLETE/DECLARATION_MISMATCH/OUT_OF_SCOPE/DECLARATIONS_CONSISTENT_UNVERIFIED다. consistent도5개 검증/승인false이며 공개 API나 표준 Result 계약이 아니다. 필수 부재와 명시 null을 나누고 입력 원문 없이 고정 issue field/code만 반환한다.


## 123 — per_scene 세 역할 파일 지문 대조

123 exact12는 BLOCKED/OUT_OF_SCOPE/FILES_MATCHED_UNVERIFIED와3역할 NOT_CHECKED/MATCH/MISMATCH를 구분한다.123 외부 artifact flag만true 가능하고122 내부의5false는 그대로다. 부분 MATCH는 전체 성공이 아니다. 새 공개 API/Result 계약이나 실행 승인은 추가하지 않았다.


### 123의 고정 SHA와124 후속

고정은 caller가 준 세 역할 SHA와 실제 읽은 bytes의 대조다. Registry ID/version/ref·실제 checkpoint identity를 연결한 것은 아니다.124 후속에서 검토할 공백이며 아직 미연결이다. 현재 결과를 실행입력이나 승인으로 자동 전달하지 않는다.


## 124 — 실제 checkpoint manifest와 고정 모델 참조

고정 모델 참조는 Store.models의 원형 version·checkpoint/report SHA·등록 선언과 결합한다. 등록 metadata는 기관 권위 인증이 아니다. checkpoint/report byte flag는 부분true 가능하며 전체BLOCKED일 수 있다. state_dict/권위/과학/실행/Workflow5false를 유지한다. 새 API/표준Result는 없다.


## 125 — 등록3참조와 명시 장면 파일

125의 exact19에서 registry_references_verified는 세metadata의 선언 관측 완료다. 이후 lineage/file이 BLOCKED여도 true로 남을 수 있다. artifact flag는123 전체 성공 뒤true다. 나머지11개 flag는false다. PUBLIC은 reader 소비 정책이며 quality의 모든 상태 관측은 실제 ACL·QA·학습 승인과 다르다.


## 126 — actual 모델과 등록 단일 장면 결합

126 exact20은 model/scene 관측과 확인 이력, aggregatebytes와10개false 축을 나눈다. MODEL_BLOCKED/SCENE_BLOCKED/OUT_OF_SCOPE/PINNED_SCENE_MATCHED_UNVERIFIED를 구분한다. 부분 model/registry flag가true여도 전체 성공이나 실행 승인은 아니다.


## 127 — 요청2~6연도 순차 읽기

127 exact24는 모델/행 관측·시도횟수·단계이력·전체flags를 분리한다. 행은 MATCHED_UNVERIFIED/BLOCKED/NOT_CHECKED다. checked_rows는 성공 수가 아니라 시도 수다. 전체 registry/artifact는 모든 행 성공에서만 계산하고11개 검증/승인flag는false다.


## 128 — 등록시간과 요청 UTC연도 결합

128 exact13은 batch127·시간관측·등록연도flag와 물리취득일/기관/과학/실행false를 분리한다. 모든행/모든시간/파일 성공 뒤에만 전체flag가true다. BLOCKED의 manifest digest는 계산후보일 수 있어 검증완료로 읽지 않는다.127 nested temporalfalse도 원래 범위를 유지한다.


## 129 — 실제 GTiff header와 장면간 격자

129 exact19는128 시간관측을 유지하고 header_observations·header/grid 전체성공flag를 추가한다. BLOCKED에 header가 있어도 전체성공이 아니다. AOI/QA/mask/pixel/state/기관/과학/실행/Workflow는false다. 새 API나 표준Result 계약은 없다.


## 130 — 등록 bbox와 표본화 영상 envelope

130 exact17은129 원형·공간row 관측과 전체bbox 포함flag를 분리한다. 하위header/time true는 공간성공이나 승인으로 승격되지 않는다. AOI/물리coverage/QA/mask/pixel/기관/과학/실행/Workflow9개flag는false다.


## 131 — 등록 품질보고서와 명시 mask 파일

131 exact18은 registry/report-binding/file MATCH 부분이력과 전체status/artifactflag를 나눈다. file NOT_CHECKED는 성공SHA MATCH 미확보이며 IO0이 아니다. report MATCH는 본문binding 성공을 뜻하지 않고 report-bindingtrue도 후속mask bytes 성공과 다르다. 전체3파일 성공 뒤 artifacttrue이며9개 검증/승인축은false다.


## 132 — 실제 영상과 mask header·격자

132 exact20은131 원형과 부분 image/mask header·전체flags를 나눈다. nested131 raster_header_verifiedfalse는bytes범위로 유지한다. 상위header/grid/artifacttrue는131·두header·격자 전체성공 뒤에만 가능하며 QA/mask/pixel/의미/AOI/기관/과학/실행/state/Workflow10false는 그대로다.


## 133 — 명시 이진 마스크 값과 품질 승인 구분

새 exact19 내부 관측의 mask_values_verified=true를 모델 readiness나 실행 계약의 승인으로 승격하지 않는다. 선언 true 뒤 값 검사가 실패하면 counts=null/전체false일 수 있다. nested132의 이전 성공은 원형 이력이다. 외부5개 실행기와 독립 라벨 미확보도 그대로다.


## 134 — 연차 공간·명시 마스크 관측과 등록 지문 연결

새 exact22 관측과 행별 exact5는 내부 계약이다. 앞 행/하위133의 counts가 있어도 연결 실패면 상위 artifact/mask_values/manifest_join은false다. 항상10개 승인 관련false를 유지하며 외부5개 실행기나 기관 표준 계약의 완료로 승격하지 않는다.
