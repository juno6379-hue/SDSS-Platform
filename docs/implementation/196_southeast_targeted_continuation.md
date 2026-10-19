# 196 — 남동2024/2025 두 표적 실제 수집·품질 미달 검산

상태: **VERIFIED_REAL — 집행·정산·새 실제 배열 검산 완료, 새 적격 나지 성과0개**. 두 worker의 정상 종료는 품질 적격 확보 성공과 구분한다. 기존80%/95%·나지256픽셀·우세도 정책을 낮추지 않았다. Root가 유일한 collector를 실행했고 품질 담당은 종료 후 새 자료만 읽었다.

## 실행과 결과

Root는193 고정 후보 QA·192 검토·195 실제 UI 확인 뒤13:19:37.339 KST에 최대2batch를 시작했다. 대상은 남동술라웨시 train의 **2024 local-rank12-2024(라벨 계획266픽셀)**와 **2025 local-rank1-2025(840픽셀)**다. 명시한 최신 source/ledger pin으로175/176/170 전검사를 수행했으며 이전 계획 수를 실제 품질 성과로 간주하지 않았다.

`target196-terminal-root-20261018.json`은13:24:50.479 KST 종료·exit0·310.5초를 기록한다. stdout은 worker 시작2·종료2, submitted/finalized2, `BOUNDED_TARGETED_STAGE_FINISHED / executed=true`, first429=false다. 두 원장 batch는 모두 settled, lock과 collector process가 사라진 뒤 독립 native 감사를 시작했다.

| 구분 | 2024 rank12 | 2025 rank1 |
|---|---:|---:|
| 생성한 실제 패치 | 1 | 1 |
| 품질 적용 전 실제 정합 라벨 나지 | 266 | 840 |
| source 품질 마스크 적용 후 나지 | **103** | **840** |
| 최종 training support 적용 후 나지 | **103** | **840** |
| 최종 유효 픽셀 | 60,639 /65,536 | 44,331 /65,536 |
| 최종 유효 비율 /최소80% | **92.527771% 통과** | **67.643738% 미달** |
| 주 내부 픽셀 | 65,536 /65,536 | 65,017 /65,536 |
| 주 내부 비율 /최소95% | **100% 통과** | **99.208069% 통과** |
| operational quality_status | quality_eligible | quality_insufficient |
| 나지256픽셀 조건 | **미달** | 통과 |
| aggregate 등록 | **0 — 미등록 receipt에 보존** | **1 — 부적격으로 등록** |
| 새 적격 나지 기여 패치 | **0** | **0** |
| 정산 바이트 | 9,564,902 | 6,172,173 |

즉 새 실제 물리 패치2개를 만들었지만 **새 aggregate 행은1개, 품질 적격 추가0개, 나지 기여 추가0개**다. 2024의 품질 자체는 통과했어도 나지 최소256픽셀을 만족하지 않아 학습 후보에 새 성과로 편입하지 않았다. 파일·라인리지는 삭제하지 않고 worker receipt의 `targeted_unenrolled_patches`에 보존했다.

## 266→103의 원인을 실제 배열로 구분

저장된 최종 label은 이미 마스크가 적용되어 있다. 따라서 그 배열을 단순히 “마스크 없이” 세더라도 원래 품질 적용 전 라벨 수가 나오지 않는다. 독립 후속 검산은 **새 raw-esri_io.tif**를 실제 raw B02의 CRS/affine/256격자에 기존 nearest 방식으로 다시 정합해 마스크 전 배열을 재구성했다. 파일이나 제품 코드를 쓰지 않았다.

2024는 정합 직후 code8이 실제 **266개**로 계획과 같았다. source의 실제 품질 마스크를 적용하자 **103개**가 남아 **163개가 제외**됐다. 최종 training support를 적용한 뒤에도103개여서, 최종 패치 단계에서 추가로 제외된 나지 픽셀은0개다. 전체 source-quality 유효 수61,333과 최종 support 유효 수60,639는 서로 다르지만 추가로 빠진 전체 픽셀694개에 나지가 있었다고 추정하지 않았다.

이 검산은 source 품질 mask에 의해 나지163개가 제외됐음을 확인한 것이다. 그163개를 모두 구름 또는 특정 SCL 코드 때문이라고 확정하지 않는다. source mask는 기존 SCL 조건과 영상 finite/nonzero 등 결합 의미를 유지하며 세부 원인별 분해는 이 감사에서 수행하지 않았다.

