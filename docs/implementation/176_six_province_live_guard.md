# 176 — 6주 고정 split의 실시간 scene/window 보호

- updated_at: 2026-10-18 KST
- source_commit: Root 통합 전176 소유 작업 트리
- evidence_paths: `evidence/integration/six176-focused-20261018.log`, `evidence/integration/six176-related-20261018.log`
- confidence: 합성 job/target·STAC·실제 CRS 연산·기존 callback 회귀 시험 범위
- status: TESTED_SYNTHETIC / 실제 6주 신규 표적 확보는 별도 검증

## 구현 목적과 소유 경계

174 확장 명세의 B단계를 구현했다. `backend/app/data/targeted_live_guards.py`의 Banten/val 제한을 고정6주 정책으로 일반화했다. source175 local plan·170 dispatcher·원장·수집 프로세스·기존 데이터·모델은 수정하거나 호출하지 않았다. 새 원격 HTTP·예약·학습·배포는0이다. 173 후보50개를 이 helper가 자동 집행하거나 품질 통과로 표시하지 않는다.

정책은 175와 동일하게 기존 `readiness_connectivity_witness.FIXED_PROVINCE_SPLITS`를 재사용한다. caller가 split map을 전달하거나 재배정할 수 없다.

| 주 | 고정 split |
|---|---|
| South Sulawesi | train |
| Gorontalo | train |
| Southeast Sulawesi | train |
| East Java | train |
| Banten | val |
| West Java | test |

## 유지한 호출 계약과 강화한 binding

`TargetedLiveGuard(job, target, shared_scene_registry, shared_window_claims)` 및 기존169의 `on_scene(item,aoi,year)`/`on_window(url,geometry)` callback은 동일하다. job과 target을 깊은 복사하여 생성 후 외부 객체의 province/split/AOI 변조가 이미 결속한 target을 재배정하지 못하게 한다. scene/window registry는 같은 인스턴스를 공유한다.

`_binding()`은 selected scene 전뿐 아니라 선정 전 SCL을 포함한 모든 window callback 앞에서 검사한다.

- job province가 정확히6주 중 하나이고 split이 canonical map과 일치한다.
- target의 province/fixed_split/year가 job의 province/split/year와 일치한다.
- job/target year는 bool이 아닌 int2020~2025다.
- config AOI가 정확1개이고 province_id가 job province다.
- target_bbox_wgs84와 config AOI bbox가 같고 유한한 정상 WGS84 범위다.
- target native CRS가 실제 projected이며 linear_units_factor가1.0인 미터 단위다.

on_scene의 실제 aoi는 config의 id/province_id/bbox와 다시 일치해야 한다. collector가 전달하는 문자열 year는 정확한2020~2025 네 자리 값을 허용하며, selected STAC datetime은 timezone이 있는 ISO timestamp이고 그 연도가 job/target과 같아야 한다. target 전체 local/native/주 경계 검증은175의 책임이며 이 binding이 그 검증을 대체하지 않는다. 기존 실제157 target의 full fields를 그대로 사용한다. footprint만 있는 불완전한 synthetic target에 대한 느슨한 fallback은 두지 않는다.

## 실제 native CRS·장면·공간 보호

주별 EPSG를 제품 정책으로 고정하지 않는다. UTM 경계·적도 또는 다른 source의 실제 native 격자는175 pinned label과 selected B02가 검증해야 한다. projected지만 feet 단위이거나 geographic/3D geographic/해석할 수 없는 CRS는 `TARGET_NATIVE_CRS_UNSUPPORTED`로 차단한다. selected reference label의 재사용 경로에도 실제 geometry CRS의 미터 조건을 적용한다. 적절한 미터 단위 native zone의 변경 자체는 거부 사유가 아니다.

기존 B02 조건은 유지한다. selected item이 선언한 정확한 B02 URL만 witness가 될 수 있다. 실제 callback CRS와 target CRS가 같고256×256/native10,-10 격자이며 target footprint bounds와 각 변이 기존 허용1픽셀(10m) 안이어야 한다. 175가 검증한 full footprint와169 실제header의 결속이며 주 이름으로 원격 자산 CRS를 추정하지 않는다. ±10m는 완전히 동일한 픽셀 경계를 보장하는 정책이 아니며 기존 수치 정렬 한계다.

