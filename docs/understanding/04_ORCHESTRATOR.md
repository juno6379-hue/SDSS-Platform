# 04 Orchestrator: 순서를 계획하는 지휘자

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-18 01:52:34 KST — 119 최종 프론트·build·실제 브라우저·보존 근거 반영 |
| source_commit | 기준 984666cac6529f6034fab84171461dbf7c51f8b6 + 119 작업파일 SHA (미커밋); 운영 승인과 별도 |
| evidence_paths | `backend/app/gmais_api.py`; `frontend/src/GeoQuery.tsx`; `tests/test_gmais_workflow_extension.py`; `evidence/integration/resume-tests-script-20261017.log`; `backend/app/job_inputs.py`; `backend/app/gmais_api.py`; `docs/implementation/27_job_input_resolution.md`; `evidence/integration/job-input-core-tests-20261017.log`; `evidence/integration/job-input-api-tests-20261017.log`; `evidence/integration/job-input-full-tests-20261017.log`; `docs/implementation/28_workflow_input_resolution.md`; `backend/app/gmais_api.py`; `tests/test_gmais_workflow_extension.py`; `evidence/integration/workflow-input-tests-20261017.log`; `evidence/integration/workflow-input-full-tests-20261017.log`; `backend/app/workflow_policy.py`; `docs/implementation/29_workflow_blocking_policy.md`; `evidence/integration/workflow-policy-core-tests-20261017.log`; `evidence/integration/workflow-policy-api-tests-20261017.log`; `evidence/integration/workflow-policy-full-tests-20261017.log`; `backend/app/workflow_lineage.py`; `backend/app/workflow_lineage_api.py`; `backend/app/lineage_batch.py`; `docs/implementation/40_workflow_lineage_validation.md`; `docs/implementation/41_workflow_lineage_ui.md`; `evidence/integration/workflow-lineage-independent-tests-20261017.log`; `evidence/integration/workflow-lineage-full-tests-20261017.log`; `evidence/integration/workflow-lineage-ui-build-20261017.log`; `evidence/integration/workflow-lineage-live-20261017.json`; `backend/app/execution_input_binding.py`; `tests/test_execution_input_binding.py`; `docs/implementation/77_execution_input_binding.md`; `evidence/integration/execution-input-binding-related-20261017.log`; `evidence/integration/execution-input-binding-independent-20261017.log`; `evidence/integration/execution-input-binding-live-validation-20261017.json`; `evidence/integration/execution-input-binding-live-replay-20261017.py`; `evidence/integration/execution-input-binding-full-tests-20261017.log`; `evidence/integration/execution-input-binding-live-integrity-20261017.json`; `backend/app/execution_binding_capture.py`; `tests/test_execution_binding_capture.py`; `docs/implementation/78_submission_binding_capture.md`; `evidence/integration/submission-binding-capture-related-20261017.log`; `evidence/integration/submission-binding-capture-independent-20261017.log`; `evidence/integration/submission-binding-capture-compat-before-20261017.json`; `evidence/integration/submission-binding-capture-compat-after-20261017.json`; `evidence/integration/submission-binding-capture-compat-runner-20261017.py`; `evidence/integration/submission-binding-capture-live-legacy-20261017.json`; `evidence/integration/submission-binding-capture-full-tests-20261017.log`; `evidence/integration/submission-binding-capture-live-integrity-20261017.json`; `backend/app/job_execution_binding_capture.py`; `backend/app/job_execution_binding_capture_api.py`; `tests/test_job_execution_binding_capture.py`; `frontend/src/StoredExecutionBindingCapture.tsx`; `frontend/src/storedExecutionBindingCaptureAdapter.ts`; `frontend/src/storedExecutionBindingCaptureAdapter.test.mjs`; `frontend/src/stored-execution-binding-capture.css`; `frontend/src/AgentCenter.tsx`; `docs/implementation/79_stored_binding_capture_api.md`; `docs/implementation/80_stored_binding_capture_ui.md`; `evidence/integration/stored-binding-capture-related-20261017.log`; `evidence/integration/stored-binding-capture-live-api-20261017.json`; `evidence/integration/stored-binding-capture-live-ui-20261017.json`; `evidence/integration/stored-binding-capture-ui-adapter-20261017.log`; `evidence/integration/stored-binding-capture-ui-tests-20261017.log`; `evidence/integration/stored-binding-capture-ui-build-20261017.log`; `evidence/integration/job-execution-binding-capture-independent-20261017.log`; `evidence/integration/stored-execution-binding-capture-ui-independent-20261017.log`; `backend/app/main.py`; `evidence/integration/stored-binding-capture-full-tests-20261017.log`; `evidence/integration/stored-binding-capture-live-integrity-20261017.json`; `backend/app/stored_job_binding_handoff.py`; `tests/test_stored_job_binding_handoff.py`; `docs/implementation/81_stored_job_binding_handoff.md`; `evidence/integration/stored-job-binding-handoff-related-20261017.log`; `evidence/integration/stored-binding-handoff-independent-20261017.log`; `evidence/integration/stored-binding-handoff-live-validation-20261017.json`; `evidence/integration/stored-binding-handoff-live-replay-20261017.py`; `evidence/integration/stored-binding-handoff-full-tests-20261017.log`; `evidence/integration/stored-binding-handoff-live-integrity-20261017.json`; `backend/app/stored_job_binding_handoff_store.py`; `tests/test_stored_job_binding_handoff_store.py`; `docs/implementation/82_stored_job_binding_handoff_store.md`; `evidence/integration/stored-binding-store-adapter-related-20261017.log`; `evidence/integration/stored-binding-store-adapter-independent-20261017.log`; `evidence/integration/stored-binding-store-adapter-live-validation-20261017.json`; `evidence/integration/stored-binding-store-adapter-live-check-20261017.py`; `evidence/integration/stored-binding-store-adapter-full-tests-20261017.log`; `evidence/integration/stored-binding-store-adapter-live-integrity-20261017.json`; `backend/app/stored_current_binding_preflight.py`; `tests/test_stored_current_binding_preflight.py`; `docs/implementation/83_stored_current_binding_preflight.md`; `evidence/integration/stored-current-binding-preflight-related-20261017.log`; `evidence/integration/stored-current-binding-independent-20261017.log`; `evidence/integration/stored-current-binding-live-validation-20261017.json`; `evidence/integration/stored-current-binding-live-check-20261017.py`; `evidence/integration/stored-current-binding-full-tests-20261017.log`; `evidence/integration/stored-current-binding-live-integrity-20261017.json`; `backend/app/stored_current_binding_preflight_api.py`; `tests/test_stored_current_binding_preflight_api.py`; `docs/implementation/84_current_input_preflight_api.md`; `docs/implementation/85_current_input_preflight_ui.md`; `frontend/src/CurrentInputPreflight.tsx`; `frontend/src/currentInputPreflightAdapter.ts`; `frontend/src/currentInputPreflightAdapter.test.mjs`; `frontend/src/current-input-preflight.css`; `evidence/integration/current-input-preflight-api-related-20261017.log`; `evidence/integration/stored-current-binding-api-independent-20261017.log`; `evidence/integration/current-input-preflight-live-api-20261017.json`; `evidence/integration/current-input-preflight-live-ui-20261017.json`; `evidence/integration/current-input-preflight-ui-desktop-20261017.jpg`; `evidence/integration/current-input-preflight-ui-adapter-20261017.log`; `evidence/integration/current-input-preflight-ui-tests-20261017.log`; `evidence/integration/current-input-preflight-ui-independent-20261017.log`; `evidence/integration/current-input-preflight-ui-build-20261017.log`; `evidence/integration/current-input-preflight-full-tests-20261017.log`; `evidence/integration/current-input-preflight-live-integrity-20261017.json`; `backend/app/workflow_node_input_handoff.py`; `tests/test_workflow_node_input_handoff.py`; `docs/implementation/86_workflow_node_input_handoff.md`; `evidence/integration/workflow-node-handoff-related-20261017.log`; `evidence/integration/workflow-node-handoff-independent-20261017.log`; `evidence/integration/workflow-node-handoff-full-tests-20261017.log`; `evidence/integration/workflow-node-handoff-live-integrity-20261017.json`; `evidence/integration/workflow-node-handoff-catalog-observation-20261017.json`; `evidence/integration/workflow-node-handoff-runtime-start-20261017.json`; `evidence/integration/workflow-node-handoff-full-interrupted-before-final-freeze-20261017.log`; `backend/app/workflow_node_input_handoff_api.py`; `tests/test_workflow_node_input_handoff_api.py`; `docs/implementation/87_workflow_node_handoff_api.md`; `docs/implementation/88_workflow_node_handoff_ui.md`; `frontend/src/WorkflowNodeHandoff.tsx`; `frontend/src/workflowNodeHandoffAdapter.ts`; `frontend/src/workflowNodeHandoffAdapter.test.mjs`; `frontend/src/workflow-node-handoff.css`; `evidence/integration/workflow-node-handoff-canonical-fixture-20261017.json`; `evidence/integration/workflow-node-handoff-api-related-20261017.log`; `evidence/integration/workflow-node-handoff-api-independent-20261017.log`; `evidence/integration/workflow-node-handoff-api-live-api-20261017.json`; `evidence/integration/workflow-node-handoff-api-live-ui-20261017.json`; `evidence/integration/workflow-node-handoff-api-full-tests-20261017.log`; `evidence/integration/workflow-node-handoff-api-live-integrity-20261017.json`; `evidence/integration/workflow-node-handoff-ui-adapter-20261017.log`; `evidence/integration/workflow-node-handoff-ui-tests-20261017.log`; `evidence/integration/workflow-node-handoff-ui-independent-20261017.log`; `evidence/integration/workflow-node-handoff-ui-build-20261017.log`; `evidence/integration/workflow-node-handoff-ui-desktop-20261017.jpg`; `backend/app/workflow_job_request_handoff.py`; `tests/test_workflow_job_request_handoff.py`; `docs/implementation/89_workflow_job_request_handoff.md`; `evidence/integration/full-job-handoff-related-20261017.log`; `evidence/integration/full-job-handoff-independent-20261017.log`; `evidence/integration/full-job-handoff-initial-format-gap-20261017.log`; `evidence/integration/full-job-handoff-full-tests-20261017.log`; `evidence/integration/full-job-handoff-live-integrity-20261017.json`; `evidence/integration/full-job-handoff-catalog-observation-20261017.json`; `evidence/integration/full-job-handoff-runtime-start-20261017.json`; `backend/app/workflow_job_request_handoff_api.py`; `tests/test_workflow_job_request_handoff_api.py`; `docs/implementation/90_full_job_handoff_api.md`; `docs/implementation/91_full_job_handoff_ui.md`; `frontend/src/FullJobHandoff.tsx`; `frontend/src/fullJobHandoffAdapter.ts`; `frontend/src/fullJobHandoffAdapter.test.mjs`; `frontend/src/full-job-handoff.css`; `evidence/integration/full-job-handoff-api-related-20261017.log`; `evidence/integration/full-job-handoff-api-independent-20261017.log`; `evidence/integration/full-job-handoff-api-live-api-20261017.json`; `evidence/integration/full-job-handoff-api-live-ui-20261017.json`; `evidence/integration/full-job-handoff-api-full-tests-20261017.log`; `evidence/integration/full-job-handoff-api-live-integrity-20261017.json`; `evidence/integration/full-job-handoff-ui-adapter-20261017.log`; `evidence/integration/full-job-handoff-ui-tests-20261017.log`; `evidence/integration/full-job-handoff-ui-independent-20261017.log`; `evidence/integration/full-job-handoff-ui-build-20261017.log`; `evidence/integration/full-job-handoff-ui-desktop-20261017.jpg`; `backend/app/schema_formats.py`; `tests/test_schema_formats.py`; `docs/implementation/92_common_datetime_validation.md`; `evidence/integration/common-datetime-related-20261017.log`; `evidence/integration/common-datetime-independent-20261017.log`; `evidence/integration/common-datetime-source-runtime-20261017.json`; `evidence/integration/common-datetime-catalog-observation-20261017.json`; `evidence/integration/common-datetime-next-review-20261017.json`; `evidence/integration/common-datetime-full-tests-20261017.log`; `evidence/integration/common-datetime-live-integrity-20261017.json`; `backend/app/agent_capability_contract.py`; `tests/test_agent_capability_contract.py`; `docs/implementation/93_agent_capability_contract.md`; `evidence/integration/agent-capability-original-gmais-20261017.py`; `evidence/integration/agent-capability-related-20261017.log`; `evidence/integration/agent-capability-independent-20261017.log`; `evidence/integration/agent-capability-source-runtime-20261017.json`; `evidence/integration/agent-capability-next-review-20261017.json`; `evidence/integration/agent-capability-full-tests-20261017.log`; `evidence/integration/agent-capability-live-integrity-20261017.json`; `backend/app/workflow_job_registration_handoff.py`; `tests/test_workflow_job_registration_handoff.py`; `tests/test_workflow_job_registration_handoff_api.py`; `docs/implementation/94_full_job_registration_api.md`; `docs/implementation/95_full_job_registration_ui.md`; `frontend/src/fullJobRegistrationAdapter.ts`; `frontend/src/fullJobRegistrationAdapter.test.mjs`; `evidence/integration/full-job-registration-api-related-20261017.log`; `evidence/integration/full-job-registration-api-independent-20261017.log`; `evidence/integration/full-job-registration-api-live-api-20261017.json`; `evidence/integration/full-job-registration-api-live-ui-20261017.json`; `evidence/integration/full-job-registration-api-full-tests-20261017.log`; `evidence/integration/full-job-registration-api-live-integrity-20261017.json`; `evidence/integration/full-job-registration-api-original-20261017.py`; `evidence/integration/full-job-registration-ui-related-20261017.log`; `evidence/integration/full-job-registration-ui-tests-20261017.log`; `evidence/integration/full-job-registration-ui-independent-20261017.log`; `evidence/integration/full-job-registration-ui-build-20261017.log`; `evidence/integration/full-job-registration-ui-desktop-20261017.png`; `evidence/integration/full-job-registration-ui-blocked-20261017.png`; `backend/app/model_reference_contract.py`; `tests/test_model_reference_contract.py`; `docs/implementation/96_model_reference_contract.md`; `evidence/integration/model-ref-related-20261017.log`; `evidence/integration/model-ref-independent-20261017.log`; `evidence/integration/model-ref-source-runtime-20261017.json`; `evidence/integration/model-ref-full-tests-20261017.log`; `evidence/integration/model-ref-live-integrity-20261017.json`; `evidence/integration/model-ref-next-review-20261017.json`; `evidence/integration/model-ref-original-gmais-20261017.py`; `evidence/integration/model-ref-original-handoff-20261017.py`; `backend/app/experiment_registry.py`; `tests/test_model_version_declaration.py`; `docs/implementation/97_model_version_declaration.md`; `evidence/integration/model-version-related-20261017.log`; `evidence/integration/model-version-independent-20261017.log`; `evidence/integration/model-version-catalog-observation-20261017.json`; `evidence/integration/model-version-original-registry-20261017.py`; `evidence/integration/model-version-initial-tests-20261017.log`; `evidence/integration/model-version-full-tests-20261017.log`; `evidence/integration/model-version-live-integrity-20261017.json`; `evidence/integration/model-version-next-review-20261017.json`; `frontend/src/ModelReview.tsx`; `frontend/src/modelVersionRegistrationAdapter.ts`; `frontend/src/modelVersionRegistrationAdapter.test.mjs`; `frontend/src/model-version-registration.css`; `docs/implementation/98_model_version_registration_api.md`; `docs/implementation/99_model_version_registration_ui.md`; `evidence/integration/model-version-api-related-20261017.log`; `evidence/integration/model-version-api-independent-20261017.log`; `evidence/integration/model-version-api-live-api-20261017.json`; `evidence/integration/model-version-api-live-ui-20261017.json`; `evidence/integration/model-version-api-full-tests-20261017.log`; `evidence/integration/model-version-api-full-tests-corrected-20261017.log`; `evidence/integration/model-version-api-live-integrity-20261017.json`; `evidence/integration/model-version-api-original-main-20261017.py`; `evidence/integration/model-version-api-original-ui-20261017.tsx`; `evidence/integration/model-version-api-next-review-20261017.json`; `evidence/integration/model-version-ui-related-20261017.log`; `evidence/integration/model-version-ui-tests-20261017.log`; `evidence/integration/model-version-ui-independent-20261017.log`; `evidence/integration/model-version-ui-build-20261017.log`; `evidence/integration/model-version-ui-related-layout-20261017.log`; `evidence/integration/model-version-ui-tests-layout-20261017.log`; `evidence/integration/model-version-ui-build-layout-20261017.log`; `evidence/integration/model-version-ui-desktop-final-20261017.png`; `backend/app/model_registration_provenance.py`; `tests/test_model_registration_provenance.py`; `docs/implementation/100_model_registration_provenance_observation.md`; `evidence/integration/model-provenance-focused-20261017.log`; `evidence/integration/model-provenance-related-20261017.log`; `evidence/integration/model-provenance-independent-20261017.log`; `evidence/integration/model-provenance-catalog-observation-20261017.json`; `evidence/integration/model-provenance-live-integrity-20261017.json`; `tests/test_model_registration_provenance_api.py`; `docs/implementation/101_model_registration_provenance_api.md`; `docs/implementation/102_model_registration_provenance_ui.md`; `frontend/src/ModelRegistrationProvenance.tsx`; `frontend/src/modelRegistrationProvenanceAdapter.ts`; `frontend/src/modelRegistrationProvenanceAdapter.test.mjs`; `frontend/src/model-registration-provenance.css`; `evidence/integration/model-provenance-api-focused-20261017.log`; `evidence/integration/model-provenance-api-focused-corrected-20261017.log`; `evidence/integration/model-provenance-api-focused-final-20261017.log`; `evidence/integration/model-provenance-api-related-20261017.log`; `evidence/integration/model-provenance-api-independent-20261017.log`; `evidence/integration/model-provenance-api-live-api-20261017.json`; `evidence/integration/model-provenance-api-live-ui-20261017.json`; `evidence/integration/model-provenance-api-full-tests-20261017.log`; `evidence/integration/model-provenance-api-live-integrity-20261017.json`; `evidence/integration/model-provenance-api-next-review-20261017.json`; `evidence/integration/model-provenance-ui-related-20261017.log`; `evidence/integration/model-provenance-ui-tests-20261017.log`; `evidence/integration/model-provenance-ui-independent-20261017.log`; `evidence/integration/model-provenance-ui-build-20261017.log`; `evidence/integration/model-provenance-ui-desktop-20261017.png`; `backend/app/model_reference_record_comparison.py`; `tests/test_model_reference_record_comparison.py`; `docs/implementation/103_model_reference_record_comparison.md`; `evidence/integration/model-reference-record-focused-20261017.log`; `evidence/integration/model-reference-record-related-20261017.log`; `evidence/integration/model-reference-record-independent-20261017.log`; `evidence/integration/model-reference-record-catalog-observation-20261017.json`; `evidence/integration/model-reference-record-live-integrity-20261017.json`; `backend/app/workflow_job_model_record_handoff.py`; `tests/test_workflow_job_model_record_handoff.py`; `docs/implementation/104_workflow_job_model_record_handoff.md`; `evidence/integration/workflow-model-record-focused-20261017.log`; `evidence/integration/workflow-model-record-related-20261017.log`; `evidence/integration/workflow-model-record-independent-20261017.log`; `evidence/integration/workflow-model-record-catalog-observation-20261017.json`; `evidence/integration/workflow-model-record-live-integrity-20261017.json`; `backend/app/workflow_job_model_record_handoff_api.py`; `tests/test_workflow_job_model_record_handoff_api.py`; `docs/implementation/105_workflow_job_model_record_handoff_api.md`; `docs/implementation/106_workflow_model_record_handoff_ui.md`; `frontend/src/WorkflowModelRecordHandoff.tsx`; `frontend/src/workflowModelRecordHandoffAdapter.ts`; `frontend/src/workflowModelRecordHandoffAdapter.test.mjs`; `frontend/src/workflow-model-record-handoff.css`; `evidence/integration/workflow-model-record-api-focused-20261017.log`; `evidence/integration/workflow-model-record-api-related-20261017.log`; `evidence/integration/workflow-model-record-api-independent-20261017.log`; `evidence/integration/workflow-model-record-api-full-tests-20261017.log`; `evidence/integration/workflow-model-record-api-full-tests-final-20261017.log`; `evidence/integration/workflow-model-record-api-live-api-20261017.json`; `evidence/integration/workflow-model-record-api-live-ui-20261017.json`; `evidence/integration/workflow-model-record-api-live-integrity-20261017.json`; `evidence/integration/workflow-model-record-api-test-compat-baseline-20261017.json`; `evidence/integration/workflow-model-record-api-test-compat-focused-20261017.log`; `evidence/integration/workflow-model-record-api-test-compat-original-20261017.py`; `evidence/integration/workflow-model-record-api-test-compat-result-20261017.json`; `evidence/integration/workflow-model-record-api-next-queue-review-20261017.json`; `evidence/integration/workflow-model-record-ui-related-initial-failure-20261017.log`; `evidence/integration/workflow-model-record-ui-related-20261017.log`; `evidence/integration/workflow-model-record-ui-independent-20261017.log`; `evidence/integration/workflow-model-record-ui-tests-20261017.log`; `evidence/integration/workflow-model-record-ui-build-20261017.log`; `evidence/integration/workflow-model-record-ui-desktop-20261017.png`; `backend/app/workflow_dependency_order.py`; `tests/test_workflow_dependency_order.py`; `docs/implementation/107_workflow_dependency_order.md`; `evidence/integration/workflow-dependency-order-focused-20261017.log`; `evidence/integration/workflow-dependency-order-focused-final-20261017.log`; `evidence/integration/workflow-dependency-order-related-20261017.log`; `evidence/integration/workflow-dependency-order-independent-20261017.log`; `evidence/integration/workflow-dependency-order-independent-review-20261017.json`; `evidence/integration/workflow-dependency-order-full-tests-20261017.log`; `evidence/integration/workflow-dependency-order-live-integrity-20261017.json`; `evidence/integration/workflow-dependency-order-preflight-20261017.json`; `evidence/integration/workflow-dependency-order-original-gmais_api-20261017.py`; `evidence/integration/workflow-dependency-order-original-workflow_lineage-20261017.py`; `evidence/integration/workflow-dependency-order-original-workflow_policy-20261017.py`; `backend/app/data/recovery_commit_contract.py`; `tests/test_recovery_commit_contract.py`; `docs/implementation/109_area_completion_audit.md`; `docs/implementation/110_recovery_commit_contract.md`; `scripts/collect_training_parallel.py`; `backend/app/data/budget.py`; `evidence/integration/recovery-commit-contract-focused-20261017.log`; `evidence/integration/recovery-commit-contract-focused-final-20261017.log`; `evidence/integration/recovery-commit-contract-focused-final2-20261017.log`; `evidence/integration/recovery-commit-contract-related-20261017.log`; `evidence/integration/recovery-commit-contract-related-final-20261017.log`; `evidence/integration/recovery-commit-contract-related-final2-20261017.log`; `evidence/integration/recovery-commit-contract-independent-before-key-guard-20261017.log`; `evidence/integration/recovery-commit-contract-independent-20261017.log`; `evidence/integration/recovery-commit-contract-independent-final3-20261017.log`; `evidence/integration/recovery-commit-contract-preflight-20261017.json`; `evidence/integration/recovery-commit-contract-live-integrity-20261017.json`; `evidence/integration/recovery-commit-contract-external-dependencies-20261017.json`; `docs/implementation/111_data_pipeline_completion.md`; `docs/implementation/112_lcluc_ml_completion.md`; `docs/implementation/113_lcluc_integration_acceptance.md`; `docs/implementation/114_geollm_technical_review.md`; `backend/app/data/collection_registration.py`; `scripts/register_collection.py`; `tests/test_collection_version_registration.py`; `backend/app/ml/error_analysis.py`; `backend/app/ml/service.py`; `backend/app/ml/network.py`; `tests/test_ml_error_analysis.py`; `scripts/evaluate_geollm_local.py`; `scripts/evaluate_geollm_tools.py`; `tests/test_geollm_local_evaluation.py`; `tests/test_geollm_tool_evaluation.py`; `evidence/integration/data-pipeline-inventory-20261018.json`; `evidence/integration/data-pipeline-focused-final-20261018.log`; `evidence/integration/data-pipeline-related-final-20261018.log`; `evidence/integration/data-pipeline-independent-20261018.log`; `evidence/integration/data-pipeline-independent-review-20261018.json`; `evidence/integration/lcluc-ml-architecture-20261018.json`; `evidence/integration/lcluc-ml-error-analysis-focused-20261018.log`; `evidence/integration/lcluc-ml-error-analysis-related-20261018.log`; `evidence/integration/lcluc-ml-error-analysis-integrity-20261018.json`; `evidence/integration/lcluc-ml-existing-report-error-analysis-20261018.json`; `evidence/integration/geollm-local-evaluation-20261018.json`; `evidence/integration/geollm-native-tools-20261018.json`; `evidence/integration/geollm-runtime-audit-20261018.json`; `evidence/integration/geollm-evaluation-tests-final3-20261018.log`; `evidence/integration/geollm-independent-tests-final-20261018.log`; `evidence/integration/geollm-independent-review-20261018.json`; `evidence/integration/lcluc-geollm-full-tests-20261018.log`; `evidence/integration/lcluc-geollm-live-integrity-final-20261018.json`; `backend/app/lcluc_workflow.py`; `scripts/run_lcluc_workflow.py`; `tests/test_lcluc_workflow.py`; `docs/implementation/115_lcluc_workflow_executor.md`; `evidence/integration/lcluc-workflow-source-freeze-20261018.json`; `evidence/integration/lcluc-workflow-focused-final4-20261018.log`; `evidence/integration/lcluc-workflow-independent-final2-20261018.log`; `evidence/integration/lcluc-workflow-independent-related-20261018.log`; `evidence/integration/lcluc-workflow-independent-review-20261018.json`; `evidence/integration/lcluc-workflow-full-tests-20261018.log`; `evidence/integration/lcluc-workflow-live-integrity-20261018.json`; `backend/app/lcluc_workflow_api.py`; `tests/test_lcluc_workflow_api.py`; `frontend/src/LclucWorkflowPanel.tsx`; `frontend/src/lclucWorkflowAdapter.ts`; `frontend/src/lclucWorkflowClient.ts`; `frontend/src/lcluc-workflow.css`; `frontend/src/ModelAnalysisWorkspace.tsx`; `docs/implementation/116_lcluc_workflow_api.md`; `docs/implementation/117_lcluc_workflow_ui.md`; `evidence/integration/lcluc-workflow-api-focused-final2-20261018.log`; `evidence/integration/lcluc-workflow-api-independent-tests-20261018.log`; `evidence/integration/lcluc-workflow-api-route-preservation-tests-20261018.log`; `evidence/integration/lcluc-workflow-ui-related-final-20261018.log`; `evidence/integration/lcluc-workflow-ui-tests-final-20261018.log`; `evidence/integration/lcluc-workflow-ui-build-final-20261018.log`; `evidence/integration/lcluc-workflow-ui-browser-20261018.json`; `evidence/integration/lcluc-workflow-api-live-integrity-20261018.json`; `evidence/integration/lcluc-workflow-api-live-route-20261018.json`; `evidence/integration/lcluc-workflow-ui-related-final3-20261018.log`; `evidence/integration/lcluc-workflow-ui-tests-final2-20261018.log`; `evidence/integration/lcluc-workflow-ui-build-final2-20261018.log`; `evidence/integration/lcluc-workflow-api-full-tests-20261018.log`; `evidence/integration/lcluc-workflow-api-related-20261018.log`; `evidence/integration/lcluc-workflow-ui-build-final3-20261018.log`; `evidence/integration/lcluc-workflow-ui-synthetic-desktop-final2-20261018.png`; `frontend/src/lclucChangeMapAdapter.ts`; `frontend/src/LclucWorkflowChangeMap.tsx`; `docs/implementation/118_lcluc_workflow_change_map.md`; `evidence/integration/lcluc-change-map-adapter-focused-20261018.log`; `evidence/integration/lcluc-change-map-ui-related-final-20261018.log`; `evidence/integration/lcluc-change-map-generated-fixture-20261018.json`; `evidence/integration/lcluc-change-map-independent-20261018.log`; `evidence/integration/lcluc-change-map-core-focused-20261018.log`; `evidence/integration/lcluc-change-map-core-api-final-20261018.log`; `evidence/integration/lcluc-change-map-nonempty-initial-diagnostic-20261018.log`; `evidence/integration/lcluc-change-map-ui-tests-20261018.log`; `evidence/integration/lcluc-change-map-ui-build-20261018.log`; `evidence/integration/lcluc-change-map-full-backend-20261018.log`; `evidence/integration/lcluc-change-map-live-integrity-20261018.json`; `evidence/integration/lcluc-change-map-browser-20261018.json`; `evidence/integration/lcluc-change-map-nonempty-20261018.png`; `evidence/integration/lcluc-change-map-empty-20261018.png`; `frontend/src/lclucTransitionAdapter.ts`; `frontend/src/LclucTransitionSummary.tsx`; `evidence/integration/lcluc-transition-adapter-focused-final-20261018.log`; `evidence/integration/lcluc-transition-ui-related-20261018.log`; `evidence/integration/lcluc-transition-independent-20261018.log`; `evidence/integration/lcluc-transition-generated-fixture-20261018.json`; `docs/implementation/119_lcluc_transition_matrix.md`; `evidence/integration/lcluc-transition-ui-tests-20261018.log`; `evidence/integration/lcluc-transition-ui-build-20261018.log`; `evidence/integration/lcluc-transition-ui-build-initial-20261018.log`; `evidence/integration/lcluc-transition-browser-20261018.json`; `evidence/integration/lcluc-transition-live-integrity-20261018.json`; `evidence/integration/lcluc-transition-matrix-final-20261018.png`; `evidence/integration/lcluc-transition-class-map-20261018.png` |
| confidence | 완료 소스·최종 로그·실제 CPU 보고서/브라우저 확인; 산술 정합과 과학 승인 구분 |
| status | TESTED_SYNTHETIC 저장 통계 검산·표시; 독립 정확도/운영 승인 BLOCKED |

