# 02 LCLUC: 토지피복 학습과 멈춰야 할 이유

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-18 03:01:19 KST — 125 최종 독립·실제 Temp 등록자료/bytes·보존 근거 반영 |
| source_commit | 기준 4824b45aada7ba677381bdfad5a9739e12bd2dd5 + 125 작업파일 SHA (미커밋); 실행 gate 변경 없음 |
| evidence_paths | `backend/app/ml/readiness.py`; `backend/app/ml/network.py`; `docs/implementation/23_ml_readiness_resume_20261017.md`; `evidence/integration/ml-readiness-resume-20261017.json`; `docs/implementation/25_ml_split_repair_plan.md`; `evidence/integration/ml-split-repair-plan-20261017.json`; `docs/implementation/26_dataset_version_registry_core.md`; `evidence/integration/dataset-versions-tests-20261017.log`; `backend/app/ml/split_validation.py`; `scripts/validate_training_split_repair.py`; `docs/implementation/44_ml_split_repair_validation.md`; `evidence/integration/ml-split-validation-tests-20261017.log`; `evidence/integration/ml-split-validation-independent-20261017.log`; `evidence/integration/ml-split-validation-full-tests-20261017.log`; `evidence/integration/ml-split-repair-validation-live-final-20261017.json`; `evidence/integration/ml-split-validation-live-integrity-20261017.json`; `backend/app/data/recovery_aggregate.py`; `scripts/inspect_recovery_aggregate.py`; `docs/implementation/46_recovery_aggregate_reconciliation.md`; `evidence/integration/recovery-aggregate-tests-20261017.log`; `evidence/integration/recovery-aggregate-independent-20261017.log`; `evidence/integration/recovery-aggregate-full-tests-20261017.log`; `evidence/integration/recovery-aggregate-live-final-20261017.json`; `evidence/integration/recovery-aggregate-live-integrity-20261017.json`; `backend/app/data/recovery_crop.py`; `scripts/inspect_recovery_crop.py`; `docs/implementation/47_recovery_crop_reconciliation.md`; `evidence/integration/recovery-crop-tests-20261017.log`; `evidence/integration/recovery-crop-independent-20261017.log`; `evidence/integration/recovery-crop-full-tests-20261017.log`; `evidence/integration/recovery-crop-live-final-20261017.json`; `evidence/integration/recovery-crop-live-integrity-20261017.json`; `backend/app/data/recovery_raster_headers.py`; `scripts/inspect_recovery_raster_headers.py`; `docs/implementation/48_recovery_raster_header_validation.md`; `evidence/integration/recovery-raster-headers-tests-20261017.log`; `evidence/integration/recovery-raster-headers-independent-20261017.log`; `evidence/integration/recovery-raster-headers-live-final-20261017.json`; `evidence/integration/recovery-raster-headers-full-tests-20261017.log`; `evidence/integration/recovery-raster-headers-live-integrity-20261017.json`; `backend/app/data/recovery_raster_content.py`; `scripts/inspect_recovery_raster_content.py`; `docs/implementation/49_recovery_raster_content_validation.md`; `evidence/integration/recovery-raster-content-tests-20261017.log`; `evidence/integration/recovery-raster-content-independent-20261017.log`; `evidence/integration/recovery-raster-content-live-final-20261017.json`; `evidence/integration/recovery-raster-content-full-tests-20261017.log`; `evidence/integration/recovery-raster-content-live-integrity-20261017.json`; `backend/app/data/recovery_auxiliary_content.py`; `scripts/inspect_recovery_auxiliary_content.py`; `docs/implementation/50_recovery_auxiliary_content_validation.md`; `evidence/integration/recovery-auxiliary-content-tests-20261017.log`; `evidence/integration/recovery-auxiliary-content-independent-20261017.log`; `evidence/integration/recovery-auxiliary-content-live-final-20261017.json`; `evidence/integration/recovery-auxiliary-content-full-tests-20261017.log`; `evidence/integration/recovery-auxiliary-content-live-integrity-20261017.json`; `backend/app/data/recovery_auxiliary_headers.py`; `scripts/inspect_recovery_auxiliary_headers.py`; `docs/implementation/51_recovery_auxiliary_headers_validation.md`; `evidence/integration/recovery-auxiliary-headers-tests-20261017.log`; `evidence/integration/recovery-auxiliary-headers-independent-20261017.log`; `evidence/integration/recovery-auxiliary-headers-live-final-20261017.json`; `evidence/integration/recovery-auxiliary-headers-full-tests-20261017.log`; `evidence/integration/recovery-auxiliary-headers-live-integrity-20261017.json`; `backend/app/data/recovery_boundary.py`; `scripts/inspect_recovery_boundary.py`; `docs/implementation/52_recovery_boundary_validation.md`; `evidence/integration/recovery-boundary-tests-20261017.log`; `evidence/integration/recovery-boundary-independent-20261017.log`; `evidence/integration/recovery-boundary-live-final-20261017.json`; `evidence/integration/recovery-boundary-full-tests-20261017.log`; `evidence/integration/recovery-boundary-live-integrity-20261017.json`; `backend/app/data/recovery_boundary_topology.py`; `scripts/inspect_recovery_boundary_topology.py`; `docs/implementation/53_recovery_boundary_topology_validation.md`; `evidence/integration/recovery-boundary-topology-tests-20261017.log`; `evidence/integration/recovery-boundary-topology-independent-20261017.log`; `evidence/integration/recovery-boundary-topology-live-final-20261017.json`; `evidence/integration/recovery-boundary-topology-full-tests-20261017.log`; `evidence/integration/recovery-boundary-topology-live-integrity-20261017.json`; `backend/app/data/recovery_boundary_relations.py`; `scripts/inspect_recovery_boundary_relations.py`; `docs/implementation/54_recovery_boundary_relations_validation.md`; `evidence/integration/recovery-boundary-relations-tests-20261017.log`; `evidence/integration/recovery-boundary-relations-independent-20261017.log`; `evidence/integration/recovery-boundary-relations-live-final-20261017.json`; `evidence/integration/recovery-boundary-relations-full-tests-20261017.log`; `evidence/integration/recovery-boundary-relations-live-integrity-20261017.json`; `backend/app/data/recovery_source_footprints.py`; `scripts/inspect_recovery_source_footprints.py`; `docs/implementation/55_recovery_source_footprints_validation.md`; `evidence/integration/recovery-source-footprints-tests-20261017.log`; `evidence/integration/recovery-source-footprints-independent-20261017.log`; `evidence/integration/recovery-source-footprints-live-final-20261017.json`; `evidence/integration/recovery-source-footprints-full-tests-20261017.log`; `evidence/integration/recovery-source-footprints-live-integrity-20261017.json`; `backend/app/data/recovery_source_split_overlap.py`; `scripts/inspect_recovery_source_split_overlap.py`; `docs/implementation/56_recovery_source_split_overlap_validation.md`; `evidence/integration/recovery-source-split-overlap-tests-20261017.log`; `evidence/integration/recovery-source-split-overlap-independent-20261017.log`; `evidence/integration/recovery-source-split-overlap-plan-check-20261017.log`; `evidence/integration/recovery-source-split-overlap-live-final-20261017.json`; `evidence/integration/recovery-source-split-overlap-full-tests-20261017.log`; `evidence/integration/recovery-source-split-overlap-live-integrity-20261017.json`; `backend/app/data/recovery_readiness_comparison.py`; `scripts/inspect_recovery_readiness_comparison.py`; `docs/implementation/57_recovery_readiness_comparison_validation.md`; `evidence/integration/recovery-readiness-comparison-tests-20261017.log`; `evidence/integration/recovery-readiness-comparison-independent-20261017.log`; `evidence/integration/recovery-readiness-comparison-live-final-20261017.json`; `evidence/integration/recovery-readiness-comparison-full-tests-20261017.log`; `evidence/integration/recovery-readiness-comparison-live-integrity-20261017.json`; `backend/app/data/readiness_connectivity_witness.py`; `tests/test_readiness_connectivity_witness.py`; `docs/implementation/58_readiness_connectivity_witness_validation.md`; `evidence/integration/readiness-connectivity-witness-related-20261017.log`; `evidence/integration/readiness-connectivity-witness-independent-20261017.log`; `evidence/integration/readiness-connectivity-witness-live-absence-20261017.json`; `evidence/integration/readiness-connectivity-witness-full-tests-20261017.log`; `evidence/integration/readiness-connectivity-witness-live-integrity-20261017.json`; `backend/app/data/readiness_connectivity_envelope.py`; `tests/test_readiness_connectivity_envelope.py`; `docs/implementation/59_readiness_connectivity_envelope_validation.md`; `evidence/integration/readiness-connectivity-envelope-related-20261017.log`; `evidence/integration/readiness-connectivity-envelope-independent-20261017.log`; `evidence/integration/readiness-connectivity-envelope-live-absence-20261017.json`; `evidence/integration/readiness-connectivity-envelope-live-validation-20261017.json`; `evidence/integration/readiness-connectivity-envelope-full-tests-20261017.log`; `evidence/integration/readiness-connectivity-envelope-live-integrity-20261017.json`; `backend/app/ml/readiness_connectivity_adapter.py`; `tests/test_readiness_connectivity_adapter.py`; `docs/implementation/60_readiness_connectivity_adapter_validation.md`; `evidence/integration/readiness-connectivity-adapter-related-20261017.log`; `evidence/integration/readiness-connectivity-adapter-independent-20261017.log`; `evidence/integration/readiness-connectivity-adapter-ast-parity-20261017.json`; `evidence/integration/readiness-connectivity-adapter-live-saved-state-20261017.json`; `evidence/integration/readiness-connectivity-adapter-full-tests-20261017.log`; `evidence/integration/readiness-connectivity-adapter-live-integrity-20261017.json`; `scripts/run_experiment.py`; `tests/test_readiness_connectivity_cli.py`; `docs/implementation/61_readiness_connectivity_cli_validation.md`; `evidence/integration/readiness-connectivity-cli-related-20261017.log`; `evidence/integration/readiness-connectivity-cli-independent-20261017.log`; `evidence/integration/readiness-connectivity-cli-live-help-20261017.json`; `evidence/integration/readiness-connectivity-cli-ast-parity-20261017.json`; `evidence/integration/readiness-connectivity-cli-full-tests-20261017.log`; `evidence/integration/readiness-connectivity-cli-live-integrity-20261017.json`; `docs/implementation/62_readiness_connectivity_real_validation.md`; `data/first-group/readiness-connectivity-20261017.json`; `evidence/integration/readiness-connectivity-real-preflight-20261017.json`; `evidence/integration/readiness-connectivity-real-execution-20261017.json`; `evidence/integration/readiness-connectivity-real-validation-20261017.json`; `evidence/integration/readiness-connectivity-real-independent-20261017.log`; `evidence/integration/readiness-connectivity-real-token-membership-20261017.json`; `evidence/integration/readiness-connectivity-real-live-integrity-20261017.json`; `backend/app/data/readiness_connectivity_lineage.py`; `scripts/inspect_readiness_connectivity_lineage.py`; `tests/test_readiness_connectivity_lineage.py`; `docs/implementation/63_readiness_connectivity_lineage_validation.md`; `evidence/integration/readiness-connectivity-lineage-related-20261017.log`; `evidence/integration/readiness-connectivity-lineage-independent-20261017.log`; `evidence/integration/readiness-connectivity-lineage-live-cli-20261017.log`; `evidence/integration/readiness-connectivity-lineage-live-20261017.json`; `evidence/integration/readiness-connectivity-lineage-full-tests-20261017.log`; `evidence/integration/readiness-connectivity-lineage-live-integrity-20261017.json`; `docs/implementation/64_readiness_source_identity_contract.md`; `evidence/integration/readiness-source-identity-related-20261017.log`; `evidence/integration/readiness-source-identity-independent-20261017.log`; `evidence/integration/readiness-source-identity-full-tests-20261017.log`; `evidence/integration/readiness-source-identity-live-integrity-20261017.json`; `docs/implementation/65_readiness_source_identity_consumer.md`; `evidence/integration/readiness-source-identity-consumer-related-20261017.log`; `evidence/integration/readiness-source-identity-consumer-independent-20261017.log`; `evidence/integration/readiness-source-identity-consumer-live-cli-20261017.log`; `evidence/integration/readiness-source-identity-consumer-live-legacy-20261017.json`; `evidence/integration/readiness-source-identity-consumer-live-legacy-validation-20261017.json`; `evidence/integration/readiness-source-identity-consumer-full-tests-20261017.log`; `evidence/integration/readiness-source-identity-consumer-live-integrity-20261017.json`; `data/first-group/readiness-source-identity-20261017.json`; `evidence/integration/readiness-source-identity-real-preflight-20261017.json`; `evidence/integration/readiness-source-identity-real-execution-20261017.json`; `evidence/integration/readiness-source-identity-real-cli-20261017.log`; `evidence/integration/readiness-source-identity-real-lineage-20261017.json`; `evidence/integration/readiness-source-identity-real-lineage-cli-20261017.log`; `evidence/integration/readiness-source-identity-real-validation-20261017.json`; `evidence/integration/readiness-source-identity-real-independent-20261017.json`; `evidence/integration/readiness-source-identity-real-live-integrity-20261017.json`; `docs/implementation/66_readiness_source_identity_real_validation.md`; `backend/app/readiness_source_identity_api.py`; `backend/app/main.py`; `tests/test_readiness_source_identity_api.py`; `frontend/src/AgentCenter.tsx`; `frontend/src/ReadinessSourceIdentityDiagnostics.tsx`; `frontend/src/readinessSourceIdentityAdapter.ts`; `frontend/src/readinessSourceIdentityAdapter.test.mjs`; `frontend/src/readiness-source-identity.css`; `docs/implementation/67_readiness_source_identity_api.md`; `docs/implementation/68_readiness_source_identity_ui.md`; `evidence/integration/readiness-source-identity-api-related-20261017.log`; `evidence/integration/readiness-source-identity-api-independent-20261017.log`; `evidence/integration/readiness-source-identity-api-live-20261017.json`; `evidence/integration/readiness-source-identity-api-ui-full-tests-20261017.log`; `evidence/integration/readiness-source-identity-ui-adapter-20261017.log`; `evidence/integration/readiness-source-identity-ui-tests-20261017.log`; `evidence/integration/readiness-source-identity-ui-build-20261017.log`; `evidence/integration/readiness-source-identity-ui-independent-20261017.log`; `evidence/integration/readiness-source-identity-ui-live-20261017.json`; `evidence/integration/readiness-source-identity-ui-console-20261017.json`; `evidence/integration/readiness-source-identity-api-ui-live-integrity-20261017.json`; `backend/app/ml/candidate_plan_lineage.py`; `scripts/inspect_candidate_plan_lineage.py`; `tests/test_candidate_plan_lineage.py`; `docs/implementation/69_candidate_plan_lineage.md`; `evidence/integration/candidate-plan-lineage-related-20261017.log`; `evidence/integration/candidate-plan-lineage-independent-20261017.log`; `evidence/integration/candidate-plan-lineage-live-20261017.json`; `evidence/integration/candidate-plan-lineage-live-cli-20261017.log`; `evidence/integration/candidate-plan-lineage-full-tests-20261017.log`; `evidence/integration/candidate-plan-lineage-live-integrity-20261017.json`; `backend/app/ml/split_planning.py`; `backend/app/ml/split_json_io.py`; `tests/test_split_bounded_io.py`; `docs/implementation/70_split_bounded_io.md`; `evidence/integration/split-bounded-io-related-20261017.log`; `evidence/integration/split-bounded-io-independent-20261017.log`; `evidence/integration/split-bounded-io-live-20261017.json`; `evidence/integration/split-bounded-io-live-run-20261017.log`; `evidence/integration/split-bounded-io-full-tests-20261017.log`; `evidence/integration/split-bounded-io-live-integrity-20261017.json`; `backend/app/ml/candidate_materialization.py`; `scripts/materialize_split_candidate.py`; `tests/test_candidate_materialization.py`; `docs/implementation/71_candidate_materialization.md`; `evidence/integration/candidate-materialization-related-20261017.log`; `evidence/integration/candidate-materialization-independent-20261017.log`; `evidence/integration/candidate-materialization-live-cli-20261017.log`; `evidence/integration/candidate-materialization-live-validation-20261017.json`; `evidence/integration/candidate-materialization-full-tests-20261017.log`; `evidence/integration/candidate-materialization-live-integrity-20261017.json`; `evidence/integration/candidate-materialization-live-20261017/plan.json`; `evidence/integration/candidate-materialization-live-20261017/candidate.json`; `evidence/integration/candidate-materialization-live-20261017/receipt.json`; `backend/app/ml/candidate_staging.py`; `scripts/stage_split_candidate.py`; `tests/test_candidate_staging.py`; `docs/implementation/72_candidate_staging.md`; `evidence/integration/candidate-staging-related-20261017.log`; `evidence/integration/candidate-staging-independent-20261017.log`; `evidence/integration/candidate-staging-live-cli-20261017.log`; `evidence/integration/candidate-staging-live-validation-20261017.json`; `evidence/integration/candidate-staging-full-tests-20261017.log`; `evidence/integration/candidate-staging-live-integrity-20261017.json`; `data/first-group-candidate-qa-stage-20261017/candidate.json`; `data/first-group-candidate-qa-stage-20261017/staging-receipt.json`; `backend/app/ml/candidate_readiness_qa.py`; `scripts/assess_staged_candidate.py`; `tests/test_candidate_readiness_qa.py`; `docs/implementation/73_candidate_readiness_qa.md`; `evidence/integration/candidate-readiness-qa-related-20261017.log`; `evidence/integration/candidate-readiness-qa-independent-20261017.log`; `evidence/integration/candidate-readiness-qa-live-cli-20261017.log`; `evidence/integration/candidate-readiness-qa-live-execution-20261017.json`; `evidence/integration/candidate-readiness-qa-live-validation-20261017.json`; `evidence/integration/candidate-readiness-qa-full-tests-20261017.log`; `evidence/integration/candidate-readiness-qa-live-integrity-20261017.json`; `data/first-group-candidate-readiness-qa-20261017/readiness.json`; `data/first-group-candidate-readiness-qa-20261017/qa-receipt.json`; `backend/app/ml/candidate_qa_comparison.py`; `backend/app/candidate_qa_comparison_api.py`; `tests/test_candidate_qa_comparison.py`; `frontend/src/CandidateQaComparisonDiagnostics.tsx`; `frontend/src/candidateQaComparisonAdapter.ts`; `frontend/src/candidateQaComparisonAdapter.test.mjs`; `frontend/src/candidate-qa-comparison.css`; `docs/implementation/74_candidate_qa_comparison_api.md`; `docs/implementation/75_candidate_qa_comparison_ui.md`; `evidence/integration/candidate-qa-comparison-related-20261017.log`; `evidence/integration/candidate-qa-comparison-independent-20261017.log`; `evidence/integration/candidate-qa-comparison-ui-adapter-20261017.log`; `evidence/integration/candidate-qa-comparison-ui-tests-20261017.log`; `evidence/integration/candidate-qa-comparison-ui-build-20261017.log`; `evidence/integration/candidate-qa-comparison-ui-independent-20261017.log`; `evidence/integration/candidate-qa-comparison-live-http-20261017.json`; `evidence/integration/candidate-qa-comparison-ui-live-20261017.json`; `evidence/integration/candidate-qa-comparison-ui-console-before-fix-20261017.json`; `evidence/integration/candidate-qa-comparison-ui-console-after-fix-20261017.json`; `evidence/integration/candidate-qa-comparison-full-tests-20261017.log`; `evidence/integration/candidate-qa-comparison-live-integrity-20261017.json`; `backend/app/ml/bare_class_requirements.py`; `scripts/inspect_bare_class_requirements.py`; `tests/test_bare_class_requirements.py`; `docs/implementation/76_bare_class_requirements.md`; `evidence/integration/bare-class-requirements-related-20261017.log`; `evidence/integration/bare-class-requirements-independent-20261017.log`; `evidence/integration/bare-class-requirements-independent-arithmetic-20261017.json`; `evidence/integration/bare-class-requirements-live-20261017.json`; `evidence/integration/bare-class-requirements-live-cli-20261017.log`; `evidence/integration/bare-class-requirements-live-validation-20261017.json`; `evidence/integration/bare-class-requirements-full-tests-20261017.log`; `evidence/integration/bare-class-requirements-live-integrity-20261017.json`; `backend/app/ml/bare_patch_feasibility.py`; `scripts/inspect_bare_patch_feasibility.py`; `tests/test_bare_patch_feasibility.py`; `docs/implementation/108_bare_patch_feasibility.md`; `evidence/integration/bare-class-patch-feasibility-focused-20261017.log`; `evidence/integration/bare-class-patch-feasibility-related-20261017.log`; `evidence/integration/bare-class-patch-feasibility-related-corrected-20261017.log`; `evidence/integration/bare-class-patch-feasibility-independent-20261017.log`; `evidence/integration/bare-class-patch-feasibility-independent-review-20261017.json`; `evidence/integration/bare-class-patch-feasibility-live-20261017.json`; `evidence/integration/bare-class-patch-feasibility-live-cli-20261017.log`; `evidence/integration/bare-class-patch-feasibility-live-integrity-20261017.json`; `evidence/integration/bare-class-patch-feasibility-collection-next-review-20261017.json`; `backend/app/data/recovery_commit_contract.py`; `tests/test_recovery_commit_contract.py`; `docs/implementation/109_area_completion_audit.md`; `docs/implementation/110_recovery_commit_contract.md`; `scripts/collect_training_parallel.py`; `backend/app/data/budget.py`; `evidence/integration/recovery-commit-contract-focused-20261017.log`; `evidence/integration/recovery-commit-contract-focused-final-20261017.log`; `evidence/integration/recovery-commit-contract-focused-final2-20261017.log`; `evidence/integration/recovery-commit-contract-related-20261017.log`; `evidence/integration/recovery-commit-contract-related-final-20261017.log`; `evidence/integration/recovery-commit-contract-related-final2-20261017.log`; `evidence/integration/recovery-commit-contract-independent-before-key-guard-20261017.log`; `evidence/integration/recovery-commit-contract-independent-20261017.log`; `evidence/integration/recovery-commit-contract-independent-final3-20261017.log`; `evidence/integration/recovery-commit-contract-preflight-20261017.json`; `evidence/integration/recovery-commit-contract-live-integrity-20261017.json`; `evidence/integration/recovery-commit-contract-external-dependencies-20261017.json`; `docs/implementation/111_data_pipeline_completion.md`; `docs/implementation/112_lcluc_ml_completion.md`; `docs/implementation/113_lcluc_integration_acceptance.md`; `docs/implementation/114_geollm_technical_review.md`; `backend/app/data/collection_registration.py`; `scripts/register_collection.py`; `tests/test_collection_version_registration.py`; `backend/app/ml/error_analysis.py`; `backend/app/ml/service.py`; `tests/test_ml_error_analysis.py`; `scripts/evaluate_geollm_local.py`; `scripts/evaluate_geollm_tools.py`; `tests/test_geollm_local_evaluation.py`; `tests/test_geollm_tool_evaluation.py`; `evidence/integration/data-pipeline-inventory-20261018.json`; `evidence/integration/data-pipeline-focused-final-20261018.log`; `evidence/integration/data-pipeline-related-final-20261018.log`; `evidence/integration/data-pipeline-independent-20261018.log`; `evidence/integration/data-pipeline-independent-review-20261018.json`; `evidence/integration/lcluc-ml-architecture-20261018.json`; `evidence/integration/lcluc-ml-error-analysis-focused-20261018.log`; `evidence/integration/lcluc-ml-error-analysis-related-20261018.log`; `evidence/integration/lcluc-ml-error-analysis-integrity-20261018.json`; `evidence/integration/lcluc-ml-existing-report-error-analysis-20261018.json`; `evidence/integration/geollm-local-evaluation-20261018.json`; `evidence/integration/geollm-native-tools-20261018.json`; `evidence/integration/geollm-runtime-audit-20261018.json`; `evidence/integration/geollm-evaluation-tests-final3-20261018.log`; `evidence/integration/geollm-independent-tests-final-20261018.log`; `evidence/integration/geollm-independent-review-20261018.json`; `evidence/integration/lcluc-geollm-full-tests-20261018.log`; `evidence/integration/lcluc-geollm-live-integrity-final-20261018.json`; `backend/app/lcluc_workflow.py`; `scripts/run_lcluc_workflow.py`; `tests/test_lcluc_workflow.py`; `docs/implementation/115_lcluc_workflow_executor.md`; `evidence/integration/lcluc-workflow-source-freeze-20261018.json`; `evidence/integration/lcluc-workflow-focused-final4-20261018.log`; `evidence/integration/lcluc-workflow-independent-final2-20261018.log`; `evidence/integration/lcluc-workflow-independent-related-20261018.log`; `evidence/integration/lcluc-workflow-independent-review-20261018.json`; `evidence/integration/lcluc-workflow-full-tests-20261018.log`; `evidence/integration/lcluc-workflow-live-integrity-20261018.json`; `backend/app/lcluc_workflow_api.py`; `tests/test_lcluc_workflow_api.py`; `frontend/src/LclucWorkflowPanel.tsx`; `frontend/src/lclucWorkflowAdapter.ts`; `frontend/src/lclucWorkflowClient.ts`; `frontend/src/lcluc-workflow.css`; `frontend/src/ModelAnalysisWorkspace.tsx`; `docs/implementation/116_lcluc_workflow_api.md`; `docs/implementation/117_lcluc_workflow_ui.md`; `evidence/integration/lcluc-workflow-api-focused-final2-20261018.log`; `evidence/integration/lcluc-workflow-api-independent-tests-20261018.log`; `evidence/integration/lcluc-workflow-api-route-preservation-tests-20261018.log`; `evidence/integration/lcluc-workflow-ui-related-final-20261018.log`; `evidence/integration/lcluc-workflow-ui-tests-final-20261018.log`; `evidence/integration/lcluc-workflow-ui-build-final-20261018.log`; `evidence/integration/lcluc-workflow-ui-browser-20261018.json`; `evidence/integration/lcluc-workflow-api-live-integrity-20261018.json`; `evidence/integration/lcluc-workflow-api-live-route-20261018.json`; `evidence/integration/lcluc-workflow-ui-related-final3-20261018.log`; `evidence/integration/lcluc-workflow-ui-tests-final2-20261018.log`; `evidence/integration/lcluc-workflow-ui-build-final2-20261018.log`; `evidence/integration/lcluc-workflow-api-full-tests-20261018.log`; `evidence/integration/lcluc-workflow-api-related-20261018.log`; `evidence/integration/lcluc-workflow-ui-build-final3-20261018.log`; `evidence/integration/lcluc-workflow-ui-synthetic-desktop-final2-20261018.png`; `frontend/src/lclucChangeMapAdapter.ts`; `frontend/src/LclucWorkflowChangeMap.tsx`; `docs/implementation/118_lcluc_workflow_change_map.md`; `evidence/integration/lcluc-change-map-adapter-focused-20261018.log`; `evidence/integration/lcluc-change-map-ui-related-final-20261018.log`; `evidence/integration/lcluc-change-map-generated-fixture-20261018.json`; `evidence/integration/lcluc-change-map-independent-20261018.log`; `evidence/integration/lcluc-change-map-core-focused-20261018.log`; `evidence/integration/lcluc-change-map-core-api-final-20261018.log`; `evidence/integration/lcluc-change-map-nonempty-initial-diagnostic-20261018.log`; `evidence/integration/lcluc-change-map-ui-tests-20261018.log`; `evidence/integration/lcluc-change-map-ui-build-20261018.log`; `evidence/integration/lcluc-change-map-full-backend-20261018.log`; `evidence/integration/lcluc-change-map-live-integrity-20261018.json`; `evidence/integration/lcluc-change-map-browser-20261018.json`; `evidence/integration/lcluc-change-map-nonempty-20261018.png`; `evidence/integration/lcluc-change-map-empty-20261018.png`; `frontend/src/lclucTransitionAdapter.ts`; `frontend/src/LclucTransitionSummary.tsx`; `evidence/integration/lcluc-transition-adapter-focused-final-20261018.log`; `evidence/integration/lcluc-transition-ui-related-20261018.log`; `evidence/integration/lcluc-transition-independent-20261018.log`; `evidence/integration/lcluc-transition-generated-fixture-20261018.json`; `docs/implementation/119_lcluc_transition_matrix.md`; `evidence/integration/lcluc-transition-ui-tests-20261018.log`; `evidence/integration/lcluc-transition-ui-build-20261018.log`; `evidence/integration/lcluc-transition-ui-build-initial-20261018.log`; `evidence/integration/lcluc-transition-browser-20261018.json`; `evidence/integration/lcluc-transition-live-integrity-20261018.json`; `evidence/integration/lcluc-transition-matrix-final-20261018.png`; `evidence/integration/lcluc-transition-class-map-20261018.png`; `backend/app/model_error_analysis_api.py`; `tests/test_model_error_analysis_api.py`; `docs/implementation/120_model_error_analysis_read.md`; `evidence/integration/model-error-analysis-api-focused-final-20261018.log`; `evidence/integration/model-error-analysis-api-related-20261018.log`; `evidence/integration/model-error-read-route-guards-20261018.log`; `frontend/src/ModelErrorAnalysis.tsx`; `frontend/src/modelErrorAnalysisAdapter.ts`; `frontend/src/modelErrorAnalysisClient.ts`; `frontend/src/model-error-analysis.css`; `docs/implementation/121_model_error_analysis_ui.md`; `evidence/integration/model-error-analysis-ui-related-final2-20261018.log`; `evidence/integration/model-error-analysis-ui-tests-final-20261018.log`; `evidence/integration/model-error-analysis-ui-build-final-20261018.log`; `evidence/integration/model-error-read-independent-20261018.json`; `evidence/integration/model-error-read-browser-20261018.json`; `evidence/integration/model-error-read-live-integrity-20261018.json`; `evidence/integration/model-error-read-backend-all-20261018.log`; `backend/app/ml/per_scene_normalization_contract.py`; `tests/test_per_scene_normalization_contract.py`; `backend/app/ml/normalization.py`; `evidence/integration/per-scene-contract-focused-20261018.log`; `evidence/integration/per-scene-contract-existing-boundaries-20261018.log`; `docs/implementation/122_per_scene_normalization_contract.md`; `evidence/integration/per-scene-contract-independent-20261018.json`; `evidence/integration/per-scene-contract-independent-20261018.log`; `evidence/integration/per-scene-contract-runtime-boundary-20261018.json`; `evidence/integration/per-scene-contract-runtime-boundary-20261018.log`; `evidence/integration/per-scene-contract-live-integrity-20261018.json`; `backend/app/ml/per_scene_normalization_files.py`; `tests/test_per_scene_normalization_files.py`; `evidence/integration/per-scene-files-focused-final-20261018.log`; `evidence/integration/per-scene-files-related-20261018.log`; `evidence/integration/per-scene-files-runtime-comparison-20261018.json`; `evidence/integration/per-scene-files-live-integrity-20261018.json`; `docs/implementation/123_per_scene_normalization_files.md`; `evidence/integration/per-scene-files-independent-20261018.json`; `evidence/integration/per-scene-files-independent-20261018.log`; `evidence/integration/per-scene-files-independent-initial-20261018.json`; `evidence/integration/per-scene-files-independent-initial-20261018.log`; `backend/app/ml/model_checkpoint_manifest.py`; `tests/test_model_checkpoint_manifest.py`; `evidence/integration/model-manifest-read-agent-focused-final-20261018.log`; `evidence/integration/model-manifest-read-root-related-20261018.log`; `evidence/integration/model-manifest-read-runtime-20261018.json`; `evidence/integration/model-manifest-read-live-integrity-20261018.json`; `docs/implementation/124_model_checkpoint_manifest.md`; `evidence/integration/model-manifest-read-independent-20261018.json`; `evidence/integration/model-manifest-read-independent-20261018.log`; `evidence/integration/model-manifest-read-agent-focused-20261018.log`; `backend/app/ml/registered_per_scene_files.py`; `tests/test_registered_per_scene_files.py`; `docs/implementation/125_registered_per_scene_files.md`; `backend/app/dataset_registry.py`; `evidence/integration/registry-normalization-agent-focused-20261018.log`; `evidence/integration/registry-normalization-root-related-20261018.log`; `evidence/integration/registry-normalization-runtime-20261018.json`; `evidence/integration/registry-normalization-live-integrity-20261018.json`; `evidence/integration/registry-normalization-independent-20261018.json`; `evidence/integration/registry-normalization-independent-20261018.log` |
| confidence | 완료 소스·집중13/관련38/독립9·실제 Temp6시나리오·보존 확인; 등록선언과 기관/품질/실행 승인 구분 |
| status | TESTED_SYNTHETIC 명시 Dataset3참조·한 장면 파일 읽기; actual 모델 자동연계/과학·실행 승인 BLOCKED |

