# 01 데이터: 원재료를 모으고 같은 자리에 맞추기

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-18 11:00 KST — 5차1212/셀85·후보1125 실제UI;6차 시작/완료미확인 |
| source_commit | 기준 76949f650123653f30841507feebc7678aaea151 + 148–157 검증 작업파일 raw SHA (관측 시점 작업파일; 최종 Git 게시의 바이트 보존은 별도 확인) |
| evidence_paths | `backend/app/data/service.py`; `docs/implementation/00_next_session_handoff.md`; `evidence/integration/ml-readiness-resume-20261017.json`; `docs/implementation/25_ml_split_repair_plan.md`; `evidence/integration/ml-split-repair-plan-20261017.json`; `docs/implementation/26_dataset_version_registry_core.md`; `evidence/integration/dataset-versions-tests-20261017.log`; `docs/implementation/24_collection_recovery_plan.md`; `evidence/integration/continuous-tests-20261017.log`; `evidence/integration/collection-recovery-plans/validation-20261017T003037618057Z.json`; `evidence/integration/collection-recovery-plans/integrity-20261017T003101447624Z.json`; `backend/app/job_inputs.py`; `backend/app/gmais_api.py`; `docs/implementation/27_job_input_resolution.md`; `evidence/integration/job-input-core-tests-20261017.log`; `evidence/integration/job-input-api-tests-20261017.log`; `evidence/integration/job-input-full-tests-20261017.log`; `docs/implementation/28_workflow_input_resolution.md`; `tests/test_gmais_workflow_extension.py`; `evidence/integration/workflow-input-tests-20261017.log`; `evidence/integration/workflow-input-full-tests-20261017.log`; `backend/app/dataset_lineage.py`; `docs/implementation/35_dataset_lineage_verification.md`; `evidence/integration/dataset-lineage-tests-20261017.log`; `evidence/integration/dataset-lineage-full-tests-20261017.log`; `evidence/integration/dataset-lineage-synthetic-20261017.json`; `backend/app/dataset_lineage_api.py`; `docs/implementation/36_dataset_lineage_api_plan.md`; `docs/implementation/37_dataset_lineage_ui.md`; `evidence/integration/dataset-lineage-api-independent-tests-20261017.log`; `evidence/integration/dataset-lineage-api-full-tests-20261017.log`; `evidence/integration/dataset-lineage-ui-build-20261017.log`; `evidence/integration/dataset-lineage-api-live-20261017.json`; `backend/app/job_lineage.py`; `backend/app/job_lineage_api.py`; `docs/implementation/38_job_lineage_validation.md`; `docs/implementation/39_job_lineage_ui.md`; `evidence/integration/job-lineage-tests-20261017.log`; `evidence/integration/job-lineage-full-tests-20261017.log`; `evidence/integration/job-lineage-ui-build-20261017.log`; `evidence/integration/job-lineage-live-20261017.json`; `backend/app/workflow_lineage.py`; `backend/app/workflow_lineage_api.py`; `backend/app/lineage_batch.py`; `docs/implementation/40_workflow_lineage_validation.md`; `docs/implementation/41_workflow_lineage_ui.md`; `evidence/integration/workflow-lineage-independent-tests-20261017.log`; `evidence/integration/workflow-lineage-full-tests-20261017.log`; `evidence/integration/workflow-lineage-ui-build-20261017.log`; `evidence/integration/workflow-lineage-live-20261017.json`; `docs/implementation/43_catalog_insight_data_contract.md`; `docs/implementation/42_catalog_insights_navigation.md`; `backend/app/ml/split_validation.py`; `scripts/validate_training_split_repair.py`; `docs/implementation/44_ml_split_repair_validation.md`; `evidence/integration/ml-split-validation-tests-20261017.log`; `evidence/integration/ml-split-validation-independent-20261017.log`; `evidence/integration/ml-split-validation-full-tests-20261017.log`; `evidence/integration/ml-split-repair-validation-live-final-20261017.json`; `evidence/integration/ml-split-validation-live-integrity-20261017.json`; `backend/app/data/recovery_terminal.py`; `scripts/inspect_recovery_terminal.py`; `docs/implementation/45_recovery_terminal_reconciliation.md`; `evidence/integration/recovery-terminal-tests-20261017.log`; `evidence/integration/recovery-terminal-independent-20261017.log`; `evidence/integration/recovery-terminal-full-tests-20261017.log`; `evidence/integration/recovery-terminal-live-final-20261017.json`; `evidence/integration/recovery-terminal-live-integrity-20261017.json`; `backend/app/data/recovery_aggregate.py`; `scripts/inspect_recovery_aggregate.py`; `docs/implementation/46_recovery_aggregate_reconciliation.md`; `evidence/integration/recovery-aggregate-tests-20261017.log`; `evidence/integration/recovery-aggregate-independent-20261017.log`; `evidence/integration/recovery-aggregate-full-tests-20261017.log`; `evidence/integration/recovery-aggregate-live-final-20261017.json`; `evidence/integration/recovery-aggregate-live-integrity-20261017.json`; `backend/app/data/recovery_crop.py`; `scripts/inspect_recovery_crop.py`; `docs/implementation/47_recovery_crop_reconciliation.md`; `evidence/integration/recovery-crop-tests-20261017.log`; `evidence/integration/recovery-crop-independent-20261017.log`; `evidence/integration/recovery-crop-full-tests-20261017.log`; `evidence/integration/recovery-crop-live-final-20261017.json`; `evidence/integration/recovery-crop-live-integrity-20261017.json`; `backend/app/data/recovery_raster_headers.py`; `scripts/inspect_recovery_raster_headers.py`; `docs/implementation/48_recovery_raster_header_validation.md`; `evidence/integration/recovery-raster-headers-tests-20261017.log`; `evidence/integration/recovery-raster-headers-independent-20261017.log`; `evidence/integration/recovery-raster-headers-live-final-20261017.json`; `evidence/integration/recovery-raster-headers-full-tests-20261017.log`; `evidence/integration/recovery-raster-headers-live-integrity-20261017.json`; `backend/app/data/recovery_raster_content.py`; `scripts/inspect_recovery_raster_content.py`; `docs/implementation/49_recovery_raster_content_validation.md`; `evidence/integration/recovery-raster-content-tests-20261017.log`; `evidence/integration/recovery-raster-content-independent-20261017.log`; `evidence/integration/recovery-raster-content-live-final-20261017.json`; `evidence/integration/recovery-raster-content-full-tests-20261017.log`; `evidence/integration/recovery-raster-content-live-integrity-20261017.json`; `backend/app/data/recovery_auxiliary_content.py`; `scripts/inspect_recovery_auxiliary_content.py`; `docs/implementation/50_recovery_auxiliary_content_validation.md`; `evidence/integration/recovery-auxiliary-content-tests-20261017.log`; `evidence/integration/recovery-auxiliary-content-independent-20261017.log`; `evidence/integration/recovery-auxiliary-content-live-final-20261017.json`; `evidence/integration/recovery-auxiliary-content-full-tests-20261017.log`; `evidence/integration/recovery-auxiliary-content-live-integrity-20261017.json`; `backend/app/data/recovery_auxiliary_headers.py`; `scripts/inspect_recovery_auxiliary_headers.py`; `docs/implementation/51_recovery_auxiliary_headers_validation.md`; `evidence/integration/recovery-auxiliary-headers-tests-20261017.log`; `evidence/integration/recovery-auxiliary-headers-independent-20261017.log`; `evidence/integration/recovery-auxiliary-headers-live-final-20261017.json`; `evidence/integration/recovery-auxiliary-headers-full-tests-20261017.log`; `evidence/integration/recovery-auxiliary-headers-live-integrity-20261017.json`; `backend/app/data/recovery_boundary.py`; `scripts/inspect_recovery_boundary.py`; `docs/implementation/52_recovery_boundary_validation.md`; `evidence/integration/recovery-boundary-tests-20261017.log`; `evidence/integration/recovery-boundary-independent-20261017.log`; `evidence/integration/recovery-boundary-live-final-20261017.json`; `evidence/integration/recovery-boundary-full-tests-20261017.log`; `evidence/integration/recovery-boundary-live-integrity-20261017.json`; `backend/app/data/recovery_boundary_topology.py`; `scripts/inspect_recovery_boundary_topology.py`; `docs/implementation/53_recovery_boundary_topology_validation.md`; `evidence/integration/recovery-boundary-topology-tests-20261017.log`; `evidence/integration/recovery-boundary-topology-independent-20261017.log`; `evidence/integration/recovery-boundary-topology-live-final-20261017.json`; `evidence/integration/recovery-boundary-topology-full-tests-20261017.log`; `evidence/integration/recovery-boundary-topology-live-integrity-20261017.json`; `backend/app/data/recovery_boundary_relations.py`; `scripts/inspect_recovery_boundary_relations.py`; `docs/implementation/54_recovery_boundary_relations_validation.md`; `evidence/integration/recovery-boundary-relations-tests-20261017.log`; `evidence/integration/recovery-boundary-relations-independent-20261017.log`; `evidence/integration/recovery-boundary-relations-live-final-20261017.json`; `evidence/integration/recovery-boundary-relations-full-tests-20261017.log`; `evidence/integration/recovery-boundary-relations-live-integrity-20261017.json`; `backend/app/data/recovery_source_footprints.py`; `scripts/inspect_recovery_source_footprints.py`; `docs/implementation/55_recovery_source_footprints_validation.md`; `evidence/integration/recovery-source-footprints-tests-20261017.log`; `evidence/integration/recovery-source-footprints-independent-20261017.log`; `evidence/integration/recovery-source-footprints-live-final-20261017.json`; `evidence/integration/recovery-source-footprints-full-tests-20261017.log`; `evidence/integration/recovery-source-footprints-live-integrity-20261017.json`; `backend/app/data/recovery_source_split_overlap.py`; `scripts/inspect_recovery_source_split_overlap.py`; `docs/implementation/56_recovery_source_split_overlap_validation.md`; `evidence/integration/recovery-source-split-overlap-tests-20261017.log`; `evidence/integration/recovery-source-split-overlap-independent-20261017.log`; `evidence/integration/recovery-source-split-overlap-plan-check-20261017.log`; `evidence/integration/recovery-source-split-overlap-live-final-20261017.json`; `evidence/integration/recovery-source-split-overlap-full-tests-20261017.log`; `evidence/integration/recovery-source-split-overlap-live-integrity-20261017.json`; `backend/app/data/recovery_readiness_comparison.py`; `scripts/inspect_recovery_readiness_comparison.py`; `docs/implementation/57_recovery_readiness_comparison_validation.md`; `evidence/integration/recovery-readiness-comparison-tests-20261017.log`; `evidence/integration/recovery-readiness-comparison-independent-20261017.log`; `evidence/integration/recovery-readiness-comparison-live-final-20261017.json`; `evidence/integration/recovery-readiness-comparison-full-tests-20261017.log`; `evidence/integration/recovery-readiness-comparison-live-integrity-20261017.json`; `backend/app/data/readiness_connectivity_witness.py`; `tests/test_readiness_connectivity_witness.py`; `docs/implementation/58_readiness_connectivity_witness_validation.md`; `evidence/integration/readiness-connectivity-witness-related-20261017.log`; `evidence/integration/readiness-connectivity-witness-independent-20261017.log`; `evidence/integration/readiness-connectivity-witness-live-absence-20261017.json`; `evidence/integration/readiness-connectivity-witness-full-tests-20261017.log`; `evidence/integration/readiness-connectivity-witness-live-integrity-20261017.json`; `backend/app/data/readiness_connectivity_envelope.py`; `tests/test_readiness_connectivity_envelope.py`; `docs/implementation/59_readiness_connectivity_envelope_validation.md`; `evidence/integration/readiness-connectivity-envelope-related-20261017.log`; `evidence/integration/readiness-connectivity-envelope-independent-20261017.log`; `evidence/integration/readiness-connectivity-envelope-live-absence-20261017.json`; `evidence/integration/readiness-connectivity-envelope-live-validation-20261017.json`; `evidence/integration/readiness-connectivity-envelope-full-tests-20261017.log`; `evidence/integration/readiness-connectivity-envelope-live-integrity-20261017.json`; `backend/app/ml/readiness.py`; `backend/app/ml/readiness_connectivity_adapter.py`; `tests/test_readiness_connectivity_adapter.py`; `docs/implementation/60_readiness_connectivity_adapter_validation.md`; `evidence/integration/readiness-connectivity-adapter-related-20261017.log`; `evidence/integration/readiness-connectivity-adapter-independent-20261017.log`; `evidence/integration/readiness-connectivity-adapter-ast-parity-20261017.json`; `evidence/integration/readiness-connectivity-adapter-live-saved-state-20261017.json`; `evidence/integration/readiness-connectivity-adapter-full-tests-20261017.log`; `evidence/integration/readiness-connectivity-adapter-live-integrity-20261017.json`; `scripts/run_experiment.py`; `tests/test_readiness_connectivity_cli.py`; `docs/implementation/61_readiness_connectivity_cli_validation.md`; `evidence/integration/readiness-connectivity-cli-related-20261017.log`; `evidence/integration/readiness-connectivity-cli-independent-20261017.log`; `evidence/integration/readiness-connectivity-cli-live-help-20261017.json`; `evidence/integration/readiness-connectivity-cli-ast-parity-20261017.json`; `evidence/integration/readiness-connectivity-cli-full-tests-20261017.log`; `evidence/integration/readiness-connectivity-cli-live-integrity-20261017.json`; `docs/implementation/62_readiness_connectivity_real_validation.md`; `data/first-group/readiness-connectivity-20261017.json`; `evidence/integration/readiness-connectivity-real-preflight-20261017.json`; `evidence/integration/readiness-connectivity-real-execution-20261017.json`; `evidence/integration/readiness-connectivity-real-validation-20261017.json`; `evidence/integration/readiness-connectivity-real-independent-20261017.log`; `evidence/integration/readiness-connectivity-real-token-membership-20261017.json`; `evidence/integration/readiness-connectivity-real-live-integrity-20261017.json`; `backend/app/data/readiness_connectivity_lineage.py`; `scripts/inspect_readiness_connectivity_lineage.py`; `tests/test_readiness_connectivity_lineage.py`; `docs/implementation/63_readiness_connectivity_lineage_validation.md`; `evidence/integration/readiness-connectivity-lineage-related-20261017.log`; `evidence/integration/readiness-connectivity-lineage-independent-20261017.log`; `evidence/integration/readiness-connectivity-lineage-live-cli-20261017.log`; `evidence/integration/readiness-connectivity-lineage-live-20261017.json`; `evidence/integration/readiness-connectivity-lineage-full-tests-20261017.log`; `evidence/integration/readiness-connectivity-lineage-live-integrity-20261017.json`; `docs/implementation/64_readiness_source_identity_contract.md`; `evidence/integration/readiness-source-identity-related-20261017.log`; `evidence/integration/readiness-source-identity-independent-20261017.log`; `evidence/integration/readiness-source-identity-full-tests-20261017.log`; `evidence/integration/readiness-source-identity-live-integrity-20261017.json`; `docs/implementation/65_readiness_source_identity_consumer.md`; `evidence/integration/readiness-source-identity-consumer-related-20261017.log`; `evidence/integration/readiness-source-identity-consumer-independent-20261017.log`; `evidence/integration/readiness-source-identity-consumer-live-cli-20261017.log`; `evidence/integration/readiness-source-identity-consumer-live-legacy-20261017.json`; `evidence/integration/readiness-source-identity-consumer-live-legacy-validation-20261017.json`; `evidence/integration/readiness-source-identity-consumer-full-tests-20261017.log`; `evidence/integration/readiness-source-identity-consumer-live-integrity-20261017.json`; `data/first-group/readiness-source-identity-20261017.json`; `evidence/integration/readiness-source-identity-real-preflight-20261017.json`; `evidence/integration/readiness-source-identity-real-execution-20261017.json`; `evidence/integration/readiness-source-identity-real-cli-20261017.log`; `evidence/integration/readiness-source-identity-real-lineage-20261017.json`; `evidence/integration/readiness-source-identity-real-lineage-cli-20261017.log`; `evidence/integration/readiness-source-identity-real-validation-20261017.json`; `evidence/integration/readiness-source-identity-real-independent-20261017.json`; `evidence/integration/readiness-source-identity-real-live-integrity-20261017.json`; `docs/implementation/66_readiness_source_identity_real_validation.md`; `backend/app/readiness_source_identity_api.py`; `backend/app/main.py`; `tests/test_readiness_source_identity_api.py`; `frontend/src/AgentCenter.tsx`; `frontend/src/ReadinessSourceIdentityDiagnostics.tsx`; `frontend/src/readinessSourceIdentityAdapter.ts`; `frontend/src/readinessSourceIdentityAdapter.test.mjs`; `frontend/src/readiness-source-identity.css`; `docs/implementation/67_readiness_source_identity_api.md`; `docs/implementation/68_readiness_source_identity_ui.md`; `evidence/integration/readiness-source-identity-api-related-20261017.log`; `evidence/integration/readiness-source-identity-api-independent-20261017.log`; `evidence/integration/readiness-source-identity-api-live-20261017.json`; `evidence/integration/readiness-source-identity-api-ui-full-tests-20261017.log`; `evidence/integration/readiness-source-identity-ui-adapter-20261017.log`; `evidence/integration/readiness-source-identity-ui-tests-20261017.log`; `evidence/integration/readiness-source-identity-ui-build-20261017.log`; `evidence/integration/readiness-source-identity-ui-independent-20261017.log`; `evidence/integration/readiness-source-identity-ui-live-20261017.json`; `evidence/integration/readiness-source-identity-ui-console-20261017.json`; `evidence/integration/readiness-source-identity-api-ui-live-integrity-20261017.json`; `backend/app/ml/candidate_plan_lineage.py`; `scripts/inspect_candidate_plan_lineage.py`; `tests/test_candidate_plan_lineage.py`; `docs/implementation/69_candidate_plan_lineage.md`; `evidence/integration/candidate-plan-lineage-related-20261017.log`; `evidence/integration/candidate-plan-lineage-independent-20261017.log`; `evidence/integration/candidate-plan-lineage-live-20261017.json`; `evidence/integration/candidate-plan-lineage-live-cli-20261017.log`; `evidence/integration/candidate-plan-lineage-full-tests-20261017.log`; `evidence/integration/candidate-plan-lineage-live-integrity-20261017.json`; `backend/app/ml/split_planning.py`; `backend/app/ml/split_json_io.py`; `tests/test_split_bounded_io.py`; `docs/implementation/70_split_bounded_io.md`; `evidence/integration/split-bounded-io-related-20261017.log`; `evidence/integration/split-bounded-io-independent-20261017.log`; `evidence/integration/split-bounded-io-live-20261017.json`; `evidence/integration/split-bounded-io-live-run-20261017.log`; `evidence/integration/split-bounded-io-full-tests-20261017.log`; `evidence/integration/split-bounded-io-live-integrity-20261017.json`; `backend/app/ml/candidate_materialization.py`; `scripts/materialize_split_candidate.py`; `tests/test_candidate_materialization.py`; `docs/implementation/71_candidate_materialization.md`; `evidence/integration/candidate-materialization-related-20261017.log`; `evidence/integration/candidate-materialization-independent-20261017.log`; `evidence/integration/candidate-materialization-live-cli-20261017.log`; `evidence/integration/candidate-materialization-live-validation-20261017.json`; `evidence/integration/candidate-materialization-full-tests-20261017.log`; `evidence/integration/candidate-materialization-live-integrity-20261017.json`; `evidence/integration/candidate-materialization-live-20261017/plan.json`; `evidence/integration/candidate-materialization-live-20261017/candidate.json`; `evidence/integration/candidate-materialization-live-20261017/receipt.json`; `backend/app/ml/candidate_staging.py`; `scripts/stage_split_candidate.py`; `tests/test_candidate_staging.py`; `docs/implementation/72_candidate_staging.md`; `evidence/integration/candidate-staging-related-20261017.log`; `evidence/integration/candidate-staging-independent-20261017.log`; `evidence/integration/candidate-staging-live-cli-20261017.log`; `evidence/integration/candidate-staging-live-validation-20261017.json`; `evidence/integration/candidate-staging-full-tests-20261017.log`; `evidence/integration/candidate-staging-live-integrity-20261017.json`; `data/first-group-candidate-qa-stage-20261017/candidate.json`; `data/first-group-candidate-qa-stage-20261017/staging-receipt.json`; `backend/app/ml/candidate_readiness_qa.py`; `scripts/assess_staged_candidate.py`; `tests/test_candidate_readiness_qa.py`; `docs/implementation/73_candidate_readiness_qa.md`; `evidence/integration/candidate-readiness-qa-related-20261017.log`; `evidence/integration/candidate-readiness-qa-independent-20261017.log`; `evidence/integration/candidate-readiness-qa-live-cli-20261017.log`; `evidence/integration/candidate-readiness-qa-live-execution-20261017.json`; `evidence/integration/candidate-readiness-qa-live-validation-20261017.json`; `evidence/integration/candidate-readiness-qa-full-tests-20261017.log`; `evidence/integration/candidate-readiness-qa-live-integrity-20261017.json`; `data/first-group-candidate-readiness-qa-20261017/readiness.json`; `data/first-group-candidate-readiness-qa-20261017/qa-receipt.json`; `backend/app/ml/candidate_qa_comparison.py`; `backend/app/candidate_qa_comparison_api.py`; `tests/test_candidate_qa_comparison.py`; `frontend/src/CandidateQaComparisonDiagnostics.tsx`; `frontend/src/candidateQaComparisonAdapter.ts`; `frontend/src/candidateQaComparisonAdapter.test.mjs`; `frontend/src/candidate-qa-comparison.css`; `docs/implementation/74_candidate_qa_comparison_api.md`; `docs/implementation/75_candidate_qa_comparison_ui.md`; `evidence/integration/candidate-qa-comparison-related-20261017.log`; `evidence/integration/candidate-qa-comparison-independent-20261017.log`; `evidence/integration/candidate-qa-comparison-ui-adapter-20261017.log`; `evidence/integration/candidate-qa-comparison-ui-tests-20261017.log`; `evidence/integration/candidate-qa-comparison-ui-build-20261017.log`; `evidence/integration/candidate-qa-comparison-ui-independent-20261017.log`; `evidence/integration/candidate-qa-comparison-live-http-20261017.json`; `evidence/integration/candidate-qa-comparison-ui-live-20261017.json`; `evidence/integration/candidate-qa-comparison-ui-console-before-fix-20261017.json`; `evidence/integration/candidate-qa-comparison-ui-console-after-fix-20261017.json`; `evidence/integration/candidate-qa-comparison-full-tests-20261017.log`; `evidence/integration/candidate-qa-comparison-live-integrity-20261017.json`; `backend/app/ml/bare_class_requirements.py`; `scripts/inspect_bare_class_requirements.py`; `tests/test_bare_class_requirements.py`; `docs/implementation/76_bare_class_requirements.md`; `evidence/integration/bare-class-requirements-related-20261017.log`; `evidence/integration/bare-class-requirements-independent-20261017.log`; `evidence/integration/bare-class-requirements-independent-arithmetic-20261017.json`; `evidence/integration/bare-class-requirements-live-20261017.json`; `evidence/integration/bare-class-requirements-live-cli-20261017.log`; `evidence/integration/bare-class-requirements-live-validation-20261017.json`; `evidence/integration/bare-class-requirements-full-tests-20261017.log`; `evidence/integration/bare-class-requirements-live-integrity-20261017.json`; `backend/app/ml/bare_patch_feasibility.py`; `scripts/inspect_bare_patch_feasibility.py`; `tests/test_bare_patch_feasibility.py`; `docs/implementation/108_bare_patch_feasibility.md`; `evidence/integration/bare-class-patch-feasibility-focused-20261017.log`; `evidence/integration/bare-class-patch-feasibility-related-20261017.log`; `evidence/integration/bare-class-patch-feasibility-related-corrected-20261017.log`; `evidence/integration/bare-class-patch-feasibility-independent-20261017.log`; `evidence/integration/bare-class-patch-feasibility-independent-review-20261017.json`; `evidence/integration/bare-class-patch-feasibility-live-20261017.json`; `evidence/integration/bare-class-patch-feasibility-live-cli-20261017.log`; `evidence/integration/bare-class-patch-feasibility-live-integrity-20261017.json`; `evidence/integration/bare-class-patch-feasibility-collection-next-review-20261017.json`; `backend/app/data/recovery_commit_contract.py`; `tests/test_recovery_commit_contract.py`; `docs/implementation/109_area_completion_audit.md`; `docs/implementation/110_recovery_commit_contract.md`; `scripts/collect_training_parallel.py`; `backend/app/data/budget.py`; `evidence/integration/recovery-commit-contract-focused-20261017.log`; `evidence/integration/recovery-commit-contract-focused-final-20261017.log`; `evidence/integration/recovery-commit-contract-focused-final2-20261017.log`; `evidence/integration/recovery-commit-contract-related-20261017.log`; `evidence/integration/recovery-commit-contract-related-final-20261017.log`; `evidence/integration/recovery-commit-contract-related-final2-20261017.log`; `evidence/integration/recovery-commit-contract-independent-before-key-guard-20261017.log`; `evidence/integration/recovery-commit-contract-independent-20261017.log`; `evidence/integration/recovery-commit-contract-independent-final3-20261017.log`; `evidence/integration/recovery-commit-contract-preflight-20261017.json`; `evidence/integration/recovery-commit-contract-live-integrity-20261017.json`; `evidence/integration/recovery-commit-contract-external-dependencies-20261017.json`; `docs/implementation/111_data_pipeline_completion.md`; `docs/implementation/112_lcluc_ml_completion.md`; `docs/implementation/113_lcluc_integration_acceptance.md`; `docs/implementation/114_geollm_technical_review.md`; `backend/app/data/collection_registration.py`; `scripts/register_collection.py`; `tests/test_collection_version_registration.py`; `backend/app/ml/error_analysis.py`; `backend/app/ml/service.py`; `backend/app/ml/network.py`; `tests/test_ml_error_analysis.py`; `scripts/evaluate_geollm_local.py`; `scripts/evaluate_geollm_tools.py`; `tests/test_geollm_local_evaluation.py`; `tests/test_geollm_tool_evaluation.py`; `evidence/integration/data-pipeline-inventory-20261018.json`; `evidence/integration/data-pipeline-focused-final-20261018.log`; `evidence/integration/data-pipeline-related-final-20261018.log`; `evidence/integration/data-pipeline-independent-20261018.log`; `evidence/integration/data-pipeline-independent-review-20261018.json`; `evidence/integration/lcluc-ml-architecture-20261018.json`; `evidence/integration/lcluc-ml-error-analysis-focused-20261018.log`; `evidence/integration/lcluc-ml-error-analysis-related-20261018.log`; `evidence/integration/lcluc-ml-error-analysis-integrity-20261018.json`; `evidence/integration/lcluc-ml-existing-report-error-analysis-20261018.json`; `evidence/integration/geollm-local-evaluation-20261018.json`; `evidence/integration/geollm-native-tools-20261018.json`; `evidence/integration/geollm-runtime-audit-20261018.json`; `evidence/integration/geollm-evaluation-tests-final3-20261018.log`; `evidence/integration/geollm-independent-tests-final-20261018.log`; `evidence/integration/geollm-independent-review-20261018.json`; `evidence/integration/lcluc-geollm-full-tests-20261018.log`; `evidence/integration/lcluc-geollm-live-integrity-final-20261018.json`; `backend/app/lcluc_workflow.py`; `scripts/run_lcluc_workflow.py`; `tests/test_lcluc_workflow.py`; `docs/implementation/115_lcluc_workflow_executor.md`; `evidence/integration/lcluc-workflow-source-freeze-20261018.json`; `evidence/integration/lcluc-workflow-focused-final4-20261018.log`; `evidence/integration/lcluc-workflow-independent-final2-20261018.log`; `evidence/integration/lcluc-workflow-independent-related-20261018.log`; `evidence/integration/lcluc-workflow-independent-review-20261018.json`; `evidence/integration/lcluc-workflow-full-tests-20261018.log`; `evidence/integration/lcluc-workflow-live-integrity-20261018.json`; `backend/app/lcluc_workflow_api.py`; `tests/test_lcluc_workflow_api.py`; `frontend/src/LclucWorkflowPanel.tsx`; `frontend/src/lclucWorkflowAdapter.ts`; `frontend/src/lclucWorkflowClient.ts`; `frontend/src/lcluc-workflow.css`; `frontend/src/ModelAnalysisWorkspace.tsx`; `docs/implementation/116_lcluc_workflow_api.md`; `docs/implementation/117_lcluc_workflow_ui.md`; `evidence/integration/lcluc-workflow-api-focused-final2-20261018.log`; `evidence/integration/lcluc-workflow-api-independent-tests-20261018.log`; `evidence/integration/lcluc-workflow-api-route-preservation-tests-20261018.log`; `evidence/integration/lcluc-workflow-ui-related-final-20261018.log`; `evidence/integration/lcluc-workflow-ui-tests-final-20261018.log`; `evidence/integration/lcluc-workflow-ui-build-final-20261018.log`; `evidence/integration/lcluc-workflow-ui-browser-20261018.json`; `evidence/integration/lcluc-workflow-api-live-integrity-20261018.json`; `evidence/integration/lcluc-workflow-api-live-route-20261018.json`; `evidence/integration/lcluc-workflow-ui-related-final3-20261018.log`; `evidence/integration/lcluc-workflow-ui-tests-final2-20261018.log`; `evidence/integration/lcluc-workflow-ui-build-final2-20261018.log`; `evidence/integration/lcluc-workflow-api-full-tests-20261018.log`; `evidence/integration/lcluc-workflow-api-related-20261018.log`; `evidence/integration/lcluc-workflow-ui-build-final3-20261018.log`; `evidence/integration/lcluc-workflow-ui-synthetic-desktop-final2-20261018.png`; `frontend/src/lclucChangeMapAdapter.ts`; `frontend/src/LclucWorkflowChangeMap.tsx`; `docs/implementation/118_lcluc_workflow_change_map.md`; `evidence/integration/lcluc-change-map-adapter-focused-20261018.log`; `evidence/integration/lcluc-change-map-ui-related-final-20261018.log`; `evidence/integration/lcluc-change-map-generated-fixture-20261018.json`; `evidence/integration/lcluc-change-map-independent-20261018.log`; `evidence/integration/lcluc-change-map-core-focused-20261018.log`; `evidence/integration/lcluc-change-map-core-api-final-20261018.log`; `evidence/integration/lcluc-change-map-nonempty-initial-diagnostic-20261018.log`; `evidence/integration/lcluc-change-map-ui-tests-20261018.log`; `evidence/integration/lcluc-change-map-ui-build-20261018.log`; `evidence/integration/lcluc-change-map-full-backend-20261018.log`; `evidence/integration/lcluc-change-map-live-integrity-20261018.json`; `evidence/integration/lcluc-change-map-browser-20261018.json`; `evidence/integration/lcluc-change-map-nonempty-20261018.png`; `evidence/integration/lcluc-change-map-empty-20261018.png`; `frontend/src/lclucTransitionAdapter.ts`; `frontend/src/LclucTransitionSummary.tsx`; `evidence/integration/lcluc-transition-adapter-focused-final-20261018.log`; `evidence/integration/lcluc-transition-ui-related-20261018.log`; `evidence/integration/lcluc-transition-independent-20261018.log`; `evidence/integration/lcluc-transition-generated-fixture-20261018.json`; `docs/implementation/119_lcluc_transition_matrix.md`; `evidence/integration/lcluc-transition-ui-tests-20261018.log`; `evidence/integration/lcluc-transition-ui-build-20261018.log`; `evidence/integration/lcluc-transition-ui-build-initial-20261018.log`; `evidence/integration/lcluc-transition-browser-20261018.json`; `evidence/integration/lcluc-transition-live-integrity-20261018.json`; `evidence/integration/lcluc-transition-matrix-final-20261018.png`; `evidence/integration/lcluc-transition-class-map-20261018.png`; `backend/app/model_error_analysis_api.py`; `tests/test_model_error_analysis_api.py`; `docs/implementation/120_model_error_analysis_read.md`; `evidence/integration/model-error-analysis-api-focused-final-20261018.log`; `evidence/integration/model-error-analysis-api-related-20261018.log`; `evidence/integration/model-error-read-route-guards-20261018.log`; `frontend/src/ModelErrorAnalysis.tsx`; `frontend/src/modelErrorAnalysisAdapter.ts`; `frontend/src/modelErrorAnalysisClient.ts`; `frontend/src/model-error-analysis.css`; `docs/implementation/121_model_error_analysis_ui.md`; `evidence/integration/model-error-analysis-ui-related-final2-20261018.log`; `evidence/integration/model-error-analysis-ui-tests-final-20261018.log`; `evidence/integration/model-error-analysis-ui-build-final-20261018.log`; `evidence/integration/model-error-read-independent-20261018.json`; `evidence/integration/model-error-read-browser-20261018.json`; `evidence/integration/model-error-read-live-integrity-20261018.json`; `evidence/integration/model-error-read-backend-all-20261018.log`; `backend/app/ml/per_scene_normalization_contract.py`; `tests/test_per_scene_normalization_contract.py`; `backend/app/ml/normalization.py`; `evidence/integration/per-scene-contract-focused-20261018.log`; `evidence/integration/per-scene-contract-existing-boundaries-20261018.log`; `docs/implementation/122_per_scene_normalization_contract.md`; `evidence/integration/per-scene-contract-independent-20261018.json`; `evidence/integration/per-scene-contract-independent-20261018.log`; `evidence/integration/per-scene-contract-runtime-boundary-20261018.json`; `evidence/integration/per-scene-contract-runtime-boundary-20261018.log`; `evidence/integration/per-scene-contract-live-integrity-20261018.json`; `backend/app/ml/per_scene_normalization_files.py`; `tests/test_per_scene_normalization_files.py`; `evidence/integration/per-scene-files-focused-final-20261018.log`; `evidence/integration/per-scene-files-related-20261018.log`; `evidence/integration/per-scene-files-runtime-comparison-20261018.json`; `evidence/integration/per-scene-files-live-integrity-20261018.json`; `docs/implementation/123_per_scene_normalization_files.md`; `evidence/integration/per-scene-files-independent-20261018.json`; `evidence/integration/per-scene-files-independent-20261018.log`; `evidence/integration/per-scene-files-independent-initial-20261018.json`; `evidence/integration/per-scene-files-independent-initial-20261018.log`; `backend/app/ml/model_checkpoint_manifest.py`; `tests/test_model_checkpoint_manifest.py`; `evidence/integration/model-manifest-read-agent-focused-final-20261018.log`; `evidence/integration/model-manifest-read-root-related-20261018.log`; `evidence/integration/model-manifest-read-runtime-20261018.json`; `evidence/integration/model-manifest-read-live-integrity-20261018.json`; `docs/implementation/124_model_checkpoint_manifest.md`; `evidence/integration/model-manifest-read-independent-20261018.json`; `evidence/integration/model-manifest-read-independent-20261018.log`; `evidence/integration/model-manifest-read-agent-focused-20261018.log`; `backend/app/ml/registered_per_scene_files.py`; `tests/test_registered_per_scene_files.py`; `docs/implementation/125_registered_per_scene_files.md`; `backend/app/dataset_registry.py`; `evidence/integration/registry-normalization-agent-focused-20261018.log`; `evidence/integration/registry-normalization-root-related-20261018.log`; `evidence/integration/registry-normalization-runtime-20261018.json`; `evidence/integration/registry-normalization-live-integrity-20261018.json`; `evidence/integration/registry-normalization-independent-20261018.json`; `evidence/integration/registry-normalization-independent-20261018.log`; `backend/app/ml/pinned_scene_normalization.py`; `tests/test_pinned_scene_normalization.py`; `evidence/integration/pinned-scene-agent-20261018-focused.log`; `evidence/integration/pinned-scene-runtime-20261018.json`; `evidence/integration/pinned-scene-operating-inventory-20261018.json`; `docs/implementation/126_pinned_scene_normalization.md`; `evidence/integration/pinned-scene-root-related-20261018.log`; `evidence/integration/pinned-scene-runtime-initial-20261018.log`; `evidence/integration/pinned-scene-live-integrity-20261018.json`; `evidence/integration/pinned-scene-independent-20261018.json`; `evidence/integration/pinned-scene-independent-20261018.log`; `backend/app/ml/pinned_annual_normalization.py`; `tests/test_pinned_annual_normalization.py`; `evidence/integration/annual-normalization-agent-20261018-focused.log`; `evidence/integration/annual-normalization-operating-inventory-20261018.json`; `docs/implementation/127_pinned_annual_normalization.md`; `evidence/integration/annual-normalization-root-related-20261018.log`; `evidence/integration/annual-normalization-runtime-20261018.json`; `evidence/integration/annual-normalization-live-integrity-20261018.json`; `evidence/integration/annual-normalization-independent-20261018.json`; `evidence/integration/annual-normalization-independent-20261018.log`; `backend/app/ml/registry_temporal_normalization.py`; `tests/test_registry_temporal_normalization.py`; `evidence/integration/temporal-normalization-agent-20261018-focused-final.log`; `evidence/integration/temporal-normalization-agent-20261018-focused.log`; `evidence/integration/temporal-normalization-live-integrity-20261018.json`; `evidence/integration/temporal-normalization-operating-inventory-20261018.json`; `docs/implementation/128_registry_temporal_normalization.md`; `evidence/integration/temporal-normalization-root-related-20261018.log`; `evidence/integration/temporal-normalization-runtime-20261018.json`; `evidence/integration/temporal-normalization-independent-20261018.json`; `evidence/integration/temporal-normalization-independent-20261018.log`; `backend/app/ml/registry_raster_grid_normalization.py`; `tests/test_registry_raster_grid_normalization.py`; `evidence/integration/raster-grid-agent-20261018-focused-final.log`; `evidence/integration/raster-grid-agent-20261018-focused.log`; `evidence/integration/raster-grid-live-integrity-20261018.json`; `evidence/integration/raster-grid-operating-inventory-20261018.json`; `docs/implementation/129_registry_raster_grid_normalization.md`; `evidence/integration/raster-grid-root-related-20261018.log`; `evidence/integration/raster-grid-runtime-20261018.json`; `evidence/integration/raster-grid-independent-20261018.json`; `evidence/integration/raster-grid-independent-20261018.log`; `backend/app/ml/registry_spatial_normalization.py`; `tests/test_registry_spatial_normalization.py`; `evidence/integration/registry-spatial-agent-20261018-focused.log`; `evidence/integration/registry-spatial-live-integrity-20261018.json`; `evidence/integration/registry-spatial-operating-inventory-20261018.json`; `docs/implementation/130_registry_spatial_normalization.md`; `evidence/integration/registry-spatial-root-related-20261018.log`; `evidence/integration/registry-spatial-runtime-20261018.json`; `evidence/integration/registry-spatial-independent-20261018.json`; `evidence/integration/registry-spatial-independent-20261018.log`; `backend/app/ml/registered_quality_mask_files.py`; `tests/test_registered_quality_mask_files.py`; `evidence/integration/quality-mask-agent-20261018-focused.log`; `evidence/integration/quality-mask-operating-inventory-20261018.json`; `docs/implementation/131_registered_quality_mask_files.md`; `evidence/integration/quality-mask-agent-20261018-focused-final.log`; `evidence/integration/quality-mask-root-related-20261018.log`; `evidence/integration/quality-mask-runtime-20261018.json`; `evidence/integration/quality-mask-live-integrity-20261018.json`; `evidence/integration/quality-mask-independent-20261018.json`; `evidence/integration/quality-mask-independent-20261018.log`; `backend/app/ml/registered_quality_mask_grid.py`; `tests/test_registered_quality_mask_grid.py`; `docs/implementation/132_registered_quality_mask_grid.md`; `evidence/integration/mask-grid-agent-20261018-focused.log`; `evidence/integration/mask-grid-independent-20261018.json`; `evidence/integration/mask-grid-independent-20261018.log`; `evidence/integration/mask-grid-operating-inventory-20261018.json`; `evidence/integration/mask-grid-root-related-final-20261018.log`; `evidence/integration/mask-grid-root-related-20261018.log`; `evidence/integration/mask-grid-runtime-20261018.json`; `evidence/integration/mask-grid-live-integrity-20261018.json`; `backend/app/ml/registered_binary_mask_values.py`; `tests/test_registered_binary_mask_values.py`; `evidence/integration/binary-mask-agent-20261018-focused.log`; `docs/implementation/133_registered_binary_mask_values.md`; `evidence/integration/binary-mask-root-related-20261018.log`; `evidence/integration/binary-mask-runtime-20261018.json`; `evidence/integration/binary-mask-live-integrity-20261018.json`; `evidence/integration/binary-mask-operating-inventory-20261018.json`; `evidence/integration/binary-mask-independent-20261018.json`; `evidence/integration/binary-mask-independent-20261018.log`; `backend/app/ml/annual_quality_mask_diagnostics.py`; `tests/test_annual_quality_mask_diagnostics.py`; `docs/implementation/134_annual_quality_mask_diagnostics.md`; `evidence/integration/annual-mask-agent-20261018-focused-final.log`; `evidence/integration/annual-mask-agent-20261018-focused.log`; `evidence/integration/annual-mask-root-related-20261018.log`; `evidence/integration/annual-mask-runtime-20261018.json`; `evidence/integration/annual-mask-live-integrity-20261018.json`; `evidence/integration/annual-mask-operating-inventory-20261018.json`; `evidence/integration/annual-mask-independent-20261018.json`; `evidence/integration/annual-mask-independent-20261018.log`; `backend/app/ml/annual_mask_policy.py`; `tests/test_annual_mask_policy.py`; `docs/implementation/135_annual_mask_policy.md`; `evidence/integration/annual-mask-policy-agent-20261018-focused.log`; `evidence/integration/mask-policy-root-related-20261018.log`; `evidence/integration/mask-policy-runtime-20261018.json`; `evidence/integration/mask-policy-live-integrity-20261018.json`; `evidence/integration/mask-policy-operating-inventory-20261018.json`; `evidence/integration/mask-policy-independent-20261018.json`; `evidence/integration/mask-policy-independent-20261018.log`; `backend/app/annual_diagnostics_service.py`; `tests/test_annual_diagnostics_service.py`; `docs/implementation/136_annual_diagnostics_service.md`; `contracts/internal/lcluc-annual-diagnostics-request.schema.json`; `contracts/internal/lcluc-annual-diagnostics-response.schema.json`; `evidence/integration/diagnostic-service-agent-20261018-focused-final.log`; `evidence/integration/diagnostic-service-agent-20261018-focused-final2.log`; `evidence/integration/diagnostic-service-runtime-20261018.json`; `evidence/integration/diagnostic-service-runtime-final-20261018.log`; `evidence/integration/diagnostic-service-live-integrity-20261018.json`; `evidence/integration/diagnostic-service-operating-inventory-20261018.json`; `evidence/integration/diagnostic-service-root-related-final-20261018.log`; `evidence/integration/diagnostic-service-root-related-20261018.log`; `evidence/integration/diagnostic-service-runtime-20261018.log`; `evidence/integration/diagnostic-service-independent-20261018.json`; `evidence/integration/diagnostic-service-independent-20261018.log`; `backend/app/annual_diagnostics_api.py`; `tests/test_annual_diagnostics_api.py`; `frontend/src/AnnualInputDiagnostics.tsx`; `frontend/src/annualInputDiagnosticsAdapter.ts`; `frontend/src/annualInputDiagnosticsClient.ts`; `frontend/src/annual-input-diagnostics.css`; `frontend/src/ModelReview.tsx`; `evidence/integration/diagnostic-api-agent-20261018-focused-final3.log`; `evidence/integration/annual-input-diagnostics-ui-front-20261018.log`; `evidence/integration/annual-input-diagnostics-ui-build-final2-20261018.log`; `docs/implementation/137_annual_diagnostics_api_ui.md`; `evidence/integration/diagnostic-api-live-http-20261018.json`; `evidence/integration/diagnostic-api-browser-20261018.json`; `evidence/integration/diagnostic-api-operating-inventory-20261018.json`; `evidence/integration/diagnostic-api-live-integrity-20261018.json`; `evidence/integration/diagnostic-api-compat-tests-final2-20261018.log`; `evidence/integration/diagnostic-api-compat-tests-final-20261018.log`; `evidence/integration/diagnostic-api-compat-test-update-20261018.json`; `evidence/integration/diagnostic-api-live-integrity-final-20261018.json`; `evidence/integration/diagnostic-api-root-full-backend-20261018.log`; `scripts/collect_samples.py`; `scripts/collect_training_grid.py`; `evidence/integration/diagnostic-api-root-full-backend-final2-20261018.log`; `evidence/integration/diagnostic-api-final-processes-20261018.json`; `backend/app/data/quality_mask_bundle.py`; `tests/test_quality_mask_bundle.py`; `evidence/integration/quality-mask-bundle-agent-20261018.log`; `docs/implementation/138_quality_mask_bundle.md`; `evidence/integration/quality-mask-bundle-root-related-20261018.log`; `evidence/integration/quality-mask-bundle-independent-20261018.json`; `evidence/integration/quality-mask-bundle-independent-20261018.log`; `evidence/integration/quality-mask-bundle-independent-initial-20261018.json`; `evidence/integration/quality-mask-bundle-independent-initial-20261018.log`; `evidence/integration/quality-mask-bundle-live-integrity-final-20261018.json`; `evidence/integration/quality-mask-bundle-operating-inventory-20261018.json`; `backend/app/data/quality_report_completion.py`; `tests/test_quality_report_completion.py`; `docs/implementation/139_quality_report_completion.md`; `evidence/integration/quality-report-completion-agent-20261018.log`; `evidence/integration/quality-report-completion-agent-final-20261018.log`; `evidence/integration/quality-report-completion-root-related-20261018.log`; `evidence/integration/quality-report-completion-root-related-final2-20261018.log`; `evidence/integration/quality-report-completion-independent-20261018.json`; `evidence/integration/quality-report-completion-independent-20261018.log`; `evidence/integration/quality-report-completion-independent-initial-20261018.json`; `evidence/integration/quality-report-completion-independent-initial-20261018.log`; `evidence/integration/quality-report-completion-live-integrity-final-20261018.json`; `evidence/integration/quality-report-completion-operating-inventory-20261018.json`; `backend/app/data/quality_report_storage.py`; `tests/test_quality_report_storage.py`; `docs/implementation/140_quality_report_storage.md`; `evidence/integration/quality-report-storage-agent-20261018.log`; `evidence/integration/quality-report-storage-agent-initial-20261018.log`; `evidence/integration/quality-report-storage-root-related-final-20261018.log`; `evidence/integration/quality-report-storage-root-related-20261018.log`; `evidence/integration/quality-report-storage-root-related-initial-20261018.log`; `evidence/integration/quality-report-storage-independent-20261018.json`; `evidence/integration/quality-report-storage-independent-20261018.log`; `evidence/integration/quality-report-storage-independent-initial-20261018.json`; `evidence/integration/quality-report-storage-independent-initial-20261018.log`; `evidence/integration/quality-report-storage-independent-pre-native-guard-20261018.json`; `evidence/integration/quality-report-storage-independent-pre-native-guard-20261018.log`; `evidence/integration/quality-report-storage-live-integrity-final-20261018.json`; `evidence/integration/quality-report-storage-operating-inventory-20261018.json`; `backend/app/data/quality_report_preflight.py`; `tests/test_quality_report_preflight.py`; `docs/implementation/141_quality_report_preflight.md`; `evidence/integration/quality-report-preflight-agent-20261018.log`; `evidence/integration/quality-report-preflight-agent-initial-20261018.log`; `evidence/integration/quality-report-preflight-root-related-20261018.log`; `evidence/integration/quality-report-preflight-independent-20261018.json`; `evidence/integration/quality-report-preflight-independent-20261018.log`; `evidence/integration/quality-report-preflight-independent-initial-20261018.json`; `evidence/integration/quality-report-preflight-independent-initial-20261018.log`; `evidence/integration/quality-report-preflight-live-integrity-final-20261018.json`; `evidence/integration/quality-report-preflight-operating-inventory-20261018.json`; `backend/app/data/quality_report_registration.py`; `tests/test_quality_report_registration.py`; `docs/implementation/142_quality_report_registration.md`; `evidence/integration/quality-report-registration-agent-20261018.log`; `evidence/integration/quality-report-registration-agent-initial-20261018.log`; `evidence/integration/quality-report-registration-agent-initial2-20261018.log`; `evidence/integration/quality-report-registration-root-related-20261018.log`; `evidence/integration/quality-report-registration-independent-20261018.py`; `evidence/integration/quality-report-registration-independent-20261018.json`; `evidence/integration/quality-report-registration-independent-20261018.log`; `evidence/integration/quality-report-registration-independent-initial-20261018.py`; `evidence/integration/quality-report-registration-independent-initial-20261018.json`; `evidence/integration/quality-report-registration-independent-initial-20261018.log`; `evidence/integration/quality-report-registration-live-integrity-final-20261018.json`; `evidence/integration/quality-report-registration-operating-inventory-20261018.json`; `scripts/quality_report_cli.py`; `tests/test_quality_report_cli.py`; `docs/implementation/143_quality_report_cli.md`; `evidence/integration/quality-report-cli-agent-20261018.log`; `evidence/integration/quality-report-cli-agent-initial-20261018.log`; `evidence/integration/quality-report-cli-root-related-20261018.log`; `evidence/integration/quality-report-cli-independent-20261018.py`; `evidence/integration/quality-report-cli-independent-20261018.json`; `evidence/integration/quality-report-cli-independent-20261018.log`; `evidence/integration/quality-report-cli-live-integrity-final-20261018.json`; `evidence/integration/quality-report-cli-operating-inventory-20261018.json`; `tests/test_collection_raster_declarations.py`; `docs/implementation/144_collection_raster_declarations.md`; `evidence/integration/collection-raster-declarations-agent-20261018.log`; `evidence/integration/collection-raster-declarations-agent-initial-20261018.log`; `evidence/integration/collection-raster-declarations-independent-20261018.py`; `evidence/integration/collection-raster-declarations-independent-20261018.json`; `evidence/integration/collection-raster-declarations-independent-20261018.log`; `evidence/integration/collection-raster-declarations-root-related-20261018.log`; `evidence/integration/collection-raster-declarations-source-scope-20261018.json`; `evidence/integration/collection-raster-declarations-full-20261018.log`; `evidence/integration/collection-raster-declarations-operating-inventory-20261018.json`; `evidence/integration/collection-raster-declarations-live-integrity-final-20261018.json`; `evidence/integration/collection-raster-declarations-live-integrity-initial-20261018.json`; `evidence/integration/collection-raster-declarations-source-scope-20261018.py`; `tests/test_grid_patch_declarations.py`; `evidence/integration/grid-patch-declarations-agent-20261018.log`; `evidence/integration/grid-patch-declarations-agent-initial-20261018.log`; `evidence/integration/grid-patch-declarations-source-scope-20261018.json`; `evidence/integration/grid-patch-declarations-operating-inventory-20261018.json`; `docs/implementation/145_grid_patch_declarations.md`; `evidence/integration/grid-patch-declarations-independent-20261018.py`; `evidence/integration/grid-patch-declarations-independent-20261018.json`; `evidence/integration/grid-patch-declarations-independent-20261018.log`; `evidence/integration/grid-patch-declarations-live-integrity-final-20261018.json`; `evidence/integration/grid-patch-declarations-root-related-20261018.log`; `evidence/integration/grid-patch-declarations-full-20261018.log`; `evidence/integration/grid-patch-declarations-final-processes-20261018.json`; `scripts/register_dataset_version.py`; `tests/test_source_raster_registration_cli.py`; `evidence/integration/source-raster-registration-cli-agent-20261018.log`; `evidence/integration/source-raster-registration-cli-self-catalog-reproduction-20261018.py`; `evidence/integration/source-raster-registration-cli-self-catalog-reproduction-20261018.json`; `evidence/integration/source-raster-registration-cli-self-catalog-reproduction-20261018.log`; `evidence/integration/source-raster-registration-cli-agent-initial-20261018.log`; `docs/implementation/146_source_raster_registration_cli.md`; `evidence/integration/source-raster-registration-cli-independent-20261018.py`; `evidence/integration/source-raster-registration-cli-independent-20261018.json`; `evidence/integration/source-raster-registration-cli-independent-20261018.log`; `evidence/integration/source-raster-registration-cli-independent-initial-20261018.py`; `evidence/integration/source-raster-registration-cli-independent-initial-20261018.json`; `evidence/integration/source-raster-registration-cli-independent-initial-20261018.log`; `evidence/integration/source-raster-registration-cli-live-integrity-final-20261018.json`; `evidence/integration/source-raster-registration-cli-operating-inventory-20261018.json`; `evidence/integration/source-raster-registration-cli-root-related-20261018.log`; `evidence/integration/source-raster-registration-cli-root-related-initial-20261018.log`; `evidence/integration/source-raster-registration-cli-live-integrity-initial-20261018.json`; `evidence/integration/source-raster-registration-cli-final-processes-20261018.json`; `frontend/src/GeoWorkflowEvidence.tsx`; `frontend/src/geollmWorkflowEvidenceAdapter.ts`; `frontend/src/geollmWorkflowEvidenceClient.ts`; `docs/implementation/147_geollm_workflow_evidence_ui.md`; `evidence/integration/geollm-workflow-evidence-ui-focused-20261018.log`; `evidence/integration/geollm-workflow-evidence-root-backend-20261018.log`; `evidence/integration/geollm-workflow-evidence-root-frontend-20261018.log`; `evidence/integration/geollm-workflow-evidence-build-20261018.log`; `evidence/integration/geollm-workflow-evidence-independent-20261018.py`; `evidence/integration/geollm-workflow-evidence-independent-20261018.json`; `evidence/integration/geollm-workflow-evidence-independent-20261018.log`; `evidence/integration/geollm-workflow-evidence-ui-focused-initial-20261018.log`; `evidence/integration/geollm-workflow-evidence-browser-20261018.json`; `evidence/integration/geollm-workflow-evidence-browser-dom-20261018.txt`; `evidence/integration/geollm-workflow-evidence-browser-20261018.png`; `evidence/integration/geollm-workflow-evidence-map-browser-20261018.png`; `evidence/integration/geollm-workflow-evidence-applied-dom-20261018.txt`; `evidence/integration/geollm-workflow-evidence-applied-browser-20261018.png`; `evidence/integration/geollm-workflow-evidence-browser-http-20261018.log`; `evidence/integration/geollm-workflow-evidence-browser-server-initial-20261018.log`; `evidence/integration/geollm-workflow-evidence-browser-server-initial2-20261018.log`; `evidence/integration/geollm-workflow-evidence-live-integrity-final-20261018.json`; `evidence/integration/geollm-workflow-evidence-dev-server-after-20261018.json`; `evidence/integration/geollm-workflow-evidence-final-processes-20261018.json`; `docs/implementation/152_priority_collection.md`; `docs/implementation/152_targeted_bare_collection_rfc.md`; `docs/implementation/153_priority_collection_split_candidate_qa.md`; `docs/implementation/154_collection_progress_ui.md`; `docs/implementation/155_collection_priority_status_contract.md`; `docs/implementation/157_targeted_bare_plan.md`; `scripts/collect_training_priority.py`; `backend/app/collection_priority_status.py`; `backend/app/data/targeted_bare_plan.py`; `frontend/src/CollectionProgress.tsx`; `frontend/src/collectionProgressAdapter.ts`; `evidence/integration/priority-collection-final-20261018.json`; `evidence/integration/priority-collection-root-tests-final-20261018.log`; `evidence/integration/priority-root-related-20261018.log`; `evidence/integration/collection-progress-ui-focused-final-20261018.log`; `evidence/integration/collection-progress-ui-frontend-20261018.log`; `evidence/integration/collection-progress-ui-build-final-20261018.log`; `evidence/integration/targeted-bare-plan-local-20261018.json`; `evidence/integration/priority-collection-round2-final-20261018.json`; `evidence/integration/priority-ml-20261018-summary.json`; `evidence/integration/priority-ml-20261018-final-verification.json`; `evidence/integration/priority-ml-ui-receipt-20261018.json`; `evidence/integration/priority-collection-independent-20261018.json`; `evidence/integration/collection-progress-ui-candidate-browser-20261018.json`; `evidence/integration/collection-progress-ui-candidate-refresh-final-20261018.png`; `evidence/integration/collection-progress-ui-candidate-refresh-dom-20261018.txt`; `evidence/integration/priority-root-related-final-20261018.log`; `evidence/integration/priority-status-tests-final-20261018.log`; `evidence/integration/priority-collection-round3-final-20261018.json`; `evidence/integration/priority-status-api-final-restored-20261018.json`; `evidence/integration/priority-frontend-isolated-source-20261018.json`; `evidence/integration/priority-frontend-isolated-build-20261018.log`; `evidence/integration/priority-frontend-isolated-tests-initial-20261018.log`; `evidence/integration/priority-frontend-isolated-tests-20261018.log`; `docs/implementation/159_next_collection_candidate_qa.md`; `evidence/integration/priority-frontend-isolated-tests-fixtures-partial-20261018.log`; `evidence/integration/collection-progress-ui-final1464-browser-20261018.json`; `evidence/integration/collection-progress-ui-final1464-dom-20261018.txt`; `evidence/integration/collection-progress-ui-final1464-candidate-20261018.png` |
| confidence | round3 정산·153 후보1106 실제QA·최신1464 UI·격리frontend288 PASS/build120 확인; 159 최종은 별도 대기 |
| status | VERIFIED_REAL 실제수집·153 고정후보QA·최신UI / 157 실행BLOCKED·나지4차단 / round4 PLANNED·159 QA 진행 |