> 이번 작성은 읽기와 문서화다. 아래 시험 결과는 2026-10-17 보존 로그의 역사적 기록이며 재실행 결과가 아니다. 상태는 각 범위에 한정한다.

## 1분: 조리 순서표

여러 분석을 묶는 일은 여러 요리를 동시에 만드는 일과 같다. 재료가 준비돼야 다음 공정을 시작할 수 있다. 현재 Orchestrator는 순서표와 준비조건을 검사하며, 실제 모든 분석을 돌리는 지휘 기능은 아직 연결되지 않았다.

## 5분: 요청 → DAG → 준비도

노드마다 Agent·capability·입력 참조·의존 노드를 지정한다. 순환 없는 방향 그래프(DAG)의 순서를 계산하고 중복 노드, 순환, 알 수 없는 기능, 부적절한 입력 연결을 검사한다. 실행 자격이 없는 노드는 BLOCKED다. 현재 응답의 `mode=PLAN_ONLY`, `execution_started=false`, `can_execute=false`가 핵심이다.

```mermaid
flowchart LR
 A[Workflow JSON] --> B[Schema·중복·순환 검사]
 B --> C[위상 정렬·Capability·입력 검토]
 C --> D[PLAN_ONLY·BLOCKED·Trace]
 D -. 후속 미구현 .-> E[실제 DAG 실행·재시도·집계]
```