> 이번 작성은 읽기와 문서화다. 아래 시험 결과는 2026-10-17 보존 로그의 역사적 기록이며 재실행 결과가 아니다. 상태는 각 범위에 한정한다.

## 1분: 시험문제와 답안을 분리하기

모델은 영상의 각 픽셀에 산림·물·시가화 등 이름을 붙이는 학생과 같다. 연습 문제와 시험 문제에 같은 원본 영상이 섞이거나 나지 문제를 거의 배우지 못하면 시험 점수를 믿기 어렵다. 수량은 늘었지만 바로 이 조건 때문에 정식 실자료 학습을 멈춘 상태다.

## 5분: 입력 → 학습 자격 → 평가

6밴드 영상·참조라벨·품질 mask를 준비하고 고정 지역 train/validation/test를 나눈다. readiness가 파일 지문, 밴드, 반사도 정규화, 정합, 공간 대표성, 원본 scene 독립성, 클래스 비율을 검사한다. 통과한 자료에서만 학습을 계획하고, 추후 독립 현장 라벨 평가와 승인 절차를 거친다.

현재 구현은 `TinyUNet`이라는 소형 U-Net 계열이다. 영상을 줄이며 문맥을 보고 다시 늘리며 픽셀 위치를 복원하는 분할 구조다. U-Net++의 구현·성능 우월성을 확인한 근거는 없다. Patch는 작은 영상 조각, Epoch는 학습자료 한 순회, Loss는 예측 오차를 줄이는 기준이다. 모델을 크게 바꾸는 것으로 누출·표본 부족을 해결할 수 없다.