> 이번 작성은 읽기와 문서화다. 아래 시험 결과는 2026-10-17 보존 로그의 역사적 기록이며 재실행 결과가 아니다. 상태는 각 범위에 한정한다.

## 1분: 사진과 투명 필름 맞추기

위성영상, 토지피복 참조지도, 구름 마스크는 서로 다른 투명 필름과 같다. 같은 좌표와 픽셀 격자로 맞춰야 한 위치를 비교할 수 있다. 현재 실자료 검사 기록은 있지만 그 자료로 만든 모델의 독립 정확도가 확보된 것은 아니다.

## 5분: 입력과 처리

관심영역(AOI)·기간 → STAC 검색 → Scene의 밴드 Asset 선택 → COG 일부 창 바이트 수집 → 반사도 보정·품질 mask·참조라벨 정합 → 출처·해시·연차 manifest가 흐름이다. STAC는 목록 검색이므로 검색 결과가 있다고 파일을 받은 것은 아니다.

B02 청색, B03 녹색, B04 적색, B08 근적외선, B11/B12 단파적외선을 쓴다. 가시광 외 식생·수분 정보도 함께 보는 이유다. SWIR의 원래 20m 정보를 10m 격자로 재표본화해도 새로운 10m 세부정보가 생기지는 않는다. SCL은 구름 등 품질 분류이며 토지피복 정답이 아니다.

