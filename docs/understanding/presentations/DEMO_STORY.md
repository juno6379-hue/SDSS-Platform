# 발표 시연: 보이는 것과 검증된 것을 구분하기

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-18 10:45:15 KST — 원본1464/1164 실제UI·격리288 PASS 확정; round4 계획/159 QA 진행 분리 |
| source_commit | 기준 76949f650123653f30841507feebc7678aaea151 + 148–157 검증 작업파일 raw SHA (관측 시점 작업파일; 최종 Git 게시의 바이트 보존은 별도 확인) |
| evidence_paths | `docs/implementation/00_next_session_handoff.md`; `docs/implementation/23_ml_readiness_resume_20261017.md`; `docs/implementation/23_ui_completion.md`; `evidence/integration/ml-readiness-resume-20261017.json`; `evidence/integration/resume-tests-script-20261017.log`; `docs/implementation/30_workflow_diagnostics_ui.md`; `frontend/src/InputDiagnostics.tsx`; `frontend/src/inputDiagnosticsAdapter.ts`; `evidence/integration/workflow-policy-ui-build-20261017.log`; `evidence/integration/workflow-policy-live-ui-20261017.json`; `evidence/ui-20261017/workflow-diagnostics-live.png`; `backend/app/job_snapshot.py`; `docs/implementation/31_job_input_snapshot_read.md`; `docs/implementation/32_job_snapshot_ui.md`; `evidence/integration/job-snapshot-tests-20261017.log`; `evidence/integration/job-snapshot-full-tests-20261017.log`; `evidence/integration/job-snapshot-ui-build-20261017.log`; `evidence/integration/job-snapshot-live-ui-20261017.json`; `docs/implementation/33_dashboard_reference_ui.md`; `docs/implementation/34_data_catalog_reference_ui.md`; `evidence/integration/dashboard-reference-build-20261017.log`; `evidence/integration/data-catalog-reference-build-20261017.log`; `evidence/integration/reference-ui-live-20261017.json`; `backend/app/dataset_lineage_api.py`; `docs/implementation/36_dataset_lineage_api_plan.md`; `docs/implementation/37_dataset_lineage_ui.md`; `evidence/integration/dataset-lineage-api-independent-tests-20261017.log`; `evidence/integration/dataset-lineage-api-full-tests-20261017.log`; `evidence/integration/dataset-lineage-ui-build-20261017.log`; `evidence/integration/dataset-lineage-api-live-20261017.json`; `backend/app/job_lineage.py`; `backend/app/job_lineage_api.py`; `docs/implementation/38_job_lineage_validation.md`; `docs/implementation/39_job_lineage_ui.md`; `evidence/integration/job-lineage-tests-20261017.log`; `evidence/integration/job-lineage-full-tests-20261017.log`; `evidence/integration/job-lineage-ui-build-20261017.log`; `evidence/integration/job-lineage-live-20261017.json`; `backend/app/workflow_lineage.py`; `backend/app/workflow_lineage_api.py`; `backend/app/lineage_batch.py`; `docs/implementation/40_workflow_lineage_validation.md`; `docs/implementation/41_workflow_lineage_ui.md`; `evidence/integration/workflow-lineage-independent-tests-20261017.log`; `evidence/integration/workflow-lineage-full-tests-20261017.log`; `evidence/integration/workflow-lineage-ui-build-20261017.log`; `evidence/integration/workflow-lineage-live-20261017.json`; `docs/implementation/42_catalog_insights_navigation.md`; `docs/implementation/43_catalog_insight_data_contract.md`; `frontend/src/CatalogInsights.tsx`; `frontend/src/catalogNavigation.ts`; `evidence/integration/catalog-insights-navigation-tests-20261017.log`; `evidence/integration/catalog-navigation-independent-ui-tests-20261017.log`; `evidence/integration/catalog-insights-navigation-build-20261017.log`; `evidence/integration/catalog-insights-browser-20261017.json`; `backend/app/ml/split_validation.py`; `scripts/validate_training_split_repair.py`; `docs/implementation/44_ml_split_repair_validation.md`; `evidence/integration/ml-split-validation-tests-20261017.log`; `evidence/integration/ml-split-validation-independent-20261017.log`; `evidence/integration/ml-split-validation-full-tests-20261017.log`; `evidence/integration/ml-split-repair-validation-live-final-20261017.json`; `evidence/integration/ml-split-validation-live-integrity-20261017.json`; `backend/app/data/recovery_terminal.py`; `scripts/inspect_recovery_terminal.py`; `docs/implementation/45_recovery_terminal_reconciliation.md`; `evidence/integration/recovery-terminal-tests-20261017.log`; `evidence/integration/recovery-terminal-independent-20261017.log`; `evidence/integration/recovery-terminal-full-tests-20261017.log`; `evidence/integration/recovery-terminal-live-final-20261017.json`; `evidence/integration/recovery-terminal-live-integrity-20261017.json`; `backend/app/data/recovery_aggregate.py`; `scripts/inspect_recovery_aggregate.py`; `docs/implementation/46_recovery_aggregate_reconciliation.md`; `evidence/integration/recovery-aggregate-tests-20261017.log`; `evidence/integration/recovery-aggregate-independent-20261017.log`; `evidence/integration/recovery-aggregate-full-tests-20261017.log`; `evidence/integration/recovery-aggregate-live-final-20261017.json`; `evidence/integration/recovery-aggregate-live-integrity-20261017.json`; `backend/app/data/recovery_crop.py`; `scripts/inspect_recovery_crop.py`; `docs/implementation/47_recovery_crop_reconciliation.md`; `evidence/integration/recovery-crop-tests-20261017.log`; `evidence/integration/recovery-crop-independent-20261017.log`; `evidence/integration/recovery-crop-full-tests-20261017.log`; `evidence/integration/recovery-crop-live-final-20261017.json`; `evidence/integration/recovery-crop-live-integrity-20261017.json`; `backend/app/data/recovery_raster_headers.py`; `scripts/inspect_recovery_raster_headers.py`; `docs/implementation/48_recovery_raster_header_validation.md`; `evidence/integration/recovery-raster-headers-tests-20261017.log`; `evidence/integration/recovery-raster-headers-independent-20261017.log`; `evidence/integration/recovery-raster-headers-live-final-20261017.json`; `evidence/integration/recovery-raster-headers-full-tests-20261017.log`; `evidence/integration/recovery-raster-headers-live-integrity-20261017.json`; `backend/app/data/recovery_raster_content.py`; `scripts/inspect_recovery_raster_content.py`; `docs/implementation/49_recovery_raster_content_validation.md`; `evidence/integration/recovery-raster-content-tests-20261017.log`; `evidence/integration/recovery-raster-content-independent-20261017.log`; `evidence/integration/recovery-raster-content-live-final-20261017.json`; `evidence/integration/recovery-raster-content-full-tests-20261017.log`; `evidence/integration/recovery-raster-content-live-integrity-20261017.json`; `backend/app/data/recovery_auxiliary_content.py`; `scripts/inspect_recovery_auxiliary_content.py`; `docs/implementation/50_recovery_auxiliary_content_validation.md`; `evidence/integration/recovery-auxiliary-content-tests-20261017.log`; `evidence/integration/recovery-auxiliary-content-independent-20261017.log`; `evidence/integration/recovery-auxiliary-content-live-final-20261017.json`; `evidence/integration/recovery-auxiliary-content-full-tests-20261017.log`; `evidence/integration/recovery-auxiliary-content-live-integrity-20261017.json`; `backend/app/data/recovery_auxiliary_headers.py`; `scripts/inspect_recovery_auxiliary_headers.py`; `docs/implementation/51_recovery_auxiliary_headers_validation.md`; `evidence/integration/recovery-auxiliary-headers-tests-20261017.log`; `evidence/integration/recovery-auxiliary-headers-independent-20261017.log`; `evidence/integration/recovery-auxiliary-headers-live-final-20261017.json`; `evidence/integration/recovery-auxiliary-headers-full-tests-20261017.log`; `evidence/integration/recovery-auxiliary-headers-live-integrity-20261017.json`; `backend/app/data/recovery_boundary.py`; `scripts/inspect_recovery_boundary.py`; `docs/implementation/52_recovery_boundary_validation.md`; `evidence/integration/recovery-boundary-tests-20261017.log`; `evidence/integration/recovery-boundary-independent-20261017.log`; `evidence/integration/recovery-boundary-live-final-20261017.json`; `evidence/integration/recovery-boundary-full-tests-20261017.log`; `evidence/integration/recovery-boundary-live-integrity-20261017.json`; `backend/app/data/recovery_boundary_topology.py`; `scripts/inspect_recovery_boundary_topology.py`; `docs/implementation/53_recovery_boundary_topology_validation.md`; `evidence/integration/recovery-boundary-topology-tests-20261017.log`; `evidence/integration/recovery-boundary-topology-independent-20261017.log`; `evidence/integration/recovery-boundary-topology-live-final-20261017.json`; `evidence/integration/recovery-boundary-topology-full-tests-20261017.log`; `evidence/integration/recovery-boundary-topology-live-integrity-20261017.json`; `backend/app/data/recovery_boundary_relations.py`; `scripts/inspect_recovery_boundary_relations.py`; `docs/implementation/54_recovery_boundary_relations_validation.md`; `evidence/integration/recovery-boundary-relations-tests-20261017.log`; `evidence/integration/recovery-boundary-relations-independent-20261017.log`; `evidence/integration/recovery-boundary-relations-live-final-20261017.json`; `evidence/integration/recovery-boundary-relations-full-tests-20261017.log`; `evidence/integration/recovery-boundary-relations-live-integrity-20261017.json`; `backend/app/data/recovery_source_footprints.py`; `scripts/inspect_recovery_source_footprints.py`; `docs/implementation/55_recovery_source_footprints_validation.md`; `evidence/integration/recovery-source-footprints-tests-20261017.log`; `evidence/integration/recovery-source-footprints-independent-20261017.log`; `evidence/integration/recovery-source-footprints-live-final-20261017.json`; `evidence/integration/recovery-source-footprints-full-tests-20261017.log`; `evidence/integration/recovery-source-footprints-live-integrity-20261017.json`; `backend/app/data/recovery_source_split_overlap.py`; `scripts/inspect_recovery_source_split_overlap.py`; `docs/implementation/56_recovery_source_split_overlap_validation.md`; `evidence/integration/recovery-source-split-overlap-tests-20261017.log`; `evidence/integration/recovery-source-split-overlap-independent-20261017.log`; `evidence/integration/recovery-source-split-overlap-plan-check-20261017.log`; `evidence/integration/recovery-source-split-overlap-live-final-20261017.json`; `evidence/integration/recovery-source-split-overlap-full-tests-20261017.log`; `evidence/integration/recovery-source-split-overlap-live-integrity-20261017.json`; `backend/app/data/recovery_readiness_comparison.py`; `scripts/inspect_recovery_readiness_comparison.py`; `docs/implementation/57_recovery_readiness_comparison_validation.md`; `evidence/integration/recovery-readiness-comparison-tests-20261017.log`; `evidence/integration/recovery-readiness-comparison-independent-20261017.log`; `evidence/integration/recovery-readiness-comparison-live-final-20261017.json`; `evidence/integration/recovery-readiness-comparison-full-tests-20261017.log`; `evidence/integration/recovery-readiness-comparison-live-integrity-20261017.json`; `backend/app/data/readiness_connectivity_witness.py`; `tests/test_readiness_connectivity_witness.py`; `docs/implementation/58_readiness_connectivity_witness_validation.md`; `evidence/integration/readiness-connectivity-witness-related-20261017.log`; `evidence/integration/readiness-connectivity-witness-independent-20261017.log`; `evidence/integration/readiness-connectivity-witness-live-absence-20261017.json`; `evidence/integration/readiness-connectivity-witness-full-tests-20261017.log`; `evidence/integration/readiness-connectivity-witness-live-integrity-20261017.json`; `backend/app/data/readiness_connectivity_envelope.py`; `tests/test_readiness_connectivity_envelope.py`; `docs/implementation/59_readiness_connectivity_envelope_validation.md`; `evidence/integration/readiness-connectivity-envelope-related-20261017.log`; `evidence/integration/readiness-connectivity-envelope-independent-20261017.log`; `evidence/integration/readiness-connectivity-envelope-live-absence-20261017.json`; `evidence/integration/readiness-connectivity-envelope-live-validation-20261017.json`; `evidence/integration/readiness-connectivity-envelope-full-tests-20261017.log`; `evidence/integration/readiness-connectivity-envelope-live-integrity-20261017.json`; `backend/app/ml/readiness.py`; `backend/app/ml/readiness_connectivity_adapter.py`; `tests/test_readiness_connectivity_adapter.py`; `docs/implementation/60_readiness_connectivity_adapter_validation.md`; `evidence/integration/readiness-connectivity-adapter-related-20261017.log`; `evidence/integration/readiness-connectivity-adapter-independent-20261017.log`; `evidence/integration/readiness-connectivity-adapter-ast-parity-20261017.json`; `evidence/integration/readiness-connectivity-adapter-live-saved-state-20261017.json`; `evidence/integration/readiness-connectivity-adapter-full-tests-20261017.log`; `evidence/integration/readiness-connectivity-adapter-live-integrity-20261017.json`; `scripts/run_experiment.py`; `tests/test_readiness_connectivity_cli.py`; `docs/implementation/61_readiness_connectivity_cli_validation.md`; `evidence/integration/readiness-connectivity-cli-related-20261017.log`; `evidence/integration/readiness-connectivity-cli-independent-20261017.log`; `evidence/integration/readiness-connectivity-cli-live-help-20261017.json`; `evidence/integration/readiness-connectivity-cli-ast-parity-20261017.json`; `evidence/integration/readiness-connectivity-cli-full-tests-20261017.log`; `evidence/integration/readiness-connectivity-cli-live-integrity-20261017.json`; `docs/implementation/62_readiness_connectivity_real_validation.md`; `data/first-group/readiness-connectivity-20261017.json`; `evidence/integration/readiness-connectivity-real-preflight-20261017.json`; `evidence/integration/readiness-connectivity-real-execution-20261017.json`; `evidence/integration/readiness-connectivity-real-validation-20261017.json`; `evidence/integration/readiness-connectivity-real-independent-20261017.log`; `evidence/integration/readiness-connectivity-real-token-membership-20261017.json`; `evidence/integration/readiness-connectivity-real-live-integrity-20261017.json`; `backend/app/data/readiness_connectivity_lineage.py`; `scripts/inspect_readiness_connectivity_lineage.py`; `tests/test_readiness_connectivity_lineage.py`; `docs/implementation/63_readiness_connectivity_lineage_validation.md`; `evidence/integration/readiness-connectivity-lineage-related-20261017.log`; `evidence/integration/readiness-connectivity-lineage-independent-20261017.log`; `evidence/integration/readiness-connectivity-lineage-live-cli-20261017.log`; `evidence/integration/readiness-connectivity-lineage-live-20261017.json`; `evidence/integration/readiness-connectivity-lineage-full-tests-20261017.log`; `evidence/integration/readiness-connectivity-lineage-live-integrity-20261017.json`; `docs/implementation/64_readiness_source_identity_contract.md`; `evidence/integration/readiness-source-identity-related-20261017.log`; `evidence/integration/readiness-source-identity-independent-20261017.log`; `evidence/integration/readiness-source-identity-full-tests-20261017.log`; `evidence/integration/readiness-source-identity-live-integrity-20261017.json`; `docs/implementation/65_readiness_source_identity_consumer.md`; `evidence/integration/readiness-source-identity-consumer-related-20261017.log`; `evidence/integration/readiness-source-identity-consumer-independent-20261017.log`; `evidence/integration/readiness-source-identity-consumer-live-cli-20261017.log`; `evidence/integration/readiness-source-identity-consumer-live-legacy-20261017.json`; `evidence/integration/readiness-source-identity-consumer-live-legacy-validation-20261017.json`; `evidence/integration/readiness-source-identity-consumer-full-tests-20261017.log`; `evidence/integration/readiness-source-identity-consumer-live-integrity-20261017.json`; `data/first-group/readiness-source-identity-20261017.json`; `evidence/integration/readiness-source-identity-real-preflight-20261017.json`; `evidence/integration/readiness-source-identity-real-execution-20261017.json`; `evidence/integration/readiness-source-identity-real-cli-20261017.log`; `evidence/integration/readiness-source-identity-real-lineage-20261017.json`; `evidence/integration/readiness-source-identity-real-lineage-cli-20261017.log`; `evidence/integration/readiness-source-identity-real-validation-20261017.json`; `evidence/integration/readiness-source-identity-real-independent-20261017.json`; `evidence/integration/readiness-source-identity-real-live-integrity-20261017.json`; `docs/implementation/66_readiness_source_identity_real_validation.md`; `backend/app/readiness_source_identity_api.py`; `backend/app/main.py`; `tests/test_readiness_source_identity_api.py`; `frontend/src/AgentCenter.tsx`; `frontend/src/ReadinessSourceIdentityDiagnostics.tsx`; `frontend/src/readinessSourceIdentityAdapter.ts`; `frontend/src/readinessSourceIdentityAdapter.test.mjs`; `frontend/src/readiness-source-identity.css`; `docs/implementation/67_readiness_source_identity_api.md`; `docs/implementation/68_readiness_source_identity_ui.md`; `evidence/integration/readiness-source-identity-api-related-20261017.log`; `evidence/integration/readiness-source-identity-api-independent-20261017.log`; `evidence/integration/readiness-source-identity-api-live-20261017.json`; `evidence/integration/readiness-source-identity-api-ui-full-tests-20261017.log`; `evidence/integration/readiness-source-identity-ui-adapter-20261017.log`; `evidence/integration/readiness-source-identity-ui-tests-20261017.log`; `evidence/integration/readiness-source-identity-ui-build-20261017.log`; `evidence/integration/readiness-source-identity-ui-independent-20261017.log`; `evidence/integration/readiness-source-identity-ui-live-20261017.json`; `evidence/integration/readiness-source-identity-ui-console-20261017.json`; `evidence/integration/readiness-source-identity-api-ui-live-integrity-20261017.json`; `backend/app/ml/candidate_plan_lineage.py`; `scripts/inspect_candidate_plan_lineage.py`; `tests/test_candidate_plan_lineage.py`; `docs/implementation/69_candidate_plan_lineage.md`; `evidence/integration/candidate-plan-lineage-related-20261017.log`; `evidence/integration/candidate-plan-lineage-independent-20261017.log`; `evidence/integration/candidate-plan-lineage-live-20261017.json`; `evidence/integration/candidate-plan-lineage-live-cli-20261017.log`; `evidence/integration/candidate-plan-lineage-full-tests-20261017.log`; `evidence/integration/candidate-plan-lineage-live-integrity-20261017.json`; `backend/app/ml/split_planning.py`; `backend/app/ml/split_json_io.py`; `tests/test_split_bounded_io.py`; `docs/implementation/70_split_bounded_io.md`; `evidence/integration/split-bounded-io-related-20261017.log`; `evidence/integration/split-bounded-io-independent-20261017.log`; `evidence/integration/split-bounded-io-live-20261017.json`; `evidence/integration/split-bounded-io-live-run-20261017.log`; `evidence/integration/split-bounded-io-full-tests-20261017.log`; `evidence/integration/split-bounded-io-live-integrity-20261017.json`; `backend/app/ml/candidate_materialization.py`; `scripts/materialize_split_candidate.py`; `tests/test_candidate_materialization.py`; `docs/implementation/71_candidate_materialization.md`; `evidence/integration/candidate-materialization-related-20261017.log`; `evidence/integration/candidate-materialization-independent-20261017.log`; `evidence/integration/candidate-materialization-live-cli-20261017.log`; `evidence/integration/candidate-materialization-live-validation-20261017.json`; `evidence/integration/candidate-materialization-full-tests-20261017.log`; `evidence/integration/candidate-materialization-live-integrity-20261017.json`; `evidence/integration/candidate-materialization-live-20261017/plan.json`; `evidence/integration/candidate-materialization-live-20261017/candidate.json`; `evidence/integration/candidate-materialization-live-20261017/receipt.json`; `backend/app/ml/candidate_staging.py`; `scripts/stage_split_candidate.py`; `tests/test_candidate_staging.py`; `docs/implementation/72_candidate_staging.md`; `evidence/integration/candidate-staging-related-20261017.log`; `evidence/integration/candidate-staging-independent-20261017.log`; `evidence/integration/candidate-staging-live-cli-20261017.log`; `evidence/integration/candidate-staging-live-validation-20261017.json`; `evidence/integration/candidate-staging-full-tests-20261017.log`; `evidence/integration/candidate-staging-live-integrity-20261017.json`; `data/first-group-candidate-qa-stage-20261017/candidate.json`; `data/first-group-candidate-qa-stage-20261017/staging-receipt.json`; `backend/app/ml/candidate_readiness_qa.py`; `scripts/assess_staged_candidate.py`; `tests/test_candidate_readiness_qa.py`; `docs/implementation/73_candidate_readiness_qa.md`; `evidence/integration/candidate-readiness-qa-related-20261017.log`; `evidence/integration/candidate-readiness-qa-independent-20261017.log`; `evidence/integration/candidate-readiness-qa-live-cli-20261017.log`; `evidence/integration/candidate-readiness-qa-live-execution-20261017.json`; `evidence/integration/candidate-readiness-qa-live-validation-20261017.json`; `evidence/integration/candidate-readiness-qa-full-tests-20261017.log`; `evidence/integration/candidate-readiness-qa-live-integrity-20261017.json`; `data/first-group-candidate-readiness-qa-20261017/readiness.json`; `data/first-group-candidate-readiness-qa-20261017/qa-receipt.json`; `backend/app/ml/candidate_qa_comparison.py`; `backend/app/candidate_qa_comparison_api.py`; `tests/test_candidate_qa_comparison.py`; `frontend/src/CandidateQaComparisonDiagnostics.tsx`; `frontend/src/candidateQaComparisonAdapter.ts`; `frontend/src/candidateQaComparisonAdapter.test.mjs`; `frontend/src/candidate-qa-comparison.css`; `docs/implementation/74_candidate_qa_comparison_api.md`; `docs/implementation/75_candidate_qa_comparison_ui.md`; `evidence/integration/candidate-qa-comparison-related-20261017.log`; `evidence/integration/candidate-qa-comparison-independent-20261017.log`; `evidence/integration/candidate-qa-comparison-ui-adapter-20261017.log`; `evidence/integration/candidate-qa-comparison-ui-tests-20261017.log`; `evidence/integration/candidate-qa-comparison-ui-build-20261017.log`; `evidence/integration/candidate-qa-comparison-ui-independent-20261017.log`; `evidence/integration/candidate-qa-comparison-live-http-20261017.json`; `evidence/integration/candidate-qa-comparison-ui-live-20261017.json`; `evidence/integration/candidate-qa-comparison-ui-console-before-fix-20261017.json`; `evidence/integration/candidate-qa-comparison-ui-console-after-fix-20261017.json`; `evidence/integration/candidate-qa-comparison-full-tests-20261017.log`; `evidence/integration/candidate-qa-comparison-live-integrity-20261017.json`; `backend/app/ml/bare_class_requirements.py`; `scripts/inspect_bare_class_requirements.py`; `tests/test_bare_class_requirements.py`; `docs/implementation/76_bare_class_requirements.md`; `evidence/integration/bare-class-requirements-related-20261017.log`; `evidence/integration/bare-class-requirements-independent-20261017.log`; `evidence/integration/bare-class-requirements-independent-arithmetic-20261017.json`; `evidence/integration/bare-class-requirements-live-20261017.json`; `evidence/integration/bare-class-requirements-live-cli-20261017.log`; `evidence/integration/bare-class-requirements-live-validation-20261017.json`; `evidence/integration/bare-class-requirements-full-tests-20261017.log`; `evidence/integration/bare-class-requirements-live-integrity-20261017.json`; `backend/app/execution_input_binding.py`; `tests/test_execution_input_binding.py`; `docs/implementation/77_execution_input_binding.md`; `evidence/integration/execution-input-binding-related-20261017.log`; `evidence/integration/execution-input-binding-independent-20261017.log`; `evidence/integration/execution-input-binding-live-validation-20261017.json`; `evidence/integration/execution-input-binding-live-replay-20261017.py`; `evidence/integration/execution-input-binding-full-tests-20261017.log`; `evidence/integration/execution-input-binding-live-integrity-20261017.json`; `backend/app/execution_binding_capture.py`; `backend/app/job_inputs.py`; `backend/app/gmais_api.py`; `tests/test_execution_binding_capture.py`; `docs/implementation/78_submission_binding_capture.md`; `evidence/integration/submission-binding-capture-related-20261017.log`; `evidence/integration/submission-binding-capture-independent-20261017.log`; `evidence/integration/submission-binding-capture-compat-before-20261017.json`; `evidence/integration/submission-binding-capture-compat-after-20261017.json`; `evidence/integration/submission-binding-capture-compat-runner-20261017.py`; `evidence/integration/submission-binding-capture-live-legacy-20261017.json`; `evidence/integration/submission-binding-capture-full-tests-20261017.log`; `evidence/integration/submission-binding-capture-live-integrity-20261017.json`; `backend/app/job_execution_binding_capture.py`; `backend/app/job_execution_binding_capture_api.py`; `tests/test_job_execution_binding_capture.py`; `frontend/src/StoredExecutionBindingCapture.tsx`; `frontend/src/storedExecutionBindingCaptureAdapter.ts`; `frontend/src/storedExecutionBindingCaptureAdapter.test.mjs`; `frontend/src/stored-execution-binding-capture.css`; `docs/implementation/79_stored_binding_capture_api.md`; `docs/implementation/80_stored_binding_capture_ui.md`; `evidence/integration/stored-binding-capture-related-20261017.log`; `evidence/integration/stored-binding-capture-live-api-20261017.json`; `evidence/integration/stored-binding-capture-live-ui-20261017.json`; `evidence/integration/stored-binding-capture-ui-adapter-20261017.log`; `evidence/integration/stored-binding-capture-ui-tests-20261017.log`; `evidence/integration/stored-binding-capture-ui-build-20261017.log`; `evidence/integration/job-execution-binding-capture-independent-20261017.log`; `evidence/integration/stored-execution-binding-capture-ui-independent-20261017.log`; `evidence/integration/stored-binding-capture-full-tests-20261017.log`; `evidence/integration/stored-binding-capture-live-integrity-20261017.json`; `backend/app/stored_job_binding_handoff.py`; `tests/test_stored_job_binding_handoff.py`; `docs/implementation/81_stored_job_binding_handoff.md`; `evidence/integration/stored-job-binding-handoff-related-20261017.log`; `evidence/integration/stored-binding-handoff-independent-20261017.log`; `evidence/integration/stored-binding-handoff-live-validation-20261017.json`; `evidence/integration/stored-binding-handoff-live-replay-20261017.py`; `evidence/integration/stored-binding-handoff-full-tests-20261017.log`; `evidence/integration/stored-binding-handoff-live-integrity-20261017.json`; `backend/app/stored_job_binding_handoff_store.py`; `tests/test_stored_job_binding_handoff_store.py`; `docs/implementation/82_stored_job_binding_handoff_store.md`; `evidence/integration/stored-binding-store-adapter-related-20261017.log`; `evidence/integration/stored-binding-store-adapter-independent-20261017.log`; `evidence/integration/stored-binding-store-adapter-live-validation-20261017.json`; `evidence/integration/stored-binding-store-adapter-live-check-20261017.py`; `evidence/integration/stored-binding-store-adapter-full-tests-20261017.log`; `evidence/integration/stored-binding-store-adapter-live-integrity-20261017.json`; `backend/app/stored_current_binding_preflight.py`; `tests/test_stored_current_binding_preflight.py`; `docs/implementation/83_stored_current_binding_preflight.md`; `evidence/integration/stored-current-binding-preflight-related-20261017.log`; `evidence/integration/stored-current-binding-independent-20261017.log`; `evidence/integration/stored-current-binding-live-validation-20261017.json`; `evidence/integration/stored-current-binding-live-check-20261017.py`; `evidence/integration/stored-current-binding-full-tests-20261017.log`; `evidence/integration/stored-current-binding-live-integrity-20261017.json`; `backend/app/stored_current_binding_preflight_api.py`; `tests/test_stored_current_binding_preflight_api.py`; `docs/implementation/84_current_input_preflight_api.md`; `docs/implementation/85_current_input_preflight_ui.md`; `frontend/src/CurrentInputPreflight.tsx`; `frontend/src/currentInputPreflightAdapter.ts`; `frontend/src/currentInputPreflightAdapter.test.mjs`; `frontend/src/current-input-preflight.css`; `evidence/integration/current-input-preflight-api-related-20261017.log`; `evidence/integration/stored-current-binding-api-independent-20261017.log`; `evidence/integration/current-input-preflight-live-api-20261017.json`; `evidence/integration/current-input-preflight-live-ui-20261017.json`; `evidence/integration/current-input-preflight-ui-desktop-20261017.jpg`; `evidence/integration/current-input-preflight-ui-adapter-20261017.log`; `evidence/integration/current-input-preflight-ui-tests-20261017.log`; `evidence/integration/current-input-preflight-ui-independent-20261017.log`; `evidence/integration/current-input-preflight-ui-build-20261017.log`; `evidence/integration/current-input-preflight-full-tests-20261017.log`; `evidence/integration/current-input-preflight-live-integrity-20261017.json`; `backend/app/workflow_node_input_handoff.py`; `tests/test_workflow_node_input_handoff.py`; `docs/implementation/86_workflow_node_input_handoff.md`; `evidence/integration/workflow-node-handoff-related-20261017.log`; `evidence/integration/workflow-node-handoff-independent-20261017.log`; `evidence/integration/workflow-node-handoff-full-tests-20261017.log`; `evidence/integration/workflow-node-handoff-live-integrity-20261017.json`; `evidence/integration/workflow-node-handoff-catalog-observation-20261017.json`; `evidence/integration/workflow-node-handoff-runtime-start-20261017.json`; `evidence/integration/workflow-node-handoff-full-interrupted-before-final-freeze-20261017.log`; `backend/app/workflow_node_input_handoff_api.py`; `tests/test_workflow_node_input_handoff_api.py`; `docs/implementation/87_workflow_node_handoff_api.md`; `docs/implementation/88_workflow_node_handoff_ui.md`; `frontend/src/WorkflowNodeHandoff.tsx`; `frontend/src/workflowNodeHandoffAdapter.ts`; `frontend/src/workflowNodeHandoffAdapter.test.mjs`; `frontend/src/workflow-node-handoff.css`; `frontend/src/GeoQuery.tsx`; `evidence/integration/workflow-node-handoff-canonical-fixture-20261017.json`; `evidence/integration/workflow-node-handoff-api-related-20261017.log`; `evidence/integration/workflow-node-handoff-api-independent-20261017.log`; `evidence/integration/workflow-node-handoff-api-live-api-20261017.json`; `evidence/integration/workflow-node-handoff-api-live-ui-20261017.json`; `evidence/integration/workflow-node-handoff-api-full-tests-20261017.log`; `evidence/integration/workflow-node-handoff-api-live-integrity-20261017.json`; `evidence/integration/workflow-node-handoff-ui-adapter-20261017.log`; `evidence/integration/workflow-node-handoff-ui-tests-20261017.log`; `evidence/integration/workflow-node-handoff-ui-independent-20261017.log`; `evidence/integration/workflow-node-handoff-ui-build-20261017.log`; `evidence/integration/workflow-node-handoff-ui-desktop-20261017.jpg`; `backend/app/workflow_job_request_handoff.py`; `tests/test_workflow_job_request_handoff.py`; `docs/implementation/89_workflow_job_request_handoff.md`; `evidence/integration/full-job-handoff-related-20261017.log`; `evidence/integration/full-job-handoff-independent-20261017.log`; `evidence/integration/full-job-handoff-initial-format-gap-20261017.log`; `evidence/integration/full-job-handoff-full-tests-20261017.log`; `evidence/integration/full-job-handoff-live-integrity-20261017.json`; `evidence/integration/full-job-handoff-catalog-observation-20261017.json`; `evidence/integration/full-job-handoff-runtime-start-20261017.json`; `backend/app/workflow_job_request_handoff_api.py`; `tests/test_workflow_job_request_handoff_api.py`; `docs/implementation/90_full_job_handoff_api.md`; `docs/implementation/91_full_job_handoff_ui.md`; `frontend/src/FullJobHandoff.tsx`; `frontend/src/fullJobHandoffAdapter.ts`; `frontend/src/fullJobHandoffAdapter.test.mjs`; `frontend/src/full-job-handoff.css`; `evidence/integration/full-job-handoff-api-related-20261017.log`; `evidence/integration/full-job-handoff-api-independent-20261017.log`; `evidence/integration/full-job-handoff-api-live-api-20261017.json`; `evidence/integration/full-job-handoff-api-live-ui-20261017.json`; `evidence/integration/full-job-handoff-api-full-tests-20261017.log`; `evidence/integration/full-job-handoff-api-live-integrity-20261017.json`; `evidence/integration/full-job-handoff-ui-adapter-20261017.log`; `evidence/integration/full-job-handoff-ui-tests-20261017.log`; `evidence/integration/full-job-handoff-ui-independent-20261017.log`; `evidence/integration/full-job-handoff-ui-build-20261017.log`; `evidence/integration/full-job-handoff-ui-desktop-20261017.jpg`; `backend/app/schema_formats.py`; `tests/test_schema_formats.py`; `docs/implementation/92_common_datetime_validation.md`; `evidence/integration/common-datetime-related-20261017.log`; `evidence/integration/common-datetime-independent-20261017.log`; `evidence/integration/common-datetime-source-runtime-20261017.json`; `evidence/integration/common-datetime-catalog-observation-20261017.json`; `evidence/integration/common-datetime-next-review-20261017.json`; `evidence/integration/common-datetime-full-tests-20261017.log`; `evidence/integration/common-datetime-live-integrity-20261017.json`; `backend/app/agent_capability_contract.py`; `tests/test_agent_capability_contract.py`; `docs/implementation/93_agent_capability_contract.md`; `evidence/integration/agent-capability-original-gmais-20261017.py`; `evidence/integration/agent-capability-related-20261017.log`; `evidence/integration/agent-capability-independent-20261017.log`; `evidence/integration/agent-capability-source-runtime-20261017.json`; `evidence/integration/agent-capability-next-review-20261017.json`; `evidence/integration/agent-capability-full-tests-20261017.log`; `evidence/integration/agent-capability-live-integrity-20261017.json`; `backend/app/workflow_job_registration_handoff.py`; `tests/test_workflow_job_registration_handoff.py`; `tests/test_workflow_job_registration_handoff_api.py`; `docs/implementation/94_full_job_registration_api.md`; `docs/implementation/95_full_job_registration_ui.md`; `frontend/src/fullJobRegistrationAdapter.ts`; `frontend/src/fullJobRegistrationAdapter.test.mjs`; `evidence/integration/full-job-registration-api-related-20261017.log`; `evidence/integration/full-job-registration-api-independent-20261017.log`; `evidence/integration/full-job-registration-api-live-api-20261017.json`; `evidence/integration/full-job-registration-api-live-ui-20261017.json`; `evidence/integration/full-job-registration-api-full-tests-20261017.log`; `evidence/integration/full-job-registration-api-live-integrity-20261017.json`; `evidence/integration/full-job-registration-api-original-20261017.py`; `evidence/integration/full-job-registration-ui-related-20261017.log`; `evidence/integration/full-job-registration-ui-tests-20261017.log`; `evidence/integration/full-job-registration-ui-independent-20261017.log`; `evidence/integration/full-job-registration-ui-build-20261017.log`; `evidence/integration/full-job-registration-ui-desktop-20261017.png`; `evidence/integration/full-job-registration-ui-blocked-20261017.png`; `backend/app/model_reference_contract.py`; `tests/test_model_reference_contract.py`; `docs/implementation/96_model_reference_contract.md`; `evidence/integration/model-ref-related-20261017.log`; `evidence/integration/model-ref-independent-20261017.log`; `evidence/integration/model-ref-source-runtime-20261017.json`; `evidence/integration/model-ref-full-tests-20261017.log`; `evidence/integration/model-ref-live-integrity-20261017.json`; `evidence/integration/model-ref-next-review-20261017.json`; `evidence/integration/model-ref-original-gmais-20261017.py`; `evidence/integration/model-ref-original-handoff-20261017.py`; `backend/app/experiment_registry.py`; `tests/test_model_version_declaration.py`; `docs/implementation/97_model_version_declaration.md`; `evidence/integration/model-version-related-20261017.log`; `evidence/integration/model-version-independent-20261017.log`; `evidence/integration/model-version-catalog-observation-20261017.json`; `evidence/integration/model-version-original-registry-20261017.py`; `evidence/integration/model-version-initial-tests-20261017.log`; `evidence/integration/model-version-full-tests-20261017.log`; `evidence/integration/model-version-live-integrity-20261017.json`; `evidence/integration/model-version-next-review-20261017.json`; `frontend/src/ModelReview.tsx`; `frontend/src/modelVersionRegistrationAdapter.ts`; `frontend/src/modelVersionRegistrationAdapter.test.mjs`; `frontend/src/model-version-registration.css`; `docs/implementation/98_model_version_registration_api.md`; `docs/implementation/99_model_version_registration_ui.md`; `evidence/integration/model-version-api-related-20261017.log`; `evidence/integration/model-version-api-independent-20261017.log`; `evidence/integration/model-version-api-live-api-20261017.json`; `evidence/integration/model-version-api-live-ui-20261017.json`; `evidence/integration/model-version-api-full-tests-20261017.log`; `evidence/integration/model-version-api-full-tests-corrected-20261017.log`; `evidence/integration/model-version-api-live-integrity-20261017.json`; `evidence/integration/model-version-api-original-main-20261017.py`; `evidence/integration/model-version-api-original-ui-20261017.tsx`; `evidence/integration/model-version-api-next-review-20261017.json`; `evidence/integration/model-version-ui-related-20261017.log`; `evidence/integration/model-version-ui-tests-20261017.log`; `evidence/integration/model-version-ui-independent-20261017.log`; `evidence/integration/model-version-ui-build-20261017.log`; `evidence/integration/model-version-ui-related-layout-20261017.log`; `evidence/integration/model-version-ui-tests-layout-20261017.log`; `evidence/integration/model-version-ui-build-layout-20261017.log`; `evidence/integration/model-version-ui-desktop-final-20261017.png`; `backend/app/model_registration_provenance.py`; `tests/test_model_registration_provenance.py`; `docs/implementation/100_model_registration_provenance_observation.md`; `evidence/integration/model-provenance-focused-20261017.log`; `evidence/integration/model-provenance-related-20261017.log`; `evidence/integration/model-provenance-independent-20261017.log`; `evidence/integration/model-provenance-catalog-observation-20261017.json`; `evidence/integration/model-provenance-live-integrity-20261017.json`; `tests/test_model_registration_provenance_api.py`; `docs/implementation/101_model_registration_provenance_api.md`; `docs/implementation/102_model_registration_provenance_ui.md`; `frontend/src/ModelRegistrationProvenance.tsx`; `frontend/src/modelRegistrationProvenanceAdapter.ts`; `frontend/src/modelRegistrationProvenanceAdapter.test.mjs`; `frontend/src/model-registration-provenance.css`; `evidence/integration/model-provenance-api-focused-20261017.log`; `evidence/integration/model-provenance-api-focused-corrected-20261017.log`; `evidence/integration/model-provenance-api-focused-final-20261017.log`; `evidence/integration/model-provenance-api-related-20261017.log`; `evidence/integration/model-provenance-api-independent-20261017.log`; `evidence/integration/model-provenance-api-live-api-20261017.json`; `evidence/integration/model-provenance-api-live-ui-20261017.json`; `evidence/integration/model-provenance-api-full-tests-20261017.log`; `evidence/integration/model-provenance-api-live-integrity-20261017.json`; `evidence/integration/model-provenance-api-next-review-20261017.json`; `evidence/integration/model-provenance-ui-related-20261017.log`; `evidence/integration/model-provenance-ui-tests-20261017.log`; `evidence/integration/model-provenance-ui-independent-20261017.log`; `evidence/integration/model-provenance-ui-build-20261017.log`; `evidence/integration/model-provenance-ui-desktop-20261017.png`; `backend/app/model_reference_record_comparison.py`; `tests/test_model_reference_record_comparison.py`; `docs/implementation/103_model_reference_record_comparison.md`; `evidence/integration/model-reference-record-focused-20261017.log`; `evidence/integration/model-reference-record-related-20261017.log`; `evidence/integration/model-reference-record-independent-20261017.log`; `evidence/integration/model-reference-record-catalog-observation-20261017.json`; `evidence/integration/model-reference-record-live-integrity-20261017.json`; `backend/app/workflow_job_model_record_handoff.py`; `tests/test_workflow_job_model_record_handoff.py`; `docs/implementation/104_workflow_job_model_record_handoff.md`; `evidence/integration/workflow-model-record-focused-20261017.log`; `evidence/integration/workflow-model-record-related-20261017.log`; `evidence/integration/workflow-model-record-independent-20261017.log`; `evidence/integration/workflow-model-record-catalog-observation-20261017.json`; `evidence/integration/workflow-model-record-live-integrity-20261017.json`; `backend/app/workflow_job_model_record_handoff_api.py`; `tests/test_workflow_job_model_record_handoff_api.py`; `docs/implementation/105_workflow_job_model_record_handoff_api.md`; `docs/implementation/106_workflow_model_record_handoff_ui.md`; `frontend/src/WorkflowModelRecordHandoff.tsx`; `frontend/src/workflowModelRecordHandoffAdapter.ts`; `frontend/src/workflowModelRecordHandoffAdapter.test.mjs`; `frontend/src/workflow-model-record-handoff.css`; `evidence/integration/workflow-model-record-api-focused-20261017.log`; `evidence/integration/workflow-model-record-api-related-20261017.log`; `evidence/integration/workflow-model-record-api-independent-20261017.log`; `evidence/integration/workflow-model-record-api-full-tests-20261017.log`; `evidence/integration/workflow-model-record-api-full-tests-final-20261017.log`; `evidence/integration/workflow-model-record-api-live-api-20261017.json`; `evidence/integration/workflow-model-record-api-live-ui-20261017.json`; `evidence/integration/workflow-model-record-api-live-integrity-20261017.json`; `evidence/integration/workflow-model-record-api-test-compat-baseline-20261017.json`; `evidence/integration/workflow-model-record-api-test-compat-focused-20261017.log`; `evidence/integration/workflow-model-record-api-test-compat-original-20261017.py`; `evidence/integration/workflow-model-record-api-test-compat-result-20261017.json`; `evidence/integration/workflow-model-record-api-next-queue-review-20261017.json`; `evidence/integration/workflow-model-record-ui-related-initial-failure-20261017.log`; `evidence/integration/workflow-model-record-ui-related-20261017.log`; `evidence/integration/workflow-model-record-ui-independent-20261017.log`; `evidence/integration/workflow-model-record-ui-tests-20261017.log`; `evidence/integration/workflow-model-record-ui-build-20261017.log`; `evidence/integration/workflow-model-record-ui-desktop-20261017.png`; `backend/app/workflow_dependency_order.py`; `tests/test_workflow_dependency_order.py`; `backend/app/workflow_policy.py`; `docs/implementation/107_workflow_dependency_order.md`; `evidence/integration/workflow-dependency-order-focused-20261017.log`; `evidence/integration/workflow-dependency-order-focused-final-20261017.log`; `evidence/integration/workflow-dependency-order-related-20261017.log`; `evidence/integration/workflow-dependency-order-independent-20261017.log`; `evidence/integration/workflow-dependency-order-independent-review-20261017.json`; `evidence/integration/workflow-dependency-order-full-tests-20261017.log`; `evidence/integration/workflow-dependency-order-live-integrity-20261017.json`; `evidence/integration/workflow-dependency-order-preflight-20261017.json`; `evidence/integration/workflow-dependency-order-original-gmais_api-20261017.py`; `evidence/integration/workflow-dependency-order-original-workflow_lineage-20261017.py`; `evidence/integration/workflow-dependency-order-original-workflow_policy-20261017.py`; `backend/app/ml/bare_patch_feasibility.py`; `scripts/inspect_bare_patch_feasibility.py`; `tests/test_bare_patch_feasibility.py`; `docs/implementation/108_bare_patch_feasibility.md`; `evidence/integration/bare-class-patch-feasibility-focused-20261017.log`; `evidence/integration/bare-class-patch-feasibility-related-20261017.log`; `evidence/integration/bare-class-patch-feasibility-related-corrected-20261017.log`; `evidence/integration/bare-class-patch-feasibility-independent-20261017.log`; `evidence/integration/bare-class-patch-feasibility-independent-review-20261017.json`; `evidence/integration/bare-class-patch-feasibility-live-20261017.json`; `evidence/integration/bare-class-patch-feasibility-live-cli-20261017.log`; `evidence/integration/bare-class-patch-feasibility-live-integrity-20261017.json`; `evidence/integration/bare-class-patch-feasibility-collection-next-review-20261017.json`; `backend/app/data/recovery_commit_contract.py`; `tests/test_recovery_commit_contract.py`; `docs/implementation/109_area_completion_audit.md`; `docs/implementation/110_recovery_commit_contract.md`; `scripts/collect_training_parallel.py`; `backend/app/data/budget.py`; `evidence/integration/recovery-commit-contract-focused-20261017.log`; `evidence/integration/recovery-commit-contract-focused-final-20261017.log`; `evidence/integration/recovery-commit-contract-focused-final2-20261017.log`; `evidence/integration/recovery-commit-contract-related-20261017.log`; `evidence/integration/recovery-commit-contract-related-final-20261017.log`; `evidence/integration/recovery-commit-contract-related-final2-20261017.log`; `evidence/integration/recovery-commit-contract-independent-before-key-guard-20261017.log`; `evidence/integration/recovery-commit-contract-independent-20261017.log`; `evidence/integration/recovery-commit-contract-independent-final3-20261017.log`; `evidence/integration/recovery-commit-contract-preflight-20261017.json`; `evidence/integration/recovery-commit-contract-live-integrity-20261017.json`; `evidence/integration/recovery-commit-contract-external-dependencies-20261017.json`; `docs/implementation/111_data_pipeline_completion.md`; `docs/implementation/112_lcluc_ml_completion.md`; `docs/implementation/113_lcluc_integration_acceptance.md`; `docs/implementation/114_geollm_technical_review.md`; `backend/app/data/collection_registration.py`; `scripts/register_collection.py`; `tests/test_collection_version_registration.py`; `backend/app/ml/error_analysis.py`; `backend/app/ml/service.py`; `backend/app/ml/network.py`; `tests/test_ml_error_analysis.py`; `scripts/evaluate_geollm_local.py`; `scripts/evaluate_geollm_tools.py`; `tests/test_geollm_local_evaluation.py`; `tests/test_geollm_tool_evaluation.py`; `evidence/integration/data-pipeline-inventory-20261018.json`; `evidence/integration/data-pipeline-focused-final-20261018.log`; `evidence/integration/data-pipeline-related-final-20261018.log`; `evidence/integration/data-pipeline-independent-20261018.log`; `evidence/integration/data-pipeline-independent-review-20261018.json`; `evidence/integration/lcluc-ml-architecture-20261018.json`; `evidence/integration/lcluc-ml-error-analysis-focused-20261018.log`; `evidence/integration/lcluc-ml-error-analysis-related-20261018.log`; `evidence/integration/lcluc-ml-error-analysis-integrity-20261018.json`; `evidence/integration/lcluc-ml-existing-report-error-analysis-20261018.json`; `evidence/integration/geollm-local-evaluation-20261018.json`; `evidence/integration/geollm-native-tools-20261018.json`; `evidence/integration/geollm-runtime-audit-20261018.json`; `evidence/integration/geollm-evaluation-tests-final3-20261018.log`; `evidence/integration/geollm-independent-tests-final-20261018.log`; `evidence/integration/geollm-independent-review-20261018.json`; `evidence/integration/lcluc-geollm-full-tests-20261018.log`; `evidence/integration/lcluc-geollm-live-integrity-final-20261018.json`; `backend/app/lcluc_workflow.py`; `scripts/run_lcluc_workflow.py`; `tests/test_lcluc_workflow.py`; `docs/implementation/115_lcluc_workflow_executor.md`; `evidence/integration/lcluc-workflow-source-freeze-20261018.json`; `evidence/integration/lcluc-workflow-focused-final4-20261018.log`; `evidence/integration/lcluc-workflow-independent-final2-20261018.log`; `evidence/integration/lcluc-workflow-independent-related-20261018.log`; `evidence/integration/lcluc-workflow-independent-review-20261018.json`; `evidence/integration/lcluc-workflow-full-tests-20261018.log`; `evidence/integration/lcluc-workflow-live-integrity-20261018.json`; `backend/app/lcluc_workflow_api.py`; `tests/test_lcluc_workflow_api.py`; `frontend/src/LclucWorkflowPanel.tsx`; `frontend/src/lclucWorkflowAdapter.ts`; `frontend/src/lclucWorkflowClient.ts`; `frontend/src/lcluc-workflow.css`; `frontend/src/ModelAnalysisWorkspace.tsx`; `docs/implementation/116_lcluc_workflow_api.md`; `docs/implementation/117_lcluc_workflow_ui.md`; `evidence/integration/lcluc-workflow-api-focused-final2-20261018.log`; `evidence/integration/lcluc-workflow-api-independent-tests-20261018.log`; `evidence/integration/lcluc-workflow-api-route-preservation-tests-20261018.log`; `evidence/integration/lcluc-workflow-ui-related-final-20261018.log`; `evidence/integration/lcluc-workflow-ui-tests-final-20261018.log`; `evidence/integration/lcluc-workflow-ui-build-final-20261018.log`; `evidence/integration/lcluc-workflow-ui-browser-20261018.json`; `evidence/integration/lcluc-workflow-api-live-integrity-20261018.json`; `evidence/integration/lcluc-workflow-api-live-route-20261018.json`; `evidence/integration/lcluc-workflow-ui-related-final3-20261018.log`; `evidence/integration/lcluc-workflow-ui-tests-final2-20261018.log`; `evidence/integration/lcluc-workflow-ui-build-final2-20261018.log`; `evidence/integration/lcluc-workflow-api-full-tests-20261018.log`; `evidence/integration/lcluc-workflow-api-related-20261018.log`; `evidence/integration/lcluc-workflow-ui-build-final3-20261018.log`; `evidence/integration/lcluc-workflow-ui-synthetic-desktop-final2-20261018.png`; `frontend/src/lclucChangeMapAdapter.ts`; `frontend/src/LclucWorkflowChangeMap.tsx`; `docs/implementation/118_lcluc_workflow_change_map.md`; `evidence/integration/lcluc-change-map-adapter-focused-20261018.log`; `evidence/integration/lcluc-change-map-ui-related-final-20261018.log`; `evidence/integration/lcluc-change-map-generated-fixture-20261018.json`; `evidence/integration/lcluc-change-map-independent-20261018.log`; `evidence/integration/lcluc-change-map-core-focused-20261018.log`; `evidence/integration/lcluc-change-map-core-api-final-20261018.log`; `evidence/integration/lcluc-change-map-nonempty-initial-diagnostic-20261018.log`; `evidence/integration/lcluc-change-map-ui-tests-20261018.log`; `evidence/integration/lcluc-change-map-ui-build-20261018.log`; `evidence/integration/lcluc-change-map-full-backend-20261018.log`; `evidence/integration/lcluc-change-map-live-integrity-20261018.json`; `evidence/integration/lcluc-change-map-browser-20261018.json`; `evidence/integration/lcluc-change-map-nonempty-20261018.png`; `evidence/integration/lcluc-change-map-empty-20261018.png`; `frontend/src/lclucTransitionAdapter.ts`; `frontend/src/LclucTransitionSummary.tsx`; `evidence/integration/lcluc-transition-adapter-focused-final-20261018.log`; `evidence/integration/lcluc-transition-ui-related-20261018.log`; `evidence/integration/lcluc-transition-independent-20261018.log`; `evidence/integration/lcluc-transition-generated-fixture-20261018.json`; `docs/implementation/119_lcluc_transition_matrix.md`; `evidence/integration/lcluc-transition-ui-tests-20261018.log`; `evidence/integration/lcluc-transition-ui-build-20261018.log`; `evidence/integration/lcluc-transition-ui-build-initial-20261018.log`; `evidence/integration/lcluc-transition-browser-20261018.json`; `evidence/integration/lcluc-transition-live-integrity-20261018.json`; `evidence/integration/lcluc-transition-matrix-final-20261018.png`; `evidence/integration/lcluc-transition-class-map-20261018.png`; `backend/app/model_error_analysis_api.py`; `tests/test_model_error_analysis_api.py`; `docs/implementation/120_model_error_analysis_read.md`; `evidence/integration/model-error-analysis-api-focused-final-20261018.log`; `evidence/integration/model-error-analysis-api-related-20261018.log`; `evidence/integration/model-error-read-route-guards-20261018.log`; `frontend/src/ModelErrorAnalysis.tsx`; `frontend/src/modelErrorAnalysisAdapter.ts`; `frontend/src/modelErrorAnalysisClient.ts`; `frontend/src/model-error-analysis.css`; `docs/implementation/121_model_error_analysis_ui.md`; `evidence/integration/model-error-analysis-ui-related-final2-20261018.log`; `evidence/integration/model-error-analysis-ui-tests-final-20261018.log`; `evidence/integration/model-error-analysis-ui-build-final-20261018.log`; `evidence/integration/model-error-read-independent-20261018.json`; `evidence/integration/model-error-read-browser-20261018.json`; `evidence/integration/model-error-read-live-integrity-20261018.json`; `evidence/integration/model-error-read-backend-all-20261018.log`; `backend/app/ml/per_scene_normalization_contract.py`; `tests/test_per_scene_normalization_contract.py`; `backend/app/ml/normalization.py`; `evidence/integration/per-scene-contract-focused-20261018.log`; `evidence/integration/per-scene-contract-existing-boundaries-20261018.log`; `docs/implementation/122_per_scene_normalization_contract.md`; `evidence/integration/per-scene-contract-independent-20261018.json`; `evidence/integration/per-scene-contract-independent-20261018.log`; `evidence/integration/per-scene-contract-runtime-boundary-20261018.json`; `evidence/integration/per-scene-contract-runtime-boundary-20261018.log`; `evidence/integration/per-scene-contract-live-integrity-20261018.json`; `backend/app/ml/per_scene_normalization_files.py`; `tests/test_per_scene_normalization_files.py`; `evidence/integration/per-scene-files-focused-final-20261018.log`; `evidence/integration/per-scene-files-related-20261018.log`; `evidence/integration/per-scene-files-runtime-comparison-20261018.json`; `evidence/integration/per-scene-files-live-integrity-20261018.json`; `docs/implementation/123_per_scene_normalization_files.md`; `evidence/integration/per-scene-files-independent-20261018.json`; `evidence/integration/per-scene-files-independent-20261018.log`; `evidence/integration/per-scene-files-independent-initial-20261018.json`; `evidence/integration/per-scene-files-independent-initial-20261018.log`; `backend/app/ml/model_checkpoint_manifest.py`; `tests/test_model_checkpoint_manifest.py`; `evidence/integration/model-manifest-read-agent-focused-final-20261018.log`; `evidence/integration/model-manifest-read-root-related-20261018.log`; `evidence/integration/model-manifest-read-runtime-20261018.json`; `evidence/integration/model-manifest-read-live-integrity-20261018.json`; `docs/implementation/124_model_checkpoint_manifest.md`; `evidence/integration/model-manifest-read-independent-20261018.json`; `evidence/integration/model-manifest-read-independent-20261018.log`; `evidence/integration/model-manifest-read-agent-focused-20261018.log`; `backend/app/ml/registered_per_scene_files.py`; `tests/test_registered_per_scene_files.py`; `docs/implementation/125_registered_per_scene_files.md`; `backend/app/dataset_registry.py`; `evidence/integration/registry-normalization-agent-focused-20261018.log`; `evidence/integration/registry-normalization-root-related-20261018.log`; `evidence/integration/registry-normalization-runtime-20261018.json`; `evidence/integration/registry-normalization-live-integrity-20261018.json`; `evidence/integration/registry-normalization-independent-20261018.json`; `evidence/integration/registry-normalization-independent-20261018.log`; `backend/app/ml/pinned_scene_normalization.py`; `tests/test_pinned_scene_normalization.py`; `evidence/integration/pinned-scene-agent-20261018-focused.log`; `evidence/integration/pinned-scene-runtime-20261018.json`; `evidence/integration/pinned-scene-operating-inventory-20261018.json`; `docs/implementation/126_pinned_scene_normalization.md`; `evidence/integration/pinned-scene-root-related-20261018.log`; `evidence/integration/pinned-scene-runtime-initial-20261018.log`; `evidence/integration/pinned-scene-live-integrity-20261018.json`; `evidence/integration/pinned-scene-independent-20261018.json`; `evidence/integration/pinned-scene-independent-20261018.log`; `backend/app/ml/pinned_annual_normalization.py`; `tests/test_pinned_annual_normalization.py`; `evidence/integration/annual-normalization-agent-20261018-focused.log`; `evidence/integration/annual-normalization-operating-inventory-20261018.json`; `docs/implementation/127_pinned_annual_normalization.md`; `evidence/integration/annual-normalization-root-related-20261018.log`; `evidence/integration/annual-normalization-runtime-20261018.json`; `evidence/integration/annual-normalization-live-integrity-20261018.json`; `evidence/integration/annual-normalization-independent-20261018.json`; `evidence/integration/annual-normalization-independent-20261018.log`; `backend/app/ml/registry_temporal_normalization.py`; `tests/test_registry_temporal_normalization.py`; `evidence/integration/temporal-normalization-agent-20261018-focused-final.log`; `evidence/integration/temporal-normalization-agent-20261018-focused.log`; `evidence/integration/temporal-normalization-live-integrity-20261018.json`; `evidence/integration/temporal-normalization-operating-inventory-20261018.json`; `docs/implementation/128_registry_temporal_normalization.md`; `evidence/integration/temporal-normalization-root-related-20261018.log`; `evidence/integration/temporal-normalization-runtime-20261018.json`; `evidence/integration/temporal-normalization-independent-20261018.json`; `evidence/integration/temporal-normalization-independent-20261018.log`; `backend/app/ml/registry_raster_grid_normalization.py`; `tests/test_registry_raster_grid_normalization.py`; `evidence/integration/raster-grid-agent-20261018-focused-final.log`; `evidence/integration/raster-grid-agent-20261018-focused.log`; `evidence/integration/raster-grid-live-integrity-20261018.json`; `evidence/integration/raster-grid-operating-inventory-20261018.json`; `docs/implementation/129_registry_raster_grid_normalization.md`; `evidence/integration/raster-grid-root-related-20261018.log`; `evidence/integration/raster-grid-runtime-20261018.json`; `evidence/integration/raster-grid-independent-20261018.json`; `evidence/integration/raster-grid-independent-20261018.log`; `backend/app/ml/registry_spatial_normalization.py`; `tests/test_registry_spatial_normalization.py`; `evidence/integration/registry-spatial-agent-20261018-focused.log`; `evidence/integration/registry-spatial-live-integrity-20261018.json`; `evidence/integration/registry-spatial-operating-inventory-20261018.json`; `docs/implementation/130_registry_spatial_normalization.md`; `evidence/integration/registry-spatial-root-related-20261018.log`; `evidence/integration/registry-spatial-runtime-20261018.json`; `evidence/integration/registry-spatial-independent-20261018.json`; `evidence/integration/registry-spatial-independent-20261018.log`; `backend/app/ml/registered_quality_mask_files.py`; `tests/test_registered_quality_mask_files.py`; `evidence/integration/quality-mask-agent-20261018-focused.log`; `evidence/integration/quality-mask-operating-inventory-20261018.json`; `docs/implementation/131_registered_quality_mask_files.md`; `evidence/integration/quality-mask-agent-20261018-focused-final.log`; `evidence/integration/quality-mask-root-related-20261018.log`; `evidence/integration/quality-mask-runtime-20261018.json`; `evidence/integration/quality-mask-live-integrity-20261018.json`; `evidence/integration/quality-mask-independent-20261018.json`; `evidence/integration/quality-mask-independent-20261018.log`; `backend/app/ml/registered_quality_mask_grid.py`; `tests/test_registered_quality_mask_grid.py`; `docs/implementation/132_registered_quality_mask_grid.md`; `evidence/integration/mask-grid-agent-20261018-focused.log`; `evidence/integration/mask-grid-independent-20261018.json`; `evidence/integration/mask-grid-independent-20261018.log`; `evidence/integration/mask-grid-operating-inventory-20261018.json`; `evidence/integration/mask-grid-root-related-final-20261018.log`; `evidence/integration/mask-grid-root-related-20261018.log`; `evidence/integration/mask-grid-runtime-20261018.json`; `evidence/integration/mask-grid-live-integrity-20261018.json`; `backend/app/ml/registered_binary_mask_values.py`; `tests/test_registered_binary_mask_values.py`; `evidence/integration/binary-mask-agent-20261018-focused.log`; `docs/implementation/133_registered_binary_mask_values.md`; `evidence/integration/binary-mask-root-related-20261018.log`; `evidence/integration/binary-mask-runtime-20261018.json`; `evidence/integration/binary-mask-live-integrity-20261018.json`; `evidence/integration/binary-mask-operating-inventory-20261018.json`; `evidence/integration/binary-mask-independent-20261018.json`; `evidence/integration/binary-mask-independent-20261018.log`; `backend/app/ml/annual_quality_mask_diagnostics.py`; `tests/test_annual_quality_mask_diagnostics.py`; `docs/implementation/134_annual_quality_mask_diagnostics.md`; `evidence/integration/annual-mask-agent-20261018-focused-final.log`; `evidence/integration/annual-mask-agent-20261018-focused.log`; `evidence/integration/annual-mask-root-related-20261018.log`; `evidence/integration/annual-mask-runtime-20261018.json`; `evidence/integration/annual-mask-live-integrity-20261018.json`; `evidence/integration/annual-mask-operating-inventory-20261018.json`; `evidence/integration/annual-mask-independent-20261018.json`; `evidence/integration/annual-mask-independent-20261018.log`; `backend/app/ml/annual_mask_policy.py`; `tests/test_annual_mask_policy.py`; `docs/implementation/135_annual_mask_policy.md`; `evidence/integration/annual-mask-policy-agent-20261018-focused.log`; `evidence/integration/mask-policy-root-related-20261018.log`; `evidence/integration/mask-policy-runtime-20261018.json`; `evidence/integration/mask-policy-live-integrity-20261018.json`; `evidence/integration/mask-policy-operating-inventory-20261018.json`; `evidence/integration/mask-policy-independent-20261018.json`; `evidence/integration/mask-policy-independent-20261018.log`; `backend/app/annual_diagnostics_service.py`; `tests/test_annual_diagnostics_service.py`; `docs/implementation/136_annual_diagnostics_service.md`; `contracts/internal/lcluc-annual-diagnostics-request.schema.json`; `contracts/internal/lcluc-annual-diagnostics-response.schema.json`; `evidence/integration/diagnostic-service-agent-20261018-focused-final.log`; `evidence/integration/diagnostic-service-agent-20261018-focused-final2.log`; `evidence/integration/diagnostic-service-runtime-20261018.json`; `evidence/integration/diagnostic-service-runtime-final-20261018.log`; `evidence/integration/diagnostic-service-live-integrity-20261018.json`; `evidence/integration/diagnostic-service-operating-inventory-20261018.json`; `evidence/integration/diagnostic-service-root-related-final-20261018.log`; `evidence/integration/diagnostic-service-root-related-20261018.log`; `evidence/integration/diagnostic-service-runtime-20261018.log`; `evidence/integration/diagnostic-service-independent-20261018.json`; `evidence/integration/diagnostic-service-independent-20261018.log`; `backend/app/annual_diagnostics_api.py`; `tests/test_annual_diagnostics_api.py`; `frontend/src/AnnualInputDiagnostics.tsx`; `frontend/src/annualInputDiagnosticsAdapter.ts`; `frontend/src/annualInputDiagnosticsClient.ts`; `frontend/src/annual-input-diagnostics.css`; `evidence/integration/diagnostic-api-agent-20261018-focused-final3.log`; `evidence/integration/annual-input-diagnostics-ui-front-20261018.log`; `evidence/integration/annual-input-diagnostics-ui-build-final2-20261018.log`; `docs/implementation/137_annual_diagnostics_api_ui.md`; `evidence/integration/diagnostic-api-live-http-20261018.json`; `evidence/integration/diagnostic-api-browser-20261018.json`; `evidence/integration/diagnostic-api-operating-inventory-20261018.json`; `evidence/integration/diagnostic-api-live-integrity-20261018.json`; `evidence/integration/diagnostic-api-compat-tests-final2-20261018.log`; `evidence/integration/diagnostic-api-compat-tests-final-20261018.log`; `evidence/integration/diagnostic-api-compat-test-update-20261018.json`; `evidence/integration/diagnostic-api-live-integrity-final-20261018.json`; `evidence/integration/diagnostic-api-root-full-backend-20261018.log`; `evidence/integration/diagnostic-api-root-full-backend-final2-20261018.log`; `evidence/integration/diagnostic-api-final-processes-20261018.json`; `backend/app/data/quality_mask_bundle.py`; `tests/test_quality_mask_bundle.py`; `evidence/integration/quality-mask-bundle-agent-20261018.log`; `docs/implementation/138_quality_mask_bundle.md`; `evidence/integration/quality-mask-bundle-root-related-20261018.log`; `evidence/integration/quality-mask-bundle-independent-20261018.json`; `evidence/integration/quality-mask-bundle-independent-20261018.log`; `evidence/integration/quality-mask-bundle-independent-initial-20261018.json`; `evidence/integration/quality-mask-bundle-independent-initial-20261018.log`; `evidence/integration/quality-mask-bundle-live-integrity-final-20261018.json`; `evidence/integration/quality-mask-bundle-operating-inventory-20261018.json`; `backend/app/data/quality_report_completion.py`; `tests/test_quality_report_completion.py`; `docs/implementation/139_quality_report_completion.md`; `evidence/integration/quality-report-completion-agent-20261018.log`; `evidence/integration/quality-report-completion-agent-final-20261018.log`; `evidence/integration/quality-report-completion-root-related-20261018.log`; `evidence/integration/quality-report-completion-root-related-final2-20261018.log`; `evidence/integration/quality-report-completion-independent-20261018.json`; `evidence/integration/quality-report-completion-independent-20261018.log`; `evidence/integration/quality-report-completion-independent-initial-20261018.json`; `evidence/integration/quality-report-completion-independent-initial-20261018.log`; `evidence/integration/quality-report-completion-live-integrity-final-20261018.json`; `evidence/integration/quality-report-completion-operating-inventory-20261018.json`; `backend/app/data/quality_report_storage.py`; `tests/test_quality_report_storage.py`; `docs/implementation/140_quality_report_storage.md`; `evidence/integration/quality-report-storage-agent-20261018.log`; `evidence/integration/quality-report-storage-agent-initial-20261018.log`; `evidence/integration/quality-report-storage-root-related-final-20261018.log`; `evidence/integration/quality-report-storage-root-related-20261018.log`; `evidence/integration/quality-report-storage-root-related-initial-20261018.log`; `evidence/integration/quality-report-storage-independent-20261018.json`; `evidence/integration/quality-report-storage-independent-20261018.log`; `evidence/integration/quality-report-storage-independent-initial-20261018.json`; `evidence/integration/quality-report-storage-independent-initial-20261018.log`; `evidence/integration/quality-report-storage-independent-pre-native-guard-20261018.json`; `evidence/integration/quality-report-storage-independent-pre-native-guard-20261018.log`; `evidence/integration/quality-report-storage-live-integrity-final-20261018.json`; `evidence/integration/quality-report-storage-operating-inventory-20261018.json`; `backend/app/data/quality_report_preflight.py`; `tests/test_quality_report_preflight.py`; `docs/implementation/141_quality_report_preflight.md`; `evidence/integration/quality-report-preflight-agent-20261018.log`; `evidence/integration/quality-report-preflight-agent-initial-20261018.log`; `evidence/integration/quality-report-preflight-root-related-20261018.log`; `evidence/integration/quality-report-preflight-independent-20261018.json`; `evidence/integration/quality-report-preflight-independent-20261018.log`; `evidence/integration/quality-report-preflight-independent-initial-20261018.json`; `evidence/integration/quality-report-preflight-independent-initial-20261018.log`; `evidence/integration/quality-report-preflight-live-integrity-final-20261018.json`; `evidence/integration/quality-report-preflight-operating-inventory-20261018.json`; `backend/app/data/quality_report_registration.py`; `tests/test_quality_report_registration.py`; `docs/implementation/142_quality_report_registration.md`; `evidence/integration/quality-report-registration-agent-20261018.log`; `evidence/integration/quality-report-registration-agent-initial-20261018.log`; `evidence/integration/quality-report-registration-agent-initial2-20261018.log`; `evidence/integration/quality-report-registration-root-related-20261018.log`; `evidence/integration/quality-report-registration-independent-20261018.py`; `evidence/integration/quality-report-registration-independent-20261018.json`; `evidence/integration/quality-report-registration-independent-20261018.log`; `evidence/integration/quality-report-registration-independent-initial-20261018.py`; `evidence/integration/quality-report-registration-independent-initial-20261018.json`; `evidence/integration/quality-report-registration-independent-initial-20261018.log`; `evidence/integration/quality-report-registration-live-integrity-final-20261018.json`; `evidence/integration/quality-report-registration-operating-inventory-20261018.json`; `scripts/quality_report_cli.py`; `tests/test_quality_report_cli.py`; `docs/implementation/143_quality_report_cli.md`; `evidence/integration/quality-report-cli-agent-20261018.log`; `evidence/integration/quality-report-cli-agent-initial-20261018.log`; `evidence/integration/quality-report-cli-root-related-20261018.log`; `evidence/integration/quality-report-cli-independent-20261018.py`; `evidence/integration/quality-report-cli-independent-20261018.json`; `evidence/integration/quality-report-cli-independent-20261018.log`; `evidence/integration/quality-report-cli-live-integrity-final-20261018.json`; `evidence/integration/quality-report-cli-operating-inventory-20261018.json`; `scripts/collect_samples.py`; `tests/test_collection_raster_declarations.py`; `docs/implementation/144_collection_raster_declarations.md`; `evidence/integration/collection-raster-declarations-agent-20261018.log`; `evidence/integration/collection-raster-declarations-agent-initial-20261018.log`; `evidence/integration/collection-raster-declarations-independent-20261018.py`; `evidence/integration/collection-raster-declarations-independent-20261018.json`; `evidence/integration/collection-raster-declarations-independent-20261018.log`; `evidence/integration/collection-raster-declarations-root-related-20261018.log`; `evidence/integration/collection-raster-declarations-source-scope-20261018.json`; `evidence/integration/collection-raster-declarations-full-20261018.log`; `evidence/integration/collection-raster-declarations-operating-inventory-20261018.json`; `evidence/integration/collection-raster-declarations-live-integrity-final-20261018.json`; `evidence/integration/collection-raster-declarations-live-integrity-initial-20261018.json`; `evidence/integration/collection-raster-declarations-source-scope-20261018.py`; `scripts/collect_training_grid.py`; `tests/test_grid_patch_declarations.py`; `evidence/integration/grid-patch-declarations-agent-20261018.log`; `evidence/integration/grid-patch-declarations-agent-initial-20261018.log`; `evidence/integration/grid-patch-declarations-source-scope-20261018.json`; `evidence/integration/grid-patch-declarations-operating-inventory-20261018.json`; `docs/implementation/145_grid_patch_declarations.md`; `evidence/integration/grid-patch-declarations-independent-20261018.py`; `evidence/integration/grid-patch-declarations-independent-20261018.json`; `evidence/integration/grid-patch-declarations-independent-20261018.log`; `evidence/integration/grid-patch-declarations-live-integrity-final-20261018.json`; `evidence/integration/grid-patch-declarations-root-related-20261018.log`; `evidence/integration/grid-patch-declarations-full-20261018.log`; `evidence/integration/grid-patch-declarations-final-processes-20261018.json`; `scripts/register_dataset_version.py`; `tests/test_source_raster_registration_cli.py`; `evidence/integration/source-raster-registration-cli-agent-20261018.log`; `evidence/integration/source-raster-registration-cli-self-catalog-reproduction-20261018.py`; `evidence/integration/source-raster-registration-cli-self-catalog-reproduction-20261018.json`; `evidence/integration/source-raster-registration-cli-self-catalog-reproduction-20261018.log`; `evidence/integration/source-raster-registration-cli-agent-initial-20261018.log`; `docs/implementation/146_source_raster_registration_cli.md`; `evidence/integration/source-raster-registration-cli-independent-20261018.py`; `evidence/integration/source-raster-registration-cli-independent-20261018.json`; `evidence/integration/source-raster-registration-cli-independent-20261018.log`; `evidence/integration/source-raster-registration-cli-independent-initial-20261018.py`; `evidence/integration/source-raster-registration-cli-independent-initial-20261018.json`; `evidence/integration/source-raster-registration-cli-independent-initial-20261018.log`; `evidence/integration/source-raster-registration-cli-live-integrity-final-20261018.json`; `evidence/integration/source-raster-registration-cli-operating-inventory-20261018.json`; `evidence/integration/source-raster-registration-cli-root-related-20261018.log`; `evidence/integration/source-raster-registration-cli-root-related-initial-20261018.log`; `evidence/integration/source-raster-registration-cli-live-integrity-initial-20261018.json`; `evidence/integration/source-raster-registration-cli-final-processes-20261018.json`; `frontend/src/GeoWorkflowEvidence.tsx`; `frontend/src/geollmWorkflowEvidenceAdapter.ts`; `frontend/src/geollmWorkflowEvidenceClient.ts`; `docs/implementation/147_geollm_workflow_evidence_ui.md`; `evidence/integration/geollm-workflow-evidence-ui-focused-20261018.log`; `evidence/integration/geollm-workflow-evidence-root-backend-20261018.log`; `evidence/integration/geollm-workflow-evidence-root-frontend-20261018.log`; `evidence/integration/geollm-workflow-evidence-build-20261018.log`; `evidence/integration/geollm-workflow-evidence-independent-20261018.py`; `evidence/integration/geollm-workflow-evidence-independent-20261018.json`; `evidence/integration/geollm-workflow-evidence-independent-20261018.log`; `evidence/integration/geollm-workflow-evidence-ui-focused-initial-20261018.log`; `evidence/integration/geollm-workflow-evidence-browser-20261018.json`; `evidence/integration/geollm-workflow-evidence-browser-dom-20261018.txt`; `evidence/integration/geollm-workflow-evidence-browser-20261018.png`; `evidence/integration/geollm-workflow-evidence-map-browser-20261018.png`; `evidence/integration/geollm-workflow-evidence-applied-dom-20261018.txt`; `evidence/integration/geollm-workflow-evidence-applied-browser-20261018.png`; `evidence/integration/geollm-workflow-evidence-browser-http-20261018.log`; `evidence/integration/geollm-workflow-evidence-browser-server-initial-20261018.log`; `evidence/integration/geollm-workflow-evidence-browser-server-initial2-20261018.log`; `evidence/integration/geollm-workflow-evidence-live-integrity-final-20261018.json`; `evidence/integration/geollm-workflow-evidence-dev-server-after-20261018.json`; `evidence/integration/geollm-workflow-evidence-final-processes-20261018.json`; `docs/implementation/152_priority_collection.md`; `docs/implementation/152_targeted_bare_collection_rfc.md`; `docs/implementation/153_priority_collection_split_candidate_qa.md`; `docs/implementation/154_collection_progress_ui.md`; `docs/implementation/155_collection_priority_status_contract.md`; `docs/implementation/157_targeted_bare_plan.md`; `scripts/collect_training_priority.py`; `backend/app/collection_priority_status.py`; `backend/app/data/targeted_bare_plan.py`; `frontend/src/CollectionProgress.tsx`; `frontend/src/collectionProgressAdapter.ts`; `evidence/integration/priority-collection-final-20261018.json`; `evidence/integration/priority-collection-root-tests-final-20261018.log`; `evidence/integration/priority-root-related-20261018.log`; `evidence/integration/collection-progress-ui-focused-final-20261018.log`; `evidence/integration/collection-progress-ui-frontend-20261018.log`; `evidence/integration/collection-progress-ui-build-final-20261018.log`; `evidence/integration/targeted-bare-plan-local-20261018.json`; `evidence/integration/priority-collection-round2-final-20261018.json`; `evidence/integration/priority-ml-20261018-summary.json`; `evidence/integration/priority-ml-20261018-final-verification.json`; `evidence/integration/priority-ml-ui-receipt-20261018.json`; `evidence/integration/priority-collection-independent-20261018.json`; `evidence/integration/collection-progress-ui-candidate-browser-20261018.json`; `evidence/integration/collection-progress-ui-candidate-refresh-final-20261018.png`; `evidence/integration/collection-progress-ui-candidate-refresh-dom-20261018.txt`; `evidence/integration/priority-root-related-final-20261018.log`; `evidence/integration/priority-status-tests-final-20261018.log`; `evidence/integration/priority-collection-round3-final-20261018.json`; `evidence/integration/priority-status-api-final-restored-20261018.json`; `evidence/integration/priority-frontend-isolated-source-20261018.json`; `evidence/integration/priority-frontend-isolated-build-20261018.log`; `evidence/integration/priority-frontend-isolated-tests-initial-20261018.log`; `evidence/integration/priority-frontend-isolated-tests-20261018.log`; `docs/implementation/159_next_collection_candidate_qa.md`; `evidence/integration/priority-frontend-isolated-tests-fixtures-partial-20261018.log`; `evidence/integration/collection-progress-ui-final1464-browser-20261018.json`; `evidence/integration/collection-progress-ui-final1464-dom-20261018.txt`; `evidence/integration/collection-progress-ui-final1464-candidate-20261018.png` |
| confidence | round3 정산·153 후보1106 실제QA·최신1464 UI·격리frontend288 PASS/build120 확인; 159 최종은 별도 대기 |
| status | VERIFIED_REAL 실제수집·153 고정후보QA·최신UI / 157 실행BLOCKED·나지4차단 / round4 PLANNED·159 QA 진행 |