## 이론과 평가

전체 정확도 OA는 맞춘 픽셀 수/평가 픽셀 수다. 클래스별 IoU는 TP/(TP+FP+FN), mIoU는 유효 클래스 IoU 평균이다. 숲이 대부분이면 모든 픽셀을 숲으로 예측해도 OA가 높게 보일 수 있어 혼동행렬과 클래스별 지표·단일 클래스 붕괴를 함께 확인한다. 클래스 가중치를 평가 split까지 보고 정하면 누출이 생겨 `train_only_weights`처럼 학습 기준을 분리한다.

```mermaid
flowchart LR
 A[6밴드·라벨·mask] --> B[readiness.assess]
 B --> C[현재 BLOCKED: 5 blocker]
 C -. 자료 문제 해소 후 .-> D[TinyUNet 학습]
 D -. 후속 독립 검증 .-> E[현장 평가·전문가 승인]
 E -. 승인 후 .-> F[연도별 추론·변화 분석]
```

## 실제 코드·API

| 역할 | 위치·이름 |
|---|---|
| 준비성 | `backend/app/ml/readiness.py:assess`, `balance_diagnostics`, `validate_prepared_training` |
| 날짜·해시·가중치 | 같은 파일 `esri_reference_matches_year`, `verify_files`, `train_only_weights` |
| 신경망 | `backend/app/ml/network.py:TinyUNet` |
| 실행 | `backend/app/ml/service.py:train_model`, `infer_raster`, `evaluate_model`, `metrics` |
| 변화·시계열 | 같은 파일 `analyze_change`, `analyze_timeseries` |
| HTTP | `POST /api/training`, `/api/inference`, `/api/change`, `/api/timeseries` |
| 실험 계획 | `scripts/run_experiment.py`; `--execute` 없는 계획과 실제 학습 분리 |

## 현재 실자료 증거: 08:49 KST 스냅샷

물리 1,384/적격 1,111, 36/36 주·연도, train/val/test 628/233/250, 학습 주 고유 위치 최소32 조건 통과다. manifest SHA는 `cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f`. 기존 QA는 4,335개 고유 파일 지문을 고정했다. 이번에는 그 전체 파일을 재감사하지 않았다.

| 차단 | 이유 |
|---|---|
| 원본 분할 1건 | 동일 `S2A_MSIL2A_20210812T025551_R032_T48MXT_20210812T132431`가 Banten val·West Java test에 걸침; 적격 16/9행 |
| 클래스 불균형 3건 | bare(class7) 비율 train 0.003532%, val 0.001390%, test 0.006307%; 기준 0.5% 미달 |
| validation 클래스 픽셀 1건 | bare 209픽셀로 최소256 미달 |

bare의 기여 패치는 “해당 클래스 256픽셀 이상인 패치”이며 split별 최소5개가 필요하지만 모두0개다. bare 픽셀이 전혀 없다는 뜻은 아니다. 총 blocker5, `ready_for_training=false`, `prepared_payload=null`, 신규 실자료 학습·추론·등록 미실행이다.

## 기존 시험과 한계

`TESTED_SYNTHETIC`: `test_ml_readiness.py` 20 PASS, `test_ml_pipeline.py` 17 PASS 기록. 임시 합성 raster에서 CPU 학습/체크포인트/resume/infer 계약을 확인한 것이며 현장 정확도가 아니다. 통합 197 PASS와 이 수를 더해 새 총합으로 발표하지 않는다.

연도별 결과 차이는 실제 변화 외 계절·구름·센서·라벨 오차에도 생긴다. 변화행렬과 면적은 좌표계·픽셀 면적·분류체계가 맞아야 의미 있다. Esri 일치도는 약한 라벨 일치도다. 정확도 목표 달성·승인 완료라고 발표할 수 없다.

## 10분 확장·발표·Q&A

5분 설명 뒤 2분은 원본 scene과 고정 holdout이 왜 둘 다 필요한지, 2분은 OA와 클래스 붕괴, 1분은 새 자료·독립 평가 계획을 말한다. 대안인 무작위 패치 분할은 쉽지만 독립성 위험이 커서 현재 gate를 유지한다.

30초: “수량·공간 바닥은 넘었지만 같은 원본 scene의 평가 분할 충돌과 나지 대표성 부족을 발견했습니다. 이 다섯 차단을 해결한 새 manifest를 검증한 뒤 학습과 독립 정확도 평가로 넘어갑니다.”

슬라이드: 픽셀 분류 / 분리된 시험 / 5개 차단 / 승인까지.

Q. 1,111개면 충분한가? A. 수량 조건 일부만 통과했다. 누출·대표성과 독립 평가는 별도다.

Q. ready=true면 운영 가능한가? A. 아니다. 학습 입력 자격이며 모델 정확도·승인·배포 인수는 뒤에 있다.

Q. 다음 Gate는? A. 원본을 덮어쓰지 않는 새 manifest와 실제 bare 표본 계획·QA를 인계받아 수치와 대본을 갱신한다.

## 2026-10-17 후속: 원본을 바꾸지 않는 split 복구계획

시험지의 중복 문항을 표시하되 원본 장부를 지우지 않는 것처럼, 새 후보에 어떤 행을 남길지 계획하는 도구를 추가했다. `backend/app/ml/split_planning.py:plan_split_repair`와 `scripts/plan_training_split_repair.py`는 입력 SHA를 고정하고 scene_id/source_group/기록된 영상 SHA가 연결한 전이적 component를 계산한다. 평가 점수·라벨 분포를 보지 않는 사전 우선순위 test→val→train으로 한 split을 보존하며 다른 split으로 행을 재배정하지 않는다. `write_plan`은 출력 직전 입력/readiness SHA를 재확인하고 기존 파일 덮어쓰기를 거부한다.

`VERIFIED_REAL`은 실제 manifest 메타데이터로 계획 JSON을 만든 범위다. `TESTED_SYNTHETIC`은 임시 JSON8 PASS/0.290초다. 실제 원본은 여전히1,384행/적격1,111, 분할628/233/250이다. Banten validation16행을 새 후보에서 제외하고 West Java test를 보존할 **계획**이라 후보 예상은1,368행/적격1,095, 분할628/217/250이다. 후보 버전 `split-repair-v1-754e7a5a0569eb9b`의 실제 manifest 발행·전체 raster QA·학습은 하지 않았다.

메타데이터 source identity 충돌 계획과 기하학적 공간누출 해소는 다르다. 기하 중첩·클래스·대표성은 재감사해야 한다. bare 기여 패치 상한은 여전히 모든 split0개로 미해결이며, 기존 실자료 학습 BLOCKED와 blocker5개 판정을 상향하지 않는다. 새 후보의 정확한 클래스 수치도 미계산이다.

1분 발표: “원본을 보존한 채 충돌 행을 새 후보에서 제외하는 계획을 계산했습니다. 1,095개는 발행된 새 재고가 아니라 계획상 예상이며 나지 부족은 남았습니다.” 5분에는 원본→고정정책→후보→QA를, 10분에는 validation 감소·기하 중첩 재검사를 설명한다. Q. 누출이 해결됐나? A. source 식별자 기반 선택 계획이며 전체 공간독립성·학습 자격 검증은 아직 아니다.

## 저장 split 복구계획을 독립 입력으로 다시 검산

`backend/app/ml/split_validation.py:validate_split_repair_plan`과 `scripts/validate_training_split_repair.py`를 추가했다. 저장한 견적서를 그 안에 적힌 값만 믿지 않고 원장과 별도 계산식으로 다시 검산하는 방식이다. 호출자가 고정한 source/readiness SHA·province split로 기존planner를 재실행해 저장계획의 **모든 필드·배열순서·타입**을 비교한다. 키순서는무관하지만 true/1·1/1.0은다르고 중복키·NaN/Infinity·비유한숫자·미지필드/실행플래그변조도 거부한다.

선택후보의 경로와SHA를 함께 주면 원본행/index/순서·lineage·버전·비실행상태까지 예상문서와 정확히 비교한다. 후보를 생성하거나 발행하는 기능은 아니다. 후보옵션이 없으면NOT_REQUESTED/candidate_integrity_valid=null/reference=null이며 **존재여부를 확인한 뜻이 아니다**. 경로를 명시했는데 없으면 실패다.

실제최종CLI는 WindowsCP949환경에서exit0·METADATA_INTEGRITY_VERIFIED였다. 원본1,384/적격1,111·분할628/233/250은그대로이며, 제외16행을반영한 **계획 예상**1,095/628·217·250이재계산돼 저장계획과 일치했다. 후보는이번명령에서미지정·미발행이고raster파일SHA·기하공간중첩·정확클래스통계는재검사하지않았다. ready_for_training·training_executed·scientific_accuracy_validated는false이며bare부족과기존학습차단을해제하지않는다.

첫실자료검사에서연도가문자열인기존계약과정수전용검사가충돌해 원본을바꾸지않고정수/ASCII4자리문자열을엄격허용하도록수정했다. 이후메타대조/UTF8evidence는성공했으나CP949stdout에서경로문자가실패한중간실행이있었다. stdout/stderr ASCIIescape회귀를추가했고 **최종live-final파일만CLI완료근거**로쓴다. 초기live파일은메타검증후콘솔실패의이력이다.

관련17 PASS/7.544초·독립17 PASS/8.900초·전체338건337 PASS/1SKIP113.601초다. 공개API/화면계약이없어이번내부CLI에는UI수정·브라우저재검증이필요하지않았다. 순차전후SHA검사는OSlock·원자적snapshot·검사후불변성보장이아니며,정식후보발행뒤전체raster/readiness·독립평가/승인이후속이다.

## Aggregate의 중복0과 ML 독립성 검사의 구분

새aggregate읽기조사에서1,384명세행의patchID/imagepath중복0과(source_window.path,scene_id)두필드의원천row유일연결을확인했다. 이것은scene분할누출0·crop중복0·물리raster정상이나클래스균형검증이아니다. year/province/cropwindow/raster는재검사하지않았다.

원본적격1,111/628·233·250과계획예상1,095/628·217·250·후보미발행·bare부족/기존학습차단은그대로다. 하나의scene에서여러patch를만드는정상행위와평가split간같은scene공유의ML누출위험을분리해서설명한다. aggregateCONSISTENT_METADATA도실제정확도·학습/운영승인이아니다.

## Crop 기록 일치와 학습 적격성의 경계

새 crop companion은 실제1,384행의 source 연결·year/province 원형 타입/값·256격자 crop 기록을 대조했다. 각 항목1,384행 일치·중복0·issue0이지만 검사 대상은 JSON 메타데이터다. 원본 raster 크기 내 crop 경계·CRS/transform·다른 파일의 동일 내용·기하 중첩·label/정확 클래스는 미검사다. source report의 province도 batch config의 인증이나 공식 행정경계 승인이 아니다.

따라서 학습 적격1,111/628·233·250과 계획 후보1,095/628·217·250은 그대로다. 누출·bare 부족의 기존5 blocker를 해소하지 않았고 후보 발행·정식 재학습은 없다. 기존 CPU baseline은 Draft로 남는다. 전체386건385 PASS·1 SKIP는 소프트웨어 회귀 근거이며 과학 정확도나 자료의 독립성을 증명하지 않는다. [Crop Gate](gate-notes/GATE_RECOVERY_CROP_20261017.md)를 함께 설명한다.

## 실제 영상 헤더 계약의 확인 범위