## 이론과 선택 이유

좌표체계(CRS), Affine 변환, 가로·세로 격자와 NoData를 함께 맞춘다. 범주 라벨은 nearest로 이웃 클래스 번호를 유지하고, 연속 영상은 bilinear 같은 보간을 사용할 수 있다. 범주 번호를 평균하면 존재하지 않는 중간 클래스가 생길 수 있다. 단일 B04보다 6밴드가 분광 구분 정보를 늘리지만 정확도를 보장하지 않는다. WorldCover/Esri 같은 참조는 의사라벨이며 독립 현장 정답과 구별한다.

```mermaid
flowchart LR
 A[AOI·날짜] --> B[search_stac: 목록]
 B --> C[read_cog_window: 바이트]
 C --> D[반사도·mask·라벨 정합]
 D --> E[manifest·checksum·lineage]
 E --> F[readiness 검사]
```

## 실제 함수·API

| 역할 | 코드·API | 입력 → 출력 |
|---|---|---|
| 검색 | `backend/app/data/service.py:search_stac`, `POST /api/data/search` | bbox·날짜 → Scene metadata |
| 창 수집 | 같은 파일 `read_cog_window`, `HTTPRangeReader` | URL·bbox·side·예산 → raster 창 |
| 정합 | 같은 파일 `align_labels`, `backend/app/ml/raster.py:assert_aligned`, `reproject_to_reference` | source·reference → 정합 라벨/검사 |
| 보정 | `backend/app/data/calibration.py:parse_product_calibration` | 제품 XML·밴드 → scale/offset |
| 공유 제한 | `backend/app/data/budget.py:CollectionLedger`, `parallel.py:run_two_workers` | 예약·계측 → 원장·작업 결과 |
| 복구 조회 | `backend/app/data/recovery.py:inspect_recovery`, `scripts/collect_recovery_inspect.py` | 현재 기록 → 진단; 재개 실행 아님 |

## 실제 기록과 한계

`VERIFIED_REAL`은 기존 QA가 실제 파일·메타데이터를 검사한 범위다. manifest 1,384행/적격 1,111, train/val/test 628/233/250이며 고유 파일 해시 4,335개 고정은 08:49 KST QA의 기록이다. 이번에 4,335개 파일을 다시 감사하지 않았다. 이번 파일 현재성 대조는 [증거 스냅샷](EVIDENCE_SNAPSHOT.json)을 확인한다.

인계 시 collector/monitor가 없고 execution lock 및 Banten/West Java 2023 pending 2건이 남았다. terminal worker report가 없어 예약 해제·중복 수집을 하지 않았다. lock만 지워 재개하면 예산·전송이 중복 계산될 수 있다. DNS·HTTP429는 재시도와 전역 중지·전송 예산을 함께 보아야 한다. 기록된 출처와 라이선스 메타데이터는 모든 공식 기관 사용권 승인 완료를 뜻하지 않는다.

## 10분 발표의 확장

앞의 5분에 격자 정합 오류 예, 검색과 바이트 차이, 예약액과 실제 수신량 차이를 각 1분 설명한다. 나머지 2분은 pending의 terminal 근거를 보존하는 복구 계획과 클래스 표본 계획을 논의한다. 대안인 전체 영상 다운로드는 단순하지만 전송량이 커진다. 현재는 필요한 창을 수집하고 예산을 공유한다.

## 발표와 Q&A

30초: “여러 위성 밴드와 라벨을 같은 좌표에 맞추고 출처를 고정했습니다. 현재 적격 1,111개이며 수량 뒤의 누출·대표성 검사가 계속 적용됩니다.”

슬라이드: 영상 목록과 바이트 / 투명 필름 정합 / 출처와 예산 / 다음 검사.

Q. 공식 데이터인가? A. 공개 원천의 실제 영상과 의사라벨을 사용한 기록이며, 기관 독립 현장 정답이나 공식 사용 승인과는 별도다.

Q. 왜 다시 수집하지 않나? A. pending의 종료·전송 근거를 먼저 대조해야 중복 계상을 피한다. 이 에이전트는 수집을 실행하지 않는다.

Q. 다음 Gate는? A. 원장 보존 복구 설계와 새 버전 manifest 계획을 인계받고 이 문서·Gate 노트·발표 수치를 함께 갱신한다.

## 2026-10-17 후속: Dataset 버전 등록 코어

접수증의 내용을 나중에 바꿀 수 없게 하는 장치처럼 자료 ID·고정 버전·자산 SHA와 manifest를 함께 등록하는 Python 코어를 추가했다. `backend/app/dataset_registry.py:register_version`은 GMAIS 원문 schema와 공간·시간·고정 참조를 검사하고 SQLite `BEGIN IMMEDIATE`/`INSERT`로 동일 버전 교체를 거부한다. 같은 내용의 반복은 멱등하게 처리하며 `resolve_version`은 manifest와 현재 자산 해시를 다시 검사한다. `latest/current` 및 가변 lineage 버전은 허용하지 않는다.

`TESTED_SYNTHETIC`: 임시 fixture 신규10 PASS(`dataset-versions-tests-20261017.log`, 1.548초)다. VALIDATED 품질은 실제 로컬 보고서가 필요하지만 과학적 타당성 검증·운영 승인은 부여하지 않는다. HTTP·기관 ACL·기존 카탈로그 변환·실자료 등록·Job resolver·lineage 부모 존재 확인·불변 자산 복제는 후속이다. 전체 G1 완료나 현재 자료의 운영 Registry 이전으로 발표하지 않는다.

1분 설명: “자료 버전의 접수증을 바꾸지 못하도록 등록 코어를 만들고 모의 자료로 시험했습니다.” 5분에는 등록→멱등성→조회 재검사→미연결 HTTP를 설명하고, 10분에는 동시등록·자산 변경 오류 사례를 추가한다. Q. 파일 자체가 영구 고정됐나? A. 아니다. 현재는 고정 해시 대조이며 불변 자산 저장소 복제는 후속이다.

수집 복구계획 도구는 별도 담당의 완료 근거 인계 대기이며 이 항목으로 완료 처리하지 않는다.