## 실제 코드·API·예외

`backend/app/gmais_api.py:_workflow_plan_validator`, `create_router`의 `POST /v1/workflows/plan`이 구현 지점이다. `contracts/upstream/GMAIS-v0.2/schemas/workflow-plan.schema.json`을 사용한다. 이 endpoint는 upstream OpenAPI 원문에 없는 RFC 확장이다. `frontend/src/GeoQuery.tsx:inspectPlan`이 JSON을 제출하고 결과를 보여준다. 현재 UI는 “자동 Job 실행 미연결”을 표시한다.

Trace는 요청 처리의 연결표, Job ID는 개별 작업표다. 멱등성은 같은 요청의 중복 실행 방지다. Retry는 재시도, timeout은 기다림 상한, cancel은 취소다. 현재 `/v1/jobs/{job_id}/cancel` 경로는 존재하지만 이미 BLOCKED인 Job을 취소하려 하면409를 반환한다. 이를 실제 실행 중인 DAG의 취소·재시도 구현이라고 확대하지 않는다.

## 시험과 한계

`TESTED_SYNTHETIC`: `tests/test_gmais_workflow_extension.py`의 기존 회귀 기록을 197 PASS 로그에서 확인한다. 계약·DAG 계획 검사 범위다. 실제 DAG scheduling, 의존 상태전파, retry/timeout/cancel 정책의 운영 실행, 여러 Result 집계는 미구현이다. 자연어 GeoLLM이 답했다는 것과 승인된 실제 Job 실행은 별개다.

