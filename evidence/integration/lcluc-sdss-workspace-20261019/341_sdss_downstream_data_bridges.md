# 341. SDSS 다운스트림 데이터 통합 브릿지: LCLUC 전이행렬 기반 넷카본 및 생물다양성 워크스페이스 연계 (Common-Valid Governance 적용)

상태: **TESTED_SYNTHETIC / ISOLATED_WORKSPACE_VERIFIED** (격리 작업공간 검증 완료, 메인 무단 수정 없음).
- 구현 모듈: `evidence/integration/lcluc-sdss-workspace-20261019/lcluc_downstream_bridge.py`
- 검증 시험: `evidence/integration/lcluc-sdss-workspace-20261019/test_lcluc_downstream_bridge.py` (**33건 단위 시험 100% 통과, 2.21초**)
- 산출물: 표준 JSON 페이로드 (`carbon_workspace_payload.json`, `biodiversity_workspace_payload.json`, `sdss_downstream_integration.json`)
- 프론트엔드 정합 대상: `frontend/src/ModelAnalysisWorkspace.tsx` (`carbon` 및 `biodiversity` configs)
- 핵심 거버넌스: **공통 유효 화소 거버넌스(`valid_common`)** — 구름/그림자/NoData 결측에 의한 거짓 산림벌채 배출 왜곡(~1,100 tCO2e/ha) 및 인위적 가장자리 침식 원천 차단

(상세 내용은 docs/implementation/341_sdss_downstream_data_bridges.md 참조)