> 발표 기준은 2026-10-17 기록이다. 시험 통과는 기존 로그의 역사적 결과이며 이번 문서화에서 재실행한 결과가 아니다. [현재성 대조](../EVIDENCE_SNAPSHOT.json).

## 1분 시연 목표

화면은 여섯 분야에 공통 작업대를 제공하고, 실행·게시 자격은 근거로 별도 관리한다는 사실을 보여준다. 백화점의 진열대가 제품 인증서와 다른 것처럼 UI와 과학 검증을 구분한다.

## 준비물

- 개발 서버가 실제 켜진 경우 [현재 검증한 개발 화면](http://127.0.0.1:5174/)을 사용한다. 현재 연결 확인은 아래09:59 KST 기록 범위이며 이후 시연 시 실행 상태를 다시 확인한다. 기존5173은 새API적용 확인 대상이 아니다.
- [현재 구조도](../CURRENT_ARCHITECTURE.md), [최신 ML 설명](../02_LCLUC_ML.md), [FAQ](FAQ.md)를 별도 창에 둔다.
- 기준 증거: `evidence/ui-20261017/png-lcluc.jpg`, `png-climate.jpg`, `png-carbon.jpg`, `png-biodiversity.jpg`, `png-coastal.jpg`, `png-flood.jpg`, `panel-map-help-icons.jpg`.
- 데이터 다운로드·학습·추론·배포·예약을 시연 준비 목적으로 새로 실행하지 않는다. 아래는 읽기·탐색 시연이다.

## 5분 시연 순서

| 시간 | 화면·행동 | 그대로 말할 문장 | 예상 결과·실패 대안 |
|---|---|---|---|
| 0:00–0:40 | Dashboard→GeoAI Toolbox | “6개 분야를 한 조작 체계로 묶었습니다.” | 6개 카드; 서버가 안 열리면 PNG 기록 사용 |
| 0:40–1:30 | LCLUC Workspace, 지도 확대/축소·bbox 전환·도움말 | “실제 위성 기저지도와 연구 범위입니다. 예측 overlay는 미연결입니다.” | SVG 버튼·도움말 상태 변화; tile 오류면 연결오류 표시를 설명 |
| 1:30–2:10 | 시계열·변화·행렬·핫스팟 탭 | “분석 도구의 화면과 대기 상태입니다. 빈 지표를 실제0으로 읽지 않습니다.” | 탭과 panel 제목 전환; 가상 수치 생성 없음 |
| 2:10–2:50 | 준비도/Model & MLOps의 실제 기록 조회 | “수량은1,111개이며 누출과 나지 부족으로 학습이 차단됐습니다.” | 보고서 출처·최신성을 확인; 화면이 구형이면 JSON 기록을 기준으로 대조 |
| 2:50–3:30 | Agent Center 읽기·외부 모델 Workspace 한 개 | “외부5는 화면과 계약이 있고 실행기 연결은 대기입니다.” | readiness/NOT_IMPLEMENTED; 제출 실행은 하지 않음 |
| 3:30–4:15 | GeoLLM Assistant의 정형 근거 조회 화면 | “현재는 근거 읽기이며 자연어 임의 실행이나 정책 판정을 하지 않습니다.” | 저장 근거가 없으면 없음 표시; 응답을 추정하지 않음 |
| 4:15–5:00 | 구조도와 다음 단계 | “자료 독립성·대표성 다음에 독립 평가와 승인이 필요합니다.” | blocker5·승인 gate를 짚고 FAQ1·2로 마침 |

## 10분 확장과 실제 코드 연결

추가5분은 `backend/app/data/service.py:search_stac`(목록), `read_cog_window`(바이트), `ml/readiness.py:assess`(자격), `gmais_api.py:create_router`(Job/Trace), `sdss_results.py:project_result`(게시 검사)를 구조도 순서로 보여준다. 코드 위치는 구현 근거이며 해당 코드를 현장에서 실행해 승인 결과를 만든다는 뜻은 아니다.

입력 AOI/기간→정합된 자료→readiness→조건부 모델→Result→지도·보고서의 순서다. 모델 결과가 생성되지 않은 단계는 승인 Result screenshot으로 꾸미지 않는다. 현재 표준 Result→SDSS 경로에는 신원·SHA·독립검증 검사 코드와 fixture 시험이 있으나 실제 승인 Result의 운영 인수 증거는 없다.

## 시험·질문·다음 Gate

로컬 UI 검증은 기존 `docs/implementation/23_ui_completion.md`와 이미지/build 로그를 인용한다. 이 시연 계획 자체를 완료된 UAT로 기록하지 않는다. 전체197 PASS도 역사적 코드시험 기록이다.

Q. 무엇을 직접 본 것인가? A. 실제 켜진 로컬 화면을 보거나, 명시한 날짜의 기록 이미지를 본 것이다. 모델 과학 결과는 별도다.

Q. 서버가 안 열리면? A. 기록 시연이라고 말하고 기존 PNG와 JSON을 설명한다. 서비스가 살아 있다고 말하지 않는다.

다음 Gate에서는 변경된 화면·승인 근거·시연 경로만 갱신하고 예전 screenshot의 기준일을 숨기지 않는다.

## 진단카드 시연 — 09:59 KST 개발 연결 확인

1. [새 UI5174](http://127.0.0.1:5174/)→GeoLLM Assistant→실행계획 검토를 연다. execution유형이 자동으로 열린다. 새 화면은 동일출처DEVproxy로API8001에 연결되며 기존5173/8000을 보존했다.
2. 사전 검증한 기록은 빈 input_bindings의 source→dependent와 independent3노드 계획이다. 실제자료를 등록하거나 학습을 시작하지 않았다. 빈입력에는 INPUT_REFS_REQUIRED를 표시한다.
3. STOP_DEPENDENTS에서는 dependent의 선행 원인source와 독립 노드에 선행 원인이 없음을 짚는다. FAIL_ALL에서는 비선행 원인의 정책열이 추가됨을 보여준다. 같은 원인을 실제 선행과 정책으로 혼동하지 않는다.
4. 검사시각·범위·입력상태와 “계획 검사·실행하지 않음”, PLAN_ONLY/BLOCKED·비활성 실행 버튼을 확인한다. 원인 없음은READY가 아니다.
5. [STOP_DEPENDENTS 기록](../../../evidence/ui-20261017/workflow-stop-dependents-live.png), [FAIL_ALL 기록](../../../evidence/ui-20261017/workflow-fail-all-live.png), [입력 진단카드 기록](../../../evidence/ui-20261017/workflow-diagnostics-live.png)을 실패 시 기록 시연으로 사용하고 현재 라이브로 확인한 것처럼 말하지 않는다.

발표 문장: “입력과 정책 때문에 멈추는 이유를 화면에서 나눠 확인합니다. 실제 계획API응답이며 모델 실행 결과는 아닙니다.” 최신전체코드시험262건중261PASS·1SKIP, UIadapter10PASS와build52modules/18.95초는 각각 다른 증거다. 실제Catalog·원장·manifest전후SHA는 같고이번신규Job/Result/Trace0이다. 기존gmais_jobs2건은이번새실행이아니다.

개발proxy는productionbuild가제공하는기능이아니다. 운영 배포에는 지정API의CORS/reverse proxy와기관인수가별도로필요하다. 과학·정책판정·기관승인은시연범위가아니다.

## 최신 Job 기록 시연과 현재API — 10:09 KST 기록

현재주소는[UI5174](http://127.0.0.1:5174/)를유지하되동일출처proxy의target은새API8002(--reload)다. 이전8001연결은앞선시점기록이고8000/8001프로세스는보존했다.

AgentCenter에서기존발급JobID를넣고`Job·Trace·입력 기록 실제 조회`를선택한다. 검증한기존2Job은LEGACY/available=false다. “당시저장기록이없으며현재자료로만들어채우지않습니다”라고설명한다. ID편집즉시기존상태·기록이사라지는지확인하고없는ID는404로보이며이전snapshot이남지않는다. [legacy기록](../../../evidence/ui-20261017/job-input-snapshot-legacy-live.png)과[없는Job기록](../../../evidence/ui-20261017/job-input-snapshot-not-found-live.png)을기록시연으로사용할수있다.

정상RECORDEDsnapshot은임시fixture시험범위로만설명한다. 실제성공Job을만들거나현재파일을재검증한시연이아니다. 최신전체274건273 PASS·1 SKIP/70.655초, UI13 PASS·build52modules/15.97초를각각구분한다. 원본Catalog·원장·manifest는전후같고신규실행기록은0이다. 새PNG대시보드는진행중으로현재완료시연에포함하지않는다.

## 최신 대시보드·카탈로그 시연 — 10:29 KST 근거

1. [UI5174](http://127.0.0.1:5174/)의대시보드를연다. 실제6주·6Dataset·6Agent와LCLUC Draft/외부모델대기를설명한다. 위험·운영서비스등미제공값은—이며원본482개/위험지수는실제성과로복제하지않았다.
2. 지도는공개2017년6주참조경계와기저영상이며공식사업경계/모델위험예측이아님을출처고지와함께말한다. 조회시간과원본자료최신성도구분한다.
3. 데이터카탈로그에서전체6행을보고baseline2021검색→1행→상세로명시ID/version과미확인metadata를확인한다. CSV는검증기록상UTF-8 BOM/13열/1행이며원본파일다운로드가아니다.
4. 시작2025/종료2020의역전기간은오류·0행·CSV비활성을표시한다. 초기화로6행에돌아간다. 품질패널은항목기록존재율이며과학정확도와다르다.
5. 모델허브6개와기존분석/진단메뉴연결을확인한다. 실제학습이나등록을시연목적으로시작하지않는다.

기록대안은[Dashboard desktop](../../../evidence/ui-20261017/dashboard-reference-desktop.png)/[mobile](../../../evidence/ui-20261017/dashboard-reference-mobile.png),[Catalog desktop](../../../evidence/ui-20261017/catalog-reference-desktop.png)/[mobile](../../../evidence/ui-20261017/catalog-reference-mobile.png)다. live로보지않으면기록시연이라고말한다. 요청1672×941/실측1673×941와390×844/실측390×845를구분하며전체수평넘침없음을확인했다. 모바일은세로로카드를쌓고표는내용을탐색한다.

현재API8002연결·UIadapter19 PASS·build57modules/19.20초·backend전체287건286 PASS/1SKIP는각기다른근거다. 보호파일SHA는전후같고신규실행기록은0이다. 과학모델/기관/운영승인이나픽셀완전동일성은시연범위가아니다.

## 최신 계보 읽기 진단 시연

[UI5174](http://127.0.0.1:5174/)→데이터카탈로그→baseline2021상세→`불변 Dataset 계보 읽기 검증(내부 RFC)`를펼친다. 폼은빈값이며현재legacy자료의ID/version/SHA를자동추정하지않는다. 실제검증기록은명시미등록ID와임시고정형식참조로BLOCKED/DATASET_VERSION_NOT_FOUND를확인한것이다. 임시SHA가실제자료의지문이라는뜻이아니다.

검사시각KST·현재자산확인시도≠전체성공·권한/실행/과학승인없음을짚는다. version을latest로바꾸면이전결과가사라지고버튼이비활성,고정1로돌려재조회되는동작을기록했다. 성공계보를새로등록하거나학습을시작하는시연은하지않는다.

기록시연은[차단desktop](../../../evidence/ui-20261017/dataset-lineage-blocked-desktop.png),[차단사유desktop](../../../evidence/ui-20261017/dataset-lineage-reason-desktop.png),[mobile](../../../evidence/ui-20261017/dataset-lineage-reason-mobile.png)을쓴다.1440×1000/390×844요청과mobile dialog351/document375<390을확인했다. current5174→API8002는유지되고보호5SHA같음·신규실행0이다. 전체298건297 PASS/1SKIP·UI25 PASS/build60modules22.09초는각각코드/프론트근거다.

## Job의 과거 기록과 현재 계보를 나란히 설명하기

[UI5174](http://127.0.0.1:5174/)→AgentCenter→기존Job상태·제출기록을조회한다. 검증한Job은제출snapshot이LEGACY다. 이때현재계보카드는아직결과가없어야한다. `이 Job 입력의 현재 계보 읽기 검증`을명시적으로눌러저장원요청의고정refs를검사한다. 기록상현재결과는BLOCKED/DATASET_VERSION_NOT_FOUND다.

“옛점검표는없지만저장된접수요청으로지금자료를검사해미등록을확인했습니다. 현재결과가옛기록을만들거나실행허가를바꾸지는않습니다”라고말한다. checked/reused·한도/수행량·KST·시도≠성공을짚고ID변경즉시clear·다른기존Job상태조회만으로자동현재검사가없음을확인한다. 성공계보를새로등록하는시연은하지않는다.

기록대안은[desktop](../../../evidence/ui-20261017/job-current-lineage-desktop.png),[사유desktop](../../../evidence/ui-20261017/job-current-lineage-reason-desktop.png),[mobile](../../../evidence/ui-20261017/job-current-lineage-mobile.png)다.1440×1000/390×844요청과mobile document375<390·viewport복원을기록했다. 신규실행0·보호5SHA/기존Job2불변이며실제성공계보는fixture를넘어검증하지않았다. 최신전체310건309 PASS/1SKIP·UI32 PASS/build63modules24.15초를각기구분한다.

## Workflow 현재 계보의 명시 조회 시연

[UI5174](http://127.0.0.1:5174/)→GeoLLM Assistant→실행계획검토에서기존계획JSON과기존plan버튼을확인한다. 새`Workflow 입력의 현재 계보 읽기 검증`은별도버튼이다. 실제검증기록은공유미등록ref를쓰는source/dependent2노드와입력빈empty1노드다. 진단1/비용1·dependent재사용·empty의INPUT_REFS_REQUIRED와PLAN_ONLY/BLOCKED를짚는다.

“같은재료는한번확인해공유하지만자료가맞아도작업실행허가는아닙니다”라고설명한다. 화면의본문SHA는실제전송JSON.stringify(parsedPayload)의UTF8bytes를서버wireSHA와비교한것이며원본textarea공백hash가아니다. JSON편집시기존결과clear·invalidJSON비활성·원래823자초안DOM정확복원을기록했다. 기존plan도다시조회해입력/정책카드가그대로이고새계보자동호출없음을확인했다.

기록은[desktop](../../../evidence/ui-20261017/workflow-current-lineage-desktop.png),[공유진단desktop](../../../evidence/ui-20261017/workflow-current-lineage-shared-desktop.png),[mobile](../../../evidence/ui-20261017/workflow-current-lineage-mobile.png)을사용한다.1440×1000/390×844요청·mobile폭375<390·viewport복원을기록했다. 성공계보는fixture,실제는미등록/빈노드차단이며원본/Job2불변·신규실행0이다. 최신전체321건320PASS/1SKIP·UI38PASS/build66modules19.37초를별도로설명한다.

## 카탈로그 활용 인사이트와 뒤로가기 시연

[카탈로그](http://127.0.0.1:5174/#/catalog)에서baseline2021로6행중1행을찾아체크선택하고상세를연다. 브라우저뒤로는검색1·선택1,앞으로는상세ID복귀,새로고침도같은상태를복원한기록이있다. 상세의메타데이터·품질CTA와하단5인사이트는같은명시ID문맥으로연결한다.

입력자료→이용조건→메타데이터/품질→Toolbox→WebGIS의하위화면을보여주며전역7개메뉴는그대로임을설명한다. “책을찾았어도이용조건과서지기록·도구/지도적합성은따로검토합니다. 화면의미확인은0%나통과가아닙니다”라고말한다.5페이지는`#/catalog/insights/{inputs,terms,metadata,toolbox,webgis}`다.

Toolbox에서Climate를고르고Workspace로이동했다가뒤로돌아와Climate·Dataset문맥이유지되는지확인한기록이있다. Gorontalo참조지역·forward/reload·WebGIS왕복도확인했다. Workspace열기는자료자동주입/호환성판정/Job실행이아니다. 없는Datasetquery는최신목록확인후replace로제거하고invalidroute나직접첫진입이전은카탈로그fallback이다.

기록대안은[입력자료](../../../evidence/ui-20261017/catalog-insight-inputs-desktop.png),[이용조건](../../../evidence/ui-20261017/catalog-insight-terms-desktop.png),[메타품질](../../../evidence/ui-20261017/catalog-insight-metadata-desktop.png),[Toolbox](../../../evidence/ui-20261017/catalog-insight-toolbox-desktop.png),[WebGIS](../../../evidence/ui-20261017/catalog-insight-webgis-desktop.png),[없는ID](../../../evidence/ui-20261017/catalog-insight-missing-dataset.png)다. mobile은metadata/WebGIS의390×844요청·390×845실측과폭375<390을기록했다.

최신UI49PASS·독립49PASS/build69modules18.53초다. backend변경없어직전321회귀를이번에반복하지않았다. legacy6행과불변버전0행,미확인권한/품질/기간·공개참조경계≠공식AOI,SEE_COLLECTION_TERMS≠다운로드허가를설명한다. 필터/선택복귀는탭저장소가용성에따르고차단환경reload보존을보장하지않는다.

카탈로그인사이트mobile기록은[메타품질](../../../evidence/ui-20261017/catalog-insight-metadata-mobile.png)과[WebGIS](../../../evidence/ui-20261017/catalog-insight-webgis-mobile.png)다. 원본5PNG/보호5SHA/기존Job2불변·신규실행0과추적backendPython21파일불변은catalog-insights-live JSON을따른다. 이단위에서backend회귀는반복하지않았고QA후원래사용자선택화면/viewport를복원했다. 기록화면을보이면실시간검증으로오인시키지않는다.

## ML 분할계획 검증 설명 시연 — 새 UI 변경 없음

이번단위는내부읽기CLI이므로새버튼이나화면을찾지않는다. [ML설명](../02_LCLUC_ML.md)과문서44·최종`ml-split-repair-validation-live-final-20261017.json`을읽어METADATA_INTEGRITY_VERIFIED·제외16·계획1,095/628·217·250을보여준다. 원본1,111/628·233·250과후보미요청NOT_REQUESTED/null·학습false를나란히설명한다.

“견적서를원장과독립계산식으로검산했으며실제재료나현장을다시검사한것은아닙니다”라고말한다. raster_files_rehashed/spatial_overlap_rechecked/exact_class_counts_recomputed=false를짚는다. 미요청은후보존재판정이아니다. 처음live파일은메타검증후CP949stdout실패이력,final파일은최종명령exit0근거다.

실제CLI를다시실행한척하지말고개발팀의완료근거를읽는시연이라고말한다. --output을사용할경우새evidence경로만허용하며후보를만들거나수집/학습을시작하지않는다. fresh수집복구VALID_BLOCKED·예약136,314,880B보존·보호6SHA불변·전체338건337PASS/1SKIP와API/화면변경없음을함께설명한다.

## terminal 읽기 점검표 시연 — UI 변경 없는 내부 기능

문서45와`recovery-terminal-live-final-20261017.json`을읽어2batch의MISSING/BLOCKED·worker/source파일부재·두config계약각true를보여준다. “운송장과장부형식은대조했지만종료보고서와완전계측이없어정산/재개는보류합니다”라고말한다. raw/normalizedconfigdigest와파일bytesSHA를같은지문으로혼동하지않는다.

각33,554,432B차이를환불액으로읽지않고총예약136,314,880B보존·proposed_refund0·정산/실행/자동재개false를짚는다. source신원binding·완전전송·aggregateexactly-once UNKNOWN·processfalse도설명한다. 메타일치fixture는계속BLOCKED이고실제terminal성공을운영자료로만들지않았다.

최종CP949exit0·전체356건355PASS/1SKIP·관련/독립18시험·보호19refs/기존계약5SHA불변과원래복구계획동일ID VALID_BLOCKED를근거로쓴다. 이번은공개API/화면계약없는CLI라새버튼/브라우저시연을찾지않는다. 원장정산·lock삭제·환불·수집재시작·학습은시연하지않았다.

## Aggregate 읽기 대조 시연 — 화면 변경 없음

문서46과`recovery-aggregate-live-final-20261017.json`의요약을읽는다. 실제113source참조가모두존재하고1,384명세행의두필드쌍이원천row각1개에연결되며patchID/이미지경로중복0·issues0을보여준다. “목록번호연결이맞는지검산했으며실제영상파일을다시검사한것은아닙니다”라고설명한다.

ledger119중현재115(113report+pending2)와다른실험4를구별한다. 같은scene에서16patch를만드는것과patch0report도정상계약이라scene반복/patch0을단순오류로세지않는다. year/province_binding NOT_CHECKED·crop_window_identity_checked=false·raster_files_read0/source_file_hashes_verified=false·exactly_once_appliedUNKNOWN을짚는다.

최종CP949exit0·CONSISTENT_METADATA와statusBLOCKED/환불0/정산·재개false는양립한다. 보호132refs/기존계약7SHA불변·전체372건371PASS/1SKIP·관련/독립16시험은메타/코드근거이며실제복구·학습/운영승인이아니다. 새API/화면계약이없어새UI버튼이나브라우저검증은추가하지않았다.

## Crop 메타데이터를 보여주는 시연

이 단위에는 새 화면이나 API가 없다. 기존 UI를 그대로 두고 `evidence/integration/recovery-crop-live-final-20261017.json`의 요약과 문서47을 보여준다. 명령을 다시 실행하지 않고 보존된 최종 결과임을 먼저 말한다.

“출처113개와 합산1,384행을 연결한 뒤 연도·지역·잘라낸 좌표의 기록을 비교했습니다. 각 항목1,384행이 계약과 맞고 중복0·issue0입니다. 하지만 실제 영상 경계와 픽셀을 검사하지 않아 BLOCKED를 유지합니다.” 이어 `raster_files_read=0`, 경계검사false, exactly-once UNKNOWN·환불0을 보여준다. 전체386건385 PASS·1 SKIP와 보호132참조/계약8SHA 불변은 시험·보존 근거다. UI 재검사·수집·학습은 수행하지 않았다.

## 로컬 헤더 대조를 제시하는 시연

새 화면은 없다. 최종 `evidence/integration/recovery-raster-headers-live-final-20261017.json`의 요약을 열어 고유1,475파일 VALID_HEADER·1,384행 HEADER_CONTRACT_MATCH·issue0·CONSISTENT_HEADERS와 **BLOCKED**를 함께 보여준다. 보존 결과를 읽는 시연이며 CLI/수집/학습을 재실행하지 않는다.

“이번에는 목록만이 아니라 영상 내부의 크기와 좌표표도 읽었습니다. 원본 범위 안의 patch 위치와 좌표 변환이 계약에 맞았습니다. 하지만 픽셀이나 정답 품질·자료 독립성·전체 내용 해시는 검사하지 않아 실행과 학습을 허용하지 않습니다.” 내부 georef·PAM/네트워크 제한과 전체 SHA 미계산을 짚는다. API/화면 계약이 없는 내부CLI이므로 UI 수정·브라우저 재검사는 불필요했다.

시험/보존 근거로403건402 PASS·1 SKIP/95.828초·보호132참조/9SHA 불변과 raster1,475개의 stat/16바이트/목록 관측 변경0을 제시한다. “전체 파일 내용의 SHA를 보존 검증했다”라고 말하지 않는다. streaming 내용SHA는 다음 PLANNED 작업이다.

## 파일 byte SHA 검사를 설명하는 시연

새 화면 대신 content companion의 최종 보존 JSON을 보여주며 명세 pin·예상/관측SHA·실제 반환byte·동일digest경로 진단을 읽는다. 최종 실자료 근거가 확정된 범위만 말하고 대용량 CLI를 시연 중 다시 실행하지 않는다. “지문이 맞는 것과 영상 속 의미·정답 품질·공간 독립성은 다릅니다”를 함께 설명한다. 기존 헤더 보고서의 contentSHAfalse는 과거/모듈 범위 그대로이며 새 companion과 혼동하지 않는다. 내부CLI라 UI 변경·브라우저 재검사는 불필요하다.

확정 시연 수치는1,475 MATCH·RECORDED_SHA_MATCH·실제2,332,461,937B/예산3,000,000,000B·issue0/동일digest경로그룹0·BLOCKED다. 전체418건417 PASS·1 SKIP/92.959초·보호132참조/10SHA 불변을 함께 제시한다. 이번 image fullSHA는 streaming 관측이지만 label/quality·4,335개 전수감사·원자적 snapshot/공간 독립 승인이 아님을 말한다.

## 보조자산의 부분 성공을 보여주는 시연

최종 `evidence/integration/recovery-auxiliary-content-live-final-20261017.json`을 읽고 files2,855 MATCH·계획/실제12,719,583B·issues0과 **RECORDED_AVAILABLE_SHA_MATCH_PARTIAL / INCOMPLETE_REFERENCES / BLOCKED**를 함께 보여준다. role coverage표의 source quality/boundary UNKNOWN각80·총160을 빠뜨리지 않는다.

“명시된 표는 지문이 맞지만 오래된80행의 표 주소와 지문은 기록되지 않았습니다. 없는 정보를 추정하지 않아 부분검증으로 남깁니다.” 동일digest175그룹은 반복 byte이며 누출/공간독립 판정이 아님을 말한다. image+aux4,330을 과거4,335개 fresh 전수감사로 표현하지 않는다. 공개API/화면 계약 없는 내부CLI라 UI 변경·브라우저 재검사는 불필요하며 대용량/보조 CLI도 시연 중 재실행하지 않는다.

최종 시험/보존 슬라이드의 근거는432건431 PASS·1 SKIP/103.139초·보호132참조/계약11SHA 불변·보조2,855 stat/prefix16와1,471부모목록 관측변화0이다. 이 자료는 실제 streaming 관측 범위이며 원자적 snapshot이나 미기재 참조 성공으로 설명하지 않는다.

## 보조 TIFF의 정합을 보여주는 시연

최종 auxiliary headers JSON에서 role별 matched_rows·exact_affine_rows·unknown_rows를 나란히 보여준다. 허용오차 일치와 exact 일치를 구분하고 readiness_full_gate_revalidated=false·raster_content_sha_revalidated=false·BLOCKED를 함께 읽는다. 보존 근거 시연이며 TIFF/CLI를 다시 열거나 실행하지 않는다. sourcequality UNKNOWN과 boundary OUT_OF_SCOPE를 빼지 않는다. 같은 격자가 라벨 의미·QA성능 승인과 다름을 설명한다. 내부CLI/APIUI계약불변이라 UI 변경·브라우저 재검사는 불필요하다.

실제4,329 VALID_HEADER·4,072 pairing/exact 일치와 UNKNOWN80·PARTIAL/BLOCKED를 함께 보여준다. 전체446건445 PASS·1 SKIP/116.342초·보호132참조/계약12SHA·4,329 stat/prefix16/1,475부모목록 관측불변이 근거다. 현재 내용재해시/원자snapshotfalse와 boundary OUT_OF_SCOPE를 유지한다. 다음 boundary 구조/출처 진단은 PLANNED다.

## 경계 구조 진단을 설명하는 시연

최종 boundary JSON에서 raw SHA/구조 결과·feature/vertex 수·region_links·UNKNOWN/coverage를 함께 보여준다. “주소표가 잘 읽히고 지역명이 내부키에 연결됩니다. 공식 경계·권한·자기교차·raster포함은 다른 검사입니다”라고 설명한다. 보존근거만 읽고 CLI를 재실행하지 않는다. 기존auxiliary 헤더의 boundary OUT_OF_SCOPE는 그모듈 범위이며 새companion과 구분한다. 공개API/UI계약 없는 내부CLI라 화면수정·브라우저 재검사는 불필요하다.

확정 시연 수치는1파일482,365B SHA/구조일치·6feature/17,940position·1,304지역연결·UNKNOWN80/부분coverage·BLOCKED다. 전체462건461 PASS·1 SKIP/107.796초·보호132참조/13SHA·boundary stat/prefix16/부모목록 불변을 함께 제시한다. `.is_valid` topology는 아직 PLANNED이며 geometry자동수정이나 공식승인으로 말하지 않는다.

## 경계 topology를 설명하는 시연

최종 topology JSON에서 geometry_runtime·feature_checks·validity_reason·평면 degree²·UNKNOWN/coverage와BLOCKED를 함께 읽는다. 파일구조 STRUCTURE_MATCH와 feature VALID_TOPOLOGY를 구분한다. “도형마다 꼬임을 진단했지만 서로다른지역간중첩·공식권한·영상포함·공간독립성은 검사하지 않았습니다”라고 설명한다. 자동repair/재투영없음·입력상한은 hard CPU시간 보장아님을 말한다. 보존근거 시연이며 CLI재실행·원본수정·새화면은 없다. 내부CLI/APIUI불변으로 UI변경·브라우저 재검사는 불필요하다.

확정시연은 Shapely2.1.2/GEOS3.13.1의6 VALID_TOPOLOGY/6시도·지역연결1,304/UNKNOWN80·부분coverage/BLOCKED다. 전체475건474 PASS·1 SKIP/103.359초·보호132참조/계약14SHA·boundary stat/prefix16/부모목록불변을 함께 제시한다. 평면degree²면적숫자는 사업면적으로 제시하지 않는다. 교차feature접촉/면적중첩진단은 다음PLANNED다.

## 경계쌍 관계를 보여주는 시연

최종relations JSON의pair_scope·planned/attemptcount·pair_results와 area_overlap_findings·UNKNOWN/coverage/BLOCKED를함께읽는다. 접촉쌍은교차면적0이어도nonempty이므로DISJOINT와다르다고설명한다. finding을기관경계오류로단정하지않고 평면degree²를사업면적으로제시하지않는다. 보존근거시연이며CLI재실행/자동repair는없다. 같은파일범위·다른파일OUT_OF_SCOPE와 내부CLI/APIUI불변 UI변경불필요를말한다.

확정 시연은 계획/시도15쌍=13떨어짐+2접촉+양수면적중첩0이다. 접촉은 South Sulawesi–Southeast Sulawesi와 Banten–West Java이며 빈 교차와 구분한다. UNKNOWN80·부분coverage/BLOCKED와 전체490건489 PASS·1 SKIP/107.418초·보호132참조/15SHA 불변을 함께 제시한다. 원본영상 footprint·주 연결은 다음 PLANNED이며 현재 픽셀 내부 비율을 검증했다고 말하지 않는다.

## 원본영상 네 모서리 진단 시연

최종source-footprints JSON에서 source header·pixel_edge_corners·임시lon/lat geometry·명시주관계와UNKNOWN/coverage/BLOCKED를함께읽는다. “사진의네모서리를지도에옮긴직선근사이며 픽셀포함비율이나정확footprint는아닙니다”라고설명한다. 변환중offline·finally복원과sourceSHA재해시false를제시한다. 원본영상/경계를재투영저장하거나CLI를시연중재실행하지않는다. 내부CLI/APIUI계약불변으로UI변경·브라우저재검사는불필요하다.

확정 시연은 source91개 유효헤더/직선근사와 고유86관계 양수교차, UNKNOWN80·부분coverage/BLOCKED다. pyproj3.7.2/PROJ9.5.1·network false→false/복원true와 전체506건505 PASS·1 SKIP/161.521초·보호132참조/16SHA불변을 제시한다. 양수교차를 영상전체가 주 안에 있거나 픽셀비율이 확보된 결과로 말하지 않는다. 다음 source간/고정split후보 진단은 PLANNED다.

## Source 고정split 후보 시연

최종 source-split-overlap JSON에서 scope_rows·physical_row_counts_by_fixed_split·fixedpolicy/SHA와 적격/readiness재계산false를 먼저 보여준다. sharedsource finding·plannedpair·diagnosticrecord·intersectionattempt를 구분하고 NOT_CHECKED를 성공으로 읽지 않는다. 같은split범위밖·boundary미사용·corner근사한계·BLOCKED를 함께 제시한다. 보존근거 시연이며 CLI재실행·원본분할재배정·후보발행은 없다. 내부CLI/APIUI계약불변으로 UI변경·브라우저재검사는 불필요하다.

확정 시연은 물리1,384행/91source·고정split848·272·264와 교차2,227계획/진단/실시도 모두DISJOINT, sharedcanonicalcrosssplit0·같은단일split1,868범위밖이다. 전체521건520 PASS·1 SKIP/160.195초·보호132참조/17SHA불변·BLOCKED를 함께 제시한다. 적격1,111/628·233·250을 다시평가한결과가 아니며 기존readiness token/bbox검사와 다르다고 설명한다. 기존차단의 원인분기는 추측하지 않는다.

## 저장 readiness와 corner 범위를 함께 보여주는 시연

최종comparison JSON에서 세입력SHA·comparison_status·저장blockers/적격계수와물리계수·corner완료/요약을 함께읽는다. eligible_scene_witness_status와shared_source_token_or_bbox_branch_cause가 UNKNOWN_NOT_PERSISTED인지보여준다. “문서가맞물리는것과당시실제차단원인증명은다릅니다”라고설명한다. 저장header/runtime를현재영상/엔진재검증이라하지않고 snapshot_evidence_only·현재재검증false·BLOCKED를제시한다. 보존근거시연이며CLI/영상검사를재실행하지않는다. 내부CLI/APIUI불변으로UI변경·브라우저재검사는불필요하다.

확정 시연은 세JSON일관/issue0·저장5차단 원형보존·적격628/233/250과물리848/272/264·차이220/39/14(산술만)·원인UNKNOWN이다. 저장corner2,227 recorded DISJOINT true와 현재raster/GEOS/assessfalse·BLOCKED를 함께 제시한다. 전체538건537 PASS·1 SKIP/174.829초·보호132참조/18SHA·입력3JSON불변을 읽는다. 향후witness계약/helper는 계획이며 과거원인소급복원이 아니다.

## Witness helper와 실제부재를 설명하는 시연

실제live-absence JSON의saved_report_SHA·prepared_payloadnull·scene/witness부재와 helper(None)의UNKNOWN·union_completefalse를읽는다. 합성예시의연결edge는실제과거장면근거가아님을먼저말한다. “앞으로명시입력을받을순수도구를만들었으며 과거빈공책을채운것은아닙니다”라고설명한다. 실제helper재실행이나gate재평가는하지않는다. callerasserted적격성·저장truncation/전체union·None/empty를구분한다. CLI/API/UI연결없는순수함수라 새화면적용대상이없다.

최종시험/보존근거는554건553 PASS·1 SKIP/197.097초·보호132참조/기존19계약SHA·저장readiness불변이다. 실제부재확인과 합성16/독립16·별도BFS300사례를 구분한다. 실제적격scene연결을 수행하지 않았고 None→UNKNOWN/union미완료만 확인했다. 반환edge는 메모리목록이며 영속저장·assess/화면통합은 계획이다.

## None envelope byte왕복 시연

live-validation audit에서독립구성한None/None/defaultlimits의expectedinputpin·3,385bytes·byte_identical_reencode=true와provenance/실행코드인증false를읽는다. rawenvelope의UNKNOWN witness와5blocker/적격계수보존을연결한다. “봉투가일관된것과실제출처서명·적격성은다릅니다”라고설명한다. Root의evidence파일작성과모듈영속저장을구분하고새CLI/화면을실행하지않는다. 실제eligible장면/과거원인복원·assess통합은없으며 새UI대상은없다.

최종시험/보존근거는572건571 PASS·1 SKIP/158.325초·보호132참조/20계약SHA·저장readiness/5blocker불변이다. 관련18/독립18·별도signedzero와 실제None3,385bytes왕복은 구분한다. 실자료장면이나 출처/실행코드를 인증한결과로 설명하지 않는다. 순수메모리기능이며 Root증거쓰기≠모듈저장, adapter/실제gate연결은계획이다.

## 기본 off adapter를 설명하는 시연

새화면이없으므로 문서60·합성on/off동등성로그·AST parity와saved-state를보여준다. “내부옵션연결은구현됐지만실제전체자료의재평가결과는아닙니다”라고말한다. 합성0patchbridge·copy변조후raise격리사례와실제저장reportSHA/diagnostics부재·역사scene수UNKNOWN을구분한다. childBLOCKED는별도진단권한없음이며outergate추가차단이아님을설명한다. 기본자동활성화·실자료CLI재실행은하지않고 공개API/UI계약없음으로화면변경도불필요하다.

최종시험/보존근거는589건588 PASS·1 SKIP/164.510초·보호132참조/21진단계약SHA·저장report불변이다. 의도한기존코드변경은readiness.py뿐이며 현재raw90b6b3...와정규화text2f70b1...를구분한다. 기본off·합성17/독립17·별도200사례·AST와실자료미재평가를 함께말한다. 저장patch1,111을역사scene수로설명하지않는다. CLI노출/envelope검토는계획이다.

## CLI help와 합성 출력보호 시연

실제live-help JSON/log에서새flag노출·exit0와실자료assess/학습false를보여준다. 합성output보호로그의새파일/입력별칭·writer경쟁·부분파일보존·Windows14path거부를실자료결과와구분한다. CP949환경변수가있어도기존stdoutUTF8재설정을유지했고 새요약이ASCII라는사실만말한다. 실제자료명령을시연중실행하거나자동진단을켜지않는다. 공개API/UI계약이없어화면변경은불필요하다.

최종시험/보존근거는608건607 PASS·1 SKIP/207.921초·보호132참조/23계약·저장report불변이다. 이전추적파일변경0과별도preflight의run_experiment.py변경을구분해 전체workspace무변경으로말하지않는다. 관련19/독립19·별도14path·실제help는실자료assess/학습실행과다르다. 다음실자료진단범위/입력SHA·자원계획또는envelope검토는PLANNED다.

## 새실자료 보고서 시연

보존된 `readiness-connectivity-20261017.json`과문서62를열어1,384scene/0patch273/patch1,111·CAPTURED_COMPONENTS_MATCH와5 blocker/BLOCKED를함께보여준다. 현재tokenevent1096→303 다음에전체28회원(Banten16positive·WestJava9positive/3zero)을보여주어0patch만의문제로단정하지않는다. index는assess내부순번이며rawmanifest행binding은아직미검증이다.

현재helper는957,036 bbox쌍/2,768 token을처리했고 event15,019개(token2,595+bbox12,424)중10,000개를저장해5,019개가생략됐지만 union_complete=true다. 독립graph/BFS 검토가현재전체projected JSONmetadata에서모든계수·첫10,000필드·component를대조해 cross-split bbox0/token1을확인했다. 이는잘린prefix만의추론도 원본영상/정확기하독립성검사도아니다. 문서validation20항목은새unittest20개가아니다.

생산코드변경0·보호132참조/24코드계약SHA·기존savedreport/원장/lock/분할/모델은불변이다. 새보고서는11,132,483bytes·SHA `95f7622ac72ef6a3d43aafc35a3607a4e9f39ed2912ac01280a07cc62c854e35`다.135회표본의peak tree RSS214,724,608B·감시기준timeout600초/RSS2GiB·중지없음은관측값이며 hard memory cap/순간최대보장이아니다. **이번62단위새unittest/full회귀실행은없다.**608건607 PASS·1 SKIP/207.921초는직전61코드단위로그이며 실제CLI1회/독립JSON검증을거기에합산하지않는다. 이해에이전트는보고서만읽고실행·독립계산을재수행하지않았다.

기존UI는oldreadiness5차단상태이며새witness카드는연결하지않았다. CLI를재실행하거나장면삭제/정책변경을시연하지않는다.

## 모호한 원본후보를 정직하게 보여주는 시연

새lineage evidence의OBSERVED_METADATA_MEMBERSHIP·report/raw회원28·candidate_links400/고유raw28·AMBIGUOUS28·exact_row_binding=false를함께보여준다. “원본후보를모두찾았지만단일행으로인증할단서가부족합니다”라고말한다. 내부index와rawrow를같게고르지않고 선언imagepath/hash를실제파일검증으로표현하지않는다. 전체projected/raw조회와잘린witnessprefix·event재생을구분한다. CLI를재실행하거나원본/정책/분할을수정하지않고 공개API/UI계약없음으로화면변경도불필요하다.

## Source identity 계약 설명 시연 — 실자료 화면 변화 없음

새 Gate의 상태표를 열어 부재·부분·무효·전체 선언을 설명한다. optional 객체의 경로·지문은 파일 인증 결과가 아니라 이미 계산한 단서 전달임을 먼저 말한다. 기존 projected5키·helper/gate 유지와 추가 IO0을 설명하고 현재63 결과28장면 전원 모호성과 비교한다. 실자료 재assess/새 보고서·소비자 연결·새 화면은 없으므로 개선된 원본행 결과를 보여주는 시연은 하지 않는다. 다음 소비자는 PLANNED다.

## 선언 단서 소비 시연 범위

새 Gate의 원후보/별도 refinement 상태표를 열어 비교 불가 시 집합 전체를 유지하는 이유를 설명한다. 합성 singleton도 원본 인증이 아님을 먼저 말한다. 실제 기존 보고서는 단서 없는 legacy라28모호성이 그대로이며, 현재 실제 결과를 개선된 새 보고서처럼 시연하지 않는다. 새 API/UI 변화는 없고 다음 noexecute 보고서 관측은 PLANNED다.

## 66 실자료 선언 대조 시연

새 Gate의 두 후보표를 함께 보여준다. 넓은28회원/400연결·전원모호성과 별도28연결·전원유일선언후보를 나란히 설명하고 exact binding false를 바로 읽는다. 새 보고서1,384선언 coverage는 token28대조보다 넓은 필드 존재 범위이며 전체 원본 인증이 아님을 말한다. 실제 검사85.641초·RSS표본과 직전638코드회귀를 구분한다. UI 자동연결·새 모델 결과가 없으므로 화면 상태를 바꾸거나 학습을 실행하지 않는다.

## 저장 진단의 Agent Center 명시 조회 시연 — 실제 연결 확인

Agent Center LCLUC의 ‘저장된 출처 대조 진단’ 카드가 새 화면 연결 지점이다. 고정 핀과 token입력을 확인하고 명시 버튼으로만 조회하는 흐름을 설명한다. 결과에서 넓은 후보/유일선언/0패치/패치·저장차단을 구분한다. 입력을 바꾸면 이전 결과가 사라지는 의미와 경로 비노출을 말한다. 최종 실제 API/브라우저 근거에서 새5174/8002 연결을 확인했다. 빌드·어댑터시험과 실제 수동조회를 분리한다.

### 실제 적용 확인 후 시연 경로

`http://127.0.0.1:5174/#/view/24?model=lcluc&tab=evidence`에서 저장 출처 대조 카드를 찾는다. 입력핀/token확인→명시조회→28/400/28·0patch3/patch25·차단5를 함께 읽는다. 입력을 바꾸면 결과가 지워지고 틀린핀은409안내임을 설명한다. 허브 back/forward에서는 이전결과가 유지되지 않는다. [실제 desktop근거](../../../evidence/integration/readiness-source-identity-ui-desktop-20261017.jpg)·[mobile근거](../../../evidence/integration/readiness-source-identity-ui-mobile-20261017.jpg)는 Root확인 기록이다. 기존5173서버의 적용으로 설명하지 않으며 학습/Job 제출 버튼을 누르는 시연은 하지 않는다.

## 후보계획 참조 묶음 설명 시연

다섯 입력참조와 선택metadata 범위를 새 Gate에서 보여준다. 선언 유일후보의 내부sceneindex/raw후보행index를 구분해 저장계획의 유지/제외 예정 집합을 설명한다. 실제 원본에서 행을 지우거나 새 Dataset을 등록한 것으로 말하지 않는다. NOT_PERFORMED전체planner와 CONSERVATIVE_BOUNDS_ONLY클래스, 원본인증false를 함께 읽는다. 이번새API/UI없음이며 기존저장조회화면에서 후보가발행된것으로시연하지 않는다.

### 69 실제 관측 확인 후 설명

실제 참조패키지에서 source1384/계획1368유지16제외·query28의16제외12유지를 읽는다. projected1095와 현재1111을 나란히 설명하고 val bare상한209·원본제외0/미발행/BLOCKED를 함께 말한다. 다섯JSON pin확인은 전체planner재계산이 아니며 새 API/UI화면으로연결된것도 아니다.

## Split bounded IO 설명 시연

새 Gate에서 None기본경로/opt-in을비교하고 source/readiness/saved_plan/candidate역할과plan/candidate출력한도를보여준다. 개별bytecap을RAM/CPU/누적IO로설명하지않고사전측정후부분새파일가능성을말한다. 이번실제검증은후보미지정validator범위이며새후보발행/원본제외/학습이나새화면이아니다.

### 70 실제결과 설명

실제3JSON validator결과METADATA_INTEGRITY_VERIFIED·NOT_REQUESTED/null을함께읽는다. 계획16제외예정/1095는현재1111과별개이고이번은readonly재계산이다.69의전체planner미수행과70재계산수행을단위별로구분한다. writer의바이트동일/부분파일은합성근거이며실제후보생성시연이아니다. 다음3pin/새evidence/roundtripreceipt연결은PLANNED다.

## 후보·receipt 설명 시연 — 실제metadata생성 확인

새 Gate의세입력핀과plan/candidate/receipt순서를보여준다. receipt없으면미완료이며파일이있다는것만으로완료로표시하지않는다. exactmetadata왕복과raster/과학승인차이를읽고70미생성은당시이력으로구분한다. 실제71의candidate1368행/receipt생성·typed일치를확인했다. 운영등록/학습은시연하지않고candidate실제QA는NOT_ASSESSED라고말한다.

### 71 실제산출물확인

`evidence/integration/candidate-materialization-live-20261017`의plan/candidate/receipt를설명하되대용량JSON을다시실행/생성하지않는다. source1384→candidate1368·16개후보에서만제외·projected1095/원본1111과receipt성공을함께읽는다. 파일존재만인증하지않고Root검증JSON의SHA/size/typed일치를근거로한다. 후보의실제rasterQA/차단수는미확인이며다음DATAstaging/QA는PLANNED다.

## DATA staging 설명 시연 — 실제metadata준비 확인

71receipt/외부3핀→기존fullcandidate검증→candidateJSON만DATA새경로→같은SHA/size→stagingreceipt순서를보여준다. 영상원본복사나QA성공시연을하지않고NOT_PERFORMED를읽는다. 실제DATA후보와evidence원후보의같은SHA/size및3675Bstagingreceipt를확인했다. 새API/UI없어기존카드가후보 QA를표시하는것으로설명하지않는다.

### 72실제산출물설명

`data/first-group-candidate-qa-stage-20261017`의candidate와stagingreceipt를설명하되생성명령을반복하지않는다. 같은SHA/size·1368행/projected1095와QA NOT_PERFORMED를함께읽는다. 원본영상복제·후보준비성성공이나차단수5로설명하지않고원본5차단/후보미검사를구분한다. 다음73guard/QA는PLANNED다.

## 후보readiness QA 설명 시연 — 실제4차단 확인

새 Gate에서4외부핀·동일effectivepolicy/oldsignature→기존run noexecute/noresume→새readiness/QA완료receipt를설명한다. 이전72미검사와새73실제QA완료를구분하고후보4차단/원본5차단·누출완전해소미승인을함께말한다. BLOCKED도검사완료지만학습/등록승인이아님을함께읽는다. 새API/UI없어저장원본카드가새후보결과로자동바뀐것처럼시연하지않는다.

### 73실제보고서설명

`data/first-group-candidate-readiness-qa-20261017`의readiness/qaReceipt를근거로QA_COMPLETED·blocked/readyfalse·class7관련4차단·628/217/250를읽는다. 기존저장조회UI는원본보고서기준이므로후보4차단과혼동하지않는다. bare기여patch0/val209한계를말하고학습/등록을시연하지않는다. 다음74수동비교UI는PLANNED이며원본물리장면수old미저장은null로표시할계획이다.

## 원본·후보저장QA비교시연 — 실제적용 확인

LCLUC전용네핀폼에서명시조회하는흐름과1111→1095/5→4·코드빈도/나지부족을설명한다. 원본물리장면미저장은null이며stage선언/후보캡처를분리해읽는다. 표시중단을서버취소라고하지않는다. 최종실제5174→8002조회와build/시험을분리확인했다. 이번모바일실측은없다.

### 실제수동비교시연경로

`http://127.0.0.1:5174/#/view/24?model=lcluc&tab=evidence`의원본·후보준비성비교에서네핀을확인하고명시조회한다.1111→1095/5→4·나지부족·원본물리미저장/선언/캡처를함께읽는다. 입력변경/허브왕복으로결과가폐기되며응답표시중단은서버취소가아님을설명한다. [수정후desktop근거](../../../evidence/integration/candidate-qa-comparison-ui-desktop-20261017.jpg)는Root관측이며기존5173적용/모바일실측/새QA실행근거가아니다. 다음나지데이터요구계약은PLANNED다.

## 나지요구조건 설명 시연 — 실제저장산술 확인

새 Gate의픽셀부족0/47/0과기여patch부족5각·9클래스분모/낮은bare비율을나란히읽는다.47만채우기/새15patch를확정수집계획으로표현하지않는다. 순수balance재계산은새영상/라벨QA가아니며현재4차단화면은유지한다. 내부CLI출력이새UI요구카드로연결된것도아니다.

### 76실제출력설명

`evidence/integration/bare-class-requirements-live-20261017.json`의0/47/0·5각·0.003532%/0.001494%/0.006307%와정책0.5%를읽는다. ratio분모9클래스합과기여patch의최소256픽셀을구분한다. 실제출력은새자료수집표나새UI카드가아니고저장통계산술이다. 명령을반복하거나47픽셀/15새patch충족으로학습완료를시연하지않는다.

## 실행입력binding 설명 시연 — 최종전체/보존 확인

새 Gate의주문서/전달목록과BLOCKED/UNKNOWN/MATCH상태표를읽는다. expected미기록manifestpin은supplied새값으로채우지않는다. bindingshash와Jobidentity를구분하고실제legacy2기록/로컬8replay를executorcapture와동일시하지않는다. 새API/UI/실행연결이없어실행시연/Job제출을하지않는다.

### 77최종근거설명

localreplay근거의실제저장참조와로컬복사/변조를구분하고UNKNOWN4/BLOCKED4·실제MATCH없음을읽는다. helper무IO와RootreadonlyDB조회범위를섞지않는다.789건788 PASS·1 SKIP와별도648/8을합산하지않으며다음78비공개제출capture는PLANNED다. DB/Job/실행기작동시연은하지않는다.

## 제출binding capture 설명 시연 — 최종근거 확인

기존resolver공개결과와새내부capture를분리해설명한다. samepasspin/추가IO0·RECORDED와quality/ACL차단을나란히읽고기존HTTP/UI는그대로임을말한다. TempStore호환3사례는운영POST성공으로설명하지않으며legacy역채움·실제executor시연을하지않는다. 최종전체805/804PASS1SKIP와실제legacy4GET보존을확인했으며신규운영capture생성은미관측이다.

### 78최종근거설명

TempStorebefore/after3사례의공개호환과실제2legacyJob GET4회호환을별도읽는다. 새capture생성을운영POST나실제executor전달로설명하지않고기존legacy미기록/역채움없음을보여준다. 다음79safeprojection/API·수동UI는PLANNED이며현재공개화면에새capture가노출되는시연은하지않는다.

## 저장capture API·UI 설명 — 실제legacy 확인

네상태와null≠0·요청hash/배열hash·14false를새Gate에서읽는다. 실제2legacy관측을RECORDED실자료조회로설명하지않고큰원문/식별자/경로노출이없음을말한다. 80코드/프론트/실제legacy수동조회를확인했다. 나머지상태/강제late/mobile은실환경검증범위가아니다. 저장조회가현재files/executor검사나학습승인은아니다.

### 실제저장capture수동시연

`http://127.0.0.1:5174/#/view/24?model=lcluc&tab=evidence`의표준JobID에기존ID를명시하고‘저장된입력연결기록조회’를누른다. request1과capture/pin의미기록·미확인/null을읽고0개나현재파일인증으로설명하지않는다. [실제desktop근거](../../../evidence/integration/stored-binding-capture-ui-desktop-20261017.jpg)는Root관측이며신규운영RECORDED·모바일·실제executor근거가아니다. 입력/Agent/메뉴가바뀌면결과를지우며표시중단은서버취소아니다.

## 저장expected handoff 설명 — 최종전체/보존 확인

79저장검증→RECORDED안의expected만77비교와legacyvisiblemismatch차단을상태표로설명한다. 실제2기록/로컬8replay를실제executor포착으로말하지않고passedJoboriginfalse/현재filesfalse를함께읽는다. 새API/UI/DB연결이없어실행/Job제출/화면변경시연을하지않는다.

### 81최종근거설명

storedcapture가RECORDED일때만기준expected를꺼내는흐름과legacyvisiblemismatch차단을읽는다. 실제선언/localreplay와실제executor를섞지않고832건831 PASS·1 SKIP·141보호42코어를근거로말한다. 다음configuredStoreget1adapter는PLANNED이며실제Job쓰기/실행/새화면시연은하지않는다.

## 82 Store handoff adapter 설명 — 최종 근거 확인

네Store상태와inner세binding상태를분리해읽는다. validget1/invalid0·malformedOBSERVED/innerBLOCKED·실제readonlyget9/local8replay범위를설명하고운영MATCH/실행과섞지않는다. 기존전체DB파싱/출처인증false·새API/UI없음을함께말하고실제DB쓰기/실행시연은하지않는다.


82 최종 증거: 관련·독립 각 12개 통과, 전체 844건 중 843 PASS·기존 1 SKIP/342.991초다. 실제 Store.get 9회와 로컬 재생 8회는 별도 관측이며 실제 실행기 전달은 아니다. 보호 141참조·44코어·카탈로그 14기록·기존 Job 본문을 보존했다. 공개 API·화면이 바뀌지 않아 이번 단위의 새 화면 시연은 없다. 다음 저장-vs현재 pin preflight는 PLANNED다.


## 83 내부 preflight 설명 — 최종 근거 확인

저장 근거·현재 입력 진단·선언 대조의 세 축을 설명한다. 같은 pin도 품질 차단이면 출고하지 않는 비유를 사용한다. 실제 기존 legacy 두 Job은 UNKNOWN/current NOT_RUN이고 Store.get 총3회·resolver/Registry get0이었다. 현재 positive 검증은 격리 합성시험으로 구분한다. 새 공개 API·UI가 없으므로 기존 카드에서 새 기능을 실행하는 시연은 하지 않는다.


83 최종 근거는 전체 856건 중 855 PASS·기존 1 SKIP/343.921초다. 보호 141참조·45코어·카탈로그 14기록·기존 Job 본문을 보존했다. 현재 positive는 합성 시험, 실제 legacy는 UNKNOWN/NOT_RUN이며 공개 API·UI·Workflow·실행기는 아직 연결하지 않았다. 다음 수동 API+UI는 PLANNED로만 설명한다.


## 84/85 현재 입력 재검증 — 실제 데스크톱 legacy 확인

저장 메모 조회와 현재 직접 입력 검사의 차이를 먼저 설명한다. API 실제 legacy 두 Job은 UNKNOWN/current NOT_RUN이고 기존 6응답은 baseline과 같았다. current positive와 busy/cancel은 합성 증거다. UI5174에서 명시 버튼으로 legacy UNKNOWN·3축·미확인 값을 보여준다. 저장 조회 독립과 입력/Agent/Registry/뒤로 이동 시 제거를 확인했으며 실제 current positive/busy/cancel/mobile은 시연 근거가 아니다.


## 86 Workflow 선택 입력 전달 계약 — 최종 합성·회귀 확인

전체 작업 지시서에서 한 작업의 재료 목록을 전달 초안과 비교하는 비유를 사용한다. 합성 순수 함수이며 실제 Workflow 제출·Job 생성·화면 실행은 하지 않는다. 순환이어도 목록만 같으면 MATCH일 수 있고20false/7IO0·dag_validated=false를 유지한다. 기존84/85 화면에서 새 기능이 작동한다고 시연하지 않는다.


86 최종 회귀는882건 중881 PASS·기존1 SKIP/346.255초다. 관련·독립 각13개는 반복 검증으로 별도다. 보호141참조·48코어·catalog14·기존Job 본문을 보존했다. 실제 저장Workflow0건은 환경 관측이고 새 handoff 성공을 뜻하지 않는다. API/UI 연결은 다음 PLANNED이므로 기존 화면에서 전달 실행을 시연하지 않는다.


## 87/88 원문 handoff 비교 — 실제 합성 선언 시연 확인

원지시서와전달초안의비교창구를설명한다. 원문두JSON을보존하고callerpin과outerrawSHA를나눈다. 실제HTTP의UnicodeMATCH와driftBLOCKED도합성선언범위다. 실제5174/#/view/15에서 합성 수동 MATCH·role drift BLOCKED·없는node/null·중복JSON 로컬 거부를 확인했다. 기존plan/lineage와독립이며편집/뒤로이동결과를버린다. 테스트후원초안복원·합성입력제거를완료했고스크린샷은복원전시연이다.


## 89 full Job 초안 companion — 최종 합성·회귀 확인

전체주문서양식확인후재료목록만꺼내는비유를쓴다. 내부합성helper이며기존87/88화면을fullJob검사로시연하지않는다. 원schema coldread와자산읽기0을나누고전체초안관측hash·metadatahash·callerWorkflowpin을구분한다.


89 최종 전체912건/911PASS/기존1SKIP/359.738초, 관련·독립각15개는반복검증이다. 보호141참조·57코어/원schema·catalog14·Job2본문을보존했다. 운영fullJob전달을확인한것이아니며기존87/88화면에서새helper가동작한다고시연하지않는다. 날짜보완은89전용이고공통API날짜개선은별도계획이다.


## 90/91 full Job 수동 검사 — 실제 합성 초안 확인

원문전체초안을검사하는접수창구비유를쓴다. Workflowpin·outerrawSHA·serverfullJob관측hash를나누고Job생성과다름을설명한다. 실제5174에서 소수·지수·음0 MATCH와날짜/role차단·dupe400·없는node/null을합성초안으로확인했다. 기존세조회와독립이고접기/편집/이동상태를확인했다. 원초안복원·합성필드제거완료이며스크린샷은복원전이다.


## 92 공통 날짜 검사 — source·최종 회귀 확인

공통달력검사기제작법을설명한다. freshsource합성정상6/invalid13과운영서버적용을구분한다. 기존UI/오류계약이같아직접새화면시연은없고8002reload만으로날짜동작을확인했다고말하지않는다.


92 최종전체937건/936PASS/기존1SKIP/345.696초,관련67·독립40은반복검증이다. 보호141참조·57코어/schema·catalog14·Job본문을보존했다. 새source의날짜지원은확인했지만운영HTTP제출/실행서버날짜적용과브라우저재검사는없다. 이전90/91화면시연을이번날짜운영검증으로표현하지않는다.


## 93 등록관계 공통화 — 최종 합성·회귀 확인

두접수창구의명부확인비유를쓴다. SHA고정원handler와격리response/Store순서/기록동등을설명하고운영제출성공으로확대하지않는다. 공개화면/오류계약이같아새직접화면시연은없다.


93 최종전체948건/947PASS/기존1SKIP/381.129초,관련78·독립21은반복검증이다. 보호141참조·59코어/schema·catalog14·Job본문·이전증거559파일을보존했다. 새source의등록관계일치와운영서버행동/실능력검증은다르다. 공개계약과화면이같아직접새시연은없다.


## 94/95 선택형 등록관계 — 최종 합성·화면 확인

주문서검사뒤명부를선택확인하는비유를쓴다. 기본RFC1/명시RFC2와innerMATCH·outerBLOCKED를나누고REGISTERED를실지원승인으로말하지않는다. 실제5174에서13check를확인했고원Workflow/빈입력/defaultoff로복원했다. 기록된fullJob9클릭·기존88의1클릭은네트워크계측수가아니다. 기존진단수동POST는유지하며새RFC2자동요청만없다.


## 96 model_ref 선언 범위 — 최종 합성·회귀 확인

모델주문에최신별칭대신고정문자를적는비유를쓴다. GMAIS입력범위축소와89정상결과보존을나누고실modelresolver검증으로확대하지않는다. 기존UI가400/modelcode를지원해이번직접화면재시험은없다.


96 최종전체977건/976PASS/기존1SKIP/348.393초,관련112·독립41은반복검증이다. 보호141참조·66코어/schema·catalog14·Job본문·기존599증거파일을보존했다. source새거부와운영모델/서버검증은다르며직접UI재시험은없다. 이전95화면시연을96에서다시실행했다고설명하지않는다.


## 97 내부 선택 버전 메모 — 최종 합성·회귀 확인

실험보관시담당자의선택메모비유를쓴다. 생략동등과합성명시추가를나누고모양/source만으로출처인증하지않는다. catalog기존version부재·science부재/null을그대로말한다. API/UI옵션미연결로직접새화면시연은없다.


97 최종전체987/986PASS/기존1SKIP/380.835초·관련37/독립13은반복이다. 보호141/core70/catalog14·기존Job본문/616증거는보존했다. registry사전핀보충의비교범위를설명하고실제운영등록성공이나globalimmutable로확대하지않는다. 기존API/UI옵션미연결이므로직접새시연은없다.


## 98/99 선택 모델 버전 등록 — 실제 음성·최종 회귀 확인

기본off/빈입력·원형값전달·201뒤refresh분리를설명한다. 성공은격리근거만사용하고운영에서는안전한없는보고서422까지만확인한다. 실제5174에서기본off/빈값·local안내·없는report422·완료뒤back과레이아웃을확인했다. 성공등록을시연하지않으며최종입력은빈값/off다. HMR오류1이력후reload정상과corrected전체근거를분리한다.


## 100 등록메모 관측 — 최종 관련·보존 확인

파일대신모델카드만보는비유를쓴다. 실제기존모델ABSENT와합성일관미검증을구분하고진단4false를기존필드수정으로설명하지않는다. API/UI미연결이므로직접새시연/전체/build/browser재실행은없고998전체는이전이력이다.


100 최종집중12/관련47/독립12 PASS와보호141/core70/기존제품0변경·이전662증거불변을확인했다. API/UI미연결이므로새화면/전체회귀재실행없음이다. 실제ABSENT와진단false의범위를설명하고998전체를100의새실행으로표현하지않는다.


## 101/102 선택모델 선언 조회 — 실제ABSENT·최종 회귀 확인

모델카드를읽는수동창비유를쓴다. 실제기존ABSENT·없는404와격리나머지상태/auth503을나누고4false를기존평가값으로읽지않는다. 실제5174에서모델선택뒤수동ABSENT/3NOT_CHECKED와선택/route/back결과제거를확인했다. 타상태/오류경합은합성이며조회는등록/승인이아니다.


101/102 최종전체1019/1018PASS/기존1SKIP/381.288초·UI172/build93·28.54를확인했다. 보호141/core71/catalog14·기존679증거는불변이다. 실제ABSENT/404와합성타상태·원본과학미검증을나누며기존readinesscheckpoint읽기를새metadataIO0으로숨기지않는다.


## 103 발표 시연 — 화면 추가 없이 계약을 설명

기존101/102 수동 등록 메모 창은 유지한다. 새103 비교는 API/UI에 연결하지 않았으므로 화면에서 성공했다고 시연하지 않는다. 대신 Gate의 흐름으로 명시 참조·제공 카드·내부 메모·버전/지문 대조를 설명한다. 카드 미제공을 DB 미발견으로 말하지 않는다. 합성 성공과 실제catalog14 보존 관측을 구분한다. 새 운영 등록·resolver·훈련은 없다.



## 104 화면 없는 내부 연결 설명

새 wrapper는 현재 화면/API에 연결하지 않았다. 기존 화면에서 새 모델 대조가 된 것처럼 시연하지 않는다. Gate의 흐름도로89 차단→추가 접근 중단, 참조 부재→대조 생략, 참조 존재→103 대조를 보여준다. OBSERVED와 nested 결과를 함께 읽고 None 카드는 미제공이라고 설명한다. 실제catalog 보존을 운영 Workflow 검증으로 말하지 않는다. 이번 프론트/build/브라우저 재시험은 없다.



## 105/106 수동 모델 카드 대조 시연 순서

5174의 GeoLLM 실행계획에서 ‘모델 레코드 초안 대조’를 펼친다. 기본 빈 node·Job·카드와 비활성 버튼을 확인한다. 준비된 합성 주문서와 카드를 명시 입력하고 수동 대조한다. 바깥 수행 상태와 안쪽 미제공·오류·충돌·일치 미검증을 별도로 읽는다. 실제 모델 목록에서 가져온 카드나 운영 Workflow라고 설명하지 않는다. 입력을 바꿔 이전 결과가 사라지는 점과 기존 패널 상태 독립을 보여준다. 표시중단은 서버 취소가 아니다. 새 모델 등록·Job 제출·학습은 하지 않는다.


실제 확인은11체크·수동POST4회·1449×1087 넘침/겹침0·SVG·최근20시각필터 오류0이다. 원 Workflow를 정확 복원하고 route/back 뒤 새 세 필드를 비웠다. PNG는 합성 일치 미검증 상태다. 모바일·강제지연·브라우저503/auth·5173은 이번 실제 확인 범위가 아니다.


## 107 화면 없는 공통 정렬 설명

새 UI 시연을 추가하지 않는다. a와z가 준비되고 b는a 뒤에 가능하다는 종이 예로[a,z,b] 계층 정렬을 설명한다. 기존 세 호출부 응답과 오류·자료 읽기 순서는 유지한다. 수정 전 소스 사본 대비 격리 시험을 근거로 사용하고 이전105/106 브라우저를107의 실제 서버 적용 증거로 재사용하지 않는다. 실제 실행·새 Job·학습은 없다.



## 108 화면 대신 저장 산술표 설명

새 UI 시연은 없다. Gate 표에서 나지 총량·저장 기여0·가능한 범위를 먼저 나눈다. train상한5를 실제5개로 말하지 않는다. val1071과76의47을 각 조건으로 설명하고 미래수집량으로 환산하지 않는다. 실제CLI는 고정 JSON 산술이며 영상·라벨/새QA를 검사하지 않았다. 이전1069 전체와 이전 화면 근거는 각 역사로 유지한다.



## 110 화면 시연 대신 단계표 설명

새UI는없다. Gate표로준비/원장/aggregate/run요약의선언값과인접전이·동일재관측을설명한다. 실제missing두배치에가짜작업ID·after pin을만들어시연하지않는다. COMMITTED도실제파일저장이나정산/재개허가가아니다. 외부5개실행자료·독립평가라벨은사용자확인미제공이며6모델화면을실행준비완료로소개하지않는다.



## 111~114 현재 시연 경계

111공통등록은운영DB에시연등록하지않고TempStore시험과등록계약을설명한다.36셀metadata를주전체확보로소개하지않는다.112는완료모델의새optional오류artifact계약이며구조화오류표·인증다운로드UI는아직없다.현재baseline은RGBTinyUNet이고새6밴드U-Net++라고소개하지않는다.

GeoQuery정형조회와PC의Ollama서버를분리해보여준다.별도모델/임베딩평가결과가나와도운영RAG/실제도구실행완료라고시연하지않는다. LCLUC전용시계열CLIcore는115에서구현됐고화면/API는116/117에서 연결됐고 임시 fixture 성공과 운영 원본 실행0을 구분한다. 기존화면·등록/과학/실행gate는유지한다.



## 115 실제 계산과 시연 범위

새코드는명시CLIcore이며현재화면에서실행됐다고시연하지않는다. 임시Store의mock승인과작은2연도영상에서만실제CPU추론·변화·7artifact/SHA를확인했다. 현재Draft모델/원본DATA로명령을실행하지않는다. samekey재조회·변조거부·실패부분보존은시험로그로설명한다. API/UI·선택pair지도/trace·표준Result는116후속이다.



## 116/117 — LCLUC 수동 실행·조회 API와 화면

LCLUC Workspace의 ‘고정 입력 실행 · 상태와 산출물’ 패널은 기본 접혀 있고 빈 값에서 시작한다. 요청을 직접 입력할 때만 실행 버튼을 누른다. 저장 ID 조회·보고서·index 다운로드는 각각 수동이다. 시연 성공은 임시 서버의 모의 admission fixture 여부를 밝혀야 한다. 실제 임시5175→8003에서만 명시 실행 성공을 확인했다. 운영5174는 패널과 빈 요청 차단을 확인했으며 원본 성공 실행은0이다.


### 116/117 최신 상태로 읽는 주의점

앞선115 단락의 API/UI 미연결은 당시 범위다. 현재 수동 실행·상태·보고서·검증 파일 UI는116/117에서 연결했고 실제 성공 확인은 임시5175→8003의 모의 승인 fixture다. 운영5174에는 패널과 빈 요청 차단만 확인했다. 현재6밴드 제품 정규화·지도 pair·표준 Result·운영 승인과는 분리한다.


## 118 — 검증된 선택 변화쌍 지도

성공 receipt의 보고서를 먼저 수동으로 읽고 변화쌍을 직접 선택한 뒤 지도 읽기를 누른다. 현재는 생성 영상·mock 승인 fixture 근거만 설명한다. nonempty 지도와 empty 안내를 나누고 전체 픽셀 통계와 일부 벡터를 구분한다. 원본 운영 자료 실행으로 소개하지 않으며 Root가 임시5175→8003에서 실제 MapLibre nonempty/empty·pair 변경·뒤로 가기를 확인했다. 운영 원본 실행은0이다.


### 118 최신 범위와 이전 설명

앞선115~117의 선택 pair 지도 미연결은 당시 범위다.118은 같은 실행의 수동 검증 GeoJSON을 별도 지도에 연결했다. 기존 상단 지도/KPI·6밴드 per_scene 정규화·표준 GMAIS Result·원본 운영 승인은 그대로 후속이다. 실제 브라우저 확인은 임시 mock 승인 fixture이며 운영 원본 성공 실행은0이다.


## 119 — 전체 래스터 전이행렬·범례·단위

같은 보고서를 먼저 읽고 pair를 선택해 전이 표를 본다. 행=이전/열=이후와 단위 선택을 설명한다. 1→2의256픽셀/25600m²는 작은 생성 영상 결과이며 실제 사업지역 면적이 아니다. 지도 파일은 별도 읽기 버튼으로 확인한다. Root가 임시5175→8003의 실제 화면에서256픽셀→25600m²→2.56ha와 순변화±2.56ha·grass 색상·unchanged/빈 지도·back 정리를 확인했다. 운영 원본 성공 실행은0이다.


## 120/121 — 고정 모델의 오류분석 읽기

120은 고정 성적표 조회 API다. 실제 legacy 모델의 version/report/error artifact 부재와 합성 AVAILABLE을 분리한다. 빈 통계를0으로 발표하지 않는다.121 실제 UI는 임시5175→8003에서 확인했고 임시 fixture의 성공을 운영 성능으로 소개하지 않는다.


### 120/121 최신 범위와112의 당시 한계

112 당시 후속이던 구조화 오류 표와 인증 다운로드는120/121에서 연결했다. 실제 운영 legacy 모델의 pin/오류분석 부재는 그대로 표시하고 과거 성적표를 자동 생성하지 않는다. 임시 구성 성적표의 읽기 성공은 실제 원본 모델의 독립 정확도나 승인·배포 완료가 아니다.


## 122 — per_scene 정규화 선언 계약

122는 서류 대조 함수이므로 새 화면 시연은 없다.4입력의 제품·밴드·숫자 일치와 기존 파일 verifier를 나누어 설명한다. global1~16밴드 지원을 밝혀 모든6밴드 금지 오해를 피하고 per_scene 실제 전달은 아직 미연결이라고 말한다.


## 123 — per_scene 세 역할 파일 지문 대조

123 새 화면은 없다.122 서류끼리 비교와123 실파일 지문 대조를 나누어 설명한다. Temp 변조를 거부하고 nonraster bytes도 SHA가 맞으면 통과한다는 한계를 같이 말한다. 원본 제품의 공식 인증·정상 영상·실행 완료로 소개하지 않는다.


## 124 — 실제 checkpoint manifest와 고정 모델 참조

124 새 화면은 없다. 모델 장부·SHA로 실제 checkpoint 내부 설명을 읽는 과정을 문서/Temp 근거로 설명한다. report 미끼 input_signature 대신 actual manifest를 반환한 것을 보여주되 Dataset/모든연도/mask/실행 연결은 후속이라고 말한다. 운영 모델 load·추론·학습은0이다.


## 125 — 등록3참조와 명시 장면 파일

125 새 화면은 없다. Temp의 등록3참조와 명시 scene/band에서123 파일 reader로 이어지는 읽기를 설명한다. 제품군 이름과 장면 ID의 차이, legacy 부재의 무역채움, RAW bytes 성공과 품질 승인 차이를 함께 말한다. actual124 자동 연결126은 미구현 후속이다.


## 126 — actual 모델과 등록 단일 장면 결합

126 새 화면은 없다. actual124→125의 단일 장면 내부 호출과 모델 실패 시 scene0을 문서/Temp 근거로 설명한다. 운영 DatasetVersion0과 임시 등록 성공을 나눈다. 모든연도·품질mask·기존 실행기 연결은 후속이라고 말한다.


## 127 — 요청2~6연도 순차 읽기

127 새 화면은 없다.2/6행 요청표·같은actualmanifest1회·첫 실패 뒤미검사를 문서/Temp 근거로 설명한다. 요청연도와 실제연도, 다른등록ID와 물리독립성을 구분하고128 후속을 말한다. 운영DatasetVersion0을 함께 표시한다.


## 128 — 등록시간과 요청 UTC연도 결합

128 새 화면은 없다. 요청연도·등록 UTC window·물리취득일의3층을 분리해 설명한다. BLOCKED 후보digest와 검증flag를 구분하고 운영 DatasetVersion0·129 header/grid 후속을 함께 말한다.


## 129 — 실제 GTiff header와 장면간 격자

129 새 화면은 없다. 검증 파일→실제 GTiff header→엄격 grid의 단계를 설명하고 pixel/mask/QA·AOI 미검증을 함께 말한다. 운영 DatasetVersion0·130 bbox/extent 후속과 실제 Temp 관측을 구분한다.


## 130 — 등록 bbox와 표본화 영상 envelope

130 새 화면은 없다. 같은record의 등록bbox와129 header 재사용을 설명한다. 유한edge 근사·큰bbox와coverage 차이·공간미검사와 파일IO 차이를 말하고 운영 DatasetVersion0·131 QA/mask 후속을 유지한다.


## 131 — 등록 품질보고서와 명시 mask 파일

131 새 화면은 없다. 등록3참조와 보고서의 image/mask대상·품질선언 일치를 설명하되 opaque mask·QA 미검증을 함께 말한다. 운영 DatasetVersion0과 Temp시험을 나누고 없는자료 자동생성이나 운영승인으로 소개하지 않는다.


## 132 — 실제 영상과 mask header·격자

132 새 화면은 없다.131bytes 뒤 실제6band/1uint8 header와 같은grid를 읽는 단계를 설명한다.255값 의미는 미검증이며 각파일2reads·nested이력과 상위전체성공을 나눈다. 운영 DatasetVersion0과batch 미연결도 함께 말한다.


## 133 — 명시 이진 마스크 값과 품질 승인 구분

이번 시연은 새 화면이 아니라 Gate133과 시험 기록을 펼쳐 설명한다. 132 격자 성공 →명시0/1 선언 →실제80/176 개수 예를 보여준다. 이어 all-zero 성공과 QA false를 같이 보여 “형식 통과와 자료 사용 승인은 다르다”고 말한다. 운영 등록·실행 시연으로 소개하지 않는다.


## 134 — 연차 공간·명시 마스크 관측과 등록 지문 연결

새 화면 대신 Gate134의 흐름과 시험 기록을 보여준다. 먼저 파일SHA와 등록manifestSHA의 차이를 설명하고, 같은 파일인데 source metadata만 바뀌어 연결이 차단되는 예를 보여준다. 앞 행 성공·중간 실패·뒤 mask 미검사와130 관측 이력을 같이 보여 전체 승인과 부분 기록을 구분한다.


## 135 — 명시 분수 기준의 연차 계산과 공식 승인 구분

Gate135에서 분수1/3 경계와 all-zero 기준0 사례를 보여준다. 이후 미달이어도 하위134 bytestrue·읽기 이력이 남는 것을 설명한다. 새 화면이나 실제 운영 평가로 시연하지 않고 임시자료 시험과 코드 계산 범위를 소개한다.


## 136 — 제한된 요청과 경로 없는 내부 안전 요약

새 화면 대신 Gate136의 제한 요청·요약 예를 보여준다. 같은 JSON 값의 키 순서/공백은 같은 지문이며 raw 서명은 아니라고 설명한다. source private 오류가 고정 code/year로 바뀌고 parent오염은OUTPUT_INVALID가 되는 시험 기록을 소개한다.


## 137 — 필수 인증 수동 API와 모델 화면의 연차 진단

실제 운영 Draft의 고정 핀 미확보·버튼 비활성과 빈 정책·연차 참조를 먼저 설명한다. 임시 자료의 수동 API/UI 결과는 Root의 실제 브라우저 최종 근거를 받은 뒤 소개한다. 표시 중단은 서버 읽기 취소가 아니며 정책 충족은 품질 승인이 아니라고 함께 말한다.

Root 실제 브라우저6체크는 임시자료의 빈 입력 비활성·충족/미달·입력 수정·메뉴/뒤로가기 결과 폐기와 운영5174의 Draft 핀 미확보 비활성이다. 계수128/128과SHA를 보여주되 합성자료임을 먼저 말한다. 실제 운영 진단 성공이나 모바일·강제 지연 검증으로 소개하지 않는다.

## 137 최종 검증 범위

최종 backend1359건/1358 PASS/기존 Windows1 SKIP·484.770초,API집중11/6.292초·보존시험36/6.983초·front271(신규10 포함)/25.678583초·build112/13.48초를 확인했다. 실제 임시HTTP와 브라우저6체크는 충족/미달·결과폐기·운영 핀 미확보를 구분한다. 최초 full3FAIL·중간 보존시험2FAIL 이력은 원로그로 남기고 최종 통과와 분리했다. 보호141·기존 소스307 중 허용5/불변302·이전 증거1235·catalog14 SHA·예약은 보존했다. 운영 DatasetVersion0·운영 실행/등록/학습0이며 표시 중단은 서버 취소가 아니다. 다음138 생산자 준비는 설계 후보이고 구현 완료가 아니다.


## 138 — 보고서 바이트·미등록 초안 준비와 별도 출처 메타데이터

화면 대신 Gate138에서 exact5 보고서와patch7·별도 메타데이터5개를 보여준다. 준비 함수 출력 →시험 caller의 메타데이터 제공 →Temp 파일쓰기/등록 →131/133 소비를 구분한다. 실제 운영 파일 생성·등록·품질승인 시연으로 소개하지 않는다.


## 139 — 명시 report 메타데이터의 완성 초안과 실제 등록 구분

Gate139에서 caller report metadata5개가 image와 다르게 명시되는 예를 보여준다. 초안12키·report bytes 불변·10false를 설명한 뒤 실제Temp 작성/등록/소비는 별도시험setup이라고 말한다. 운영 파일발급·등록·품질승인 시연으로 소개하지 않는다.


## 140 — 두 새 출력의 배타적 저장과 부분 실패 보존

Gate140과 Temp 결과를 사용해 두 새 파일·SHA,기존파일 거부·두 번째 경쟁/부분 실패 보존을 설명한다. reader 소비를 위한 임시 등록은 caller setup이며 writer가 운영 Registry를 만들었다고 시연하지 않는다. 실제 symlink SKIP과 모의시험을 구분한다.


## 141 — 저장2파일 등록 전 읽기와 schema 확인

정상 저장2파일 검사와 변조·비canonical 파일 차단 기록을 보여준다. 초기 날짜 거부 가정은 실제 설치 환경에서 맞지 않았고, 최종 schema 실패는 임시 엄격 validator 정책이라고 말한다. 실제 Temp 작성·등록 setup과 reader의 읽기 전용 동작을 구분하며 운영 등록 시연으로 소개하지 않는다.


## 142 — 보고서1버전 명시 등록과 결과 미확정 구분

임시 source2개 등록 setup →adapter report1건 등록 →readback →133 소비 범위를 보여준다. 집중 all-zero와 독립 checkerboard 계수를 혼동하지 않는다. source에 quality_report_ref가 없으면 등록 후 소비가 차단될 수 있고, 미확정 결과는 행이 없다는 뜻이 아니라고 설명한다.

142의 확정 시험·보존 범위는 집중 10 PASS·관련 79 PASS·독립 12 PASS/1 SKIP이다. 실제 등록은 Temp에 한정하며 운영 DatasetVersion 0·후보 차단 4개·미승인 상태를 유지한다. 상세 시간과 초기 시험 구성 오류는 Gate142에서 구분한다.


## 143 — 명시 CLI의 점검·등록과 종료 코드 구분

이미 기록된 Temp subprocess 근거로 DB 없는 inspect와 source 두 버전 setup 뒤 report 한 건 등록을 보여준다. 같은 요청 재호출의 DB/파일 불변과 131/133의 128/128/256을 확인하되 운영 명령을 실행하는 시연으로 소개하지 않는다. constructor/commit 뒤 오류는 명시 fault injection임을 말하고 exit 3을 자동 retry 안내로 바꾸지 않는다. 원영상 품질·기관 권위·학습/배포 완료 시연과 구분한다.


## 144 — 새 수집 영상의 밴드 설명과 scene mask 선언

실제 Temp image header와 uint8 0/1 mask를 보여주고 STAC/COG 서비스 응답은 Mock이었다고 먼저 말한다. 집중 5 valid/11 invalid/16 total과 독립 9/7/16은 다른 fixture다. 별도 NaN/Inf 비교는 구 코드 15/16에서 새 코드 12/16이며 raw crop 여섯 개 bytes는 같았다. caller의 명시 report/manifest·Temp Registry setup 뒤 소비 성공을 보여주되 운영 수집 재개·자동 등록·기관 QA 시연으로 소개하지 않는다.

144의 확정 보존 범위는 기존 snapshot 326개와 Git 고정 수집기 원문 한 개를 합친 소스 327개 중 수집기만 변경·326개 불변이다. 보호 141개·이전 증거 1381개·운영 catalog/예약을 보존했고 운영 수집·등록·학습·추론은 실행하지 않았다.


## 145 — 패치 밴드 설명 전파와 학습 지원 mask 구분

고정 baseline과 새 Temp patch를 비교해 image 배열·profile은 같지만 descriptions와 파일 SHA가 달라질 수 있음을 보여준다. label/quality bytes·원 report·입력 source 보존을 확인한다. patch training_support를 순수 binary_validity로 넘기면 거부되는 native helper 반례를 보여주되 전체 Registry 소비나 운영 학습 시험이라고 소개하지 않는다. 기존 open(w)의 덮어쓰기 가능성을 숨기지 않는다.

145 최종 전체는 1431 PASS/1 SKIP이며 tracked source 431개 중 허용 grid 한 개만 변경·430개 불변이다. 보호 141개·이전 증거 1399개·운영 catalog/예약 보존과 운영 호출 0을 확인했다. 기존 frontend 271건은 이번 재시험 결과가 아니다.


## 146 — 완성 source manifest 한 개의 명시 등록 CLI

실제 Temp subprocess에서 Unicode manifest와 고정 id/version의 등록·동일 replay를 보여준다. 별도 opaque bytes 등록은 형식 검증이 없다는 한계를 보여주는 반례이며 모델 입력 적합성 성공이 아니다. source 두 건의 CLI 등록과 후속 report writer/143 CLI/소비는 각각 명시 caller 단계다. 운영 root를 실행하는 시연이나 자동 수집·기관 QA 승인 시연으로 바꾸지 않는다.

146 최종 검증은 집중 12 PASS/1 SKIP·관련 126 PASS/1 SKIP·독립 10 PASS/1 SKIP이다. 새 CLI의 DB/sidecar·같은 파일 alias 거부를 보강했고 기존 소스 432개·보호 141개·이전 증거 1416개·운영 catalog/예약을 보존했다. 실제 운영 등록은 없다.


## 147 — GeoQuery의 수동 local LCLUC workflow 근거 조회

기존 GeoQuery 질의 대신 별도 local workflow ID 칸과 명시 조회를 보여준다. 완료 이력의 ID·Trace·model pin·연도·SHA를 읽고 같은 report의 지도·행렬을 수동으로 연다. RUNNING/FAILED와 오류에서 보고서 생성·대체값을 만들지 않는 점을 설명한다. 별도 Temp CPU 추론·mock 승인 fixture와 운영 실행 0을 분리하며 LLM/RAG 완료 시연으로 바꾸지 않는다.

147 최종은 집중9·독립7·front280·build116·backend관련34 PASS이며 실제 main Temp 브라우저와 운영5174 빈ID/disabled 적용을 확인했다. 운영 workflow GET·학습·추론은 0이고 LLM/RAG 연결 완료가 아니다. 지연 경쟁은 단위 시험, 브라우저 중단/뒤로 가기는 응답 완료 후 확인한 범위다.


최신 가용성 정정: 재개 후 재조회에서 기존 API 8000/8001/8002·Temp API8003·frontend5174/5180의 이전 세션은 관측되지 않았다. Ollama만 남은 상태에서 frontend5174만 hidden detached PID34484로 복원했고 API는 Store 복구 부작용을 피하려고 재시작하지 않았다. 따라서 앞선 실제 main Temp 브라우저 PASS와 운영5174 적용 확인은 당시 이력이며 현재 API 서비스 정상 가용성으로 표현하지 않는다. 세션 종료 원인과 Temp fixture 정리 여부는 미확인이다. dev-server-after JSON의 기록 시각은 09:39:17이며 재보존 감사는 09:39:32이다. 원래 사용자 탭 URL 보존과 API offline 상태도 구분한다.

## 147 완료 시연과148/149 근거 설명

먼저 서비스 상태를 읽기 전용으로 확인한다.150 감사의 API offline을 현재 정상이라고 소개하지 않는다. 기존 인증 설정이 확보되어 서버가 복원된 경우에만 GeoLLM→정형 읽기→고정 workflow ID→기록·보고서 읽기→SHA/모델/연도 검토→동일 지도·9×9행렬 수동 열기 순서로 시연한다. 시연을 위해 운영 workflow를 새로 실행하지 않는다. API가 없으면147의 보존 브라우저 증거를 과거 합성시험으로 설명한다.

다음으로148의 중단2창 표와149의 원본/후보 표를 보여준다. 부분 밴드를 완성 패치로 세지 않고 예약 환불을 시연하지 않는다. 원본1111/5차단과 후보1095/4차단을 구분한 뒤 나지 총량·기여 패치·비율 및 지역·연도151부족을 별개로 설명한다. 실제 수집 진척은 [통합 Gate](../gate-notes/GATE_RESUME_AND_DATA_REMEDIATION_20261018.md)의 최종 운영 관측이 있는 경우만 소개한다.

## 수집 재개 결과와 학습 검사 범위 — 2026-10-18 09:57 KST

실제 최대2건 수집이 정상 완료됐다(VERIFIED_REAL). 남술라웨시2021은 거의 숲인 참조창을 기존 다양성 정책으로 보류해 신규0패치,2022는16패치 생성/11적격 증가다. 누계는 물리1400·적격1122이며 새 두 작업 계상 합계19548647B,429회로=false다. 기존 중단2건의 예약136314880B와 부분파일은 보존했다. 두 작업으로 제한한 정상 종료이며 계속 실행중이라고 보고하지 않는다.

최초 실제 학습 준비도 검사는 병렬 수집의 원본 aggregate·원장 갱신을 SHA 대조에서 감지해 성공summary 없이 종료했고 실패근거를 보존했다. 고정1095후보의 별도 재검사와 신규수집분을 포함하는 새 후보 QA는 서로 다르다. 적격1122는 수집 누계이며 정식 학습 승인으로 해석하지 않는다. 최종 근거와 재검사 상태는 [통합 Gate](../gate-notes/GATE_RESUME_AND_DATA_REMEDIATION_20261018.md)의 최신 관측 절을 읽는다.

09:58 최종 감사: 적격 train/val/test639/233/250, 신규16중 적격11·부적격5다. 신규 나지 픽셀 총수는 **0픽셀**이므로 나지 차단 해결은 아니다. 실행lock 해제·기존 pending2만 보존·신규 잔여2341906244B를 확인했다(`collection-resume-audit-20261018-final-outcome.json`).

### API 복원 후속 — 앞선 offline은 과거 관측

Root가 기존 `main.authorized`의 토큰 미설정 localhost 개발 모드를 확인한 뒤 기존 코드·토큰·브라우저 인증 설정을 바꾸지 않고8002 API를 PID33956으로 복원했다. API와 Vite는 모두127.0.0.1에만 바인딩했다. 앞선150의 인증 재사용 조건부 보류는 초기 보수적 판단 이력이며 현재의 영구 차단이 아니다. 실제 GET·브라우저·catalog 보존 최종 검증은 담당의 후속 근거에서 확정한다. API 실행과 학습 준비·모델 승인도 별개다.


## 10:01 KST 확정 — 고정 후보 재검사와 서비스 복원

**VERIFIED_REAL:** 고정1095후보의 실제 raster 재검사는296.625초에 완료됐다. 고정 후보·정책·과거 QA·수집 전 보존 사본4개 SHA가 유지됐고, 파일 기록4285개를 검증했다. 적격628/217/250, 나지 차단4건, `ready_for_training=false`, `scientific_accuracy_validated=false`가 과거 후보 QA와 같음을 확인했다. summary의 `same_as_stored_candidate_QA` 아래 true는 ‘과거 결과와 같음’이라는 비교 결과이며 준비·정확도 승인 true가 아니다. 새1122 수집누계에 대한 새 후보 QA는 여전히 별도 후속이다. 최초 병렬수집 pin 대조 실패도 보존했다(`ml-resume-audit-20261018-candidate-only-summary.json`).

**VERIFIED_REAL:** 10:01:35 API PID33956에서 `/healthz`, `/readyz`, `/api/health`와 Vite5174 경유 `/api/health`가 모두GET200으로 응답했다. 기존 사용자 탭의 상태 새로고침에서도 ‘로컬 분석 서버 연결됨’을 확인했다. catalog14행의 raw·canonical SHA가 전후 같고 현재 access log의 POST는0이다. API/Vite는127.0.0.1이며 토큰 미설정인 기존 localhost 개발 모드, 인증·토큰·브라우저 설정 변경0이다. 앞선 API offline/보류는 초기 관측 이력이다. 이 복원은 공유 운영 배포·모델 정확도·학습 준비 인증이 아니다(`147-local-service-restore-20261018-verified.json`).


## 최종 동결 — 2026-10-18 10:07 KST

이번148 변경 뒤 전체 백엔드 회귀는 **1452건 중1450 PASS·2 SKIP·1046.064초·종료0**이다(`collection-resume-root-full-20261018.log`, `collection-resume-closeout-20261018.json`). 두 SKIP은 Windows 실제 symlink 권한 제한으로, `test_collection_recovery.RecoveryPlanTests.test_artifact_symlink_cannot_read_outside_data_root`와 `test_source_raster_registration_cli.SourceRasterRegistrationCLITests.test_actual_symlink_to_catalog_rejected_or_permission_skip`이다. 후자는1314 권한 오류를 명시한다. 이전145 전체1431 PASS·1 SKIP은 과거 이력이며 이번 결과와 구분한다. 집중7·독립7·전체 회귀는 겹치므로 합산하지 않는다. 코드시험 통과는 운영 모델 정확도·독립 정답·기관 승인이 아니다.

고정1095후보는 실제 QA 뒤4285파일을28.188초에 다시 SHA 계산하여 불일치0을 확인했다(`ml-resume-audit-20261018-final-verification.json`). 후속150 실제 브라우저에서 서버 연결과147 빈 ID/조회 disabled를 확인했고 catalog14행 SHA 보존·운영 POST0을 유지했다. 전체 프로젝트는 미완료이며 학습은 나지4차단으로 BLOCKED다.

**PLANNED — 다음152:** 기존1024창을 넓혀 받으면 중복되는 반텐 나지 검토 위치를256×256 표적창으로 명시 계획하는 RFC를 작성 중이다. 이는 아직 실행 코드나 새 수집 성공이 아니다. 원본 정합·동년 참조·공유 예산·고정 split·기존 공간/scene 중복 방지·품질 검사를 보존하는 설계가 필요하다. 기존 pending2건 정산을 합성하거나 중복방지 기준을 낮추지 않는다.


## 156 통합 — 부족 셀 우선 수집·별도 후보 QA·나지 표적 준비

실제 원본현황 UI의1400/1122→1432/1141 갱신과 SHA/시각을 보여주고 물리·적격·셀부족·목표부족을 분리한다. 나지 14픽셀은 기여패치확보와다르다고 말한다. 후보 미발행 안내를 원본값으로 덮지 않는다.157의2411라벨픽셀과1526개목록영상비중복 관측은 다운로드·품질적격·학습승인이 아닌 실행 차단계획으로만 보여준다.


round2 최종: EastJava2025 g01/g02는 모두 AOI 중심점이 COG 범위 밖이어서 failed였다. 원장 정산은 끝났지만 수집 성공은 아니며 신규 물리·적격·나지는 0이다. 계상 비용은1325635B, 잔여2296542772B이고 누계1432/1141/291·목표부족59·셀부족132는 유지됐다.429는 false이며 기존 pending 두 건과136314880B 예약을 보존했다. round2 stdout은 worker 시작/종료 각각2개를 전달했고 첫 round stdout 부재 이력과 다르다. 상태·수치는 각 실행 시점의 순차 관측이며 실제 후보 QA에 자동 포함되지 않는다.


153 최종 실제 QA: 고정 원본 1400행/적격 1122개(639/233/250)의 차단 5건을 230.906초에 확인했다. 반텐 16행을 새 후보에서만 제외해 1384행/적격 1106개(639/217/250)가 됐다. 후보 QA는 239.188초에 나지 차단 4건과 학습 준비 false를 확인했다. 보존 행과 원본의 일치·완전한 제외/보존 partition·scene/source group/image SHA의 분할 간 충돌 0을 추가 검산했다. 파일 4335개의 SHA도 9.125초에 다시 계산해 불일치 0이었다. 원본 snapshot SHA921152…·정책·구1095 후보는 불변이며 이후 1432행 수집은 이 QA에 포함되지 않는다. 공유 source 차단 미관측은 완전 공간 독립성·현장 정답·과학 승인과 다르다.

현재 round3 EastJava2025g03·Gorontalo2022g03의 제한2건을 시작했으며 실정산·적격 증가량은 아직 대기다. round1/2 완료 값과 실행 중인 round3를 구분한다. 후보 pointer는 source/candidate/QA 세 pin을 검산해 발행했고 API 후보 available=true·현재 원본과 cohort 일치=false를 확인했다. 후보의 실제 화면 표시와 원본 cohort 불일치 경고를 최종 검증했다.


154 최종 실브라우저는 현재 원본1432물리/1141적격/291적격 외·split658/233/250·목표부족59/셀부족132와 고정 후보1106적격·split639/217/250·차단4건·ready=false를 분리 표시했다. 현재 원본 SHA7eac…와 후보 생성 원본 SHA921152…가 달라 새 수집분을 자동 포함한 후보가 아니라는 경고를 확인했다. 수동 새로 조회 시 이전 표를 지우고 단일 busy 뒤 재표시했고 관측 console error/warn0·가로 넘침0이었다. 최초 후보 GET은 수 분 걸렸으므로 SLA로 표현하지 않는다. 모바일·강제 지연·인증 실패는 실제 화면 미재현이며 단위 시험과 구분한다.

최종 추가 관련 회귀는48 PASS/5.326초다. stale 현재 원본 SHA를 먼저 확인해 과거 readiness4335개 불필요 재해시를 생략하되 source_matches_current_manifest=false 판정은 유지했다. 실제 서버 재적용·성능 SLA는 코드 시험과 별도다. 이전47 PASS/11.479초와 묶음을 합산하지 않는다.153의 source1400/후보1106 결과는 확정했으며, 별도로 시작한159 source1432 snapshot QA와 round3 제한 수집은 아직 진행 중이다. 이후 결과를 이번153 cohort에 소급하지 않는다.


### round3 완료 후 관측 정정 — 앞선 수집·UI 수치는 각 시점 이력

10:35:17 round3는 두 작업 정산을 마쳤다. 신규 물리32개·적격23개·저장 참조 나지148픽셀을 더해 누계1464물리/1164적격/300적격 외, split681/233/250이다. 셀 부족은132→109, 전체1200 목표 부족은36이다. 이번 세 round 합계는 신규64물리·42적격·저장 나지162픽셀, 계상87636806B이며 잔여2254269438B다.429는false,실행 잠금은 정상 해제됐고 기존 pending 두 건의136314880B는 보존했다. 나지162픽셀을 새 기여 patch·분할별0.5%·학습 차단 해소로 해석하지 않는다.

기존 UI의1432/1141 관측은 당시 이력이다. API8002를 PID36400으로 재적용해 /api/health200·catalog14 SHA 보존을 확인했다. 최신 GET의 원본1164와 고정 후보1106은 서로 다른 cohort이며 source_matches_current_manifest=false다. 실제 새 UI refresh 확인은 후속이다. GET15.838초는 한 번의 관측이며 SLA가 아니다. 기존153 후보의 나지4차단·4335파일 pin 불일치0과 구1095 보존은 그대로다.

159는1432행 snapshot을 고정한 별도 후속이다. 원본 단계의 적격1141/차단5건·164.672초 관측과 진행 중인 전체 후보 생성/QA를 구분한다. 이후 round3의 새32행은 이 snapshot에 포함되지 않는다. 최종 후보 수량은 영수증·summary·파일 재검산이 끝나기 전 확정하지 않는다.

Root는 병행 Toolbox 작업을 제외한 공개 HEAD와 이번7개 frontend 파일만 격리해 build120모듈/32.33초를 통과했다. 최초 격리시험193 PASS/33 FAIL은 fixture 미수출 ENOENT 이력으로 보존했다. fixture 연결 후 현재 로그는260건 중254 PASS/6 FAIL/22.7347215초이며 최종 검증은 아직 대기다. 초기 fixture 준비 오류와 이후6 FAIL의 원인·최종 결과를 구분해 확인하며 이 실패를 숨기거나 전체 통과로 기록하지 않는다. 앞선 front288/병행 build123과 격리 build120은 서로 다른 소스 범위다.


격리 frontend 최종 정정: 공개 HEAD76949와 동결된 이번 UI7파일만 합친 범위에서288 PASS/0 FAIL/36.4999934초, build120모듈/32.33초를 확인했다. 병행 Toolbox WIP·App·PShell 변경은 이 격리 범위에 포함하지 않았다. 최초33 FAIL은 evidence fixture 미수출, 다음6 FAIL은 Python 시험 import 의존성 연결 누락이었다. 원로그를 보존하고 fixtures/backend/contracts/tests/.runtime/scripts 참조 junction을 보완해 제품 소스 변경 없이 최종 통과했다. 복사·pin metadata 출력 뒤 cp949 경로 print 오류도 준비 도구 이력으로 보존하며 복사 실패나 제품 결함으로 확대하지 않는다. 앞선254 PASS/6 FAIL은 보완 전 이력이며 현재 최종으로 사용하지 않는다. 최신 원본1464/1164의 실제 UI refresh와159 후보 QA는 별도 후속이다.


최신 UI 실제 재조회 확정: 응답 시각2026-10-18 10:41:01 KST의 실제5174→8002 화면은 원본1464물리/1164적격/300적격 외·split681/233/250·목표 부족36/셀 부족109·source SHA c57a…를 표시했다. 고정 후보는 source1400 SHA921152…의1106적격(639/217/250)·나지4차단·ready=false를 유지했고 현재 원본과 불일치 경고를 확인했다. 관측 console error/warn0·가로 넘침0·동결 UI7개 SHA 불일치0이다. 모바일·강제 지연은 실브라우저 미검증이며 저장 품질 집계를 새 native QA로 해석하지 않는다.

격리 frontend 최종288 PASS/36.4999934초·build120모듈/32.33초와 초기 준비 오류 이력을 분리했다. 이전1432 UI는 당시 관측으로 보존한다. round4 반텐2025 g01/g02는 계획 선정만 했으며 아직 실행 전이다.159의 source1432 기반 새 후보 native QA는 진행 중이고 source1400 기반153 후보 완료와 구분한다. 현재 원본1464나 round4 결과를159 QA에 자동 포함됐다고 쓰지 않는다. 전체 개발·독립 정답·나지 보완·기관/학습/배포 승인은 계속 미완료다.


### 159 후속 후보 QA 완료 — 2026-10-18 10:48 KST

PLANNED→VERIFIED_REAL(고정 원본의 파일/래스터 검사 범위):1432행 시점 원본의 새후보는 반텐16행을 제외해1416행/1125적격(train658/val217/test250)이다. sourceQA164.672초·candidateQA216.0초·별도4435파일 SHA10.328초 검사에서 불일치0·source identity 교차분할0을 확인했다. 나지1432/209/1025픽셀·기여0/0/0·차단4·학습미준비/독립정확도미검증은 유지된다. 부가 connectivity 진단은1001820쌍이 기존100만cap을 넘어 NOT_CAPTURED_BUDGET이며 가드를 완화하지 않았다. 최신1464 원본의 나머지23적격은 포함하지 않는다. UI pointer는 아직검증된153의1106후보를 표시한다.1125후보의 API/UI 승계는 다음작업이며 실제화면 반영완료로 표현하지 않는다. 근거:docs/implementation/159_next_collection_candidate_qa.md,evidence/integration/priority-ml-next-20261018-summary.json,priority-ml-next-20261018-final-verification.json.


### 161 후속 UI·수집 완료 근거 — 2026-10-18 10:54 KST

VERIFIED_REAL(수집·파일검사·실제조회범위):4차완료1496물리/1196적격(681/265/250),셀부족97/목표부족4,원본val나지600픽셀·기여1개다. 검증후보1125(658/217/250)를3핀검산·이전receipt보존후UIpointer로승계했고실제브라우저에서차단4·미준비·현재원본과고정source불일치를확인했다. 최신55적격은후보QA밖이다. 나지0.5%/기여5개·독립정답·표적집행미연결차단은미해소다.5차동자바2021 g02/g03 PID33756은시작/완료미확인이다. 보고10분ACTIVE와실제collector/학습0을구분한다. 쉬운설명·이론·동작·증거·발표·Q&A는[161 이해노트](../gate-notes/GATE_CANDIDATE159_UI_ROUND4_20261018.md)에모았다.