## 10분 확장·발표·Q&A

5분 순서 설명 뒤 2분은 A→B→A 순환 예, 2분은 선행 노드 실패와 중복 실행 예, 1분은 실제 scheduler 인수 기준을 설명한다. 단일 함수에서 순서대로 호출하는 대안은 간단하지만 복합 의존성을 드러내기 어려워 DAG 계약을 둔다. 지금은 계약의 계획 단계만 있다.

30초: “분석 순서와 실행 자격을 먼저 확인하는 계획 API를 만들었습니다. 계획 결과는 실제 실행 결과가 아니며 실행기는 후속 연결입니다.”

슬라이드: 의존관계 / 준비도 / PLAN_ONLY / 실행 인수.

Q. 버튼을 누르면 모델이 자동 실행되나? A. 현재 Workflow 검토는 실행하지 않는다.

Q. Kubernetes가 대신 해주나? A. Kubernetes는 컨테이너 자원을 관리한다. 분석 순서·입력·승인을 이해하는 업무 조정과 다르다.

Q. 다음 Gate는? A. 실제 scheduler와 실패·취소 시험의 증거를 받은 뒤 계획·실행 상태를 나눠 갱신한다.

## 최신 후속: Job 입력 진단과 Workflow 계획의 구분

개별 Job 제출의 `input_refs`를 Dataset 버전코어와대조하는 `job_inputs.py:resolve_job_inputs`가연결됐다. 이는 등록누락·신원/자산SHA·URI·품질/ACL blocker를 진단해 제출snapshot에저장하는 기능이다. 같은key재생은 최초기록을돌려주며 현재파일재인증이나실행허가는아니다. `ready_for_execution=false`, `scientific_approval=false`를유지한다.