### Registry 독립 검토 후 보완

`resolve_version`에 요청 dataset ID/version과 저장 manifest의 ID/version·저장 key를 비교하는 검사를 추가했다. 다른 버전의 유효 manifest가 잘못된 요청의 결과로 해석되는 문제를 막기 위한 수정이다. `tests/test_dataset_registry_versions.py:test_valid_manifest_from_other_version_cannot_replace_requested_identity`가 추가되어 시험 정의는11개다. 앞서 기록한10 PASS는 수정 전 시험 이력이며, 수정 후 `dataset-versions-tests-20261017.log`를 읽어11 PASS/1.335초를 확인했다. 최종 전체 통합 실행 결과는 별도 인계 대기다.

## 수집 복구계획 완료 근거 — 2026-10-17 09:31 KST

### 1분: 장부를 건드리지 않는 복구 점검표

수집을 다시 켜기 전에 마지막 장부와 남은 파일을 사진으로 찍듯 고정해 복구 점검표를 만드는 도구를 구현했다. 같은 근거는 같은 plan ID가 되고 근거가 바뀌면 이전 계획을 거부한다. 점검표가 유효해도 실제 수집 재개 허가는 아니다.

### 5분: snapshot → 계획 → 현재성 검증

`backend/app/data/recovery.py:inspect_recovery`, `build_recovery_plan`, `validate_recovery_plan`과 `scripts/plan_collection_recovery.py`가 실제 위치다. 원장·manifest·run-result·lock·pending config/window-state/terminal/source/partial의 존재와 바이트 SHA를 고정한다. 누락 파일이 나중에 생겨도 stale이 되며 같은 크기의 partial 내용 변경도 잡는다. 연속 두 snapshot과 계획의 정책 본문을 다시 비교하여 변조 뒤 ID를 재계산해도 거부한다. 이는 원장 잠금·원자적 적용이나 OS 프로세스 종료 증명은 아니다.

실제 자료로 계획을 두 번 생성해 같은 ID를 재사용했다.09:30:37 KST 검증 JSON은 `valid_for_review=true`, `status=VALID_BLOCKED`, `execution_authorized=false`, 네트워크0·원본쓰기0이다.09:31:01 KST 무결성 기록은 보호 근거15개 참조의 전후 snapshot 일치를 확인한다. 전체 raster 재감사나 실제 복구 실행 증거로 확대하지 않는다.

Banten/West Java2023 pending2건은 각68,157,440B, 합계136,314,880B 예약을 보존한다. terminal worker 결과와 source annual report가 없어 환불 제안0B다. run-result는 원장보다68,157,440B 뒤처져 예산은 실제 원장을 따른다.09:31 KST 별도 OS 조회의 collector/monitor 없음 기록과 영속 계획의 `process_evidence=NOT_VERIFIED`는 구분한다. 적용 시점에 다시 확인해야 한다.

### 시험·10분 확장·남은 일

관련 단위시험15건 중14 PASS·1 SKIP다. 실제 Windows symlink 생성권한 부족1건을 SKIP했고 deterministic resolver 대체 경계시험은 PASS다. 최신 전체회귀는225건 중224 PASS·1 SKIP/60.950초다. 원본 바이트 보존·stale/변조·중복출력·경로이탈을 검사한 코드시험이며 수집·정산·학습 실행 성공이 아니다.

10분은5분 흐름에 “누락 terminal이 등장하면 왜 stale인가”, “예약액과 실제 전송량 차이”, “정확히 한 번 정산하는 coordinator”를 덧붙인다. Q. VALID_BLOCKED면 실행 가능한가? A. 검토용 현재 근거가 일치한다는 뜻이며 실행 허가는 false다. 실제 적용 coordinator는 PLANNED이고 terminal/완전계측·정산/aggregate 중복방지 근거는 BLOCKED다. 빈 lock 삭제·예약 해제·collector 재시작 기능은 이번 도구에 없다.

앞선 수집 복구 완료근거 대기 문구는 이 절의 확인으로 대체한다. 원본 재고1,111과 학습 gate는 그대로 유지한다.

## 최신 후속: 등록된 Dataset을 Job 제출 입력과 대조

`backend/app/job_inputs.py:resolve_job_inputs`를 Job API 제출 경로에 연결했다. 등록된 Dataset의 고정 id/version/artifact SHA를 대조하고 자산을 재검사한다. 입력 SHA는 manifest 메타데이터의 SHA가 아니라 실제 자산의 지문이다. 같은 자료ID의 다른 고정버전(T1/T2)은 정상 비교 입력으로 허용하고 동일(id,version)에 다른SHA를 요구할 때 충돌한다. 제출 URI로 등록 자산을 바꾸거나 원격 파일을 가져오지 않는다.

검사 결과를 제출시점의 `input_resolution` snapshot으로 저장한다. 이는 파일지문·신원 진단이며 AOI/기간/제품 의미 적합성이나 기관 접근권한·과학 승인이 아니다. 제한자료는 ACL미연결로 막고 경로·URI·원문manifest·내부 예외를 응답에 노출하지 않는다. 원문등록 HTTPAPI·실자료등록·불변자산복제·lineage부모존재 검증은 여전히 후속이다. 앞선 “Job resolver 연결 후속”은 이 제출진단 연결로 일부 진전했으며 실제 실행직전 재검증·executor 연결까지 완료된 것은 아니다.

코어10 PASS/1.663초, API12 PASS/1.987초는 임시fixture시험이다. 최신 전체회귀240건 중239 PASS·1 SKIP/48.174초다. 등록 실제자료나 수집·학습 실행을 추가하지 않았다.1분 설명은 “접수한 재료의 고정 지문을 대조했다”,5분은 제출snapshot→재생→실행전 재검증을,10분은 T1/T2와 동일버전SHA충돌·제한자료 비노출 사례를 설명한다.

## Workflow 노드의 고정 입력 진단 연결

이제 개별 Job 접수 외에 `POST /v1/workflows/plan`에서도 각 노드의 `input_bindings`를 Dataset 버전 코어와 대조한다. 먼저 DAG의 형식·노드 ID·의존성·순환을 검사하며, 잘못된 DAG는 Registry 조회나 자산 해시 검사를 시작하지 않는다. 유효한 노드는 `job_inputs.resolve_job_inputs`로 고정 ID/version/artifact SHA와 자산을 검사한다.

PUBLIC·VALIDATED 자산이 정상 대조되면 그 입력에 무조건 붙이던 DATA_MISSING 사유를 제거한다. RAW 품질이나 제한 접근 자료는 파일 무결성이 true여도 품질·ACL blocker를 유지한다. 서로 다른 노드의 입력을 한 목록으로 합치지 않으며 같은 자료 ID의 다른 고정 버전은 T1/T2로 허용한다. 제출 URI로 등록 자산을 교체하거나 원격 자료를 가져오지 않는다.

Job의 같은 요청 재생은 최초 저장 진단을 돌려주는 반면, Workflow 계획은 매 요청 현재 파일을 다시 검사한다. 이 차이가 현재성의 범위다. 어느 쪽도 기관 권한·실제 실행·독립 과학 승인을 부여하지 않는다. 실제 실행 직전 재검증, 자료 의미 적합성, 승인 모델, 기관 ACL은 별도다. 관련 TestClient/임시 fixture 14 PASS·3.910초는 입력 연결과 비실행 경계를 확인한 코드시험이다.

### Workflow 입력 연결 후 최종 전체시험

`workflow-input-full-tests-20261017.log`를 읽어 `scripts/test.ps1`의247건/139.318초/OK(skipped=1), 즉 **246 PASS·1 SKIP**를 확인했다. SKIP은 기존 실제 OS symlink 생성권한 부족이며 대체 mock 경계시험은 통과했다. 관련 Workflow14 PASS·3.910초는 이 전체시험에 포함된 부분이며 이전240건·225건·197건에 산술 합산하지 않는다. 이해 에이전트가 재실행한 것이 아니라 개발팀의 완료 로그를 읽은 근거다. 이전 전체시험 수치는 개발 이력이고 현재 판정은 이 절이 우선한다.

실제 API 프로세스 재시작·실자료 수집/학습·Job/Result 실행은 하지 않았다. 고정 입력 진단은 PLAN_ONLY·BLOCKED 범위이고 과학·기관·운영 승인 및 실제 DAG 실행 gate는 유지한다.

## 현재 자산과 부모 계보를 읽기만 하며 검사하기

`backend/app/dataset_lineage.py:verify_dataset_lineage(store,id,version,artifact_sha,max_depth=32,max_nodes=256)`는 고정된 root와 전이적 부모 참조를 따라 현재 자산을 검사한다. 가족관계도를 따라 각 신분증의 번호가 맞는지 확인하는 것과 같다. 계보가 맞는다는 사실은 사용권한이나 자료의 과학적 정답을 보증하지 않는다.

기존 `resolve_version`으로 각 고유(id,version,SHA)를 한 번씩 확인하고 부모→자식 edge를 반환한다. 같은 자료의 다른 고정 버전은 허용하며 같은 ID/version의 다른 SHA는 충돌이다. 누락·파일변경·동적 참조·순환·깊이/노드 한도를 차단하고 diamond의 공유 부모는 중복 읽지 않는다. 얕은 경로에서 본 부모가 더 깊은 경로에 다시 나와도 깊이 한도를 우회하지 않도록 재평가한다.

제한자료의 자산이 맞아도 ACL 미연결 blocker를 남기고 그 위 계보를 확장·조회·출력하지 않는다. 숨겨진 상위 조상의 ID/URI도 노출하지 않는다. `current_assets_revalidated=true`는 한 번 이상 resolve를 시도했다는 뜻이며 전체 조상 성공이 아니다. `lineage_integrity_verified`와 blocker를 함께 읽는다. RAW 품질을 모델 학습 자격으로 판정하는 함수가 아니며 권한·실행·과학승인은 false다.

합성 Registry·실제 임시 로컬 파일로13 PASS·5.842초와 읽기 불변을 확인했고 최신 전체287건 중286 PASS·1 SKIP/103.726초다. 운영자료를 등록·수정하지 않았고 새 HTTP API도 없다. 따라서 이번 코어는 화면 응답 계약이 바뀌지 않아 UI 직접 변경을 요구하지 않는다. 실제 계보 인수·HTTP 연결·원자적 전체 snapshot·서명 출처·실행 직전 입력 고정은 후속이다. [계보 Gate](gate-notes/GATE_DATASET_LINEAGE_20261017.md)의 1/5/10분 설명을 사용한다.

## 계보 읽기 코어의 HTTP·UI 연결

앞선 코어 단위의 “HTTP/UI 미연결”에서 진전해 `POST /v1/datasets/lineage/verify`와 카탈로그 상세의 수동 검사 폼을 추가했다. POST는 검사 조건을 본문으로 받는 진단 요청이며 등록·실행·자료 쓰기가 아니다. `dataset_lineage_api.py:create_dataset_lineage_router`가 고정 root_ref·엄격한 한도를 확인한 뒤 현재 계보 검사와 allowlist 응답 투영을 thread pool에서 수행한다.

기존 카탈로그6행은 legacy `datasets`이고 고정 버전은 `dataset_versions`다. ID·버전·자산 SHA를 추정해 등록하거나 자동 입력하지 않는다. 별도로 확보한 고정 참조를 직접 넣어야 한다. 미등록은 HTTP200/BLOCKED, 잘못된 bool·한도·요청은400, 처리 불가는503이다. HTTP200은 검사가 통과했다는 뜻이 아니며 응답 모두 no-store다. 현재 자산 확인 시도 flag도 전체 조상 성공으로 읽지 않는다.

관련 API11시험, 전체298건 중297 PASS·1 SKIP/88.188초, UI25 PASS와 build60modules/22.09초를 확인했다. 실제 loopback/browser는 미등록 BLOCKED·입력오류·latest 차단·입력편집 결과제거 범위다. 공개 성공 계보는 임시 fixture 시험이며 운영 계보 인수는 아니다. 보호5개파일 SHA와 기존표준Job2건은 그대로이고 신규실행0이다. 순차시점검사·기관ACL·존재/접근등급의 운영 노출정책·서명출처·실행직전 고정·과학/운영승인은 후속이다.

## 저장 Job의 고정 입력을 현재 계보로 대조

`job_lineage.py:validate_job_lineage`는 저장된 Job의 원 요청에서 고정 input_refs를 읽고, 요청할 때 현재 전이 계보를 검사한다. 제출 당시 저장 snapshot을 읽거나 다시 쓰지 않는다. 원 요청의 ID·Agent·Trace 연결을 확인한 뒤 고정 id/version/자산SHA만 진단에 사용한다. URI hint·role·parameters 전체의 의미나 모델 실행 요건을 모두 재검증하는 기능은 아니다.

서버 한도는 입력64·고유root32·깊이32·root당64노드·요청전체256노드검사다. 같은root는 한 요청 안에서만 재사용하며 서로 다른root의 공유조상을 다시 검사한 비용도 총량에 포함한다. 예산소진 뒤 새root는 checked=false로 남기고 이전root의 캐시는 재사용할 수 있다. checked와current_assets_revalidated는 검사 수행/시도이지 성공이 아니며 부분 결과를 전체 통과로 표시하지 않는다. 노드한도는 개별자산 총byte나 운영동시부하를 보증하지 않는다.

관련12 PASS·전체310건 중309 PASS·1 SKIP/101.622초다. 실제 기존Job의 미등록입력은 현재BLOCKED이며 보호5SHA·기존2Job이 그대로이고 신규실행0이다. 저장snapshot LEGACY와 현재계보BLOCKED가 함께 표시될 수 있다. 기관ACL·독립과학·실행직전불변입력·executor·Workflow전이계보 연결은 후속이다.

## Workflow 전체가 공유하는 현재 계보 검사

새 `POST /v1/workflows/lineage-validation`은 Workflow의 고정 input_bindings를 모아 현재 전이 계보만 읽는다. 같은root를 여러노드가 쓰면 요청내 진단을 한 번 수행하고 재사용한다. `lineage_batch.py:inspect_lineage_bindings`를 Job도 재사용하도록 추출했으며 기존 Job의 정상/부분예산/상충응답은 추출전후 같음을 확인했다.

Workflow전체 한도는 노드128·입력64·고유root32·깊이32·root당64·전체256노드검사다. 같은ID/version의상충SHA는 노드가달라도 양쪽을무해시차단하고 다른고정version은 허용한다. 서로다른root의공유조상재검사비용은총량에포함하며 예산소진뒤새root는미검사로남긴다. 노드128초과는DAG계산전종료하므로 dag_validated=false이고,ref/고유root초과는DAG검증후해시전차단이다.

이검사는URI/role/quality·Agentreadiness·AOI/기간/제품의 전체실행적합성을확인하지않는다. 계보가모두일치해도전체Workflow는 PLAN_ONLY/BLOCKED·실행false다. 순차현재검사·권한/과학승인false·기관ACL/불변입력/운영노출정책한계를유지한다. 실제공유미등록2노드+빈노드의진단1/비용1·재사용·빈입력차단을확인했고보호5SHA/Job2건불변·신규실행0이다.

## 카탈로그 활용 인사이트의 실제 자료 기준

문서43의 읽기 독립 대조에서 `/api/datasets`6행과 SQLite legacy `datasets`6행이 같고, 불변 `dataset_versions`는0행이었다. 이목록은 현재자료를찾는등록메타데이터이며6개의승인된고정manifest가아니다. ID의연도·파일경로·Approved등으로기간/형식/지역/품질/권한을추정하지않는다.

6행모두명시access_class/quality_status/provider/time_range가없다. B04두행은SHA가있지만version은없고license는SEE_COLLECTION_TERMS·license_verified=false다. baselineprepared행은version은있지만표준artifactSHA가없다. 결측조합을완성해계보Registry에자동등록하거나다운로드허가로읽지않는다. 등록시각과자료관측기간도구분한다.

5개인사이트는입력자료·이용조건·메타품질·Toolbox·공간연계의검토/이동화면이다.128/108/20건·82점·99.2%AOI·모델준비율등PNG예시를실적으로복제할근거는없다. 공개2017년6주경계는공식AOI나각Datasetfootprint가아니다. 이번자료검토는API/DB읽기만수행했으며신규등록·수집·학습/Job실행은없다. 최종UI동작은문서42와Root브라우저근거로따로판정한다.

## 11:27 KST 수집 복구 근거 재대조

문서24의 새 읽기 조사와 기존 복구계획 현재검증을 확인했다. 결과는 여전히 VALID_BLOCKED·valid_for_review=true·execution_authorized=false다. Banten/West Java2023 pending2건의 terminal worker/source 보고서 쌍이 없고 예약136,314,880B를 전액 보존한다. 원장계상1,933,512,405B·잔여2,361,454,891B·run-result차이68,157,440B와 configSHA일치는 직전과 같다.

이 조회는 수집재개·예약해제·lock삭제 허가가 아니다. 별도OS조회에 UI/API서버만 보였다는 사실도 종료책임·완전전송·정산근거를 대신하지 않는다. 원장/원본/lock·수집/학습을 변경하지 않았고 exactly-once coordinator는 후속이다. 이번ML계획검증과 함께 보호6SHA(기존계획포함)가 불변임을 실제integrity근거로 확인했다.

## 중단 batch의 terminal·예산 메타데이터를 읽기 대조

`recovery_terminal.py:inspect_recovery_terminal(data_root)`와 CLI `inspect_recovery_terminal.py`를 추가했다. 운송장·정산영수증·장부의 항목을 대조하는 점검표와 같다. terminal이 JSON객체라는 사실만으로 완료 처리하지 않고 MISSING/INVALID/MISMATCH/UNKNOWN/CONSISTENT_METADATA를 구분한다. **모든 분류의 최종상태는 BLOCKED**이며 환불·정산·재시작은 하지 않는다.

config에는 서로 다른 지문이 있다. ledger는 변환전 config문서를정렬JSON으로직렬화한digest, window-state는 years→periods 변환후config의digest와비교한다. 이는파일자체bytesSHA의전후변경검사와도다르다. raw와normalized가같아야한다고가정하지않고각계약에따라따로대조한다. worker key·cog/metadata/charged합계·정수/음수·예산범위와window의legacy+measured<=upper를검사한다.

실제CP949최종CLI는exit0이지만2batch모두worker-result와source annual report가없어MISSING/BLOCKED다. raw-config/ledger와normalized-config/window대조는각각true였다. 각upper−measured33,554,432B는미계측/예약차이로 **환불가능액이 아니다**. 총예약136,314,880B를전액보존하고 proposed_refund_bytes=0·정산/실행/자동재개false를유지한다.

source report에configdigest가없으므로신원연결UNKNOWN,완전전송계측·aggregate정확히한번반영UNKNOWN·process_exit_verified=false다. 모든메타필드가맞는fixture도차단한다. strictJSON·도중파일출현/내용변경·논리경로target재해석으로stale/retarget을거부하지만원자적snapshot/OSlock·조사뒤불변성을보장하지않는다.

관련18 PASS/7.150초·독립18 PASS/7.545초·전체356건355 PASS/1SKIP110.069초다. 존재/누락19refs전후같음·기존recovery/budget/collector2script/저장계획5SHA불변,원래계획도같은ID로VALID_BLOCKED를확인했다. 새API/화면계약없는내부CLI라UI수정/브라우저재검증은불필요했고수집/학습은실행하지않았다.

## Aggregate 출처·중복·누락의 읽기 대조

`recovery_aggregate.py:inspect_recovery_aggregate(data_root)`와 CLI `inspect_recovery_aggregate.py`를 추가했다. 합산명세의 항목번호와 원천납품목록을 대조하는 점검표다. source_manifests·원장report_path를 양방향 비교하고 patch_id와canonical image_path의중복, 각행의 `(source_window.path,scene_id)` 쌍이원천보고서의어느행에연결되는지검사한다. 원본명세를고치거나raster를열지는않는다.

같은촬영scene를여러patch로나누는것은정상이며scene_id반복자체를중복patch로판정하지않는다. 한report에서patch0개가생기는것도collector계약상가능하다. 중복ref는issue로남기되색인에서원천행을가짜로여러번만들지않는다. ledger→aggregate의settled누락/pending참조와aggregate→ledger의unknown/ambiguous연결을구분하고다른실험report는범위밖으로처리한다.

실제최종CP949CLI는exit0·CONSISTENT_METADATA지만전체BLOCKED였다. source참조113/고유113이모두존재하고aggregate1,384행모두두필드쌍이원천row1개에연결됐다. patchID/imagepath중복0·issues0이며ledger119개중현재범위115(보고서113+pending2),범위밖4다. 이는패치내용이나year/province/cropwindow/공간정합의검증이아니다. raster읽기0·source_file_hashes_verified=false이고경로resolve는raster존재/bytes/SHA확인이아니다.

exactly_once_applied=UNKNOWN·정산/실행/자동재개false·환불0을유지한다. 순차JSONfingerprint와논리target재대조는원자적journal/coordinator의정확히한번반영증명이아니다. 기존pending2terminal부재·예약보존과학습BLOCKED도바꾸지않았다. 관련16PASS5.357초·독립16PASS4.579초·전체372건371PASS/1SKIP71.714초,보호132refs/기존계약7SHA불변이다. 새공개API/화면계약없는내부CLI라UI수정/브라우저재검증은불필요했다.

## 연도·지역·crop 메타데이터의 추가 대조

운송장 번호에 이어 납품 연도와 지역, 잘라낸 위치의 기록도 비교하는 점검이다. `recovery_crop.py:inspect_recovery_crop(data_root)`와 `inspect_recovery_crop.py`는 aggregate와 source report JSON을 읽는 별도 companion이다. 기존 aggregate의 원장/참조 양방향·patch ID/이미지 경로 중복 검사를 다시 수행하지 않는다.