2025는840→840→840으로 나지는 줄지 않았다. source-quality 유효44,833과 최종 support 유효44,331의 차이를 나지 손실로 해석하지 않는다. **전체 유효 비율67.643738%가80% 미만인 것이 quality_insufficient의 직접 이유**이고, 주 내부 비율은 통과했다.

## 우세도와 품질 등급의 구분

실제 유효 라벨의 최대 클래스 비율은2024 **96.860107%**,2025 **97.766800%**로 둘 다 기존90% 참조 우세도 기준을 넘는다. 이는 별도 학습 readiness에서 확인해야 하는 문제다. materializer의 operational `quality_status`는80% 유효율·95% 주내 기준으로 정하므로,2024가 quality_eligible이라는 사실을 우세도·나지 균형·독립 정확도까지 통과한 것으로 확대하지 않는다.2025의 quality_insufficient를 우세도만의 결과로 설명하지 않는다.

## 독립 native 검산과 원본 보존

첫 bounded 감사는13:26:06.086 KST, **6.096634초·exit0**, `COMPLETED_REAL_NATIVE_NO_NEW_ELIGIBLE_TARGET`다. 새 패치2개의 image/label/quality와 raw B02 **8개 고유 raster**를 실제로 열어 SHA·256×256/10m/6밴드·격자·training support·경계·클래스를 검산했다. 두 영상은 모두 실제 raw B02와 CRS/affine 및 최종 첫 밴드 전체 배열이 같다. 고정 STAC의 scene ID·연도·정확한 selected B02 source와 worker/terminal의 live witness도 대조했다.

마스크 의미 후속 검산은 새 raw 라벨·source 품질 mask4개를 추가로 확인했고, 최종 patch mask/B02는 같은 신규 자료에 한해 재사용했다. 기존1,666개 raster 전체·167 full support inventory·193 후보 QA를 재실행하지 않았다. 새로 읽은 고정 바이트의 전후 SHA가 모두 같다.

현재 manifest 첫 **1,666행은 고정 source와 정확히 동일**하다. 기존 반텐2023·서자바2023 pending 두 행과 **136,314,880바이트 예약 전액**도 원형을 유지한다. source/ledger는 감사 전후 안정, 실행 lock 없음, launch의 제품 소스4개 pin도 현재와 같다.

- 새 두 batch 정산 합계: **15,737,075바이트**, worker/window-state/metadata/중앙 원장 일치
- 새 자료 포함 manifest 행 수: **1,667행**, 품질 적격 **1,333개**
- 미등록2024 패치까지 포함한 실제 생성 물리 수: **1,668개**
- 감사 시점 잔여 예산: **1,963,547,857바이트**
- 현재 source SHA: `1a12b7bca384dd09d73a04cc31df21f75377fc34c332b501a6ee37508dd46fb5`
- 현재 ledger SHA: `f49d7e778359c1f60743f617edb599fe2ba3170e9e9243a3459211aa4bc9b0fe`

물리 상한 검사는1,667개의 등록 행만 세어서는 안 된다. 이번 미등록 패치도 보존된 실제 물리 자료이며170의 보강된 physical inventory가 후속 집행에서 포함해야 한다. 감사 담당이 이를 삭제·환불·재등록하지 않았다. 순차 고정 검산이며 OS atomic snapshot이나 crash-safe transaction 보증은 아니다.

## 증거와 다음 담당

실행 증거는 `target196-launch-root-20261018.json`, `target196-live-root-20261018-stdout.log`, `target196-terminal-root-20261018.json`이다. 독립 상세 결과·후속 mask 분해·선택 scene·정산·파일 pin은 `evidence/integration/target196-native-root-20261018.json` 및 `.log`에 보존했다.

Root는197 metadata 소비 전 검토 담당에게 source/ledger pin과1667행/실물1668개 구분을 인계했다. 기존193의 고정1,317 후보는 이전1666행 source 시점이며 새 source SHA와 달라진다. 실제 UI·후보 pointer·후속 수집은 Root 소유다. 이 담당은 새 HTTP·collector·모델·품질 가드 변경이나 원장 쓰기를 하지 않았다. 전체 나지 균형·학습·과학 검증·전체 프로젝트는 미완료다.