`POST /v1/workflows/plan`의 입력바인딩 해석·실제DAG실행은이번변경범위가아니다. PLAN_ONLY·execution_started=false가유지된다. Q.이제조정기가실제자료를연결해자동실행하나? A.개별접수의무결성진단만추가됐고실행기/스케줄러·의미검증·승인은별도다. 최신전체240건중239 PASS·1 SKIP는코드시험이며과학·운영검증과구별한다.

## 최신 구현: 계획 노드의 실제 등록 입력 대조

앞서 후속으로 남겼던 Workflow의 **고정 입력 진단 연결**을 구현했다. 이는 입력을 검사하는 계획 단계의 진전이며 실제 실행 엔진은 아니다. `POST /v1/workflows/plan`은 DAG를 먼저 검증한 뒤 각 노드의 `input_bindings`를 `resolve_job_inputs`로 대조한다. 정상 입력에 무조건 DATA_MISSING을 반환하던 이전 동작을 제거했다.

노드마다 별도 입력 목록을 검사하므로 서로 다른 노드 사이에 가짜 중복 충돌을 만들지 않는다. 같은 자료 ID의 다른 고정 버전 T1/T2는 허용하고 동일(id,version)의 다른 SHA는 해당 노드에서 차단한다. RAW·제한자료의 파일 무결성이 true여도 품질·ACL blocker는 남는다. 각 응답은 이번 요청의 snapshot이며 같은 workflow_run_id/trace_id로 다시 요청해도 현재 자산 변경을 새로 검사한다. Job의 최초 저장 진단 재생과 구분한다.