새 헤더 companion은 실제1,475개 GTiff의 내부 메타데이터를 읽어1,384 patch의 원본 bounds·크기·밴드/dtype·CRS·affine 계약이 모두 맞음을 확인했다. 이것은 앞선 JSON crop 기록 검사를 넘어선 별도 근거이며 이전 보고서의 미검사 flag는 그 당시 의미를 유지한다.

픽셀 내용·정답/quality·다른 파일의 같은 영상·독립 기하 중첩은 검사하지 않았다. abs1e-7·rel1e-12 affine 오차는 수치 비교 기준이며 모델/센서의 실제 정확도 기준이 아니다. 원본 적격1,111/628·233·250, 계획후보1,095/628·217·250과 기존 누출/bare5 blocker는 불변이다. ready_for_training=false·기존 CPU baseline Draft·후보미발행/정식재학습없음·전체BLOCKED를 유지한다. [헤더 Gate](gate-notes/GATE_RASTER_HEADERS_20261017.md)에서 시험/실제/미검증 범위를 구분한다.

전체403건402 PASS·1 SKIP/95.828초는 소프트웨어 회귀 근거다. 내용SHA 대조는 다음 PLANNED이며 현재 헤더 일치가 데이터 누출/bare 문제를 해소하지 않는다.

## 파일 byte 지문과 학습 적격성의 차이

새 content companion은 고정 manifest의 기록 SHA와 로컬 source/patch byte를 대조하고, 관측 SHA가 맞은 서로 다른 경로의 동일digest 그룹을 진단한다. 다른 압축이나 메타데이터로 저장한 같은 영상은 byte SHA가 다를 수 있고, 같은 byte도 독립 표본 승인이나 픽셀/라벨 품질을 증명하지 않는다.

원본 적격1,111/628·233·250·계획후보1,095/628·217·250·기존 누출/bare5 blocker는 그대로다. 과학 성능·기하 독립성 미검증, ready_for_training=false·baseline Draft·후보 미발행/정식 재학습 없음·전체BLOCKED를 유지한다. [내용 SHA Gate](gate-notes/GATE_RASTER_CONTENT_20261017.md)를 별도 범위로 읽는다.

최종 실제 CP949 CLI exit0에서 고유1,475파일이 모두 MATCH·RECORDED_SHA_MATCH였다. 계획 크기와 실제 반환byte는 각각2,332,461,937B로 같고 명시 예산3,000,000,000B 이내다. issue0·관측 동일digest의 다른 경로그룹0이지만 **전체상태는 BLOCKED**다. caller가 고정한 manifest SHA는 `cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f`다.

이번에는1,475 image 파일의 전체 byte SHA를 순차 streaming 시점에 기대값과 대조했다. label/quality·과거4,335파일 전체 감사·다중파일 원자적 snapshot·픽셀 의미·장면 공간/split 독립성 승인은 아니다. 같은digest 경로그룹0도 서로 다른 파일 표현의 같은 영상이나 기하 누출이 없다는 증거는 아니다. pixel decoder/GDAL/네트워크0·실행/정산/재개/학습/과학 승인false·exactly-once UNKNOWN·환불0을 유지한다.

최신 전체418건417 PASS·1 SKIP/92.959초는 코드 회귀 근거이며 과학 정확도 승인이 아니다.

## 라벨·quality SHA 일치가 학습 승인은 아닌 이유

새 auxiliary companion이 명시2,855파일 byte를 대조해 모두 MATCH였지만 source quality/boundary의 legacy 미기재가 각각80행이라 coverage는 불완전하다. 같은digest 다른경로그룹175는 정답/품질표의 byte 반복이며 그것만으로 장면누출·공간독립·표본 중복으로 판정하거나 삭제/재분할하지 않았다.

라벨 클래스 의미와 실제 정답성·quality 적합성·boundary 공식 승인·독립 성능은 미검증이다. 기존 원본 적격1,111/628·233·250·계획후보1,095/628·217·250과 누출/bare5 blocker·baseline Draft를 유지한다. ready_for_training=false·후보미발행/정식재학습없음·전체BLOCKED다. [보조자산 Gate](gate-notes/GATE_AUXILIARY_CONTENT_20261017.md)를 내용 일치와 coverage의 별도 근거로 읽는다.

최신 전체432건431 PASS·1 SKIP/103.139초는 소프트웨어 회귀 근거이며 관련/독립14를 중복 합산하지 않는다. 명시 보조파일의 지문 일치가 미기재/품질/학습승인 문제를 해소하지 않는다.

## 보조표 격자와 readiness 전체의 구분

새 보조 헤더 companion은1밴드·uint8·nodata0과 영상짝 dimensions/CRS/affine 계약을 읽는다. affine exact와 tolerance 일치는 따로 기록하며 `readiness_full_gate_revalidated=false`다. 허용오차1e-7/1e-12로 맞는 것이 readiness의 정확transform 조건과 클래스/품질·scene독립성 전체를 통과했다는 뜻은 아니다.

내용SHA는 재계산하지 않았고 label 의미·QA적합성·픽셀/과학 성능은 미검증이다. 원본 적격1,111/계획후보1,095·기존5 blocker·baseline Draft·학습false/BLOCKED를 유지한다. [보조 헤더 Gate](gate-notes/GATE_AUXILIARY_HEADERS_20261017.md)를 독립 범위의 근거로 읽는다.

실제 최종 CP949 CLI exit0에서 명시 보조TIFF2,854+영상짝1,475=고유4,329개 모두 VALID_HEADER, 역할별4,072 pairing 모두 HEADER_ALIGNMENT_MATCH·affine_exact_match=true였다. patch label/quality는 각각1,384행 일치/정확일치, sourcequality는1,304행 일치/정확일치(고유86파일)다. issue0이지만 sourcequality80 UNKNOWN이 남아 KNOWN_HEADERS_MATCH_PARTIAL/INCOMPLETE_REFERENCES·BLOCKED이며 boundary는 OUT_OF_SCOPE다.

실제 exact4,072개 일치도 readiness 전체 재검증이나 픽셀/라벨 의미·QA적합성·기하/장면독립·과학 승인과 다르다. 현재 내용SHA는 재해시하지 않았고 명시SHA의 형식/상충만 검사했다. 기존5 blocker·적격1,111/계획후보1,095·baseline Draft·terminal없는2건/예약136,314,880B·환불0·학습/실행/정산/자동재개false·exactly-once UNKNOWN은 유지한다.

최신 전체446건445 PASS·1 SKIP/116.342초는 소프트웨어 회귀 근거이며 과학 승인이 아니다.

## 경계 구조 일치가 학습 지역승인은 아닌 이유

새 boundary companion은 명시 JSON의 SHA·제한된 GeoJSON 구조·province_id 고유성과 row.province 연결을 읽는다. 닫힌 ring·경위도 범위는 topology/자기교차·raster포함·지역/장면 독립성을 증명하지 않는다. 공식ADM1/기관권한·모델 지역적합성·라벨/quality 성능도 미검증이다.

기존적격1,111/계획후보1,095·누출/bare5 blocker·baseline Draft·학습false/BLOCKED를 유지한다. legacy미기재80행은 추정하지 않는다. [경계 구조 Gate](gate-notes/GATE_BOUNDARY_STRUCTURE_20261017.md)에서 구조/출처와 과학·운영 승인을 구분한다.

최종 실제 CP949 CLI exit0에서 명시 경계1파일/482,365B의 기대·관측SHA `de7722bfa88ddff3e12137d271c28717c23b3077a87b7dc36c66d1d8c522c909`가 일치했다.6feature·17,940position의 지원 구조는 STRUCTURE_MATCH·issue0이고1,304행 모두 UNIQUE_PROVINCE_MATCH다. legacy80행 UNKNOWN으로 KNOWN_STRUCTURE_MATCH_PARTIAL/INCOMPLETE_REFERENCES·BLOCKED다. 지역연결 한 건만으로 전체파일의 다른feature/rootCRS issue를 무시하지 않으며 이번 실제결과는 전체issues도0임을 별도로 확인했다.

이는 공식ADM1/기관권한·topology/자기교차·raster pixel포함·기하/장면 독립성·과학 성능 승인이 아니다. 기존5 ML blocker·적격1,111/계획후보1,095·baseline Draft·terminal없는2건/예약136,314,880B를 유지한다. exactly-once UNKNOWN·학습/실행/정산/자동재개/과학 승인false·환불0이다.

최신 전체462건461 PASS·1 SKIP/107.796초는 소프트웨어 회귀 근거이며 과학 승인이 아니다. topology 진단은 다음 PLANNED다.

## 개별 도형 유효성과 모델 자료독립성의 차이

새 topology companion은 feature별 GEOS is_valid·empty·유한양수면적을 진단한다. 하나의 MultiPolygon 내부오류를 찾는 것과 별도feature간중첩·raster포함·장면/분할독립성은 다르다. 유효도형이 공식ADM1·기관권한·과학모델 성능승인이라는 뜻도 아니다. 원본을 자동repair하거나 재투영하지 않는다.

기존적격1,111/계획후보1,095·누출/bare5 blocker·baseline Draft·학습false/BLOCKED는 그대로다. 면적은 degree²진단값이며 실제지역면적으로 발표하지 않는다. [Topology Gate](gate-notes/GATE_BOUNDARY_TOPOLOGY_20261017.md)에서 구조와 위상·과학승인을 분리한다.

실제 최종 CP949 CLI exit0에서 명시1경계/482,365B의 SHA·6feature/17,940position·1,304지역키연결은 issue0이었다. 실행관측은 Shapely2.1.2/GEOS3.13.1이며 feature별6시도 모두 VALID_TOPOLOGY·is_empty=false/is_valid=true·유한양수 평면면적·Valid Geometry였다. legacy80 UNKNOWN으로 KNOWN_TOPOLOGY_VALID_PARTIAL/INCOMPLETE_REFERENCES·BLOCKED다. 평면 degree² 숫자를 실제 사업면적·km²로 전달하지 않는다.

개별feature 유효성은 서로다른feature간중첩·공식ADM1/기관권한·raster pixel포함·기하/장면독립성·과학 성능 승인이 아니다. 자동repair/buffer/make_valid·재투영·geometry쓰기는 없다. 입력상한도 hard CPU시간을 보장하지 않는다. 기존5 ML blocker·적격1,111/계획후보1,095·baseline Draft·terminal없는2건/예약136,314,880B·exactly-once UNKNOWN·환불0·학습/실행/정산/자동재개/과학 승인false를 유지한다.

최신전체475건474 PASS·1 SKIP/103.359초는 소프트웨어 회귀 근거이며 과학승인이 아니다. 교차feature진단은 다음PLANNED다.

## 경계쌍 진단과 학습분할 독립성의 구분

새relations companion의 같은파일 feature쌍 교차결과는 행정도형 관계진단이다. 별도파일쌍·영상/픽셀 중첩·scene/split독립성과는 다르다. 면적중첩은finding이며 기관경계오류를 자동확정하지 않는다. 접촉과양수중첩·UNKNOWN을 구분하고 degree²를실제면적으로쓰지 않는다.

[관계 Gate](gate-notes/GATE_BOUNDARY_RELATIONS_20261017.md)와 함께 기존적격1,111/계획후보1,095·누출/bare5 blocker·baseline Draft·학습false/BLOCKED를 유지한다. 자동repair·삭제·재분할·원본수정은 없다.

실제 최종 CP949 CLI exit0에서 쌍 예산15·계획15·시도15였으며, **13 DISJOINT·2 BOUNDARY_CONTACT·양수 면적 중첩0·issue0**이었다. 접촉 쌍은 South Sulawesi–Southeast Sulawesi와 Banten–West Java이며 교차 면적은0이다. Shapely2.1.2/GEOS3.13.1에서 명시 경계1파일482,365B의 SHA·6개 유효 feature·1,304지역 연결을 확인했지만 legacy80 UNKNOWN으로 KNOWN_RELATIONS_DIAGNOSED_PARTIAL/INCOMPLETE_REFERENCES·BLOCKED다. 다른 파일의 쌍은 OUT_OF_SCOPE이며 실제 제외 쌍은0이다.

같은 파일의 경계쌍 관계는 공식ADM1·기관 권한·행정경계 오류 확정·영상/픽셀 포함·기하/장면/학습분할 독립성·과학 성능 승인이 아니다. 다른 파일쌍은 검사하지 않았고 평면 degree²를 사업 면적으로 제시하지 않는다. repair·재투영·geometry 쓰기 없이 기존5 ML blocker·적격1,111/계획후보1,095·baseline Draft·terminal 없는2건/예약136,314,880B·exactly-once UNKNOWN을 유지한다. 환불0·학습/실행/정산/자동재개/과학 승인false다.

최신 전체490건489 PASS·1 SKIP/107.418초는 소프트웨어 회귀 근거이며 과학 승인이 아니다. 원본영상 footprint·주 연결 진단은 다음 PLANNED다.

## Source footprint의 위치 맥락과 학습승인 구분

네모서리 헤더기반 직선근사는 원본영상과 명시 주 경계의 위치관계를 진단한다. 정확한영상 footprint·곡선가장자리·픽셀포함비율·source대source중첩·학습분할누출과는 다르다. 평면degree²를 실제사업면적으로 제시하지 않으며 경계와닿음/교차를 과학성능이나 지역적합성승인으로 바꾸지 않는다.

기존적격1,111/계획후보1,095·누출/bare5 blocker·baseline Draft·학습false/BLOCKED는 유지한다. 원본영상/geometry·분할을 바꾸지 않고 임시좌표만 변환한다. [원본 footprint Gate](gate-notes/GATE_SOURCE_FOOTPRINTS_20261017.md)에서 sourceSHA재해시false와 근사/독립성한계를 읽는다.

실제 최종 CP949 CLI exit0에서 source header91개와 네 모서리 직선근사 footprint91개가 모두 유효했고, 고유(source,boundary,province)관계86개는 모두 POSITIVE_AREA_OVERLAP·issue0이었다. 명시1,304참조와 legacy80 UNKNOWN으로 KNOWN_CORNER_DIAGNOSTICS_PARTIAL/INCOMPLETE_BOUNDARY_REFERENCES·BLOCKED다. 실행관측은 Shapely2.1.2/GEOS3.13.1·pyproj3.7.2/PROJ9.5.1이며 projection network는 entry=false/exit=false·복원true였다. 양수 교차는 원본영상 전체가 주 안에 있다는 뜻이나 픽셀 포함 비율·정확 footprint·자료 독립성 증명이 아니다.

curved edge densification·정확 raster footprint/면적·pixel inside ratio·source대source교차·학습분할 누출 해결·기하/장면 독립성·공식경계/권한·과학 성능은 미검증이다. source는 헤더만 읽어 현재 full내용SHA를 재계산하지 않았고 임시 네좌표만 변환했으며 원본raster/geometry의 재투영저장·repair·쓰기는 없다. 평면degree²를 사업면적으로 제시하지 않는다. 기존적격1,111/계획후보1,095·ML5 blocker·baseline Draft·terminal없는2건/예약136,314,880B·exactly-once UNKNOWN·환불0·학습/실행/정산/자동재개/과학 승인false는 유지한다.

최신 전체506건505 PASS·1 SKIP/161.521초는 소프트웨어 회귀 근거이며 과학 승인이 아니다. source대source·고정split 후보진단은 다음 PLANNED다.

## 물리 source 후보와 적격학습 누출평가 구분