`(canonical source path, scene_id)`가 원천 행 하나에 연결된 뒤 year/province의 원형 타입과 값을 대조한다. year는2015~2026의 정수 또는 ASCII4자리 문자열이며 `2023`과 `"2023"`은 다르다. bool/float/범위 밖 값은 양쪽이 같아도 INVALID다. province는 공백만 있는 문자열을 거부하고 trim하거나 추정하지 않는다. `materialize_patches`는 year를 복사하고 province를 batch 값으로 지정한다. 따라서 report 지역 일치는 부분 문맥이며 batch config 신원·행정경계 승인이 아니다. aoi는 생성 과정에서 달라질 수 있어 동일성을 강제하지 않는다.

crop은 정확한 정수4개 `[x,y,256,256]`이며 x/y는0이상·256격자여야 한다. `(canonical source path, scene_id, crop4좌표)`의 반복을 중복으로 보고 같은 scene의 다른 crop은 허용한다. 실제 원본 크기 안에 들어가는지, 다른 파일이 같은 내용인지, 기하 중첩이 있는지는 검사하지 않는다. checked=true는 검사 시도 범위이며 행별 성공과 다르다.

최종 CP949 CLI exit0 기록에서 source113개·aggregate1,384행의 유일 source 연결·year/province EXACT_TYPED_MATCH·crop VALID_METADATA가 각각1,384행이었다. 지정 식별자 중복0·issue0·CONSISTENT_METADATA지만 BLOCKED다. raster 읽기0·경계/기하/다른 파일 SHA 미검사·exactly-once UNKNOWN·정산/실행/자동재개/학습/과학 승인false·환불0을 유지한다. JSON fingerprint와 논리 target 재대조도 원자적 snapshot 보장은 아니다.

관련14 PASS/8.084초·독립14 PASS/4.983초, 전체386건385 PASS·1 SKIP/111.108초다. 보호132참조(누락 포함)·기존 계약8SHA 불변이며 독립 시험을 전체에 중복 합산하지 않는다. 공개API/화면 계약이 없는 내부 CLI여서 UI 수정·브라우저 재검사는 불필요했다. [Crop Gate](gate-notes/GATE_RECOVERY_CROP_20261017.md)에 최종 근거와 한계를 연결했다.

## 로컬 헤더의 추가 검증

`recovery_raster_headers.py:inspect_recovery_raster_headers(data_root)`와 CLI는 이제 실제 로컬 GTiff 내부 헤더를 읽는 별도 companion이다. 기존 crop/aggregate/terminal 보고서의 미검사 flag를 바꾸거나 해당 원장/출처/연도 검사를 재실행하지 않는다. 고정 aggregate의 source_window.path·image_path만 따라가며 label/quality는 열지 않는다.

원본 크기 안에 crop가 들어가는지, patch가256×256인지, source/patch의 밴드수·dtype·CRS가 맞는지, 원본 affine에 crop offset을 적용한6계수가 맞는지 비교한다. 회전/skew를 지원하며 abs1e-7·rel1e-12는 수치 반올림 허용치이지 현장 정확도 기준이 아니다. bounds 밖 거대 정수는 변환 계산을 건너뛰어 overflow 없이 issue로 남긴다.

로컬 root 안 일반 TIFF만 허용하며 GDAL 전에8바이트 signature를 확인한다. GTiff 읽기 모드·INTERNAL georef·PAM NO·EMPTY_DIR·PROJ_NETWORK OFF·VRT Python NO를 사용한다. 픽셀 배열·통계 메서드는 호출하지 않지만 TIFF directory와 내부 좌표 메타데이터 바이트는 읽는다. 전체 raster SHA는 계산하지 않는다.

최종 실제 CLI exit0에서 고유1,475파일(원본91+patch1,384)이 모두 VALID_HEADER,1,384행이 모두 HEADER_CONTRACT_MATCH·issue0·CONSISTENT_HEADERS였다. **전체상태는 BLOCKED**다. 픽셀/라벨/품질·다른 파일 동일내용·독립 기하 누출·exactly-once/정산/학습 승인은 확인하지 않았다. stat/처음16바이트/부모 파일목록의 보존 관측도 전체 raster SHA 보존 증명은 아니다. [헤더 Gate](gate-notes/GATE_RASTER_HEADERS_20261017.md)에 최신 시험·보호 대조를 연결한다. 새API/화면 계약 없는 내부 CLI라 UI 변경·브라우저 재검사는 불필요하다.

최종 전체 `scripts/test.ps1`은 **403건 중402 PASS·1 SKIP/95.828초/종료0**다. 기존 OS symlink 생성 권한1건을 건너뛰었으며 deterministic 경계 시험은 통과했다. 관련17·독립17은 전체403에 중복 합산하지 않는다. 보호132 JSON/원장참조의 SHA·존재와 기존 계약9SHA는 불변이고 이전 추적 코드/데이터/계약 변경0이다.1,475 raster의 stat·처음16바이트 및 기록된1,475 부모 파일목록 관측도 변경0이었다. 이는 **전체 raster 바이트 SHA 동일성 증명이 아니다**. 보존 로그와 실제 근거를 읽은 기록이며 이해자료 작성 중 재실행하지 않았다.

다음 고정 JSON의 `source_window.sha256`·`patch_sha256.image`와 로컬 파일의 streaming SHA를 대조하는 단위는 **PLANNED**다. 대상 예상1,475파일/2,332,461,937B이며 현재 수행 결과가 아니다. 네트워크·픽셀 해석 없이 내용 지문을 읽는 계획이고, 그 결과도 픽셀/라벨 품질·과학/학습 승인과 구분한다.

## 저장 지문과 실제 파일 바이트를 대조하는 companion

`recovery_raster_content.py:inspect_recovery_raster_content`와 CLI는 caller가 manifest SHA를 고정한 뒤 source_window.sha256·patch_sha256.image와 실제 파일 바이트 SHA를 비교한다. 전체 기대값의 형식/상충/누락·canonical 경로·파일 존재를 먼저 검토하고 문제가 있으면 모든 content streaming을 시작하지 않는다. 같은 canonical 경로는 역할/행을 합쳐 한 번만 읽는다.

최대3GiB의 정확한 정수 예산 안에서 stat상 고유 크기 합을 먼저 확인하고, unbuffered 최대1MiB chunk의 실제 반환 byte를 누계한다. EOF probe는 예산 여유가 있을 때만1byte를 읽고 그 byte도 누계한다. 정확 예산 경계는 추가 read 없이 fstat/stat을 사용한다. 조기EOF·성장·descriptor/stat/논리target/manifest 변경을 거부한다. 원자적 다중파일 snapshot이나 metadata 원복 공격까지 보장하지 않는다.

GDAL/pixel decoder·네트워크를 사용하지 않는 파일 byte 읽기다. byte 동일성은 픽셀 의미·정답 품질·기하/split 독립성과 다르다. 기존 header 기능의 contentSHAfalse는 해당 모듈 범위 그대로 보존한다. [내용 SHA Gate](gate-notes/GATE_RASTER_CONTENT_20261017.md)에 최종 실제/시험 근거를 연결한다. 공개API/화면 계약 없는 내부CLI라 UI 수정·브라우저 재검사는 불필요하다.

최종 실제 CP949 CLI exit0에서 고유1,475파일이 모두 MATCH·RECORDED_SHA_MATCH였다. 계획 크기와 실제 반환byte는 각각2,332,461,937B로 같고 명시 예산3,000,000,000B 이내다. issue0·관측 동일digest의 다른 경로그룹0이지만 **전체상태는 BLOCKED**다. caller가 고정한 manifest SHA는 `cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f`다.

최종 관련15 PASS/1.477초·독립15 PASS/2.365초, 전체 `scripts/test.ps1` **418건 중417 PASS·1 SKIP/92.959초/종료0**다. 최종15개는 전체 시작 전에 작성되어418건에 포함됐으며 관련/독립/추가 early-EOF 확인을 중복 합산하지 않는다. SKIP은 기존 OS symlink 생성 권한이고 deterministic 경계 시험은 통과했다. 보호132 JSON/원장참조의 SHA·존재와 기존 계약10SHA는 불변이며 이전 추적 코드/데이터/계약 변경0이다.1,475파일 stat/처음16바이트·기록된1,475 부모목록 관측 변경0도 확인했다.

이번에는1,475 image 파일의 전체 byte SHA를 순차 streaming 시점에 기대값과 대조했다. label/quality·과거4,335파일 전체 감사·다중파일 원자적 snapshot·픽셀 의미·장면 공간/split 독립성 승인은 아니다. 같은digest 경로그룹0도 서로 다른 파일 표현의 같은 영상이나 기하 누출이 없다는 증거는 아니다. pixel decoder/GDAL/네트워크0·실행/정산/재개/학습/과학 승인false·exactly-once UNKNOWN·환불0을 유지한다.

## 보조자산 지문과 목록 커버리지의 별도 진단

`recovery_auxiliary_content.inspect_recovery_auxiliary_content`와 CLI는 고정 manifest의 patch label/quality·source quality·boundary 명시 경로/SHA 쌍만 검사한다. 두 키 모두 없으면 UNKNOWN이며 다른 명시 자산 검사를 허용한다. 한쪽만 기재·명시null·손상SHA·상충·파일누락이면 계획 INVALID/streaming0으로 구분한다. 미기재5개 source quality의 경로나 SHA를 추정하지 않는다.

실제 최종 CP949 CLI에서 명시 고유2,855파일이 모두 MATCH·계획=실제12,719,583B/예산67,108,864B·issue0이었다. 하지만 legacy80행의 source quality/boundary 참조가 역할별80개 미기재되어 UNKNOWN160·RECORDED_AVAILABLE_SHA_MATCH_PARTIAL/INCOMPLETE_REFERENCES·BLOCKED다. patch label/quality는 각각1,384행/1,384고유파일, source quality는1,304행/86고유파일, boundary는1,304행/1고유파일이다.

관측 동일digest 다른경로그룹175는 반복된 label/quality byte 진단이며 데이터누출·기하/장면독립성 판정이 아니다. 삭제/재분할하지 않았다. 기존 image1,475와 명시 aux2,855=4,330은 과거4,335파일 fresh 전체감사가 아니다. 라벨 의미·quality 적합성·공식 경계 승인도 미검증이며 학습/정산/재개false·환불0을 유지한다. [보조자산 Gate](gate-notes/GATE_AUXILIARY_CONTENT_20261017.md)에 근거를 연결한다.

최종 전체 `scripts/test.ps1`은 **432건 중431 PASS·1 SKIP/103.139초/종료0**다. SKIP은 기존 OS symlink 생성 권한이며 deterministic 경계 시험은 통과했다. 관련14 PASS/3.996초·독립14 PASS/3.534초는 전체432에 중복 합산하지 않는다. 보호132참조와 기존 계약11SHA는 불변이고 이전 추적 코드/데이터/계약 변경0이다.2,855보조파일 stat/처음16바이트와1,471부모 파일목록의 관측 변화도0이다. 전체aux SHA 확인 범위는 명시된2,855파일의 순차 읽기이며 원자적 snapshot은 아니다.

## 보조 TIFF와 영상짝의 헤더 정합 검사

`recovery_auxiliary_headers.inspect_recovery_auxiliary_headers`와 CLI는 patch label/quality를 patch image에, 명시 source quality를 source image에 대조한다. 고정 manifest의 경로/SHA 형식·상충·존재를 전수 계획하고 GTiff 내부 헤더로 크기·1밴드/uint8/nodata0·CRS·affine을 비교한다. patch는256×256도 확인한다. source quality 양키부재는 UNKNOWN, boundary는 OUT_OF_SCOPE다.

정확 affine 일치와 abs1e-7·rel1e-12 tolerance 일치를 각각 기록한다. tolerance 통과를 readiness 정확transform/전체준비도 통과로 읽지 않는다. 내용SHA는 형식/상충만 검사하며 현재 파일을 재해시하지 않는다. 이전 content companion의 byte 관측과 별도다. [보조 헤더 Gate](gate-notes/GATE_AUXILIARY_HEADERS_20261017.md)에 최종 근거를 연결한다. TIFF metadata byte는 읽되 픽셀/의미/QA적합성은 미검증이고 BLOCKED·승인false다. 공개API/화면 계약 없는 내부CLI라 UI 수정·브라우저 재검사는 불필요하다.

실제 최종 CP949 CLI exit0에서 명시 보조TIFF2,854+영상짝1,475=고유4,329개 모두 VALID_HEADER, 역할별4,072 pairing 모두 HEADER_ALIGNMENT_MATCH·affine_exact_match=true였다. patch label/quality는 각각1,384행 일치/정확일치, sourcequality는1,304행 일치/정확일치(고유86파일)다. issue0이지만 sourcequality80 UNKNOWN이 남아 KNOWN_HEADERS_MATCH_PARTIAL/INCOMPLETE_REFERENCES·BLOCKED이며 boundary는 OUT_OF_SCOPE다.

최종 전체 `scripts/test.ps1`은 **446건 중445 PASS·1 SKIP/116.342초/종료0**다. SKIP은 기존 OS symlink 생성 권한이며 deterministic 경계 시험은 통과했다. 관련14 PASS/5.580초·독립14 PASS/9.720초는 전체446에 중복 합산하지 않는다. 보호132참조와 기존 계약12SHA는 불변이며 이전 추적 코드/데이터/계약 변경0이다.4,329파일 stat/처음16바이트 및1,475부모목록 관측도 불변이었다. 전체 rasterSHA 재검증false·원자적 snapshotfalse이며 이번 문서 작업은 보존 근거를 읽었고 재실행하지 않았다.

다음 boundary JSON 구조/출처 진단은 **PLANNED**이며 아직 구현/검증 결과가 아니다. 공식 경계 승인이나 기하 독립성 보장을 뜻하지 않으며 legacy미기재80행은 UNKNOWN으로 유지할 계획이다.

## 경계 JSON 구조와 지역키의 별도 대조

`recovery_boundary.inspect_recovery_boundary`와 CLI는 고정 manifest의 명시 boundary 경로/SHA를 전수 계획하고 raw byte1회로 SHA와 JSON을 함께 읽는다. 양키부재는 UNKNOWN, partial/null/손상/상충/파일누락은 계획거부·boundary읽기0이다. 실제 소비키 `properties.province_id`가 고유하고 row.province가 그 feature에 유일하게 연결되는지 검사한다.

FeatureCollection의 Polygon/MultiPolygon·유한2D 경위도범위·닫힌4position이상 ring이라는 제한된 부분집합만 확인한다. topology/자기교차·공식ADM1/권한·raster포함·독립기하는 미검사다. strict UTF-8 depth scan은 escaped quote를 처리하고 BOM/NUL·UTF-16/32를 거부한다. invalid 짧은 ring의 position도 vertex예산에 포함한다. boundary4MiB/16파일/128feature/100,000vertex/depth32와 manifest별도64MiB/2read를 구분한다.

[경계 구조 Gate](gate-notes/GATE_BOUNDARY_STRUCTURE_20261017.md)에 최종 근거를 연결한다. 지문·서식·지역키 연결은 공식경계/기관승인/과학 성능이 아니며 기존 학습/정산/재개 차단을 유지한다. 공개API/화면 계약 없는 내부CLI라 UI 수정·브라우저 재검사는 불필요하다.

최종 실제 CP949 CLI exit0에서 명시 경계1파일/482,365B의 기대·관측SHA `de7722bfa88ddff3e12137d271c28717c23b3077a87b7dc36c66d1d8c522c909`가 일치했다.6feature·17,940position의 지원 구조는 STRUCTURE_MATCH·issue0이고1,304행 모두 UNIQUE_PROVINCE_MATCH다. legacy80행 UNKNOWN으로 KNOWN_STRUCTURE_MATCH_PARTIAL/INCOMPLETE_REFERENCES·BLOCKED다. 지역연결 한 건만으로 전체파일의 다른feature/rootCRS issue를 무시하지 않으며 이번 실제결과는 전체issues도0임을 별도로 확인했다.

최종 전체 `scripts/test.ps1`은 **462건 중461 PASS·1 SKIP/107.796초/종료0**다. SKIP은 기존 OS symlink 생성 권한이고 deterministic 경계 시험은 통과했다. 관련16 PASS/2.365초·독립16 PASS/2.304초는 전체462에 중복 합산하지 않는다. 보호132참조의 SHA·존재와 기존 계약13SHA는 불변이며 이전 추적 코드/데이터/계약 변경0이다. boundary1파일 stat/처음16바이트와1부모목록 관측변화도0이다. raw/SHA·구조·키연결의 순차읽기 범위이며 원자적 snapshot은 아니다. 이해자료 작성에서는 보존 근거를 읽었고 재실행하지 않았다.

다음 경계도형 topology 진단(`.is_valid` 등)은 **PLANNED** 별도 단위이며 현재 검증 결과가 아니다. geometry 자동보정·공식/기관 승인·기하 독립성 보장을 뜻하지 않으며 기존분할·원본과 UNKNOWN80을 유지한다.

## Feature별 GEOS topology 진단

`recovery_boundary_topology.inspect_recovery_boundary_topology`와 CLI는 같은 pinned manifest·명시boundary raw/SHA·구조·지역키를 다시 읽고 모든 선행issue가 없을 때만 feature별 GEOS진단을 시작한다. `topology_engine_attempt_count=0`은 shape/위상시도0이지 library import도 없었다는 뜻은 아니다. source legacy80행은 UNKNOWN으로 보존한다.

`shape/is_empty/is_valid/explain_validity`와 유한 양수면적을 읽고 예외는 UNKNOWN, 엔진없음은 NOT_CHECKED로 남긴다. 면적은 평면 degree²이며 km²/측지면적이 아니다. 한 MultiPolygon 내부겹침과 서로다른 feature간겹침은 별개이고 후자는 미검사다. repair/buffer/make_valid·재투영·geometry쓰기를 하지 않는다. 입력상한도 hard CPU시간을 보장하지 않는다. [Topology Gate](gate-notes/GATE_BOUNDARY_TOPOLOGY_20261017.md)에 최종 근거를 연결한다. 공식경계/권한·raster포함·독립성·과학승인은 여전히미검증/BLOCKED다. 내부CLI/APIUI계약불변으로 UI변경·브라우저 재검사는 불필요하다.

실제 최종 CP949 CLI exit0에서 명시1경계/482,365B의 SHA·6feature/17,940position·1,304지역키연결은 issue0이었다. 실행관측은 Shapely2.1.2/GEOS3.13.1이며 feature별6시도 모두 VALID_TOPOLOGY·is_empty=false/is_valid=true·유한양수 평면면적·Valid Geometry였다. legacy80 UNKNOWN으로 KNOWN_TOPOLOGY_VALID_PARTIAL/INCOMPLETE_REFERENCES·BLOCKED다. 평면 degree² 숫자를 실제 사업면적·km²로 전달하지 않는다.

최종 전체 `scripts/test.ps1`은 **475건 중474 PASS·1 SKIP/103.359초/종료0**다. SKIP은 기존 OS symlink 생성 권한이며 deterministic 경계 시험은 통과했다. 관련13 PASS/1.829초·독립13 PASS/1.809초와 추가상충SHA/설명함수예외 합성확인을 전체475에 중복 합산하지 않는다. 보호132참조와 기존 계약14SHA는 불변이며 이전 추적 코드/데이터/계약 변경0이다. boundary1파일 stat/처음16바이트와1부모목록 관측변화도0이다. 순차진단이며 원자적 snapshot은 아니다. 이해자료 작성은 보존 근거를 읽었고 재실행하지 않았다.

다음 서로다른 feature 경계 교차진단은 **PLANNED** 별도 단위다. 접촉과 면적중첩을 구분하고 입력/쌍예산을 제한하며 자동수선하지 않는 계획이다. 현재 그 검증 결과나 공식/독립성 승인으로 표현하지 않는다.

## 같은 파일 feature쌍의 경계 관계 진단

`recovery_boundary_relations.inspect_recovery_boundary_relations`와 CLI는 명세/SHA/구조/지역연결·모든feature topology가 통과한 뒤 같은파일의 무순서 i<j쌍을 전수진단한다. 전체쌍이 예산(기본64/hard8,128)을 넘으면 shape/pair작업 전에 거부한다. geometry는feature당1회·intersection은pair당1회 계산한다.

empty/면적0은DISJOINT, nonempty/면적0/touches는BOUNDARY_CONTACT, 유한한 정확양수면적은POSITIVE_AREA_OVERLAP다. equal/contains도중첩이며 tinypositive를 임의epsilon으로 숨기지 않는다. 숫자/empty/touches모순·엔진예외는UNKNOWN이다. 양수finding≠행정오류확정이며 평면degree²를 실제면적으로 사용하지 않는다. 다른파일쌍은OUT_OF_SCOPE다. [관계 Gate](gate-notes/GATE_BOUNDARY_RELATIONS_20261017.md)에서 최종 실제/시험근거를 읽는다. repair/재투영/쓰기없음·공식권한/raster포함/독립성미검증·BLOCKED를 유지한다. 내부CLI/APIUI불변으로 UI변경·브라우저재검사는 불필요하다.

실제 최종 CP949 CLI exit0에서 쌍 예산15·계획15·시도15였으며, **13 DISJOINT·2 BOUNDARY_CONTACT·양수 면적 중첩0·issue0**이었다. 접촉 쌍은 South Sulawesi–Southeast Sulawesi와 Banten–West Java이며 교차 면적은0이다. Shapely2.1.2/GEOS3.13.1에서 명시 경계1파일482,365B의 SHA·6개 유효 feature·1,304지역 연결을 확인했지만 legacy80 UNKNOWN으로 KNOWN_RELATIONS_DIAGNOSED_PARTIAL/INCOMPLETE_REFERENCES·BLOCKED다. 다른 파일의 쌍은 OUT_OF_SCOPE이며 실제 제외 쌍은0이다.