실제 DAG scheduling, 의존노드 상태 전파, STOP_DEPENDENTS/FAIL_ALL 실행, retry/timeout/cancel, 승인 모델 선택, 동적 노드 출력 바인딩, Result 생성은 후속이다. Agent READY를 시험에서 강제해도 fallback MODEL_NOT_READY로 비실행을 유지했다. 관련 fixture 14 PASS·3.910초가 이 경계를 확인한다. API 프로세스를 재시작한 실브라우저 검증이 아니라 TestClient 범위다.

1분 설명: “분석 순서표의 각 단계가 실제 등록된 자료를 가리키는지 검사합니다. 입력이 맞아도 승인된 실행기가 없으면 멈춥니다.” 5분에는 DAG 선검증→노드별 대조→오류 분류→실행 차단을 설명한다. 10분에는 잘못된 DAG의 무조회, 다른 노드 독립성, RAW/제한자료의 지문과 승인 차이, 재요청 파일 변경을 사례로 든다. Q. 이제 자동 분석되나? A. 입력 연결 진단이며 실행기는 여전히 후속이다.

### Workflow 입력 연결 후 최종 전체시험

`workflow-input-full-tests-20261017.log`를 읽어 `scripts/test.ps1`의247건/139.318초/OK(skipped=1), 즉 **246 PASS·1 SKIP**를 확인했다. SKIP은 기존 실제 OS symlink 생성권한 부족이며 대체 mock 경계시험은 통과했다. 관련 Workflow14 PASS·3.910초는 이 전체시험에 포함된 부분이며 이전240건·225건·197건에 산술 합산하지 않는다. 이해 에이전트가 재실행한 것이 아니라 개발팀의 완료 로그를 읽은 근거다. 이전 전체시험 수치는 개발 이력이고 현재 판정은 이 절이 우선한다.

실제 API 프로세스 재시작·실자료 수집/학습·Job/Result 실행은 하지 않았다. 고정 입력 진단은 PLAN_ONLY·BLOCKED 범위이고 과학·기관·운영 승인 및 실제 DAG 실행 gate는 유지한다.

## 차단 사유를 local·선행·정책으로 나누는 계획 진단

`backend/app/workflow_policy.py:diagnose_workflow_blocking(reviewed_nodes,policy)`는 파일·Store·네트워크 접근 없이 이미 계산한 local blocker snapshot을 의존 그래프에 연결하는 순수 함수다. 전달된 원인을 다시 seed로 넣지 않아 연쇄 전달에서 중복을 만들지 않는다. 순서가 바뀌어도 같은 원인 목록을 내고 원본을 깊은 복사로 보존한다.

1분 비유: “내 예약이 빠졌는지, 먼저 타야 할 항공편이 막혔는지, 전체 일정 중지 규칙 때문인지 나누어 보여줍니다. 실제 취소를 수행하는 기능은 아닙니다.” STOP_DEPENDENTS는 실제 ancestor local 원인만, FAIL_ALL은 다른 분기 원인을 policy_blocked_by에 따로 표시한다. 깨끗한 독립 분기는 순수 코어 fixture로 확인했으며 실제 Agent는 여전히 모두 차단 상태다.

코드의 `diagnostic_status=NO_BLOCKING_CAUSE_IDENTIFIED`는 READY가 아니다. `max_parallel`과 `require_human_approval`에서 실행 권한을 만들지 않는다. 전역 PLAN_ONLY·BLOCKED와 can_execute/execution_started=false, 각 execution_authorized=false를 유지한다. 실제 의존 상태 전파 실행·scheduler·timeout/retry/cancel은 여전히 후속이다.

5분은 입력 진단→local snapshot→실제 ancestor→정책 원인→실행 차단을 설명한다.10분에는 diamond 중복 제거·독립 분기·잘못된 DAG 거부·순서 결정성을 사례로 든다. Q. FAIL_ALL이면 작업을 취소했나? A. 계획에서 중지 원인 범위를 계산했으며 실행 중 작업 취소는 구현 범위 밖이다. 관련 코어9/API20시험과 최신전체262건261 PASS·1 SKIP를 구별해 읽는다.

## 현재 전이 계보의 별도 계획 검사

`workflow_lineage.py:validate_workflow_lineage`와API가 기존WorkflowJSON을받아 schema·DAG를선검증하고Workflow전체공유예산으로현재고정계보를검사한다. node128상한은DAG계산전에닫으므로dag_validated=false를“순환발견”으로읽지않는다. 정상DAG뒤ref/고유root상한은해시전차단이며부분예산결과도미검사를명시한다.