새 source-split-overlap companion은 실제 고정 province_splits를 전체 물리1,384행의 source맥락에 적용한다. quality_status필터false·eligibility_recomputed=false·readiness_gate_revalidated=false다. 따라서 물리행 split수를 적격1,111의628·233·250과 섞지 않는다.

다중split source공유와 서로다른source의corner교차후보는 별도finding이다. 네모서리근사후보가 없거나 있어도 정확영상/픽셀중첩·적격subset누출·표본독립승인이 아니며 기존5 blocker·계획후보1,095·baseline Draft·학습false/BLOCKED를 유지한다. [고정 split 후보 Gate](gate-notes/GATE_SOURCE_SPLIT_OVERLAP_20261017.md)에서 원본재배정/후보발행/학습없음과boundary미사용을 설명한다.

readiness의 기존 누출차단은 적격scene의 source_group/scene_id 토큰동일과 bounds_wgs84 bbox양수교차로 주별component를 연결한 뒤 고정split충돌을 검사한다. 이번 물리source/canonical경로/corner근사2,227 DISJOINT는 같은대상·규칙이 아니며 차단해제근거가 아니다. 기존차단의 어느분기가 실제원인인지는 현재단위에서 재분류하지 않았으므로 확정하지 않는다.

실제 최종 CP949 CLI exit0에서 전체 물리1,384행은 고정정책상 train848/val272/test264였고91 source 헤더·모서리근사가 유효했다. 교차split 계획2,227쌍·진단기록2,227개·실제intersection2,227회는 모두 DISJOINT, 접촉/양수중첩/issue0·다중split canonical source finding0이었다. 같은 단일split1,868쌍은 OUT_OF_SCOPE다. boundary는 BOUNDARY_NOT_USED이며 이전 경계미기재80행을 이번 누락source로 부르지 않는다. CROSS_SPLIT_CORNER_CANDIDATES_DIAGNOSED라도 전체 BLOCKED다.

대상은 quality필터 없는 물리source이며 적격1,111/readiness·누출을 재평가하지 않았다. 실제 readiness의 적격scene source_group/scene_id 토큰과 bounds_wgs84 bbox연결은 이번canonical source/corner근사와 다른 규칙이다. 기존차단의 실제 원인분기는 현재단위에서 재분류하지 않았으므로 추측하지 않는다.2,227 DISJOINT는 정확영상/픽셀·적격subset/기하/장면독립 승인이나 기존5 ML차단 해제가 아니다. 원본적격1,111/628·233·250·계획후보1,095/628·217·250·baseline Draft·terminal없는2건/예약136,314,880B·exactly-once UNKNOWN·환불0·학습/실행/정산/자동재개/과학 승인false를 유지한다. 원본재배정·후보발행·원본geometry/raster재투영쓰기·repair는 없다.

최신 전체521건520 PASS·1 SKIP/160.195초는 소프트웨어 회귀 근거이며 과학 승인이 아니다. 저장readiness 근거와corner scope 대조는 다음 PLANNED다.

## 저장된 차단 결과의 비교와 원인 미확정

새 comparison companion은 pinned readiness/manifest/corner JSON의 일관성을 확인하며 적격1,111개를 다시평가하거나 현재raster/GEOS·readiness.assess를 실행하지 않는다. prepared_payloadnull이고 적격scene/token/bbox witness가 저장되지않아 기존공유원본차단의 실제분기는 UNKNOWN_NOT_PERSISTED다. province_groups에 west_java→banten이 있어도 token/bbox 어느분기인지 추측하지 않는다.

group_splits는 고정6주map이며 연결component5개와 keys수가다르다고 오류가아니다. 저장5 blocker·628·233·250과 물리848·272·264를 함께 보존한다. [Readiness 범위 대조 Gate](gate-notes/GATE_READINESS_COMPARISON_20261017.md)는 snapshot일관성 근거이며 학습차단해제·적격누출/과학승인이아니다. baseline Draft·계획후보1,095·학습false/BLOCKED를 유지한다.

실제 최종 CP949 CLI exit0에서 세 pinned JSON은 CONSISTENT_SAVED_SCOPE_METADATA·issue0이었다. 저장5개 blocker와 적격1,111/628·233·250을 보존하고 물리1,384/848·272·264와 구분했다. 차이220·39·14는 산술비교이며 제외행 목록이나 원인 복원이 아니다. 저장corner의 완전성·2,227개 recorded DISJOINT·후보없음 요약은true지만 현재영상/기하를 다시 검사한 결과가 아니다. prepared_payload=null·적격scene witness와 token/bbox 실제원인분기는 UNKNOWN_NOT_PERSISTED이며 저장component 연결도 분기증거가 아니다.

이번은 JSON snapshot의 binding·범위·완료기록·최소schema 일관성 대조다. 현재raster stat/header/픽셀·GEOS·readiness.assess·source내용SHA·적격성·누출/독립성·차단원인 복원을 수행하지 않았다. 현재policy/codeSHA 대조는 저장readiness 생성시점 코드의 증명이 아니며 원자적 snapshot 보장도 아니다. 고정6주group_splits와 연결component5개를 혼동하지 않는다. 기존5 ML차단·계획후보1,095·baseline Draft·terminal없는2건/예약136,314,880B·exactly-once UNKNOWN·환불0·학습/실행/정산/자동재개/과학 승인false·BLOCKED를 유지한다.

최신 전체538건537 PASS·1 SKIP/174.829초는 소프트웨어 회귀 근거이며 과학 승인이나 차단해제 근거가 아니다. 향후witness 계약/helper는 다음 PLANNED다.

## Prospective witness와 과거원인 복원의 차이

새순수helper는 앞으로 명시공급한 scene metadata에서 token/bbox연결이유를 남길수있다. 입력은callerasserted이며 적격성·원본scene index·provenance를 승인하지않는다. 기존readiness.assess에통합하거나 현재적격scene를 재평가하지않았다.

실제저장보고서는prepared_payloadnull/scene witness부재로 helper(None)→UNKNOWN_NOT_PERSISTED·union_complete=false만확인했다. 과거5 blocker·적격1,111/628·233·250·계획후보1,095·baseline Draft·학습false/BLOCKED는그대로다. [Connectivity witness Gate](gate-notes/GATE_CONNECTIVITY_WITNESS_20261017.md)에서 저장절단/전체계산·None/empty·미확정신원을구분한다.

이번 실제 확인은 고정SHA의 저장readiness에서 prepared_payload=null·eligible scene/witness부재를 읽고 순수helper(None)를1회 연결한 범위다. 결과는 UNKNOWN_NOT_PERSISTED·union_complete=false이며 실제적격장면의 token/bbox연결을 실행하거나 과거원인을 복원하지 않았다. 기존5 blocker와 적격1,111/628·233·250은 원형 그대로 보존됐다. supplied metadata의 연결계산은 합성자료로 검증했으며 적격성은 CALLER_ASSERTED_NOT_VERIFIED다.

helper는 파일IO·raster/경계·GEOS·네트워크·readiness.assess를 하지 않는 순수함수이며 CLI/API/UI가 없다. None과 명시빈목록, 빈group의 두token skip/bbox유지, 전체union계산과 반환edge목록 절단을 구분한다. “저장한도”는 메모리 결과목록의 한도이며 파일/DB 영속저장은 구현하지 않았다. caller입력의 신원·적격성·원본scene index·전체독립성·과거원인을 승인하지 않는다. 원본gate/policy/분할/원장/lock/모델·계획후보1,095·baseline Draft·terminal없는2건/예약136,314,880B·exactly-once UNKNOWN·환불0·학습/실행/정산/자동재개/과학 승인false·BLOCKED를 유지한다.

최신전체554건553 PASS·1 SKIP/197.097초는 소프트웨어 회귀 근거이며 실제적격연결/원인복원·학습승인이 아니다. 입력provenance/eligibleidentity·assess통합은 다음 PLANNED다.

## 입력/출처지문 봉투와 적격성 승인의 차이

새envelope는 명시입력과helper반환witness를재현가능한bytes로묶는다. 외부pin·selfdigest·helper재계산은메모리계약이며 출처파일/실행코드·실제적격scene신원을인증하지않는다. provenance_verified/executing_helper_code_verified/eligibility_verified=false다.

실제과거scene목록은저장근거에없어None입력왕복만확인했고 UNKNOWN_NOT_PERSISTED·기존5차단·적격1,111/계획후보1,095·baseline Draft·학습false/BLOCKED를유지했다. [Envelope Gate](gate-notes/GATE_CONNECTIVITY_ENVELOPE_20261017.md)에서 caller핀과실자료인증·Root증거파일/모듈영속저장·향후assessadapter를구분한다.

실제 확인은 고정SHA의 저장readiness에서 scene근거/payload부재를 읽고, 독립구성한 None/None/defaultlimits입력의 pin으로 build→encode→decode→재encode한3,385bytes가 동일함을 확인한 범위다. 실제적격scene를 공급하거나 과거원인을 복원하지 않았으며 UNKNOWN_NOT_PERSISTED·기존5 blocker·적격1,111/628·233·250을 유지했다. Root가 raw/audit evidence파일을 새로 쓴 것은 모듈의 영속저장 구현이 아니다.

이 모듈은 순수메모리 build/validate/encode/decode bytes계약이며 파일/DB/CLI/API/UI·assess통합을 구현하지 않았다. 독립외부helper/provenance/input pin과 typed/canonical helper재계산을 사용하지만 caller선언SHA 일치가 실제파일출처·실행코드identity·eligibility 인증은 아니다. verified는 모두false다. Python sortkeys/compact UTF8규약은 RFC8785나 타언어serializer 동일성 보장이 아니며 None/empty·배열순서·literal/int/float/bool·signedzero·truncation을 구분한다. 원본gate/policy/분할·원장/lock/모델·계획후보1,095·baseline Draft·terminal없는2건/예약136,314,880B·exactly-once UNKNOWN·환불0·학습/실행/정산/자동재개/과학 승인false·BLOCKED를 유지한다.

최신 전체572건571 PASS·1 SKIP/158.325초는 소프트웨어 회귀 근거이며 실제적격성·과거원인복원·학습승인이 아니다. 최소선택적 adapter설계/합성검증은 다음 PLANNED다.

## 보완: 저장 패치 통계와 연결 참여 scene 수의 구분

`backend/app/ml/readiness.py`의 patch 집계·scene 추가·연결 코드를 읽어 범위를 명확히 했다. `patch_count`는0에서 시작하고 적격 조건을 만족한 patch만 증가한다. 이후 `scenes.append(..., eligible_patches=patch_count)`는 patch_count>0을 추가 조건으로 두지 않으며 token/bbox union은 구성된 scenes 전체를 순회한다.

따라서 저장628·233·250, 합계1,111은 **적격 patch 통계**다. 이를 연결 참여 scene 수가1,111이라는 증거로 사용하지 않는다. prepared_payload=null로 역사적 scene 목록·개수와 실제0패치 scene의 존재 여부는 미확인이다. 코드는0패치 scene이 포함될 가능성을 허용하지만 이번 문서 작업이 실제로 그런 장면을 발견한 것은 아니다. 기존차단의 token/bbox 실제원인도 UNKNOWN_NOT_PERSISTED로 유지한다.

후속 선택적 adapter는 실제 assess의 장면구성·연결지점을 먼저 확인해야 한다. `eligible_patches>0` 필터를 임의로 추가하면 기존union 참여집합을 바꾸어 판정동등성을 훼손할 수 있다. 현재helper/envelope는 caller가 공급한 목록만 진단하며 과거목록을 복원하지 않는다. adapter통합·실자료재평가와0패치실재 여부판정은 이번 보완에서 수행하지 않았다.

## 연결근거 관측과 기존 gate판정의 격리

새adapter는 기본off이며 True일때원report뒤별도diagnostics만추가한다. 기존union·blocker순서·고정분할·통계/payload는그대로고 진단copy/helper실패가gate를수정하지않는다. outergate가합성/약한라벨실험에서ready여도 child진단은BLOCKED/승인false다. capture상태를새학습승인/차단으로읽지않는다.

0patch포함전체append scenes·원순서를보존하고 임의필터/목록자르기는없다. [Adapter Gate](gate-notes/GATE_CONNECTIVITY_ADAPTER_20261017.md)의 합성동등성/AST와실제저장부재범위를구분한다. 저장1,111은patch통계이며 역사scene수·실제0patch존재/원인은미확인이다. 실자료assess재평가없이 기존5 blocker·baseline Draft·학습false/BLOCKED·원본/분할을유지한다.

기본off의 내부 `assess(..., connectivity_diagnostics=True)` 선택연결은 구현했고 합성 on/off 판정동등성과 격리를 확인했다. 실제전체자료 assess/on진단은 재실행하지 않았다. 실제확인은 기존저장report SHA동일·prepared_payload=null·새diagnostics부재·5 blocker 원형과 적격patch628·233·250 보존이다. 역사적union scene수·실제0patch scene존재·token/bbox 원인은 UNKNOWN_NOT_PERSISTED다.1,111은 저장patch통계이며 scene수가아니다.

True에서만 원report완료뒤deepcopy경계를 통해 별도capture를 추가한다.0patch포함모든append scenes·원순서·falsygroup양token skip/bbox유지·scalar str규칙을 보존하며 임의필터/목록자르기를 하지 않는다. copy/import/capture실패·지원밖policy/순서·metadata/예산은 capture상태만 바꾸고 원gate union/blocker/분할/통계/payload를 수정하지 않는다. child진단BLOCKED는 승인권한없음이며 outergate가합성/약한라벨ready일가능성과 별개다. CLI/API/UI·영속저장·59envelope연결은없다. 기존실자료5차단·계획후보1,095·baseline Draft·terminal없는2건/예약136,314,880B·exactly-once UNKNOWN·환불0·실행/정산/자동재개/과학 승인false를 유지한다.

최신전체589건588 PASS·1 SKIP/164.510초는 소프트웨어회귀/합성동등성근거이며 실자료재평가나 과거원인복원·학습승인이 아니다.

## CLI옵션 노출과 실제 학습/진단실행의 구분

새기본off CLI옵션은 내부adapter를명시요청할수있게하지만 실제자료를이번에재평가하지않았다. 진단요청은기존ready/execute/run-id/resume조건을우회하지않고 진단자체학습권한false다. off의기존결과/write/학습동작도유지한다.

[CLI Gate](gate-notes/GATE_CONNECTIVITY_CLI_20261017.md)에서 합성19시험/독립검증과실제help를구분한다. 저장1,111은patch통계이며 역사scene수·실제0patch존재/원인은여전히미확인이고 기존5차단·baseline Draft·계획후보1,095·실자료학습BLOCKED는유지된다. 실행후진단은별도readiness파일이며최종experiment report로자동전파되지않는다.

기본 off의 `--connectivity-diagnostics`와 명시 새readiness-output 보호는 구현됐다. 실제 확인은 CLI `--help`1회 exit0·flag노출이며 실자료 assess/학습은 실행하지 않았다. 실제저장report SHA·5 blocker 원형·적격patch628·233·250은 그대로이고 역사적union scene수·실제0patch scene존재·원인은 UNKNOWN_NOT_PERSISTED다. 공개API/UI·59envelope 연결은없다.