동일 source scene의 split 충돌·기존 multi-split quarantine·다른 owner 선점·같은 owner의 재선택은 기존162 shared claim으로 차단한다. 실패 후 scene/window claim을 자동 release하지 않는다. 선정 전 candidate SCL은 scene witness가 아니지만 기존 support와 다른 worker에 대한 공간 exclusion은 적용한다. selected item에 선언되지 않은 다른 영상 URL은 거부한다. 재사용 label 예외는 selected scene에서 기존 esri_annual_plan이 산출한 정확한 동년 공식 URI만 허용한다. URL에 연도 문자열이 들어 있다는 이유로 예외를 주지 않는다.

동일 owner의 여러 support band는 중첩할 수 있고 다른 owner의 양성 면적 겹침은 차단한다. 과거 support는 owner가 없으므로 같은 worker의 재사용 예외를 받지 않는다. 다른 CRS의 비교는 기존 densified transform+보수적 margin이며 과학적 독립성 증명으로 표현하지 않는다. 메모리 registry는 한 coordinator의 같은 객체에 한정되며 분산/영속 claim이 아니다.

## 시험 근거와 호환성

기존 Banten 시험12개는 full binding fields/province_id를 명시하도록 fixture만 보강했으며 동일 scene/B02/label/overlap 회귀를 유지했다. 신규8개를 포함한 집중 **20 PASS,1.723초**다. 한 시험 안에서6주×6연도36사례를 독립 registry로 실행하여 train/val/test 세 split을 모두 확인했다. 실제 관리구역 위치의 품질/경계를 그 fixture가 증명한 것은 아니다.

새 경계는 모든 주의 split 재배정(선정 전 SCL에서도 거부), 알 수 없는 주·target province/split/year 불일치, AOI province/bbox/개수 변조, 다른 정상 metric zone 허용, geographic/feet/잘못된 CRS 거부, Gorontalo의 B02 CRS 불일치·위조 연차label URI, train/test 같은 scene 선점, 과거 support 겹침, 실패 window claim 유지 및 외부 입력 객체 변조를 검사한다. 자체적으로 quality histogram·80/95 판정·학습 승인을 수행하지 않는다.

관련 회귀는 `PYTHONPATH=backend;.runtime;tests`에서 `python -m unittest test_targeted_live_guards test_targeted_collection_hooks test_targeted_scene_claims test_collect_targeted_bare test_targeted_asset_geometry test_targeted_bare_plan -v`다. 175 모듈은 해당 담당이 동시 편집할 수 있으므로 로그 시점의 작업 트리 합성 호환성 근거이며 175 완료/커밋 여부를 대신 인증하지 않는다. 모든 시험은 HTTP를 mock하거나 호출하지 않는 경계이고 원본·실원장 쓰기는 없다.

관련 최종 결과는 **89 PASS / 0 SKIP,31.465초**다. 175의6주×6연도 native 계획 시험과 기존 반텐 job/key 회귀도 이 묶음에서 통과했다. 실제 실행 중 원격 6주 수집이 성공했다는 증거로 확대하지 않는다. Rasterio의 PendingDeprecationWarning은 로그에 보존했고 제품 실패가 아니다.

## Root·UI·이해 에이전트 인계

Root는175 local plan과176을 동결한 뒤170에 결합하고 최신 physical inventory·pending/support·input SHA·최대1~2job/기존 예산/429를 새로 검증해야 한다. 성공한 callback이나 B02 witness는 실제 최종 라벨의 나지256픽셀·80%유효·95%주내·split별0.5%/기여5개·독립 정확도·운영 승인과 다르다. 실제6주 표적 집행/품질/원본 보존 증거는 후속의 별도 실측이다.

이 내부 callback 일반화는 endpoint/UI 상태를 새로 만들지 않으므로 직접 화면 수정은 필요 없다. 이해자료에는 “반텐 전용 live veto를 고정6주 정책과 실제 native CRS 결속으로 확장했고 합성20개 시험을 통과했다. 후보50개가 확보되거나 승인된 것은 아니다”로 전달한다. 공통 인계·이해자료는 Root가 완료 코드/시험을 받은 뒤 갱신한다.