최종 전체 `scripts/test.ps1`은 **490건 중489 PASS·1 SKIP/107.418초/종료0**다. SKIP은 기존 OS symlink 생성 권한이며 deterministic 경계 시험은 통과했다. 관련15 PASS/1.791초·독립15 PASS/1.764초는 전체490에 중복 합산하지 않는다. 보호132참조와 기존 계약15SHA는 불변이고 이전 추적 코드·데이터·계약 변경0이다. 경계1파일의 stat·처음16바이트와1부모 파일목록 관측 변화도0이다. 이는 순차 진단이며 원자적 snapshot은 아니다. 이해자료 작성은 보존 근거를 읽었고 재실행하지 않았다.

다음 source_window 원본영상의 헤더 기반 footprint·주 연결 최소 진단은 **PLANNED**다. 실제 소비 CRS/affine/변환 계약을 먼저 확인하고 고정 manifest·명시 경계·한도를 유지하는 계획이며 현재 수행 결과가 아니다. 임시 파생 footprint는 픽셀 내부 포함 비율·면적 정확성·표본 독립성 증명이 아니고 원본 raster·geometry·분할은 변경하지 않는다.

## 원본영상 네 모서리와 주 경계의 근사 관계

`recovery_source_footprints.inspect_recovery_source_footprints`와 CLI는 고정 manifest의 명시 source/boundary/province 조합을 계획한다. 원본 GTiff 헤더의 네 pixel-edge corner에 회전/skew affine을 적용하고 offline pyproj로 EPSG:4326 좌표를 만든 뒤 직선 Polygon으로 잇는다. source header와 같은관계 조합은 각각 한 번 진단한다.

preplan 경로/SHA형식·상충·누락·예산 오류는 header0이다. 이후 boundary 내용/SHA/구조/geometry issue가 생겨도 source header 독립 진단은 계속하고 주관계만 UNKNOWN으로 남긴다. 미기재경계는 추정하지 않는다. always_xy/errcheck·allow_ballpark=false/only_best=true와 네트워크finally복원을 사용하며 날짜변경선·비유한·변환오류는 UNKNOWN이다.

[원본 footprint Gate](gate-notes/GATE_SOURCE_FOOTPRINTS_20261017.md)의 근사범위를 함께 읽는다. 정확한raster 윤곽·곡선가장자리 densify·픽셀inside비율·측지면적·source대source/분할독립성 검사가 아니다. source는 헤더만 읽고 full내용SHA·픽셀을 읽지 않는다. 임시좌표변환만 수행하고 원본raster/geometry 재투영·repair·쓰기없음, BLOCKED와기존차단을 유지한다. 내부CLI/APIUI계약불변으로 UI변경·브라우저재검사는 불필요하다.

실제 최종 CP949 CLI exit0에서 source header91개와 네 모서리 직선근사 footprint91개가 모두 유효했고, 고유(source,boundary,province)관계86개는 모두 POSITIVE_AREA_OVERLAP·issue0이었다. 명시1,304참조와 legacy80 UNKNOWN으로 KNOWN_CORNER_DIAGNOSTICS_PARTIAL/INCOMPLETE_BOUNDARY_REFERENCES·BLOCKED다. 실행관측은 Shapely2.1.2/GEOS3.13.1·pyproj3.7.2/PROJ9.5.1이며 projection network는 entry=false/exit=false·복원true였다. 양수 교차는 원본영상 전체가 주 안에 있다는 뜻이나 픽셀 포함 비율·정확 footprint·자료 독립성 증명이 아니다.

최종 전체 `scripts/test.ps1`은 **506건 중505 PASS·1 SKIP/161.521초/종료0**다. SKIP은 기존 OS symlink 생성 권한이고 deterministic 경계 시험은 통과했다. 관련16 PASS/9.217초·독립16 PASS/10.829초는 전체506에 중복 합산하지 않는다. 초기14시험은 오류계층·최종 network복원 확인2개를 보완하기 전 이력이다. 보호132참조와 기존 계약16SHA는 불변이며 이전 추적 코드·데이터·계약 변경0이다.91 source+1 boundary의 stat·처음16바이트와92부모 파일목록 관측도 변하지 않았다. 원자적 snapshot·현재 source 전체SHA 보존 증명은 아니며 이해자료 작성은 보존 근거를 읽고 재실행하지 않았다.

다음 source대source 모서리근사와 고정split 연결·교차후보 진단은 **PLANNED**다. readiness.default_policy의 실제 province_splits 계약을 먼저 확인하고 물리1,384행의 source맥락과 적격patch집합을 구분해 mapping·전체pair예산을 계획한다. 원본 분할 재배정·후보발행·학습을 수행하지 않는 별도단위이며 근사교차finding은 표본독립성 증명이나 기존5차단 해제가 아니다. 현재 source_to_source_intersections_checked/training_split_leakage_resolved=false를 유지한다.

## 전체 물리 source의 고정 split 간 모서리근사 후보

`recovery_source_split_overlap.inspect_recovery_source_split_overlap`와 CLI는 실제 `readiness.default_policy.province_splits`의4 train/Banten val/West Java test를 읽고 구현·map SHA를 기록한다. 전체 물리행의 source·주·split을 연결하며 quality_status를 필터로 쓰거나 적격1,111/readiness를 재계산하지 않는다.

같은 canonical source가 여러split에 걸치면 별도 finding이다. 서로다른 source는 A{train,val}–B{train}처럼 하나라도 다른 split조합이 있으면 대상이며7개 split집합cohort로 전수쌍 수와 예산을 먼저 검사한다. 같은 단일split cohort내쌍만 OUT_OF_SCOPE다. invalidsource관련쌍은 NOT_CHECKED로 남겨 보고서행수와 실제intersection시도수를 구분한다.

[고정 split 후보 Gate](gate-notes/GATE_SOURCE_SPLIT_OVERLAP_20261017.md)에서 후보와 적격누출평가를 구분한다. 네모서리직선근사이며 경계는 BOUNDARY_NOT_USED, 픽셀/정확footprint·현재sourceSHA·학습분할독립승인이 아니다. 원본재배정·후보발행·학습 없이 BLOCKED·기존차단을 유지한다. 내부CLI/APIUI불변으로 UI변경·브라우저재검사는 불필요하다.

실제 최종 CP949 CLI exit0에서 전체 물리1,384행은 고정정책상 train848/val272/test264였고91 source 헤더·모서리근사가 유효했다. 교차split 계획2,227쌍·진단기록2,227개·실제intersection2,227회는 모두 DISJOINT, 접촉/양수중첩/issue0·다중split canonical source finding0이었다. 같은 단일split1,868쌍은 OUT_OF_SCOPE다. boundary는 BOUNDARY_NOT_USED이며 이전 경계미기재80행을 이번 누락source로 부르지 않는다. CROSS_SPLIT_CORNER_CANDIDATES_DIAGNOSED라도 전체 BLOCKED다.

최종 전체 `scripts/test.ps1`은 **521건 중520 PASS·1 SKIP/160.195초/종료0**다. SKIP은 기존 OS symlink 생성 권한이고 deterministic 경계 시험은 통과했다. 관련15 PASS/9.129초·독립15 PASS/10.368초와 별도고정seed40사례/4,532후보쌍 계획대조를 전체521에 중복 합산하지 않는다. 보호132참조·기존 계약17SHA는 불변이며 이전 추적 코드·데이터·계약 변경0이다. source91개 stat·처음16바이트와91부모목록 관측도 불변이었다. 현재 source 전체SHA·원자적 snapshot 증명은 아니며 이해자료 작성은 보존 근거를 읽고 재실행하지 않았다.

다음 저장readiness 차단근거와 이번corner진단의 scope차이를 읽기 대조하는 최소리포트는 **PLANNED**다. 원본group/scene token과 적격bbox교차의 근거를 분리해 살피되 기존gate/policy/원장/분할을 바꾸지 않고 원인·적격성 상태를 추측하지 않는 별도단위다.

## 저장 readiness와 물리 corner snapshot의 범위 대조

`recovery_readiness_comparison.inspect_recovery_readiness_comparison`와 CLI는 manifest·저장readiness·저장corner보고서 세JSON을 각각 SHA로 고정한다. 실제 고정policy/codeSHA·typed 계수·유일source·예상pair전체집합·완료상태/flags·저장header/corner 최소schema를 검사한다. 불완전보고서의 positive0을 전수DISJOINT로 요약하지 않는다.

현재source경로는 해석만 하고 raster stat/open·header/픽셀·GEOS·readiness.assess는 호출하지 않는다. 저장좌표의 변환을 새로 계산한 것도 아니다. 적격628·233·250과 물리848·272·264, 기존token/bbox와corner 규칙을 구분한다. prepared_payloadnull·witness미저장 때문에 실제원인분기는 UNKNOWN_NOT_PERSISTED다. 고정6주group_splits와5개연결component는 다른뜻이다.

[Readiness 범위 대조 Gate](gate-notes/GATE_READINESS_COMPARISON_20261017.md)에서 현재검증과저장근거를 구분한다. 기존5 blocker·BLOCKED를 유지하고 gate/policy/원장/분할을 변경하지 않는다. 내부CLI/APIUI불변으로 UI변경·브라우저재검사는 불필요하다.

실제 최종 CP949 CLI exit0에서 세 pinned JSON은 CONSISTENT_SAVED_SCOPE_METADATA·issue0이었다. 저장5개 blocker와 적격1,111/628·233·250을 보존하고 물리1,384/848·272·264와 구분했다. 차이220·39·14는 산술비교이며 제외행 목록이나 원인 복원이 아니다. 저장corner의 완전성·2,227개 recorded DISJOINT·후보없음 요약은true지만 현재영상/기하를 다시 검사한 결과가 아니다. prepared_payload=null·적격scene witness와 token/bbox 실제원인분기는 UNKNOWN_NOT_PERSISTED이며 저장component 연결도 분기증거가 아니다.

최종 전체 `scripts/test.ps1`은 **538건 중537 PASS·1 SKIP/174.829초/종료0**다. SKIP은 기존 OS symlink 생성 권한이며 deterministic 경계 시험은 통과했다. 관련17 PASS/9.343초·독립17 PASS/8.723초는 전체538에 중복 합산하지 않는다. 초기16과 중간17/8.876초는 검토 보완 전 이력이다. 보호132참조·기존 계약18SHA·입력3JSON의 SHA와 존재는 불변이고 이전 추적 코드·데이터·계약 변경0이다. 저장5개 blocker의 순서와 내용은 원형 그대로 보존했다. 이해자료 작성은 보존 근거를 읽었고 재실행하지 않았다.

다음 향후준비성 검사의 source-group/scene-token/bbox 연결witness를 제한 저장할 계약·순수진단helper는 **PLANNED**다. 적격성 증거입력이 없으면 부재로 표시하고 과거원인을 소급추정하지 않는다. 기존assess/gate/policy/분할 변경·통합·재실행은 별도후속이며 현재 미수행이다.

## 향후 연결근거를 남길 순수 metadata helper

`readiness_connectivity_witness.diagnose_readiness_connectivity`는 caller가 공급한 scene metadata의 공유token·bbox연결 witness를 계산한다. 파일IO·CLI/API/UI·GEOS·readiness.assess가 없고 적격성은 CALLER_ASSERTED_NOT_VERIFIED다. None은증거부재/UNKNOWN, 빈목록은명시0개로 구분한다.

shared source_group/scene_id namespace·lastowner·같은행no-op·within/transitive union을 보존하고 빈group은 두token역할만skip하며 bbox참여를 유지한다. 저장edge한도에 닿아도 전체연결계산은 끝나므로 union_complete와truncated를 분리한다. [Connectivity witness Gate](gate-notes/GATE_CONNECTIVITY_WITNESS_20261017.md)를 참조한다. 실제과거보고서는 scene부재라 helper(None)의UNKNOWN만확인했고 과거원인을복원하지않았다. 기존assess미통합·적격신원/저장계약은후속이며 원본·분할/BLOCKED를유지한다. 순수함수로 새UI연결대상이없다.

이 단위의 “witness 저장 한도”는 반환할 메모리 결과 목록에 남기는 edge수의 한도다. 파일·DB에 영속 저장하는 기능은 없으며 향후 저장report 통합계약은 별도 PLANNED다.

이번 실제 확인은 고정SHA의 저장readiness에서 prepared_payload=null·eligible scene/witness부재를 읽고 순수helper(None)를1회 연결한 범위다. 결과는 UNKNOWN_NOT_PERSISTED·union_complete=false이며 실제적격장면의 token/bbox연결을 실행하거나 과거원인을 복원하지 않았다. 기존5 blocker와 적격1,111/628·233·250은 원형 그대로 보존됐다. supplied metadata의 연결계산은 합성자료로 검증했으며 적격성은 CALLER_ASSERTED_NOT_VERIFIED다.

최종 전체 `scripts/test.ps1`은 **554건 중553 PASS·1 SKIP/197.097초/종료0**다. SKIP은 기존 Windows symlink 생성 권한이며 deterministic 경계 시험은 통과했다. 관련16 PASS/0.006초·독립16 PASS/0.007초·별도BFS300사례/3,917이벤트 실험은 전체554에 중복 합산하지 않는다. 보호132참조·기존19계약SHA·저장readiness SHA는 불변이고 이전 추적 코드·데이터·계약 변경0이다. 저장5 blocker의 순서/내용과 적격계수는 그대로이며 신규core/test의 freeze SHA도 일치했다. 이해자료 작성은 보존 근거를 읽었고 재실행하지 않았다.

다음 별도연결 통합설계·입력provenance/eligibleidentity·보고서 영속보존 계약은 **PLANNED**다. 기존assess/gate 실제통합·적격성 재평가는 아직 수행하지 않았고 과거저장보고서의 원인을 소급추정하지 않는다.

## Witness의 순수 canonical bytes envelope

`readiness_connectivity_envelope`의 build/validate/encode/decode는 caller입력·provenance·witness를SHA로묶고58helper를재계산해정확대조한다. validator에는독립외부helper/provenance/inputSHA pin이필요하다. 봉투에서expected를꺼내되돌리면독립신뢰기준이없다. 선언SHA일치는실제출처파일·실행helper코드·eligibility인증이아니며verified필드는false다.

Python sortkeys/compact UTF8규약이며 RFC8785/타언어serializer동일성보장은아니다. None/empty·장면순서·literal값/int/float/bool·signedzero와edge절단을구분하고 parse/serialize/helper전한도를검사한다. [Envelope Gate](gate-notes/GATE_CONNECTIVITY_ENVELOPE_20261017.md)를참조한다. 실제는과거scene부재의None입력3,385bytes왕복만확인했다. Root의새evidence작성과모듈영속저장은다르며 파일/DB/CLI/API/UI·assess연결은없다. 기존차단/BLOCKED를유지하고 새UI대상은없다.

실제 확인은 고정SHA의 저장readiness에서 scene근거/payload부재를 읽고, 독립구성한 None/None/defaultlimits입력의 pin으로 build→encode→decode→재encode한3,385bytes가 동일함을 확인한 범위다. 실제적격scene를 공급하거나 과거원인을 복원하지 않았으며 UNKNOWN_NOT_PERSISTED·기존5 blocker·적격1,111/628·233·250을 유지했다. Root가 raw/audit evidence파일을 새로 쓴 것은 모듈의 영속저장 구현이 아니다.

최종 전체 `scripts/test.ps1`은 **572건 중571 PASS·1 SKIP/158.325초/종료0**다. SKIP은 기존 Windows symlink 생성 권한이며 deterministic 경계 시험은 통과했다. 관련18 PASS/0.224초·최종독립18 PASS/0.217초·별도signedzero 변조거부 실험은 전체572에 중복 합산하지 않는다. 이전0.209초와 문서초안0.222초는 최종근거로 사용하지 않는다. 보호132참조·기존20계약SHA·저장readiness SHA는 불변이고 이전 추적 코드·데이터·계약 변경0이다. 저장5 blocker 원형/적격계수와 신규core/test freeze SHA도 같았다. 이해자료 작성은 보존 근거를 읽었고 재실행하지 않았다.

다음 실제assess의 장면구성/연결지점과 provenance매핑 검토 후 판정동등성을 유지하는 최소선택적 연결adapter 설계·합성검증은 **PLANNED**다. 현재기존gate 통합·실자료준비도 재평가는 수행하지 않았고 과거원인을 소급추정하지 않는다.

## 보완: 저장 패치 통계와 연결 참여 scene 수의 구분

`backend/app/ml/readiness.py`의 patch 집계·scene 추가·연결 코드를 읽어 범위를 명확히 했다. `patch_count`는0에서 시작하고 적격 조건을 만족한 patch만 증가한다. 이후 `scenes.append(..., eligible_patches=patch_count)`는 patch_count>0을 추가 조건으로 두지 않으며 token/bbox union은 구성된 scenes 전체를 순회한다.

따라서 저장628·233·250, 합계1,111은 **적격 patch 통계**다. 이를 연결 참여 scene 수가1,111이라는 증거로 사용하지 않는다. prepared_payload=null로 역사적 scene 목록·개수와 실제0패치 scene의 존재 여부는 미확인이다. 코드는0패치 scene이 포함될 가능성을 허용하지만 이번 문서 작업이 실제로 그런 장면을 발견한 것은 아니다. 기존차단의 token/bbox 실제원인도 UNKNOWN_NOT_PERSISTED로 유지한다.

후속 선택적 adapter는 실제 assess의 장면구성·연결지점을 먼저 확인해야 한다. `eligible_patches>0` 필터를 임의로 추가하면 기존union 참여집합을 바꾸어 판정동등성을 훼손할 수 있다. 현재helper/envelope는 caller가 공급한 목록만 진단하며 과거목록을 복원하지 않는다. adapter통합·실자료재평가와0패치실재 여부판정은 이번 보완에서 수행하지 않았다.

## 기본 off의 내부 assess 관측 adapter

`readiness.assess(..., connectivity_diagnostics=False)`에 선택적진단을 연결했다. False는adapter호출/추가key없이기존결과를 유지하고, True만 원report완료뒤try안deepcopy로장면/정책/주연결/이미계산한참조를복사해 별도capture필드를 추가한다. 진단실패·복사본변조후raise도 원판정/분할/통계를바꾸지않는다.

0patch도포함해 실제append된scenes전체를 원순서로투영하며 patch합과scene수를구분한다. falsygroup양token역할skip/bbox유지·scene_id str규칙을보존하고 지원밖/custom순서·예산은capture미포착으로만표시한다. [Adapter Gate](gate-notes/GATE_CONNECTIVITY_ADAPTER_20261017.md)를읽는다. 내부선택연결은구현됐지만 실자료assess/on진단은재실행하지않았고 저장scene수/0patch실재·과거원인은UNKNOWN이다. CLI/API/UI·영속/envelope연결없음·공개화면계약없음으로UI변경은불필요하다.

기본off의 내부 `assess(..., connectivity_diagnostics=True)` 선택연결은 구현했고 합성 on/off 판정동등성과 격리를 확인했다. 실제전체자료 assess/on진단은 재실행하지 않았다. 실제확인은 기존저장report SHA동일·prepared_payload=null·새diagnostics부재·5 blocker 원형과 적격patch628·233·250 보존이다. 역사적union scene수·실제0patch scene존재·token/bbox 원인은 UNKNOWN_NOT_PERSISTED다.1,111은 저장patch통계이며 scene수가아니다.

최종 전체 `scripts/test.ps1`은 **589건 중588 PASS·1 SKIP/164.510초/종료0**다. SKIP은 기존 Windows symlink 생성 권한이며 deterministic 경계 시험은 통과했다. 관련17 PASS/4.605초·독립17 PASS/4.435초·별도graph200합성사례는 전체589에 중복 합산하지 않는다. 보호132참조·기존21진단계약SHA·저장readiness는 불변이다. 기존추적파일 중 의도한 변경은 readiness.py만이며 원본assess/나머지module/default_policy AST는 선택적진입·반환을제외하고 같았다. 실제저장보고서를 재생성하지 않았으며 이해자료 작성은 보존근거를읽고 재실행하지 않았다.

현재readiness.py의 raw bytes SHA는 `90b6b3a82c734c481c1477828c1630061ad495034cd38e950523e3a7a35fb4dc`다(32,867bytes·CRLF428개). LF정규화텍스트 SHA `2f70b1f3757186e24a24e3275dc36a6d6592e5c0560291af80eb4441a3b6d366`와 구분한다. Root의초기proof표기는 raw/정규화지문혼용을 정정한것이며 freeze뒤추가코드변경/AST결과변경이 아니다. 과거56/57보고서의 raw `42945e...`는 역사값으로보존하고 현재SHA로덮어쓰지 않는다. 과거snapshot의성공을 현코드로재실행성공/과거생성코드인증으로확장하지않는다.

다음 `scripts/run_experiment.py`의 기본off diagnosticflag·요약출력은 **PLANNED**다. 진단요청시 새출력경로로 기존report/입력 덮어쓰기를 막고 학습execute의 기본동작을 바꾸지 않는 합성검증을 계획한다. 현재 CLI노출·자동활성화·실자료gate 재평가는 수행하지 않았다.59envelope 연결은 요청시 별도검토다.

## CLI 진단옵션과 새 readiness 파일

`run_experiment.py`의 keyword-only `connectivity_diagnostics=False`와 `--connectivity-diagnostics`를 연결했다. off는기존호출·요약4키·write동작/execute체인을 유지한다. True는명시새readiness-output이필수이고 assess전입력/plan별칭·기존file/dir/link·root이탈/Windows ADS/device별칭을거부한다. assess후parent/target을재확인하고exclusive x UTF8로새파일만쓴다.

부분새파일쓰기실패는흔적을보존하고 원자적FS보장을하지않는다. summary의scene_count와patch합·NOT_REPORTED/null·학습권한false를구분한다. 명시execute후최종experiment report에는진단이자동전파되지않아별도readiness파일을읽어야한다. [CLI Gate](gate-notes/GATE_CONNECTIVITY_CLI_20261017.md)를참조한다. 실제는help노출만확인했고 실자료assess/학습은없다. 공개API/UI계약이없어UI변경·브라우저재검사는불필요하다.