진단True는 새출력사전검사·parent/target재확인·exclusive x UTF8쓰기와 ASCII capture요약을 추가하지만 off의 기존write/4키/execute승인체인은 유지한다. partial새파일은 실패흔적으로 보존하고 전체원자적FS/악성OSretarget차단을 보장하지 않는다. NOT_REPORTED/미지/null과 scene수/patch합을 구분한다. 명시execute로 원경로를통과한 최종experiment report에는진단이자동전파되지않아 원문은별도readiness-output에있다. stdout기존UTF8재설정과 새요약ASCII는 CP949고정출력과다르다. 진단자체학습/과학/정산/재개권한false·기존실자료5차단·계획후보1,095·baseline Draft·terminal없는2건/예약136,314,880B·exactly-once UNKNOWN·환불0을 유지한다.

최신전체608건607 PASS·1 SKIP/207.921초는 소프트웨어/합성출력보호 근거이며 실자료재평가·과거원인복원·학습승인이 아니다.

## 현재 scene/patch 관측과 공유제품 전체회원

실제 CLI를 학습/재개/다운로드 없이1회 실행해 exit0·70.437초에 새진단보고서를 생성했다. 현재 CAPTURED_COMPONENTS_MATCH이며 append scene1,384개·0patch scene273개·적격patch1,111개(628/233/250)를 구분했다. 기존보고서와 assessed_at/새diagnostics 외 모든typed값·5 blocker·4,335 verified_files기록은 같다. 기존report는덮어쓰지 않았고 전체gate는BLOCKED다. 이번실제assess는 기존영상/라벨hash·픽셀QA를 수행했으며 pureadapter의추가IO0을 전체CLI무IO로확장하지 않는다.

현재 scene_id 토큰 `S2A_MSIL2A_20210812T025551_R032_T48MXT_20210812T132431`의 직접cross-split event는 West Java/test의 내부scene1096(0patch)→Banten/val의scene303(1patch)다. 같은토큰 전체회원은28scene 모두scene_id역할이며 Banten16개는전부1patch, West Java12개는0patch3개/1patch9개다. **양쪽에양수patch장면도있어 첫0patch event가충돌이0patch에만한정됨을뜻하지않는다.** 내부sceneindex를원본manifest행번호로단정하지않으며 삭제/필터후차단해소 counterfactual은검증/승인하지않았다. 현재관측은과거생성원인·회원/scene수의소급인증이아니고 역사근거는UNKNOWN_NOT_PERSISTED로유지한다.

현재helper는957,036 bbox쌍/2,768 token을처리했고 event15,019개(token2,595+bbox12,424)중10,000개를저장해5,019개가생략됐지만 union_complete=true다. 독립graph/BFS 검토가현재전체projected JSONmetadata에서모든계수·첫10,000필드·component를대조해 cross-split bbox0/token1을확인했다. 이는잘린prefix만의추론도 원본영상/정확기하독립성검사도아니다. 문서validation20항목은새unittest20개가아니다.

현재준비성관측 VERIFIED_REAL은과학정확도·기관/운영승인·정확footprint/픽셀독립성·누출해결이아니다. 기존5 blocker·baseline Draft·계획후보1,095·terminal없는2건/예약136,314,880B·환불0·exactly-once UNKNOWN·학습/실행/정산/자동재개/과학승인false를유지한다. 공개API/UI계약변경이없어화면은기존readiness5차단상태를유지하고 새tokenwitness카드를연결한것은아니다. 내부읽기진단은기존허용범위에서진행하며 과학/운영승인과새사용자승인절차를혼동하지않는다.

[실자료 관측 Gate](gate-notes/GATE_READINESS_REAL_DIAGNOSTIC_20261017.md)의새근거이며 이전scene수/원인미확인기록은역사report범위로유지한다. 이번full회귀는새로돌리지않았다.

현재 cross-split bbox교차0인데 token연결1이 남는 것은, bbox가 달라도 같은 촬영제품 ID문자열을 공유하면 같은 그룹으로 묶는 기존의 보수적 규칙을 관측한 결과다. 물리·정확픽셀 중첩이 있다고 추정하지 않고, bbox0을 학습독립성/승인으로도 해석하지 않는다. 같은제품 회원 양쪽에 양수patch장면이 있어0patch만의 문제로 좁히지 않는다.

## 원본 후보추적과 정확한 장면 identity의 차이

새lineage조회에서 현재공유token의report/raw회원은28개씩이지만 후보연결400개·고유raw행28개다. 모든report회원에여러후보가있어 정확한원본행은인증하지않았다. report에장면별image_path/hash가없고 내부sceneindex를rawrowindex로단정하지않는다.

[Lineage Gate](gate-notes/GATE_CONNECTIVITY_LINEAGE_20261017.md)의metadata후보는적격성/파일진실·과거원인/기하독립·삭제후차단해소승인이아니다. 현재28회원양쪽positivepatch·5차단·patch1,111·baseline Draft·학습BLOCKED를유지하고 영상/assess를재실행하지않았다. sourceidentityversioned계약은후속PLANNED다.

### 63 최종 검증·보존 범위

최종 전체 `scripts/test.ps1`은 **624건 중 623 PASS·1 SKIP/176.415초/종료0**다. SKIP은 기존 Windows symlink 생성 권한 제약이며 deterministic 경계 시험은 통과했다. 관련16 PASS/4.983초·독립16 PASS/5.564초와 별도8개 변조 거부 실험은 전체624에 중복 합산하지 않는다. 보호133참조(새 실자료 보고서 포함)·기존24계약SHA·입력 manifest/current report 핀이 불변이고 이전 snapshot 추적 코드·데이터·계약의 변경0을 확인했다. 저장된 다섯 차단과 패치628/233/250은 그대로다. 이 단위는 두 JSON의 후보 조회이며 영상·assess를 재실행하지 않았다.

모든28장면은 모호한 후보 집합으로 남는다. 다음 source identity 전달 계약은 PLANNED이며 이미 확인한 경로·지문을 추가 IO 없이 넘기는 설계/합성 검증부터 검토한다. 기존 준비도 판정·정책·분할을 바꾸지 않고 실자료 재assess도 하지 않았다.

## 선택적 source identity 선언 계약 — 64

[Source identity Gate](gate-notes/GATE_SOURCE_IDENTITY_CONTRACT_20261017.md)는 이미 assess가 계산한 image_path/image_sha256를 별도 versioned optional 객체로 전달하는 변경이다. 기존 schema1/projected5키·helper/gate 판정은 유지하고 추가 파일 IO는0이다. 두 값 부재·부분 선언·무효 선언·전체 선언을 구분하며, 단서 생성 예외가 기존 진단을 바꾸지 않게 격리한다. 선언 형식 검사는 파일 진실·출처·원본행 인증이 아니다.

구63 소비자는 새 객체를 아직 사용하지 않고 실자료 assess/새 보고서 생성도 없다. 따라서 현재28장면 전원 모호성·400후보연결/고유raw28·다섯 차단·패치628/233/250은 유지된다. 다음 소비자 연결은 PLANNED이며 새 API/UI 계약이 없어 이번 화면 변경은 필요 없다.

### 64 최종 검증·보존

최종 전체 `scripts/test.ps1`은 **630건 중629 PASS·1 SKIP/192.060초/종료0**다. 기존 Windows symlink 생성권한 제약1개를 건너뛰었으며 deterministic 경계 시험은 통과했다. 관련23 PASS/6.047초와 독립23 PASS/5.827초는 전체630에 중복 합산하지 않는다. 보호133참조와 adapter 외24기존 계약SHA, 입력 manifest/current report 핀, 다섯 차단·패치628/233/250은 불변이다. 이전 추적 코드·데이터·시험에서 의도한 adapter와 그 시험2개만 변경됐고 readiness assess/CLI는 그대로다. 기존 실제 보고서에는 source_identity가 없는 상태를 유지하며 실자료 assess 재실행·새 실자료 보고서 생성은 없었다.

## Source identity 소비와 별도 후보 refinement — 65

[선언 단서 소비 Gate](gate-notes/GATE_SOURCE_IDENTITY_CONSUMER_20261017.md)는 optional version1 객체를 엄격히 검사하고 완전한 선언 경로·SHA만 별도 후보 refinement에 사용한다. 원래 넓은 회원/후보·계수는 유지한다. raw 후보 하나라도 비교 불가하면 해당 원래 집합을 보존하고, 중복 선언은 모호성으로 남긴다. 단일 후보도 DECLARED_METADATA_ONLY로서 정확 원본행·파일/제품 인증은 false다. 문자열 경로 성분 비교는 실제 파일시스템 identity나 추가 영상 IO가 아니다.

현재 실제 보고서에는 단서가 없으며 새 assess/보고서를 만들지 않아28전원 모호성은 그대로다. 구 legacy 출력은 유지하고 API/UI 계약이 바뀌지 않아 화면 변경은 불필요하다. 다음 고정 입력·정책/자원 범위에서 학습 없는 새 진단 보고서 관측은 PLANNED다.

### 65 최종 검증·현재 실자료 범위

최종 전체 `scripts/test.ps1`은 **638건 중637 PASS·1 SKIP/190.384초/종료0**다. SKIP은 기존 Windows symlink 생성권한이며 deterministic 경계 시험은 통과했다. 관련 lineage24 PASS/8.893초·호환1 PASS/0.579초, 독립24 PASS/8.200초·호환1 PASS/0.419초는 전체638에 중복 합산하지 않는다. 보호133참조·lineage 외24계약SHA·manifest/current report 핀과 다섯 차단·패치628/233/250은 불변이다. 이전 추적 파일 중 의도한 lineage 코어·그 시험·adapter 호환시험3개만 변경됐고 producer adapter/readiness/CLI는 유지했다.

Root의 CP949 실제 legacy CLI1회는 종료0이며 결과57,548bytes·SHA `cff1fb4b566cb8d9be4625df253411d3776ae1f0e485854798ac36673aac2a8e`로63 출력과 바이트 동일했다. 현재 report에 identity가 없어 refinement도 없고28전원 AMBIGUOUS·400연결/고유raw28·exact binding false가 그대로다. 이는 하위호환 관측이며 새 identity의 실자료 소비 검증은 아니다. 두 고정 JSON만 조회했고 영상 IO·assess 재실행·새 readiness 보고서 생성은 없었다.

## 새 noexecute 보고서의 선언 대조 관측 — 66

[실자료 선언 대조 Gate](gate-notes/GATE_SOURCE_IDENTITY_REAL_20261017.md)는 코드변경 없이 실제 assess1회와 소비 CLI1회를 관측한 결과다. 새 보고서의1,384장면 모두 완전한 경로·SHA 선언을 포함한다. 명시 제품 token28회원의 넓은 후보는 여전히400연결·고유raw28·전원모호성이며 별도 refinement에서28연결·고유raw28·전원 UNIQUE_DECLARED_METADATA_CANDIDATE를 관측했다. 이는 선언 기록 일치일 뿐 exact binding·출처/파일시스템 identity·학습/과학승인은 false다. 특정 token28개 대조를1,384장면 원본행 인증으로 확대하지 않는다.

실제 assess는 기존 영상/라벨 읽기·해시를 수행했다. adapter 단서 전달의 추가IO0과 후속 소비 CLI의 두JSON 조회 범위는 전체 assess와 다르다. 실제85.641초·표본165회 RSS최대214,609,920B·600초/2GiB감시는 하드메모리 제한 보장이 아니다. 새 코드/unit/full은 없고 직전65의638회귀는 별도 역사 근거다. 새 API/UI 계약이 없어 화면 변경·새 보고서 자동 연결은 없으며 기존5차단은 유지한다.

### 66 최종 독립·보존과 다음 범위

최종 보존 근거는 보호133참조·25기존 계약SHA·이전 추적 코드/데이터/시험의 변경0을 확인했다. 정책·manifest·두 이전 보고서와4335 verified_file records·다섯 차단·패치628/233/250은 보존됐다. 메타데이터 검증16항목은 모두 통과했지만 새 unittest16개가 아니다. 독립 검토는 세 고정 JSON을 처음/끝 SHA 대조하고 helper/consumer/assess 없이 별도 ntpath 계산으로1,384전원 선언의 순서/상태와 경로·SHA 쌍이 각각 유일한 raw metadata 후보에 맞는지 확인했다. 이 독립 선언 검산 역시 파일·출처·정확 원본행 인증은 false다.

소비 CLI의 명시 query28회원은 Banten16장면/16패치/0patch0, WestJava12장면/9패치/0patch3으로 합계25패치·0patch3이다. 넓은400연결/28전원모호성과 별도28연결/전원유일선언후보는 함께 유지되고 절단은 없다. 독립 검토의1,384전체 선언쌍 검산과 소비 CLI의 token28명시 조회 범위를 구분한다.

다음은 현재 실자료 진단을 전달할 최소 읽기 API projection·명시 조회 UI 계약과 노출 최소화 검토다. 현재 PLANNED로 API/UI 구현·새 화면 연결은 없으며, UI 영향 기능을 구현하면 web_ui에 계약을 인계한다. 과학/운영 승인이나 gate 해소를 뜻하지 않는다.

## 저장 출처 대조의 명시 읽기 API·UI — 67/68

[저장 진단 API·UI Gate](gate-notes/GATE_SOURCE_IDENTITY_API_UI_20261017.md)는66 저장 보고서의12계수·핀/token SHA·8비승인false만 반환하는 읽기 API와 Agent Center 수동 조회 카드다. POST /v1/diagnostics/readiness-source-identity에 report_sha256·manifest_sha256·token을 명시한다. 원본 경로·행index·token원문·큰JSON을 반환하지 않고8KiB본문·threadpool/process-local 단일worker·429·no-store를 적용한다. HTTP200도BLOCKED이며 저장 관측 조회이지 현재 영상/라벨 재hash·assess·학습 시작이 아니다.

프론트는 명시 버튼만 호출하고 핀/token SHA·정확한 응답키/상태·12계수·8false/교차모순을 검사한다. 입력·Agent/모델/Job선택·Registry/메뉴 변경 때 이전 결과를 지우고 세대/입력key/hash가 맞는 응답만 표시한다. 넓은400연결과 별도28유일선언회원·0patch3·patch25·기존차단5를 분리한다. 기대 숫자를 고정 성공으로 만들지 않는다. singleton≠원본 인증·누출해결·과학승인이다. 완료 빌드와 실제 실행서버/브라우저 검증은 별도이며 최종 근거 뒤 확정한다.

### 67/68 실제 연결·최종 시험 근거

최종 backend 전체는652건 중651 PASS·1 SKIP/258.461초/종료0이다. 기존 Windows symlink 생성권한 제약1개를 건너뛰었고 deterministic 경계 시험은 통과했다. API 관련14 PASS/6.055초·독립14 PASS/4.934초, UI 신규10 PASS/302.8698ms·독립10 PASS/447.0061ms·전체59 PASS/1317.2334ms와 build72modules/16.95초는 각 검증 범위를 구분하며 전체652에 더하지 않는다.

Root 실제 API8002는200·1,065bytes/18.797초·no-store였고 badbool400/틀린핀409/본문초과413은 안전한 오류를 반환했다. GET405는 프레임워크 기본 응답으로 별도다. UI5174의 #/view/24?model=lcluc&tab=evidence에서 명시조회28회원/400넓은연결/28유일선언회원/0patch3/patch25·장면/완전선언1384·저장차단5, 입력clear·409안내·허브 back/forward 이전결과폐기를 확인했다. 모바일 요청390×844에서 client/scroll375/375·수평넘침없음/console error0·viewport복원까지 확인했다. 기존5173/8000/8001의 새 기능 적용 검증으로 확대하지 않는다.