이companion은기존`/plan`의Agent/readiness·단독입력·정책진단을대체하지않는다. URI·품질·AOI/기간·제품·실행요건전체를검사한것도아니다. 모든노드계보가맞아도Workflow는BLOCKED/PLAN_ONLY며실제DAG·Job/Trace/Result를만들지않는다. 기본정책카드와823자원래초안은보존했다.

1분비유: “여러작업의재료목록에같은재료가있으면한번확인하고공유하지만,재료가맞는다고작업실행이허가되지는않습니다.”5분은JSON→DAG→전체공유검사→노드/진단매핑→비실행,10분은본문bytes신원·노드/입력/예산상한·부분미검사·기존plan과의분리를설명한다. 실제shared미등록2노드+empty1에서진단1·비용1·dependent재사용과빈입력차단을확인했다. 관련Workflow11+기존Job12독립23PASS,전체321건320PASS/1SKIP는코드계약근거다.

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


## 83 내부 비실행 preflight

[저장 대비 현재 입력 검사](gate-notes/GATE_STORED_CURRENT_BINDING_20261017.md)는 configured Store Job get1 뒤 저장 RECORDED를 검증하고 기존 resolver 한 pass의 current envelope를 81 guard에 전달한다. 비교용 추가 Registry 조회는 없다. 현재 resolution BLOCKED는 binding MATCH여도 전체 BLOCKED다. legacy/unavailable은 UNKNOWN이며 resolver0으로 역채움을 막는다. 실제 resolver는 자산을 읽으므로 전체 IO0이 아니며 Workflow·executor·공개 API/UI에는 연결하지 않았다.


## 84/85 수동 현재 입력 검사 통로

[현재 preflight Gate](gate-notes/GATE_CURRENT_INPUT_PREFLIGHT_UI_20261017.md): 명시 GET → 기존 83 worker → exact 응답 검증. 프로세스/router별 semaphore는 실제 worker 종료까지 유지하고 바쁜 요청은 429로 안내한다. 화면 표시 중단은 서버 취소가 아니다. 현재 자산 IO가 있으나 Workflow·executor 실행은 연결하지 않는다. 수동 UI85와 최종 869건 회귀를 확인했다. actual current positive·실행은 관측하지 않았다.


## 86 선택 노드에서 제안 입력으로의 경계

[Workflow handoff Gate](gate-notes/GATE_WORKFLOW_NODE_HANDOFF_20261017.md)는 전체 요청 pin 확인 뒤 선택 노드와 제안 metadata를 순수 대조한다. 선택 외 빈 입력은 보존하지만 선택 노드는 입력이 필요하다. 미등록/self dependency는 거부해도 전체 순환을 검사하지 않아 cycle과 MATCH가 공존할 수 있다. dag_validated=false이며 기존 Workflow PLAN_ONLY·실행 차단은 그대로다.


## 87/88 수동 원문 handoff 진단

[선택 입력 비교](gate-notes/GATE_WORKFLOW_HANDOFF_API_UI_20261017.md) POST는86순수core를한번호출하는RFC진단이다. 실제Job/Registry/파일·executor는호출하지않고PLAN_ONLY를해제하지않는다. 전체원문과선택node·독립제안metadata를쓴다. rawbodySHA와canonicalpin을구분하고UI88와 실제 합성 선언 수동 비교를 확인했으며 실행 승인은 없다.


## 89 full Job draft에서 metadata 추출

[전체 초안 handoff](gate-notes/GATE_FULL_JOB_HANDOFF_20261017.md)는 bounded객체→원schema/날짜→bbox/model선언→metadata추출→86대조1회다. 기본AOI/output/context를만들거나Job을제출하지않는다. 전체초안hash와metadatahash를나누며schema coldIO가있어전체IO0을주장하지않는다. 내부helper로Workflow실행체인은변경없다.


## 90/91 full Job draft 수동 진단

[전체 초안 API](gate-notes/GATE_FULL_JOB_HANDOFF_API_UI_20261017.md)는원Workflow+fullJob원문을89에한번호출한다. Job생성/제출·기본값추정은없다. strict응답의단계·inner86·raw요청SHA를대조하고schema자원실패를503으로안전표시한다. UI91의 독립 수동검사와 실제 합성 초안 표시를 확인했으며 Workflow 실행은 연결하지 않았다.


## 92 공통 validator 생성과 날짜 지원

[날짜 factory](gate-notes/GATE_COMMON_DATETIME_20261017.md)는새validator생성때등록한다. 현재Workflow schema에는format이없어plan응답동등을확인했다. 실행순서·기간정책·Job실행을바꾸지않으며기존cached객체후행변조도없다. 운영프로세스날짜동작은별도검증대상이다.


## 93 Job/Workflow의 등록관계 helper

[공통 관계 함수](gate-notes/GATE_AGENT_CAPABILITY_20261017.md)는등록manifest선택을caller에게남기고membership만묶었다. Workflow의기존진단지속·blocker순서·Store접근과PLAN_ONLY를바꾸지않는다. 원핸들러와격리응답/기록동등을확인하며실제실행은연결하지않았다.


## 94/95 선택형 로컬 등록축

[fullJob RFC2](gate-notes/GATE_FULL_JOB_REGISTRATION_20261017.md)는89한번후93membership를Job동일firstmatch로관측한다. innerMATCH라도미등록이면outerBLOCKED다. RPC/원격Registry·Job생성·실행을추가하지않으며기존RFC1과PLAN_ONLY는유지한다.


## 96 모델 문자 선언의 caller 책임

[공통 문자 검사](gate-notes/GATE_MODEL_REFERENCE_20261017.md)는정규화/모델조회없이id/version/role과latest/current를검사한다. GMAIS기존schema/SHA/Store순서와89bbox우선/RFC1/2결과를보존한다. Workflow계획/실제modelRegistry/Job실행은연결하지않는다.


## 97 register_experiment 선택 옵션

[내부 등록 메모](gate-notes/GATE_MODEL_VERSION_DECLARATION_20261017.md)는기존검사/lineage뒤첫put전에문자/충돌을거부한다. 새version을top이나dataset에추정하지않고중복model/datasetID거부를보존한다. datasets→models두쓰기는비트랜잭션이며부분실패/동시경쟁·승인은해결하지않는다.


## 98/99 등록 요청과 표시의 수명

[선택 등록 흐름](gate-notes/GATE_MODEL_VERSION_REGISTRATION_UI_20261017.md)은manual버튼·busy/inflight로중복을막고route/unmount는표시만폐기한다. 서버201후목록갱신은화면밖에서도수행하고refresh실패를등록실패와구분한다. 표시무효화는서버취소/rollback아니며기존두쓰기한계는그대로다.


## 100 pure provenance observation

[모델 metadata 관측](gate-notes/GATE_MODEL_PROVENANCE_20261017.md)은파일/Store/Registry없이전달record의알려진선언만본다. 형식invalid우선·알려진충돌은다른부모부재보다우선이며optionalrawversion부재는정상이다. 승인/실행/등록경로를변경하지않는다.