기본 off의 `--connectivity-diagnostics`와 명시 새readiness-output 보호는 구현됐다. 실제 확인은 CLI `--help`1회 exit0·flag노출이며 실자료 assess/학습은 실행하지 않았다. 실제저장report SHA·5 blocker 원형·적격patch628·233·250은 그대로이고 역사적union scene수·실제0patch scene존재·원인은 UNKNOWN_NOT_PERSISTED다. 공개API/UI·59envelope 연결은없다.

최종 전체 `scripts/test.ps1`은 **608건 중607 PASS·1 SKIP/207.921초/종료0**다. SKIP은 기존 Windows symlink 생성 권한이며 deterministic 경계 시험은 통과했다. 관련19 PASS/4.770초·독립19 PASS/5.636초·별도14개 Windows path preflight는 전체608에 중복 합산하지 않는다. 보호132참조·기존23계약SHA·저장readiness는 불변이고 이전snapshot에 추적된 코드·데이터·계약의 변경0을 확인했다. run_experiment.py는 이전snapshot 추적대상에 없었으므로 별도명시preflight baseline의 raw0e3ae0...→현재a1b372... 변경으로 증명했다. 이를 전체workspace변경0이나 oldtracked변경1로 표현하지 않는다. script/test freezeSHA와 기존execute gate이후training/resume/infer tail AST는 같았다. 이해자료 작성은 보존근거를읽고 재실행하지 않았다.

다음 새출력 보호·입력SHA·자원계획을 확인한 뒤 학습없는 실자료 readiness진단 범위를 정하거나 읽기진단 envelope연결을 검토하는 작업은 **PLANNED**다. 현재 실자료재평가를 수행/자동승인한 것이 아니며 기존보고서를 덮어쓰거나 과거원인을 추정하지 않는다.

## 현재 실자료 준비성·연결 관측1회

[실자료 관측 Gate](gate-notes/GATE_READINESS_REAL_DIAGNOSTIC_20261017.md)를기준으로이번실행과과거보고서를구분한다.

실제 CLI를 학습/재개/다운로드 없이1회 실행해 exit0·70.437초에 새진단보고서를 생성했다. 현재 CAPTURED_COMPONENTS_MATCH이며 append scene1,384개·0patch scene273개·적격patch1,111개(628/233/250)를 구분했다. 기존보고서와 assessed_at/새diagnostics 외 모든typed값·5 blocker·4,335 verified_files기록은 같다. 기존report는덮어쓰지 않았고 전체gate는BLOCKED다. 이번실제assess는 기존영상/라벨hash·픽셀QA를 수행했으며 pureadapter의추가IO0을 전체CLI무IO로확장하지 않는다.

현재 scene_id 토큰 `S2A_MSIL2A_20210812T025551_R032_T48MXT_20210812T132431`의 직접cross-split event는 West Java/test의 내부scene1096(0patch)→Banten/val의scene303(1patch)다. 같은토큰 전체회원은28scene 모두scene_id역할이며 Banten16개는전부1patch, West Java12개는0patch3개/1patch9개다. **양쪽에양수patch장면도있어 첫0patch event가충돌이0patch에만한정됨을뜻하지않는다.** 내부sceneindex를원본manifest행번호로단정하지않으며 삭제/필터후차단해소 counterfactual은검증/승인하지않았다. 현재관측은과거생성원인·회원/scene수의소급인증이아니고 역사근거는UNKNOWN_NOT_PERSISTED로유지한다.

현재helper는957,036 bbox쌍/2,768 token을처리했고 event15,019개(token2,595+bbox12,424)중10,000개를저장해5,019개가생략됐지만 union_complete=true다. 독립graph/BFS 검토가현재전체projected JSONmetadata에서모든계수·첫10,000필드·component를대조해 cross-split bbox0/token1을확인했다. 이는잘린prefix만의추론도 원본영상/정확기하독립성검사도아니다. 문서validation20항목은새unittest20개가아니다.

생산코드변경0·보호132참조/24코드계약SHA·기존savedreport/원장/lock/분할/모델은불변이다. 새보고서는11,132,483bytes·SHA `95f7622ac72ef6a3d43aafc35a3607a4e9f39ed2912ac01280a07cc62c854e35`다.135회표본의peak tree RSS214,724,608B·감시기준timeout600초/RSS2GiB·중지없음은관측값이며 hard memory cap/순간최대보장이아니다. **이번62단위새unittest/full회귀실행은없다.**608건607 PASS·1 SKIP/207.921초는직전61코드단위로그이며 실제CLI1회/독립JSON검증을거기에합산하지않는다. 이해에이전트는보고서만읽고실행·독립계산을재수행하지않았다.

다음 고정원본manifest의명시province/scene_id/source_group·참조SHA와현재내부event를대조하는 읽기lineage trace는 **PLANNED**다. 동일product전체회원·중복/모호함을기록하고 index를원본행으로추정하지않는다. 재assess/원본영상IO·삭제/필터·정책/분할변경없이진행한다.

## 현재 token회원과 원본metadata 후보집합 조회

`readiness_connectivity_lineage.inspect_readiness_connectivity_lineage`와 CLI는 고정report/aggregate 두JSON만 읽어 caller literal token을 전체projected/rawrow에서 찾는다. missing-key fallback과scalar/falsy규칙을 보존해 literal회원과active token참여를 구분한다. source113manifest·영상/stat/hash·assess/helper는 실행하지 않는다.

실제query는report/raw active28(Banten16/WestJava12), candidate link400/고유raw28이며 모든28report장면이 AMBIGUOUS_MATCH_SET이다. 같은순번·행수·정렬을 근거로단일원본행을 고르지않는다. UNIQUE후보1개도파일/정확row인증이아니며 image_path/patch_sha256는선언값만출력한다. [Lineage Gate](gate-notes/GATE_CONNECTIVITY_LINEAGE_20261017.md)를참조한다. cap전전체계수·저장계수/절단을분리하고 원본/정책/분할·5차단/BLOCKED를유지한다. 내부읽기CLI/APIUI계약불변으로UI변경은불필요하다.

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

staging은metadata준비이지raster복사·assess/준비성QA·학습·Registry등록이아니다. qa_status NOT_PERFORMED/readyfalse이며원본5차단을후보차단수로옮기지않는다. 다음73의동일정책기존CLI noexecute/noresume+diagnostics·새readinessoutput후보 QA1회는PLANNED다. 새API/UI없는내부CLI라화면변경은불필요하다.

### 72실제metadata준비·회귀/보존과다음QA설계

Root 실제 CP949 CLI1회 종료0으로 DATA새경로에candidate JSON53,247,999bytes/SHA2ff7be093db3930d99f10cdc7687809222ef7f525ec6e9cf6248ec144725d158를동일바이트로복사했다. stagingreceipt는3,675bytes/SHAb8224cb3eb5c5ef0accf0cab10359401d792719e6fd8cae0b610279e759404dd다. 독립stream SHA/size·핀/참조·17false를대조했고최종재대조도불변이었다. 후보1368행/원본1384행·후보projected1095/원본적격1111을구분한다. QA는NOT_PERFORMED/후보준비성NOT_ASSESSED이며후보차단수는모른다. 원본저장5차단은그대로고영상/라벨복사·assess·QA·등록·훈련은없다. 실제runtime은계측하지않아초수를주장하지않는다.

최종 전체 scripts/test.ps1은 **725건 중724 PASS·1 SKIP/338.008초/종료0**다. 기존 Windows symlink 생성권한 제약1개를 건너뛰었고 deterministic 경계 시험은 통과했다. 관련19 PASS/23.740초·독립19 PASS/25.510초는 전체725에 중복 합산하지 않는다. 보호137참조(이전134+71패키지3)·30기존 코어SHA와 카탈로그14기록 canonicalSHA가 불변이며 이전 snapshot 추적 backend/scripts/tests/data/frontend 변경은0이다. 신규코드/문서·staging파일은 있으므로 전체workspace변경0은 아니며 원자snapshot/전체inventory 보장도 아니다.

다음73은PLANNED다. stagedcandidate·stagingreceipt·정책의외부SHA와명시새QA출력을고정해기존run(execute=False,resume=False,connectivity_diagnostics=True)을호출하는작은guard가남았다.72fullplan재계산을필수중복하지않으며역사동일정책자동확인은oldreadiness4번째JSON과effectivepolicy={**default_policy(),**policy} typed대조가필요하다. QA BLOCKED도정상검사완료일수있고예외/입력변경이면새report보존/완료receipt없음으로설계한다. guard/후보 QA는현재미구현·미실행이다.

## 고정후보·동일정책의학습없는QA guard — 73

[후보readiness QA Gate](gate-notes/GATE_CANDIDATE_READINESS_QA_20261017.md)는candidate/stagingreceipt/policy/oldreadiness 네외부핀을strict검증하고effectivepolicy default+caller전체를oldpolicy와typed대조한뒤기존run을executeFalse/resumeFalse/diagnosticsTrue로호출한다. source참조는old원본/candidate새입력을구분하고실자료바닥/labelsignature를유지한다. 새readiness보고서와반환객체·4핀/상태/계수/capture를대조후QA완료receipt를마지막에쓴다.

QA BLOCKED도정상검사완료일수있지만receipt실행/과학/등록승인은false다. guard후단16MiB는run내부전체IO/RAM/출력쓰기하드cap아니며실제assess는영상/라벨을읽고hash/QA한다.72의미검사는당시이력이며73실제최종결과전에는후보차단수를추정하지않는다. 새API/UI없는내부QA-onlyCLI라화면변경대상은없다.

### 73실제후보 QA·회귀/보존과후속비교계획

Root 실제 wrapper1회는 종료0/202.344초·RSS표본197회최대532,074,496B·중지없음이었다.600초/2GiB표본중지기준이며OS하드cap은아니다. 새후보보고서11,842,410B/SHA847343e1…와qaReceipt3,030B/SHA7b5ea8bb…를생성했다. QA_COMPLETED지만관측gate는blocked/readyfalse·적격1095=628/217/250·1368장면/verified_files4285·CAPTURED_COMPONENTS_MATCH다. 후보차단은4개로train/val/test class7불균형3개와val/class7 209픽셀부족1개이며원본5차단보고서는불변이다. 원본의SHARED_SOURCE_CROSSES_FIXED_SPLIT항목이이번후보보고서에는없지만누출완전해소·공간/표본독립·원본인증/과학승인뜻은아니다.

Root JSON독립대조에서동일policy/signature·원본class관련4차단과후보차단전체typed일치·공통verified4284개SHA/kind동일을확인했다. 새verified1개는stagedcandidate이고기존기록51개는후보목록에없다. bbox935028쌍/관측fixedsplit conflict0·완전선언identity1368은현재diagnostic범위다. bare픽셀train1418/val209/test1025와bare기여patch각0은그대로라클래스대표성부족이남는다. 실제assess는영상/라벨read/hash/QA를했고purediagnostic추가IO0과구분한다. 정식Dataset준비/Registry·학습/추론·정산/재개는0이며receipt권한false다.

최종 전체 scripts/test.ps1은 **744건 중743 PASS·1 SKIP/356.067초/종료0**다. 기존 Windows symlink 생성권한 제약1개를 건너뛰었고 deterministic 경계 시험은 통과했다. 관련19 PASS/12.065초·독립19 PASS/12.236초를 전체744에 중복 합산하지 않는다. 보호139참조·31기존 코어·네입력핀SHA와 카탈로그14기록 canonicalSHA가 불변이고 이전 snapshot 추적 backend/scripts/tests/data/frontend 변경은0이다. 신규코드/문서·QA파일은 있으므로 전체workspace변경0은 아니다. 원자snapshot/전체inventory를 보장하지 않는다.

다음74는PLANNED다. old/newQA·qaReceipt·stageReceipt 네JSON/네callerSHA의읽기전용비교projection/API계약과web_ui수동비교카드·실제브라우저확인을검토한다. 자동assess·자동POST는없다. old보고서미저장physical장면수는null로두고stage선언1384/1368·newdiag관측1368을각각구분하며patch1111로장면수를추정하지않는다.

## 원본·후보저장QA의명시비교 — 74/75

[후보 QA비교 Gate](gate-notes/GATE_CANDIDATE_QA_COMPARISON_20261017.md)는old/newQA·qaReceipt/stageReceipt 네고정JSON/외부4SHA만읽어최소비교projection/API와LCLUConly수동카드를연결한변경이다.2KiB본문·report16MiB/receipt64KiB·깊이32/finalpins·no-store/process-localworker1을사용하며source/candidate거대manifest/raster/assess/Registry는호출하지않는다.

원본1111/5차단→후보1095/4차단, class7코드빈도3+val209부족1과나지1418/209/1025·기여patch0을함께표시한다. oldphysicalnull NOT_PERSISTED·stage선언1384/1368·후보 QA캡처1368은각출처를구분한다. 공유항목후보미관측≠완전누출해소/독립승인이며10false권한을유지한다. 입력/선택/hash/popstate/세대는이전결과를무효화하고표시중단은서버취소가아니다. 실제API/브라우저근거전에는실행서버반영완료로주장하지않는다.

### 74/75최종실제적용·회귀/보존

Root실제API8002는200/2161bytes·no-store로1111→1095/5→4·코드빈도3·bareval209/기여patch각0·oldphysicalnull/선언1384→1368/후보캡처1368·10false를대조했다.409/400/413과GET405프레임워크별도/경로비노출도확인했다. UI5174 LCLUC evidence에서명시조회·입력clear/409·허브왕복/back-forward-back이전결과제거/수동재조회를확인했다. desktop1449×1087에서수평넘침0이며이번모바일실측은없다. 기존5173적용검증으로확대하지않는다.

초기React형제카드중복key로console오류6건과header정렬문제를발견해candidate-qa:namespace/React siblingkey회귀·scopedflex-start로수정했다. 수정후reload/수동조회·경합흐름을재확인했고2026-10-17T08:24:15UTC이후새console오류0이다. 이전6건은별도보존하며수정전UI12/전체71/build17.63초·독립12/804.0825ms와최종13/72/build18.69초·독립13/382.2987ms를시점별구분한다.

최종backend전체는 **761건 중760 PASS·1 SKIP/398.767초/종료0**다. 기존Windows symlink생성권한 제약1개를 건너뛰었고 deterministic경계시험은통과했다. 관련17 PASS/14.400초·독립17 PASS/17.124초와 최종신규UI13 PASS/460.2888ms·독립최종13 PASS/382.2987ms·전체UI72 PASS/1137.5072ms·build75modules/18.69초는범위를분리해backend761에합산하지않는다. 보호141참조·32기존코어SHA와카탈로그14기록canonicalSHA가불변이며이전추적코드/데이터/프론트중의도한main배선/AgentCenter두파일만변경됐다. 신규파일/문서/evidence도있어전체workspace변경2개라는뜻이아니고원자snapshot보장도아니다.

다음76은PLANNED다. 고정후보 QA보고서·정책에서분할별나지요구픽셀/기여patch부족을산출하는읽기전용후속데이터요구계약을검토한다. 실제이를충족할새영상/라벨/장면목록은없으며최소추가량만으로준비완료를보장하지않는다. 현재설계대기·미구현이고새수집/학습은없다.

## 저장나지부족조건의읽기진단 — 76

[나지요구조건 Gate](gate-notes/GATE_BARE_CLASS_REQUIREMENTS_20261017.md)는고정후보 QA한보고서/외부SHA의저장배열을읽어split픽셀바닥/기여patch/비율/전체balance를분리한다. 순수build는caller선언pin, reader는16MiB/depth32 strict/finalpin으로실제bytes를확인한다. 기존purebalance_diagnostics재계산과storedwholetyped일치는현재raster/assess재검증이아니다.

저장bare픽셀1418/209/1025에서256바닥부족0/47/0, 기여patch0에서최소5부족5각, bare비율은9클래스픽셀합을분모로최소.005미만이다. dominance.9충족과별개로부족이남는다.47픽셀이나새15patch만으로준비완료보장/장면·다운로드량추정은하지않고정확라벨/기하/독립성/전체gate미검증false다. 새API/UI없는내부CLI라화면/프론트/브라우저변경검사는불필요하며기존후보4차단을유지한다.

### 76실제저장요구조건·회귀/보존과다음대기열

Root 실제CP949 CLI1회는종료0·5,367bytes/SHA8a0004aa2d67af8c97e32173f90c56c97449e54317ef86420489eb1bbaee7542를생성했다. 생산helper없이먼저계산한독립산술의모든split/분모/ratio/dominance/failures필드와타입·값이같았고report핀은보존됐다. 저장bare1418/209/1025의256픽셀바닥부족은0/47/0, 기여patch0각의최소5부족은5각이다.9클래스합분모의bare비율은약0.003532%/0.001494%/0.006307%로정책0.5%미만이고dominance.9조건은모두충족했다. 현재raster/새QA가아닌저장통계산술VERIFIED_REAL범위다.

47픽셀만추가하거나새15patch를수집하면준비완료라는결론은내리지않는다. ratio차이는픽셀수가아니고미래자료는분모도바꾼다. 실제새영상/라벨/장면목록과정확라벨·품질/기간/경계·기하/독립성검증은없다. requirements_are_full_gate/ready/수집학습승인false·refund0/exactlyonceUNKNOWN이며기존후보4차단/원본5차단을유지한다. 새QA/수집/학습/Registry는없고API/UI없는내부CLI라화면변경·프론트재시험·브라우저확인은필요없다.

최종 전체 scripts/test.ps1은 **775건 중774 PASS·1 SKIP/332.522초/종료0**다. 기존Windows symlink생성권한 제약1개를 건너뛰었고 deterministic경계시험은통과했다. 관련14 PASS/5.019초·독립14 PASS/5.679초와별도독립산술은전체775에중복합산하지않는다. 보호141참조·34기존코어SHA·고정후보 QA보고서와카탈로그14기록canonicalSHA가불변이고이전snapshot추적code/data/tests/frontend변경은0이다. 신규코드/문서/evidence는있으므로전체workspace변경0이나원자snapshot보장이아니다.

다음77은PLANNED다. 제출때고정한ordered input binding과실행전달binding을id/version/SHA/role/index·Job/Agent/Trace로대조하는순수guard를검토한다. 기존등록/resolve·제출snapshot·currentlineage와구별하며정확schema/원문연결은아직미확정이다. 실제executor/등록쓰기·READY우회는없고일치도실행승인이아니며현재resolver/실제bytes확인은후속이다. 나지충족자료/정확라벨·학습차단해결은계속미완료다.


## 108 저장 나지 총량과 미래 수집 구분

고정 후보 QA JSON의 저장 통계만 읽어 가능한 기여 수 범위를 계산한다. train0..5/val0/test0..4와 저장0은 양립한다. 필요총량 차이val1071/test255는 같은 적격 집계의 산술 조건이며 미래 영상·픽셀·패치·다운로드량이 아니다. 새 자료는 분모·적격성·품질을 바꾸므로 이 값으로 수집을 지시하지 않는다. candidate의 예비 class 통계를 최종 QA per-patch 분포로 연결한 증거가 없어 사용하지 않았다. 수집 복구 다음 제안은 PLANNED이고 terminal2쌍 부재/예약136314880B·환불0을 유지한다.



## 110 복구 단계 메모와 실제 파일 적용

새 helper는 원장/aggregate/run-result의 before·expected_after·observed SHA 선언만 비교한다. 실제파일을읽거나settle/commit하지않는다. 최초PREPARED·인접전이·전체동일재관측만허용하고누락증거를채우지않는다. 기존collector finalize의settle→aggregate저장→run저장과이미settled재정산거부는그대로다. journal/원자적coordinator는후속이고실제missing두배치미적용·예약136314880B·환불0을유지한다. before==after도가능하므로선언일치가실제쓰기증거는아니다.



## 111 공통 Registry 등록 연결과 실제 재고의 범위

register_collection의 --registry-manifest 선택 경로가 image/label/quality SHA와 직접 부모를 확인한 뒤 기존 immutable DatasetVersion Registry에 연결된다. RAW/STAGED document만 허용하고 legacy datasets를 동시에 쓰지 않는다. 기존 옵션 없는 경로는 원문 대비 보존한다. 운영 등록은0이며 성공은 TempStore다. Store 초기화·등록 쓰기는 있으므로 CLI 전체가 읽기 전용은 아니다. 전이 전체DAG·기관ACL·불변자산복사는 별도다.

실제 metadata상6주×2020~2025의36셀 모두 적격행이 있으나 주전체coverage/계절대표성/새rasterQA가 아니다. 원본1384/적격1111·628/233/250과 후보1368/1095·628/217/250을 구분한다. Southeast Sulawesi2024는1개다. missing두배치·예약136314880B·독립라벨미제공·후보4차단은 유지한다.



## 115 입력 Registry와 실제 실행의 연결

새local CLIcore는2~6개연차의고정input_ref를현재resolve하고VALIDATED/PUBLIC raster·연도·band명·quality report SHA를확인한다. caller경로를받지않으며첫gate차단이면runner/claim0이다.111의RAW/STAGED수집document등록만으로이실행품질조건을통과하지않는다. 품질메타데이터와문서지문이실제과학품질/기관ACL인증은아니다. 운영자료등록/새수집·현재원본실행은하지않았고예약/원장·후보4차단을유지한다.



## 116/117 — LCLUC 수동 실행·조회 API와 화면

116/117의 입력은 고정 Registry 참조와 품질보고서 SHA다. 기존 위 지역·연도 필터에서 파일 경로나 입력 ID를 추정하지 않는다. 보고서와 산출물은 같은 저장 실행의 허용목록으로만 읽고 전송 복사 바이트 SHA를 재검사한다. 과거 성공 읽기는 현재 자료 품질·기관 ACL 재승인과 다르다.