### 67/68 최종 보존·다음 계획

최종 보존은134참조·25기존 계약SHA와 카탈로그14기록(기존 gmais_jobs2개 포함)의 canonical records SHA불변을 확인했다. 이전에 추적한 코드/데이터/프론트 중 바뀐 것은 의도한 main 배선과 AgentCenter 두 파일이며 신규 파일을 포함한 전체 workspace 변경이2개뿐이라는 뜻은 아니다. main은 두 배선 줄을 제외하면 raw baseline과 같았다. 새 source assess·Job·학습·수집/다운로드를 실행하지 않았고 저장5차단·패치628/233/250·원본 분할·모델·예약136,314,880B·환불0을 유지했다. 보존 검사는 원자적 snapshot이나 전체workspace inventory 보장이 아니다.

다음 PLANNED 단위는 원본을 보존하는 신규 Dataset 버전 후보 계획에 기존 split repair plan과 최신 진단 핀을 연결하고 클래스 부족을 명시하는 내부 작업이다. 후보계획일 뿐 발행·원본삭제·분할/gate변경·다운로드·훈련·자료준비완료가 아니다. 이번 저장조회 UI 완성과 전체 ML/프로젝트 완료를 구분한다.

## 후보계획과 최신 선언 계보의 내부 참조 연결 — 69

[후보계획 계보 Gate](gate-notes/GATE_CANDIDATE_PLAN_LINEAGE_20261017.md)는 기존plan/source/oldreadiness/newreport/lineage 다섯JSON의 선택 metadata를 연결하는 PLAN_ONLY 참조 패키지다. 순수 코어는 호출자 선언참조만 받고 CLI가 최초/최종 바이트핀을 검사한다. partition·before/projected계수·old/newgate동일·완전 유일선언후보의 저장계획 유지/제외 예정 집합을 연결한다. 내부sceneindex와raw후보행index를 구분하고0patch를 보존한다.

전체 planner재계산/witness재생은 NOT_PERFORMED, 클래스는 보수bounds한정이며 정확클래스/누출해소·원본인증false다. 후보manifest생성·실제원본제외/재배정·Registry등록·학습/gate변경·영상IO를 하지 않는다. 새 공개 API/UI 없는 내부CLI라 화면변경은 불필요하다.

### 69 실제 선택metadata·최종회귀·보존

Root 실제 CP949 CLI1회는 종료0·19,766bytes/SHAee49f84c…의 PLAN_ONLY 참조를 생성했다. 원본1384행은 유지하고 저장계획1368유지/16제외예정을 대조했다. 명시 token28유일선언후보는 계획상16제외/12유지에 연결됐고0patch3·patch25·넓은400연결은 보존됐다. projected eligible1095=628/217/250은 계획값이며 실제1111=628/233/250·5차단은 그대로다. val bare상한209픽셀/하한0·bare패치상한0이고 정확클래스·부족해소/누출해소·원본인증은 false다. 전체planner재계산은 NOT_PERFORMED이며 후보manifest생성·실제원본행제외/재배정·Registry등록·학습은 없다.

최종 전체 scripts/test.ps1은 **671건 중670 PASS·1 SKIP/246.659초/종료0**다. SKIP은 기존 Windows symlink 생성권한 제약이며 deterministic 경계 시험은 통과했다. 관련19 PASS/9.466초·독립19 PASS/9.834초를 전체671에 중복 합산하지 않는다. 보호134참조·26기존 계약SHA·다섯 입력핀·카탈로그14기록의 canonicalSHA가 불변이고 이전 snapshot 추적 backend/scripts/data/tests/frontend 변경은0이다. 새 구현 파일과 evidence가 존재하므로 전체workspace변경0으로 해석하지 않는다. 원자 snapshot/전체workspace inventory 보장은 아니다.

## 분할 계획·검증의 선택적 bounded JSON IO — 70

[Split bounded IO Gate](gate-notes/GATE_SPLIT_BOUNDED_IO_20261017.md)는 기존 planner/validator/writer에 io_policy None기본값과 opt-in 공통 BoundedJSONIO를 연결한 변경이다. 역할별 bytecap·깊이·엄격UTF8/중복키/비유한수·모든재읽기 target/stat/SHA와 출력2개 사전측정/exclusive stream을 검사한다. 독립검토에서 상위 필수SHA None우회를 발견해 거부/회귀를 보완했다.

각 cap은 개별 읽기/출력 byte상한이며 누적IO/processRAM/CPU/원자snapshot보장은 아니다. 부분새파일이 남을 수 있고 DATA/evidence scope를 강제하는 새 후보orchestrator는 후속이다. 실제후보생성/등록/원본제외/분할/gate변경·학습은 없고 candidate미지정NOT_REQUESTED/null을 유지한다. 공개CLI/API/UI변화가 없어 화면변경은 필요 없다.

### 70 실제/회귀·보존과 다음설계

Root 실제 고정3JSON readonly validator1회는 종료0/48.609초·METADATA_INTEGRITY_VERIFIED였다. opt-in source64/readiness16/saved_plan4/candidate64MiB·depth32를 사용하고 기존 full plan을 재계산해 저장계획과 typed 대조했다.69의 선택metadata NOT_PERFORMED와 구분한다. 후보는 NOT_REQUESTED/null로 파일존재검증도 없고 실제writer/후보생성/Registry등록·원본제외/재배정·학습은 없다. 계획excluded16/projected1095와 현재원본1384행/적격1111·5차단은 그대로다.

최종 전체 scripts/test.ps1은 **691건 중690 PASS·1 SKIP/298.655초/종료0**다. 기존 Windows symlink 생성권한 제약1개를 건너뛰었고 deterministic 경계 시험은 통과했다. 관련45 PASS/15.560초(신규20+기존25)와 독립 신규20 PASS/5.243초·기존25 PASS/11.972초를 전체691에 중복 합산하지 않는다. 보호134참조·26기존 계약SHA·세 고정입력과 카탈로그14기록 canonicalSHA가 불변이다. 이전 추적 코드/데이터/프론트 중 바뀐 기존파일은 의도한 split_planning.py/split_validation.py 두 개이며 변경0이 아니다. 신규파일/문서/evidence도 있으므로 전체workspace변경2개라는 주장도 하지 않는다.

다음71은 PLANNED 설계다. source/readiness/saved_plan 세callerpin+고정6주map+새evidence디렉터리→기존 bounded fullvalidator→기존 write_plan→candidate typed roundtrip→성공receipt를 잇는다.69의5JSON전체검사를 강제중복하지 않고 receipt없으면 미완료후보 사용불가·부분파일보존·등록/훈련0으로 구분한다. 현재 구현/실제후보생성은 수행하지 않았다.

## evidence전용 후보 생성·왕복검증 receipt — 71

[후보 materialization Gate](gate-notes/GATE_CANDIDATE_MATERIALIZATION_20261017.md)는 세callerpin/source-readiness-savedplan과고정6주map으로기존bounded fullvalidator→기존writer→exactcandidate typedroundtrip→최종핀/경로→64KiBexclusive receipt를연결한다. DATA원본과evidence새디렉터리 scope를구분하고기존plan.json/candidate.json/receipt.json을덮어쓰지않는다.

receipt상태는METADATA_ROUNDTRIP_VERIFIED·candidate는PLANNED_DERIVED_CANDIDATE/BLOCKED이며ready/executed/science/auth/Registryfalse다. receipt없거나무효면미완료·파일존재만성공아님·부분새파일자동삭제없음·OS원자snapshot보장없음을설명한다. 새API/UI/Registry·assess/raster/훈련은없어화면변경대상은없다.70의미생성은과거시점이며71실제완료근거는별도로기록한다.

### 71 실제metadata후보·회귀/보존·다음QA설계

Root 실제 CP949 CLI1회는 종료0으로 evidence전용 plan/candidate/receipt 패키지를 생성했다. candidate는53,247,999bytes/SHA2ff7be093db3930d99f10cdc7687809222ef7f525ec6e9cf6248ec144725d158, receipt는3,936bytes/SHA889c549d8c8620a33fb90503313157313c520088809f2e16304c1d7fdcc3be51이다. plan22,298bytes는 기존 savedplan과 바이트 동일하다. Root 독립 strictJSON/SHA·size/type 대조로candidate1368행 전체가source1384의retained행과typed일치함을 확인했다.16제외는새candidate에만 적용됐고 원본은불변이다. 후보projected적격1095=628/217/250과 원본1111=628/233/250을 구분한다. 실제명령runtime은 정확히 측정하지 않아 초수를 주장하지 않는다.

receipt는 METADATA_ROUNDTRIP_VERIFIED/candidate PLANNED_DERIVED_CANDIDATE/readiness BLOCKED지만 후보의 실제 준비성 QA는 아직 NOT_ASSESSED다. 기존 원본 저장보고서의5차단은 유지하며 후보의 실제 차단수는 아직 모른다.15개 비승인/비실행 falseflags·refund0·exactlyonceUNKNOWN을 확인했고 Registry등록/훈련·raster/공간/정확클래스/assess는 수행하지 않았다.70까지 미생성은 당시 이력이고71에서 metadata후보가 생성됐다는 현재 사실을 구분한다.

최종 전체 scripts/test.ps1은 **706건 중705 PASS·1 SKIP/329.107초/종료0**다. SKIP은 기존 Windows symlink 생성권한 제약이며 deterministic 경계 시험은 통과했다. 관련60 PASS/26.246초(신규15+기존45)·독립신규15 PASS/13.445초를 전체706에 중복 합산하지 않는다. 보호134참조·29기존 코어SHA와 카탈로그14기록 canonicalSHA가 불변이고 이전 snapshot 추적 backend/scripts/tests/data/frontend 변경은0이다. 신규코드/문서·candidate패키지는 있으므로 전체workspace변경0이 아니며 원자snapshot/정확히한번 반영 보장도 아니다.

다음72는 PLANNED다. evidencecandidate를 기존assess에 직접넣을수없어 DATAroot를repo전체로넓히지 않고 strictreceiptconsumer→같은SHA candidateJSON만 DATA새metadata경로exclusive staging→기존run_experiment의execute/resume없는diagnostics+새readinessoutput을 검토한다. 현재 --readiness-only플래그는 없으며 receiptconsumer/staging/candidateQA 구현·실행은 아직 없다.

## 검증된metadata의DATA staging — 72

[후보staging Gate](gate-notes/GATE_CANDIDATE_STAGING_20261017.md)는71receiptSHA+외부3핀·strictschema/type/15false·size/name/고정map/lineage를검사하고기존fullcandidatevalidator를1회재사용한뒤rawcandidateJSON만DATA새경로에exclusive복사한다. 같은SHA/size/typed문서를확인하고작은stagingreceipt를마지막에쓴다. DATA/evidence양방향중첩·기존경로/변조/성장/부분파일을구분하며원자snapshot보장은없다.

staging은metadata준비이지raster복사·assess/준비성QA·학습·Registry등록이아니다. qa_status NOT_PERFORMED/readyfalse이며원본5차단을후보차단수로옮기지않는다. 다음73의동일정책기존CLI noexecute/noresume+diagnostics·새readinessoutput후보QA1회는PLANNED다. 새API/UI없는내부CLI라화면변경은불필요하다.

### 72실제metadata준비·회귀/보존과다음QA설계

Root 실제 CP949 CLI1회 종료0으로 DATA새경로에candidate JSON53,247,999bytes/SHA2ff7be093db3930d99f10cdc7687809222ef7f525ec6e9cf6248ec144725d158를동일바이트로복사했다. stagingreceipt는3,675bytes/SHAb8224cb3eb5c5ef0accf0cab10359401d792719e6fd8cae0b610279e759404dd다. 독립stream SHA/size·핀/참조·17false를대조했고최종재대조도불변이었다. 후보1368행/원본1384행·후보projected1095/원본적격1111을구분한다. QA는NOT_PERFORMED/후보준비성NOT_ASSESSED이며후보차단수는모른다. 원본저장5차단은그대로고영상/라벨복사·assess·QA·등록·훈련은없다. 실제runtime은계측하지않아초수를주장하지않는다.

최종 전체 scripts/test.ps1은 **725건 중724 PASS·1 SKIP/338.008초/종료0**다. 기존 Windows symlink 생성권한 제약1개를 건너뛰었고 deterministic 경계 시험은 통과했다. 관련19 PASS/23.740초·독립19 PASS/25.510초는 전체725에 중복 합산하지 않는다. 보호137참조(이전134+71패키지3)·30기존 코어SHA와 카탈로그14기록 canonicalSHA가 불변이며 이전 snapshot 추적 backend/scripts/tests/data/frontend 변경은0이다. 신규코드/문서·staging파일은 있으므로 전체workspace변경0은 아니며 원자snapshot/전체inventory 보장도 아니다.

다음73은PLANNED다. stagedcandidate·stagingreceipt·정책의외부SHA와명시새QA출력을고정해기존run(execute=False,resume=False,connectivity_diagnostics=True)을호출하는작은guard가남았다.72fullplan재계산을필수중복하지않으며역사동일정책자동확인은oldreadiness4번째JSON과effectivepolicy={**default_policy(),**policy} typed대조가필요하다. QA BLOCKED도정상검사완료일수있고예외/입력변경이면새report보존/완료receipt없음으로설계한다. guard/후보QA는현재미구현·미실행이다.

## 고정후보·동일정책의학습없는QA guard — 73

[후보readiness QA Gate](gate-notes/GATE_CANDIDATE_READINESS_QA_20261017.md)는candidate/stagingreceipt/policy/oldreadiness 네외부핀을strict검증하고effectivepolicy default+caller전체를oldpolicy와typed대조한뒤기존run을executeFalse/resumeFalse/diagnosticsTrue로호출한다. source참조는old원본/candidate새입력을구분하고실자료바닥/labelsignature를유지한다. 새readiness보고서와반환객체·4핀/상태/계수/capture를대조후QA완료receipt를마지막에쓴다.

QA BLOCKED도정상검사완료일수있지만receipt실행/과학/등록승인은false다. guard후단16MiB는run내부전체IO/RAM/출력쓰기하드cap아니며실제assess는영상/라벨을읽고hash/QA한다.72의미검사는당시이력이며73실제최종결과전에는후보차단수를추정하지않는다. 새API/UI없는내부QA-onlyCLI라화면변경대상은없다.

### 73실제후보QA·회귀/보존과후속비교계획

Root 실제 wrapper1회는 종료0/202.344초·RSS표본197회최대532,074,496B·중지없음이었다.600초/2GiB표본중지기준이며OS하드cap은아니다. 새후보보고서11,842,410B/SHA847343e1…와qaReceipt3,030B/SHA7b5ea8bb…를생성했다. QA_COMPLETED지만관측gate는blocked/readyfalse·적격1095=628/217/250·1368장면/verified_files4285·CAPTURED_COMPONENTS_MATCH다. 후보차단은4개로train/val/test class7불균형3개와val/class7 209픽셀부족1개이며원본5차단보고서는불변이다. 원본의SHARED_SOURCE_CROSSES_FIXED_SPLIT항목이이번후보보고서에는없지만누출완전해소·공간/표본독립·원본인증/과학승인뜻은아니다.