## 101/102 수동 metadata GET과 표시방어

[관측 API/UI](gate-notes/GATE_MODEL_PROVENANCE_API_UI_20261017.md)는등록/Job/executor없이모델record1회읽기만한다. 선택/열기자동조회없음·keyed모델·route/back/unmount세대폐기로늦은표시를막는다. DB읽기와purehelperIO0을구분하고화면이동을서버읽기취소로부르지않는다.


## 103 내부 모델 카드 비교와 호출 경계

새 비교 함수는 조회할 레코드를 선택하거나 Store·Registry·실행기를 부르지 않는다. 제공 카드가 없으면 미제공, 같은 ID의 카드가 자체 일관할 때만 버전과 지문을 비교한다. 원문 패딩을 정규화하지 않고 내부 예외도 전파한다. 후속 wrapper/API가 선택·안전 오류를 책임져야 한다. 현재89/94·Job/Workflow 실행 회로에는 연결하지 않았다. 다음89 MATCH 뒤 optional model_ref를 exact3로 명시 추출하는 wrapper 계약만 PLANNED다. 실제 resolver·권위·실바이트·실행 승인은 없다.



## 104 내부 연결의 선행 조건과 미연결 범위

89의 검토가 MATCH일 때만 모델 참조를 exact3로 명시 추출해103으로 대조한다. 기존89·94·103의 결과와 호출 회로는 바꾸지 않았다. 새 wrapper는 resolver·Job 제출·API/UI에 연결하지 않았다. 카드를 고르는 출처나 현재 파일 검증도 없다. wrapper 추가IO0과89 cold schema 읽기를 나누며 schema_files_read null은 그대로다. 후속 읽기 전용 API는 PLANNED 계약 검토이며 기존 RFC1/2 형식·원장 조회 부재를 유지하는 방향이다.



## 105/106 수동 API/UI의 실행 경계

새 endpoint는 caller가 준 Workflow·전체 Job·카드만 비교한다. 모델 목록 조회·선택·resolver·Job 생성은 없다. API가 원문을 먼저 파싱한 뒤104를 한 threadpool에서 생산·검증한다. same-ID 관측 가지는 생산103/100 각각1회와 검증 추가 각각1회이며 응답 계수는 생산 범위다. 모든 router 응답은 no-store, 오염/자원 오류는 고정503이다. 기존 main 인증과 RFC1/RFC2를 유지한다. 표시 세대 폐기는 서버 취소·원자 snapshot·기관 권위를 보장하지 않는다.



## 107 공통 Kahn 계층 정렬

plan_workflow·validate_workflow_lineage·diagnose_workflow_blocking이 workflow_dependency_order.topological_order를 공유한다. a와z가 준비되고 b는a를 기다리면[a,z,b]다. 매번 전역 최소를 고르는 heap의[a,b,z]로 바꾸지 않는다. 입력 의존 집합을 복사하며 빈 map은[],진행 불가면None이다. unknown/self/중복·한도·schema검증과 순환 오류 문구는 호출자가 그대로 책임진다. 실행 순서 계산이지 scheduler·실행 승인이 아니다.



## 110 단계 선언 관측과 재개 연결 미구현

복구 helper는 previous/current 메모의11키와세대상map을검사하고고정18키로분류한다. 전이일치·동일재관측도항상BLOCKED/UNVERIFIED다. 실제journal저장·writer·정산·collector·API/UI에연결하지않는다. 참조지문은caller주장이고공급되지않은terminal/pin을생성하지않는다. 정확히한번적용UNKNOWN·정산/환불/재시작/쓰기/실행허가false·실제미완료배치미적용이다.



## 113 당시 실행 연결 계획과115 CLI 진행

현재GMAIS제출은입력snapshot과별개로409BLOCKED이며Workflow는PLAN_ONLY다.고정Registry연차입력·model_ref를resolve하고Deployed/독립평가checkpoint gate뒤기존analyze_timeseries를호출할local경로는113검토당시PLANNED였고115에서CLIcore가구현됐다.API/UI는116/117에서 연결됐고 운영 원본 실행은 별도 차단한다.새111등록CLI와112오류exporter가이실행연계를자동완료하지않는다. genericDAG/표준Result/기관승인과localscope를구분한다. LLM도구제안smoke도실제Job/runner호출이아니다.



## 115 실제 local LCLUC dispatcher 구현

execute_lcluc_workflow/명시CLI가고정요청→모델/입력admission→SQLite BEGIN IMMEDIATE단일claim→gate pin재검사→기존시계열runner→출력지문확인→자기claim CAS상태갱신을연결한다.같은key다른요청은충돌,RUNNING/FAILED는자동재시도없고성공재관측은출력SHA확인뒤기존성공을반환한다. 초기차단은claim/출력없음이며부분실패파일은보존한다. 파일과DB최종상태의원자commit·분산exactlyonce는아니다.

이전113의단일실행계획중CLIcore가구현됐으나API/UI·genericDAG·표준GMAISJob/Result는이번미연결이다. scopeLOCAL_LCLUC_WORKFLOW_ONLY·scientific_accuracy_validated/standard_gmais_result false다. 기존genericGMAIS409/PLAN_ONLY·GeoLLM은변경하지않았다.



## 116/117 — LCLUC 수동 실행·조회 API와 화면

새 API POST가115 단일 claim 실행기를 호출하고 GET은 기록/파일만 읽는다. POST는 완료까지 기다리는 threadpool 요청이며 background queue나 취소 scheduler가 아니다. RUNNING/FAILED 자동 재실행·resume이 없다. 성공 재관측은 과거 산출물 확인이지 현재 admission 승인 재실행이 아니다.


### 116/117 최신 상태로 읽는 주의점

앞선115 단락의 API/UI 미연결은 당시 범위다. 현재 수동 실행·상태·보고서·검증 파일 UI는116/117에서 연결했고 실제 성공 확인은 임시5175→8003의 모의 승인 fixture다. 운영5174에는 패널과 빈 요청 차단만 확인했다. 현재6밴드 제품 정규화·지도 pair·표준 Result·운영 승인과는 분리한다.


## 118 — 검증된 선택 변화쌍 지도

지도 읽기는 명시 pair 선택 뒤 별도 GET만 수행하며 실행 POST·자동 retry·새 Job을 만들지 않는다. pair 변경은 지도 결과만 지우고 receipt/report를 유지한다. route/입력/기록 변경은 늦은 응답을 폐기한다. core의 nonempty report 비교 결함 보완 외 admission·claim·실패 정책은 유지한다.


## 119 — 전체 래스터 전이행렬·범례·단위

pair 선택은 이미 수동 조회한 report를 로컬 검산해 통계 표를 만든다. 새 서버 GET/POST/추론은0이며 지도 파일은 여전히 별도 명시 버튼이다. 검산 실패는 지도 읽기와 통계 표를 거부하고 데이터를 추정하지 않는다. backend/API/Store는 변경하지 않았다.