## 118 — 검증된 선택 변화쌍 지도

지도는 기존 저장 산출물 index와 SHA로만 읽는다. 새 영상 수집·픽셀/라벨 QA·원본 재투영이나 Dataset 등록을 하지 않는다. WGS84 좌표 범위·도형 구조를 검사하지만 자기 교차·구멍의 관계·공식 경계/출처 권위는 검증하지 않는다. 8MiB stream 상한은 지도 payload 범위다.


## 119 — 전체 래스터 전이행렬·범례·단위

119는 이미 받은 보고서의 전체 유효 래스터 통계만 로컬 검산한다. 새 raster/label/GeoJSON GET나 수집은 없다. 지도 벡터는 최대5000개 subset일 수 있으므로 행렬·면적을 벡터 합으로 추정하지 않는다. 새 공간 면적 재계산 없이 m²→ha 표시 변환만 한다.


## 120/121 — 고정 모델의 오류분석 읽기

120은 기존 모델의 checkpoint/report/오류3파일을 고정 SHA와 경로로 읽는다. 누락 파일을 생성하거나 모델 version 선언을 추정/역채우지 않는다. 참조가 약한 라벨이면 오류율은 그 참조와의 일치도이며 새 독립 라벨 확보/평가가 아니다. CSV는 검증한 원문 바이트를 유지한다.


## 122 — per_scene 정규화 선언 계약

122는 source_scene·normalization·evidence의 제품 ID/밴드/보정 수치 선언만 비교한다. 경로/URL/SHA는 문자열 형식이며 파일·네트워크를 읽지 않는다. 기존 ML verifier의 실제 영상/evidence/source_metadata SHA 대조와 별개다. source attribution은 기관 출처 인증으로 승격하지 않는다.


## 123 — per_scene 세 역할 파일 지문 대조

123은 evidence SHA·strict JSON→122 선언 비교→image/원metadata SHA의 순차 snapshot이다. 읽기 전후 path/fd/stat를 검사하지만 세 역할 동시 원자 snapshot은 아니다. URI를 fetch하지 않고 root/상대경로의 link/alias를 거부한다. mapped drive의 물리적 네트워크 여부까지 보장하지 않는다.


## 124 — 실제 checkpoint manifest와 고정 모델 참조

124가 모델 장부와 실제 모델 파일의 manifest를 연결했지만 DatasetRegistry와123 장면 파일·전연차·품질mask를 연결한 것은 아니다. Temp 수동 조합과 제품 실행 회로를 구별한다. checkpoint/report는 별도 순차 snapshot이며 Store와 동시 원자 시점을 보장하지 않는다.


## 125 — 등록3참조와 명시 장면 파일

125는 image/evidence/metadata3참조를 dataset_versions에서 읽고 canonical identity/SHA를 검사한다. source.scene_id/band_names와 evidence 직접lineage2역할은 내부 소비 계약이며 기관 표준 추가가 아니다. 제품군 이름에서 scene을 추정하거나 checkpoint의 밴드를 source 선언으로 복사하지 않는다. 명시 필드 없는 legacy는 역채움 없이 BLOCKED다.


## 126 — actual 모델과 등록 단일 장면 결합

126은 actual 모델manifest와 등록 한 장면3참조를 내부 자동 결합했다. 운영 DatasetVersion은03:09 count에서0개이며 Temp 성공을 운영 확보로 계산하지 않는다. 전연차·품질보고서/mask·다른 계보 부모 검증과 물리적 장면 확인은 후속이다.


## 127 — 요청2~6연도 순차 읽기

127은2~6개 요청 연도 라벨과 고정3ref를 순차 읽는다. 등록 manifest/header의 실제 연도와 아직 결합하지 않으며128 후속이다. 다른 image ID/version도 동일 물리파일/SHA alias일 수 있어 자료 독립성·시공간 대표성을 증명하지 않는다. 운영 DatasetVersion0은 그대로다.


## 128 — 등록시간과 요청 UTC연도 결합

128은 같은 image Registry record의 temporal start/end 전체를 Gregorian UTC 요청연도 안에 포함시키는 새 내부 소비 정책이다. 기관/upstream 표준 변경이 아니다. 등록 날짜 선언과 실영상 취득일/header·grid/mask·물리 장면 독립성을 구분한다.


## 129 — 실제 GTiff header와 장면간 격자

129는 실제 bytes SHA·TIFF magic 뒤 MemoryFile GTiff header를 읽는다. 밴드 설명·크기·projected metre/affine·유한bounds와 장면 간 exact grid를 검사하지만 pixel/mask 배열·QA통계는 읽지 않는다. Registry bbox와 실제 extent 관계는130 후속이다.


## 130 — 등록 bbox와 표본화 영상 envelope

등록bbox가 actual header bounds를 densify21로 변환한 경위도envelope를 포함하는지 검사한다. 큰bbox가 통과해도 실제지역 coverage·유효픽셀·정확footprint가 아니다. 날짜변경선/극지를 제한하는 새 내부 소비 정책이며 기관 표준을 바꾸지 않는다.


## 131 — 등록 품질보고서와 명시 mask 파일

131은3record의 canonical/ref/type/PUBLIC을 파일 전에 확인한다. 보고서lineage의 image/mask각1pin과 image.quality_report_ref 경로가 report URI와 같아야 한다. 없는legacyref·빈{}를 추정/생성/역채우지 않는다. 새 exact5형식과 role은 내부 소비계약이며 기관 공식표준이 아니다.


## 132 — 실제 영상과 mask header·격자

132는131 등록/보고서/파일 성공 뒤 image64MiB·mask16MiB를 재스냅샷·SHA 확인해 header를 읽는다. 같은get canonical copy를 쓰고 get은총3회지만 두 자산파일은각2회 읽는다. 원자snapshot·모든경쟁 제거가 아니며 운영자료를 수집/생성하지 않는다.


## 133 — 명시 이진 마스크 값과 품질 승인 구분

133은 파일을 생성·수정하지 않는다. 같은 get의 명시 source.mask_semantics를 읽고 mask16MiB를 재스냅샷·SHA/header 대조한 뒤 band1을 한 번 읽는다. 정상 경로는 get3, 영상2회·mask3회 파일 읽기다. nodata/internal mask·255/SCL은 거부하고 자동 변환하지 않는다. 순차 snapshot·Store 원문 predecode·CPU/RSS 한계는 남는다.


## 134 — 연차 공간·명시 마스크 관측과 등록 지문 연결

134는2~6연도·각6키의 모든 참조를 I/O 전에 사본으로 고정한다.130 전체를 읽은 뒤 각133을 수행하며 이미 얻은 image manifest SHA로만 연결한다. 누락 digest를 추정하거나 추가 조회로 역채우지 않는다. 등록 metadata만 바뀌어도 파일 지문이 같다는 이유로 통과시키지 않는다. 순차 읽기는 원자 snapshot이 아니다.


## 135 — 명시 분수 기준의 연차 계산과 공식 승인 구분

135는 정책과 모든 연차 요청을 Store 전에 검증해 사본으로 만든다.134의 실제 파일·계수 관측은 그대로 재사용하며 정책 계산 때문에 추가 파일/DB/픽셀 읽기를 만들지 않는다. 잘못된 계수로 정책을 계산하지 않고 자료를 자동 보정·생성하지 않는다.


## 136 — 제한된 요청과 경로 없는 내부 안전 요약

136의 exact6 요청은 고정 참조·정책만 받고 임의 경로·manifest·실행 명령은 받지 않는다. bytes16KiB·depth16·node4096·text512·int53 한도와 duplicate/float 거부 뒤 전체 요청을 I/O 전에 검사한다. runtime 한도는 하위 파일/DB 전체 자원 hardcap이 아니다.


## 137 — 필수 인증 수동 API와 모델 화면의 연차 진단

137 수동 POST는 고정 참조만 받고 새 자료를 생성하거나 보정하지 않는다. 인증·media·body 초과는 Store 접근 전에 거부한다. 유효 진단은136 이하의 실제 파일 읽기를 수행하므로 입력 제한이 전체 파일·메모리 hardcap은 아니다. 원본·원장·예약은 보존한다.

## 다음 읽기 설계 — 품질 report 생산자의 공백 (PLANNED)

실제 수집 코드에는 마스크 쓰기가 있지만 새 소비 계약의 producer 완료를 뜻하지 않는다. collect_samples.py는 SCL/배열 nodata를 조합하고, collect_training_grid.py는 AOI·label!=0까지 결합해 각각nodata0 마스크를 쓴다.133은 명시 binary_validity와nodataNone/all_valid를 요구하므로 기존 마스크를 그대로 승인하거나 의미를 소급 선언하지 않는다. 두 코드에서 명시 LCLUC_QUALITY_MASK_EVIDENCE/source.mask_semantics 생산과 실제6밴드 description 설정은 확인하지 못했다. 운영 header는 열지 않아 현재 운영 파일이 어떤지 확정하지 않는다.

다음138 후보는 caller가 고정한 manifest에서 exact5 보고서 바이트/SHA와 미등록manifest/ref 초안만 만드는 순수 준비 함수다. Store·파일쓰기·운영등록 없이131 소비계약과 임시 호환을 검증하고 RAW/STAGED를 유지한다. 자동VALIDATED·QA·실제producer전체완료를 주장하지 않는다. 아직 설계만 있으며 구현·실행은0이다.


## 138 — 보고서 바이트·미등록 초안 준비와 별도 출처 메타데이터

138은 producer 전체가 아니라 보고서 초안 준비다. input SHA는 caller 선언이고 파일을 읽지 않는다. RAW/STAGED와 기존 access 선언을 보존하며 임의VALIDATED·출처 복사·기존mask 의미 역채움은 없다. 별도 report 메타데이터·실제 파일쓰기/등록과 기존nodata0의 파생mask 문제는 후속이다.


## 139 — 명시 report 메타데이터의 완성 초안과 실제 등록 구분

report metadata는 정확한5개 필드로 caller가 제공한다. source·시간·공간을 image에서 발명/자동복사하지 않는다. 원 report bytes는 유지하며 초안을 완성하지만 실제파일·Registry·기관출처를 검증하지 않는다. 새 경로 writer·등록·수집기 연결·기존mask 변환은 후속이다.


## 140 — 두 새 출력의 배타적 저장과 부분 실패 보존

두 새 output은 같은 기존 parent에만 쓴다. mkdir·overwrite·delete·자동 retry·replay는 없다. 원 image/mask는 열지 않으며 caller 선언과139 기대 사본에서 쓸 bytes를 만든다. 원본과 원장을 바꾸지 않고 파일별 write/readback 이력을 남긴다.


## 141 — 저장2파일 등록 전 읽기와 schema 확인

141은 writer를 호출하지 않고 기존 보고서2파일만 읽는다. 복사 바이트가 expected와 정확히 같아야 하며 저장 JSON을 재해석해 선언을 바꾸지 않는다. 원영상·마스크는 열지 않고 cold 로컬 schema 읽기는 추가될 수 있다. 등록은 다음 별도 경계이며 이번 함수가 Store에 접근하지 않는다.


## 142 — 보고서1버전 명시 등록과 결과 미확정 구분

보고서만 등록하며 기존 source2개를 생성하거나 수정하지 않는다. resolve로 원영상·mask 파일 전체 SHA를 읽지만 native header·pixel은 검사하지 않는다. 보고서2MiB 한도를 원본 파일 전체 상한으로 과장하지 않는다. 없는 quality_report_ref를 기존 버전에 자동 patch하지 않는다.

142의 확정 시험·보존 범위는 집중 10 PASS·관련 79 PASS·독립 12 PASS/1 SKIP이다. 실제 등록은 Temp에 한정하며 운영 DatasetVersion 0·후보 차단 4개·미승인 상태를 유지한다. 상세 시간과 초기 시험 구성 오류는 Gate142에서 구분한다.


## 143 — 명시 CLI의 점검·등록과 종료 코드 구분

호출자가 네 JSON 파일과 절대 data_root, manifest 상대 URI를 모두 지정한다. JSON은 각각 256KiB 이내로 strict UTF-8·중복 key·비유한 값·깊이·builtin 사본을 검사한다. inspect는 DB 없이 141만 호출한다. register는 기존 catalog/records를 읽기 전용으로 확인한 뒤 정상 Store 생성자와 142를 호출한다. 원영상·mask의 전체 SHA 읽기는 등록 경로에 남으며 JSON 상한을 전체 자료의 자원 상한으로 확대하지 않는다. source의 누락 quality_report_ref나 제한된 접근 선언을 자동 보정하지 않는다.


## 144 — 새 수집 영상의 밴드 설명과 scene mask 선언

collect_windows가 새로 쓰는 영상에 실제 asset 순서대로 band description을 넣고, 새 scene mask를 uint8 0/1·nodata=None·binary_validity로 기록한다. 유효 조건은 모든 밴드의 finite와 nonzero이며 기존 SCL 제외 코드와 nearest 정합을 유지한다. 기존 SHA 확인 뒤 skip되는 산출물·row는 재작성하거나 누락 선언을 역채우지 않는다. raw crop·예산/원장·resume 정책은 그대로다. collect_training_grid의 label+AOI mask는 이번 변경 대상이 아니다.

144의 확정 보존 범위는 기존 snapshot 326개와 Git 고정 수집기 원문 한 개를 합친 소스 327개 중 수집기만 변경·326개 불변이다. 보호 141개·이전 증거 1381개·운영 catalog/예약을 보존했고 운영 수집·등록·학습·추론은 실행하지 않았다.


## 145 — 패치 밴드 설명 전파와 학습 지원 mask 구분

materialize_patches가 새 patch image에 원 image.descriptions의 None 아닌 값만 원순서로 전파한다. None·unknown·뒤바뀐 순서는 추정하거나 수정하지 않으며 label/quality description에는 전파하지 않는다. patch의 quality는 scene QA·AOI·label!=0·영상 finite/nonzero를 결합한 기존 값이다. 원 report는 그대로 두고 반환 row의 순수 quality_mask_semantics를 제거한 뒤 training_support_mask_semantics를 별도로 기록한다. 원본·source_window·기존 split/threshold/예산·원장 정책은 바꾸지 않는다.

145 최종 전체는 1431 PASS/1 SKIP이며 tracked source 431개 중 허용 grid 한 개만 변경·430개 불변이다. 보호 141개·이전 증거 1399개·운영 catalog/예약 보존과 운영 호출 0을 확인했다. 기존 frontend 271건은 이번 재시험 결과가 아니다.


## 146 — 완성 source manifest 한 개의 명시 등록 CLI

register_dataset_version.py는 호출자가 완성한 manifest 한 개와 기존 절대 data_root를 명시해 source raster 버전 하나만 등록한다. RAW/STAGED raster subset·96 전체 schema·실제 파일 SHA와 기존 DB를 확인하지만 metadata·원본 파일·DB를 자동 준비하지 않는다. 142/143 report 등록에 필요한 source 두 버전을 별도 명령으로 준비할 수 있게 하며 quality_report_ref나 기관/시간/공간을 추정·역채우지 않는다.

146 최종 검증은 집중 12 PASS/1 SKIP·관련 126 PASS/1 SKIP·독립 10 PASS/1 SKIP이다. 새 CLI의 DB/sidecar·같은 파일 alias 거부를 보강했고 기존 소스 432개·보호 141개·이전 증거 1416개·운영 catalog/예약을 보존했다. 실제 운영 등록은 없다.


## 147 — GeoQuery의 수동 local LCLUC workflow 근거 조회

GeoQuery evidence의 별도 패널이 명시 workflow ID의 status/report만 읽는다. 각 body는 8MiB stream·strict UTF-8/중복 key/비유한 수/깊이 경계와 SHA를 확인한다. 원본·Registry·보고서·collector를 새로 만들거나 수정하지 않는다. 같은 receipt/report의 전체 래스터 통계와 별도 수동 지도 vector subset을 구분한다.

147 최종은 집중9·독립7·front280·build116·backend관련34 PASS이며 실제 main Temp 브라우저와 운영5174 빈ID/disabled 적용을 확인했다. 운영 workflow GET·학습·추론은 0이고 LLM/RAG 연결 완료가 아니다. 지연 경쟁은 단위 시험, 브라우저 중단/뒤로 가기는 응답 완료 후 확인한 범위다.


최신 가용성 정정: 재개 후 재조회에서 기존 API 8000/8001/8002·Temp API8003·frontend5174/5180의 이전 세션은 관측되지 않았다. Ollama만 남은 상태에서 frontend5174만 hidden detached PID34484로 복원했고 API는 Store 복구 부작용을 피하려고 재시작하지 않았다. 따라서 앞선 실제 main Temp 브라우저 PASS와 운영5174 적용 확인은 당시 이력이며 현재 API 서비스 정상 가용성으로 표현하지 않는다. 세션 종료 원인과 Temp fixture 정리 여부는 미확인이다. dev-server-after JSON의 기록 시각은 09:39:17이며 재보존 감사는 09:39:32이다. 원래 사용자 탭 URL 보존과 API offline 상태도 구분한다.

## 148 — 멈춘 수집과 다른 작업의 계속

멈춘 것은 반텐2023·서자바2023의 추가 공간창 각1개다. 밴드가 일부만 남았고 종료 보고서가 없어 완성 패치로 세지 않는다. 기존1384개 패치 전체가 유실된 상황은 아니다. 두 작업의 예약 합계136314880B는 그대로 보존한다.

`continuation_jobs`와 `--continue-unrelated-pending`는 같은 key와 config SHA를 확인해 기존 pending만 후보에서 제외한다. 다른 새 작업도 기존 ledger의 동일 예산에서 예약한다. 옵션 자체는 lock 해제·환불·다운로드를 하지 않는다. Root는 별도 인계를 거쳐09:52:13 KST에 최대2건 실행을 시작했으며, 시작과 전송·품질 성공을 구분한다. OS 비정상 종료는 확인됐으나 시각 충돌로 직접 원인은 미확정이다.

[쉬운 설명과 운영 관측](gate-notes/GATE_RESUME_AND_DATA_REMEDIATION_20261018.md)을 함께 읽는다.

## 수집 재개 결과와 학습 검사 범위 — 2026-10-18 09:57 KST

실제 최대2건 수집이 정상 완료됐다(VERIFIED_REAL). 남술라웨시2021은 거의 숲인 참조창을 기존 다양성 정책으로 보류해 신규0패치,2022는16패치 생성/11적격 증가다. 누계는 물리1400·적격1122이며 새 두 작업 계상 합계19548647B,429회로=false다. 기존 중단2건의 예약136314880B와 부분파일은 보존했다. 두 작업으로 제한한 정상 종료이며 계속 실행중이라고 보고하지 않는다.

최초 실제 학습 준비도 검사는 병렬 수집의 원본 aggregate·원장 갱신을 SHA 대조에서 감지해 성공summary 없이 종료했고 실패근거를 보존했다. 고정1095후보의 별도 재검사와 신규수집분을 포함하는 새 후보 QA는 서로 다르다. 적격1122는 수집 누계이며 정식 학습 승인으로 해석하지 않는다. 최종 근거와 재검사 상태는 [통합 Gate](gate-notes/GATE_RESUME_AND_DATA_REMEDIATION_20261018.md)의 최신 관측 절을 읽는다.

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

152의 첫 제한 우선 수집은 실제 두 작업 정산 후 물리1432/적격1141/적격 외291이 됐다. 기존1400행을 보존하며 새32행 중19개가 적격이고 신규 나지는 저장 참조상14픽셀뿐이다. 기존 pending 두 건 예약136314880B는 그대로이며 잔여2297868407B는 이 round1 시점 관측이다. 6주×6연도의 셀 바닥28 부족151→132와 전체 적격1200 목표 부족78→59를 구분한다. round2는 실패2건 정산 완료이고 누계는 유지됐다. 실행별 시각·근거를 구분한다.


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

VERIFIED_REAL(수집·파일검사·실제조회범위):4차완료1496물리/1196적격(681/265/250),셀부족97/목표부족4,원본val나지600픽셀·기여1개다. 검증후보1125(658/217/250)를3핀검산·이전receipt보존후UIpointer로승계했고실제브라우저에서차단4·미준비·현재원본과고정source불일치를확인했다. 최신55적격은후보QA밖이다. 나지0.5%/기여5개·독립정답·표적집행미연결차단은미해소다.5차동자바2021 g02/g03 PID33756은시작/완료미확인이다. 보고10분ACTIVE와실제collector/학습0을구분한다. 쉬운설명·이론·동작·증거·발표·Q&A는[161 이해노트](gate-notes/GATE_CANDIDATE159_UI_ROUND4_20261018.md)에모았다.


### 최신 5차 완료 관측 — 2026-10-18 11:00 KST

VERIFIED_REAL(실제수집·고정후보·조회범위): 원본1512물리/1212적격(697/265/250), 셀 부족85·전체1200 수량 부족0이다. 누출16행을 제외한 고정 후보1125(658/217/250)는 UI에 연결됐지만 이후71적격은 QA 범위 밖이다. 나지1586/600/1025픽셀·기여0/1/0, 나지4차단·학습미준비와 독립정확도미검증은 유지한다.5차 한 batch는 COG 범위 오류0개, 다른 batch는16적격/나지6픽셀이며 실제 검사9.4286137초를 완료했다. 감사helper의 scene-level 실패처리 초기로그를 보존했다.6차 동자바2024 두창은 PID8688로 시작/완료미확인이다. 전체개발·나지목표 완료가 아니며10분 보고를 계속한다. 근거: `evidence/integration/priority-collection-round5-final-20261018.json`, `evidence/integration/priority-collection-independent-round5-20261018.json`, `evidence/integration/priority-ml-next-ui-round5-20261018.json`, `evidence/integration/priority-collection-round6-launch-20261018.json`.