Root JSON독립대조에서동일policy/signature·원본class관련4차단과후보차단전체typed일치·공통verified4284개SHA/kind동일을확인했다. 새verified1개는stagedcandidate이고기존기록51개는후보목록에없다. bbox935028쌍/관측fixedsplit conflict0·완전선언identity1368은현재diagnostic범위다. bare픽셀train1418/val209/test1025와bare기여patch각0은그대로라클래스대표성부족이남는다. 실제assess는영상/라벨read/hash/QA를했고purediagnostic추가IO0과구분한다. 정식Dataset준비/Registry·학습/추론·정산/재개는0이며receipt권한false다.

최종 전체 scripts/test.ps1은 **744건 중743 PASS·1 SKIP/356.067초/종료0**다. 기존 Windows symlink 생성권한 제약1개를 건너뛰었고 deterministic 경계 시험은 통과했다. 관련19 PASS/12.065초·독립19 PASS/12.236초를 전체744에 중복 합산하지 않는다. 보호139참조·31기존 코어·네입력핀SHA와 카탈로그14기록 canonicalSHA가 불변이고 이전 snapshot 추적 backend/scripts/tests/data/frontend 변경은0이다. 신규코드/문서·QA파일은 있으므로 전체workspace변경0은 아니다. 원자snapshot/전체inventory를 보장하지 않는다.

다음74는PLANNED다. old/newQA·qaReceipt·stageReceipt 네JSON/네callerSHA의읽기전용비교projection/API계약과web_ui수동비교카드·실제브라우저확인을검토한다. 자동assess·자동POST는없다. old보고서미저장physical장면수는null로두고stage선언1384/1368·newdiag관측1368을각각구분하며patch1111로장면수를추정하지않는다.

## 원본·후보저장QA의명시비교 — 74/75

[후보QA비교 Gate](gate-notes/GATE_CANDIDATE_QA_COMPARISON_20261017.md)는old/newQA·qaReceipt/stageReceipt 네고정JSON/외부4SHA만읽어최소비교projection/API와LCLUConly수동카드를연결한변경이다.2KiB본문·report16MiB/receipt64KiB·깊이32/finalpins·no-store/process-localworker1을사용하며source/candidate거대manifest/raster/assess/Registry는호출하지않는다.

원본1111/5차단→후보1095/4차단, class7코드빈도3+val209부족1과나지1418/209/1025·기여patch0을함께표시한다. oldphysicalnull NOT_PERSISTED·stage선언1384/1368·후보QA캡처1368은각출처를구분한다. 공유항목후보미관측≠완전누출해소/독립승인이며10false권한을유지한다. 입력/선택/hash/popstate/세대는이전결과를무효화하고표시중단은서버취소가아니다. 실제API/브라우저근거전에는실행서버반영완료로주장하지않는다.

### 74/75최종실제적용·회귀/보존

Root실제API8002는200/2161bytes·no-store로1111→1095/5→4·코드빈도3·bareval209/기여patch각0·oldphysicalnull/선언1384→1368/후보캡처1368·10false를대조했다.409/400/413과GET405프레임워크별도/경로비노출도확인했다. UI5174 LCLUC evidence에서명시조회·입력clear/409·허브왕복/back-forward-back이전결과제거/수동재조회를확인했다. desktop1449×1087에서수평넘침0이며이번모바일실측은없다. 기존5173적용검증으로확대하지않는다.

초기React형제카드중복key로console오류6건과header정렬문제를발견해candidate-qa:namespace/React siblingkey회귀·scopedflex-start로수정했다. 수정후reload/수동조회·경합흐름을재확인했고2026-10-17T08:24:15UTC이후새console오류0이다. 이전6건은별도보존하며수정전UI12/전체71/build17.63초·독립12/804.0825ms와최종13/72/build18.69초·독립13/382.2987ms를시점별구분한다.

최종backend전체는 **761건 중760 PASS·1 SKIP/398.767초/종료0**다. 기존Windows symlink생성권한 제약1개를 건너뛰었고 deterministic경계시험은통과했다. 관련17 PASS/14.400초·독립17 PASS/17.124초와 최종신규UI13 PASS/460.2888ms·독립최종13 PASS/382.2987ms·전체UI72 PASS/1137.5072ms·build75modules/18.69초는범위를분리해backend761에합산하지않는다. 보호141참조·32기존코어SHA와카탈로그14기록canonicalSHA가불변이며이전추적코드/데이터/프론트중의도한main배선/AgentCenter두파일만변경됐다. 신규파일/문서/evidence도있어전체workspace변경2개라는뜻이아니고원자snapshot보장도아니다.

다음76은PLANNED다. 고정후보QA보고서·정책에서분할별나지요구픽셀/기여patch부족을산출하는읽기전용후속데이터요구계약을검토한다. 실제이를충족할새영상/라벨/장면목록은없으며최소추가량만으로준비완료를보장하지않는다. 현재설계대기·미구현이고새수집/학습은없다.

## 저장나지부족조건의읽기진단 — 76

[나지요구조건 Gate](gate-notes/GATE_BARE_CLASS_REQUIREMENTS_20261017.md)는고정후보QA한보고서/외부SHA의저장배열을읽어split픽셀바닥/기여patch/비율/전체balance를분리한다. 순수build는caller선언pin, reader는16MiB/depth32 strict/finalpin으로실제bytes를확인한다. 기존purebalance_diagnostics재계산과storedwholetyped일치는현재raster/assess재검증이아니다.

저장bare픽셀1418/209/1025에서256바닥부족0/47/0, 기여patch0에서최소5부족5각, bare비율은9클래스픽셀합을분모로최소.005미만이다. dominance.9충족과별개로부족이남는다.47픽셀이나새15patch만으로준비완료보장/장면·다운로드량추정은하지않고정확라벨/기하/독립성/전체gate미검증false다. 새API/UI없는내부CLI라화면/프론트/브라우저변경검사는불필요하며기존후보4차단을유지한다.

### 76실제저장요구조건·회귀/보존과다음대기열

Root 실제CP949 CLI1회는종료0·5,367bytes/SHA8a0004aa2d67af8c97e32173f90c56c97449e54317ef86420489eb1bbaee7542를생성했다. 생산helper없이먼저계산한독립산술의모든split/분모/ratio/dominance/failures필드와타입·값이같았고report핀은보존됐다. 저장bare1418/209/1025의256픽셀바닥부족은0/47/0, 기여patch0각의최소5부족은5각이다.9클래스합분모의bare비율은약0.003532%/0.001494%/0.006307%로정책0.5%미만이고dominance.9조건은모두충족했다. 현재raster/새QA가아닌저장통계산술VERIFIED_REAL범위다.

47픽셀만추가하거나새15patch를수집하면준비완료라는결론은내리지않는다. ratio차이는픽셀수가아니고미래자료는분모도바꾼다. 실제새영상/라벨/장면목록과정확라벨·품질/기간/경계·기하/독립성검증은없다. requirements_are_full_gate/ready/수집학습승인false·refund0/exactlyonceUNKNOWN이며기존후보4차단/원본5차단을유지한다. 새QA/수집/학습/Registry는없고API/UI없는내부CLI라화면변경·프론트재시험·브라우저확인은필요없다.

최종 전체 scripts/test.ps1은 **775건 중774 PASS·1 SKIP/332.522초/종료0**다. 기존Windows symlink생성권한 제약1개를 건너뛰었고 deterministic경계시험은통과했다. 관련14 PASS/5.019초·독립14 PASS/5.679초와별도독립산술은전체775에중복합산하지않는다. 보호141참조·34기존코어SHA·고정후보QA보고서와카탈로그14기록canonicalSHA가불변이고이전snapshot추적code/data/tests/frontend변경은0이다. 신규코드/문서/evidence는있으므로전체workspace변경0이나원자snapshot보장이아니다.

다음77은PLANNED다. 제출때고정한ordered input binding과실행전달binding을id/version/SHA/role/index·Job/Agent/Trace로대조하는순수guard를검토한다. 기존등록/resolve·제출snapshot·currentlineage와구별하며정확schema/원문연결은아직미확정이다. 실제executor/등록쓰기·READY우회는없고일치도실행승인이아니며현재resolver/실제bytes확인은후속이다. 나지충족자료/정확라벨·학습차단해결은계속미완료다.


## 108 기여 패치 범위와 필요조건

패치당 나지256픽셀 이상일 때 기여1개로 센다. E개 적격패치의 총B,용량C65536,기준T256에서 하한max(0,ceil((B-E*(T-1))/(C-T+1))),상한min(E,floor(B/T))를 계산한다. 저장E628/217/250·B1418/209/1025는 범위0..5/0/0..4이며 실제 저장 기여0이다. 상한은 실제 분포가 아니다. 요구5개×256=1280의 필요총량 차이0/1071/255는 기존76 총량 바닥차이0/47/0과 다르다. 비율·마스크·독립성·정확라벨·QA 충분조건은 별도이며 학습 BLOCKED를 유지한다.



## 사용자 확인 — 독립 정확도 검증 라벨 미제공

독립 정확도 검증용 라벨 자료는 별도로 준비되지 않았다는 사용자 확인을 반영한다. 기존 약한 라벨 학습 입력은 보존되고 사용 가능한 입력이지만 독립 평가 정답과 동등하지 않다. 이를 독립 정확도 승인이나 학습 준비 완료로 표현하지 않는다. 후보QA4차단/학습BLOCKED·기존모델Draft를유지하고외부의존성차단과내부개발지속을구분한다. 이미있는자료의위치를반복질문하지않는다.



## 112 실제 모델 확인과 완료 학습 오류 설명

기존best.pt의안전한weights_only CPU읽기에서RGB3채널·epoch3·29,833파라미터TinyUNet을확인했다. 두pooling/8·16·32feature와단순skip이며U-Net++·현재6밴드후보정식학습모델이아니다. 기존checkpoint/report를바꾸지않고필드부재를false저장으로역채우지않았다.

새오류분석은최저validation loss로선택한best의val·최종test에연결된다.행=참조/열=예측의TP/FN/FP·recall/precision·비대각혼동쌍을JSON/클래스CSV/오분류CSV로쓴다.분모0은null/evaluable false이며미관측을완벽/0정확도로바꾸지않는다.미완료에는생성하지않고test로epoch를고르지않는다. 약한라벨일치도설명이지독립정확도/공간오류지도/승인아니다.



## 115 실제 runner 연결과 v1 정규화 한계

기존analyze_timeseries를새local workflow가실제로호출해작은두연도CPU추론·분류2·변화TIF/GeoJSON/전환CSV/report·시계열JSON총7artifact를생성했다. TempStore의Deployed/독립평가와입력VALIDATED는명시mock이며전문가정확도승인이아니다. 학습은하지않았다.

v1은fixed global normalization의TinyUNet boundedtile만지원한다. 현재6밴드후보의per_scene_product_metadata는차단한다. 모든6밴드를원리상거부하는게아니라현재제품별정규화/구름mask계약이후속이다. 기존RGBDraft모델·후보4차단·독립라벨미제공·학습BLOCKED는그대로다.



## 116/117 — LCLUC 수동 실행·조회 API와 화면

115의 실제 analyze_timeseries 연결을116 API와117 수동 UI에 노출했다. 학습·정규화·추론 알고리즘은 바꾸지 않았다. TempStore의 모의 승인과 작은 실제 CPU 추론을 구분한다. 현재 Draft·후보4차단·독립 라벨 미확보는 그대로다. 현재6밴드 per_scene 정규화와 구름mask는 이번 실행 경로에서 차단한다.


## 118 — 검증된 선택 변화쌍 지도

생성3연도 영상과 미학습 시험 네트워크에서 실제 CPU 추론의 nonempty1 Polygon·256픽셀·25600m²와 empty를 확인했다. 시험 면적을 사업지역 결과로 설명하지 않는다. nonempty 좌표 tuple과 JSON list 비교로 발생한 RUNNER_REPORT_MISMATCH를 canonical JSON 동치로 고쳤고 bool/int 변조는 여전히 거부한다. 현재 모델/분할/원본과6밴드 정규화 Gate는 유지한다.


## 119 — 전체 래스터 전이행렬·범례·단위

전이 픽셀 P[i,j]의 행은 이전, 열은 이후 클래스다. 행/열합과 순변화, 비대각 면적합·면적 기준 변화율을 저장 보고서와 검산한다. 분모0은null이며0%로 추정하지 않는다. 이 전이행렬은 시점별 분류 비교이고 독립 정답을 이용한 accuracy/confusion matrix와 다르다.


## 120/121 — 고정 모델의 오류분석 읽기

112 오류분석은 고정 best의 val/test 혼동행렬을 행=참조/열=예측으로 읽는다. TP는 대각선, FN=참조합−TP, FP=예측합−TP다. 분모0 비율은null·평가 불가다.119의 시점 간 전이행렬과 다르며 test로 best epoch를 재선택하지 않는다.120은 저장 통계 재검산·읽기이고 새 추론/학습/독립 정확도 측정이 아니다.


### 120/121 최신 범위와112의 당시 한계

112 당시 후속이던 구조화 오류 표와 인증 다운로드는120/121에서 연결했다. 실제 운영 legacy 모델의 pin/오류분석 부재는 그대로 표시하고 과거 성적표를 자동 생성하지 않는다. 임시 구성 성적표의 읽기 성공은 실제 원본 모델의 독립 정확도나 승인·배포 완료가 아니다.


## 122 — per_scene 정규화 선언 계약

115는 global 정규화에서1~16밴드를 지원한다. 모든6밴드 금지가 아니라 현재6밴드 per_scene_product_metadata와115의 source_scene/normalization 전달 공백이 문제다.122는 scalar/6채널 scale·offset과 제품/밴드 선언 비교만 추가하고 기존 실제 정규화/추론/실행 gate는 바꾸지 않는다.


## 123 — per_scene 세 역할 파일 지문 대조

123 artifact_bytes_verified true는 읽은 세 역할 bytes 대조에 한정한다. checkpoint_manifest는 caller metadata이며 checkpoint/header/CRS/스펙트럼/mask/float32·실행/과학 검증은false다. 비래스터 bytes도 SHA가 맞으면 통과하는 경계를 Temp 시험으로 확인했다. 기존115 global-only/per_scene 전달 공백은 바꾸지 않는다.


### 123의 고정 SHA와124 후속

고정은 caller가 준 세 역할 SHA와 실제 읽은 bytes의 대조다. Registry ID/version/ref·실제 checkpoint identity를 연결한 것은 아니다.124 후속에서 검토할 공백이며 아직 미연결이다. 현재 결과를 실행입력이나 승인으로 자동 전달하지 않는다.


## 124 — 실제 checkpoint manifest와 고정 모델 참조

실제 SHA 고정 checkpoint 복사 바이트를 CPU weights_only로 열어 manifest를 반환한다. report.input_signature를 대용으로 쓰지 않는다. state_dict 호환·tensor shape·forward·학습은 검증하지 않으며 state_dict_verified false다. 미학습 Temp6밴드 모델 저장/읽기와 운영 checkpoint load0을 구별한다.


## 125 — 등록3참조와 명시 장면 파일

pin된 evidence에서 scale/offset을 추출해123으로 같은 pin을 검산하는 것은 제품 보정의 독립 물리 검증이 아니다. checkpointmanifest는 caller 입력이며 actual124 모델 연결126·전연차·품질mask는 후속이다. header·스펙트럼·float32·state/과학/실행 승인은 검사하지 않는다.
