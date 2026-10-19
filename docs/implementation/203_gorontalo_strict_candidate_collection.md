# 203 — 고론탈로2024 엄격 표적의 검색 결과0·정산 검산

상태: **실제 집행은 종료됐으나 새 영상·패치 성과0개**다. source report는 `search_failed`, 원인은 **해당 AOI/연도/계절의 검색 조건에서 선택할 장면이 없음**이다. 작업이 exit0로 끝난 사실을 자료 확보 성공으로 보고하지 않는다. 새 패치가 없어 native 검사를 추가하지 않았다.

## 실제 집행 경계

Root는13:38:21.622 KST에192 검토 index1의 고론탈로2024 `local-rank1-2024`, 로컬 약한 라벨 나지273픽셀 선언을 최대1batch로 지정했다. 새 proposal190과 선별0.9·fresh175/176/170 사전검사를 사용했다. collector와 원장 소유는 Root이며 독립 검토 담당은 재실행하지 않았다.

`target203-terminal-root-20261018.json`은13:40:29.210 KST 종료·**exit0·126.719초**를 기록한다. stdout은 worker 시작1·종료1, submitted/finalized1·settle/publish1, `BOUNDED_TARGETED_STAGE_FINISHED / executed=true`다. 그러나 `patches=0`, `eligible=0`, `live_b02_checked=false`이며 첫429 회로도 false다. 새 패치나 나지 기여 성과는 없다.

batch key는 `target256-bare-gorontalo-2024-local-rank1-2024-8ebfbcf25cc5`다. worker receipt·원장·source report·window-state를 읽어 아래 원인을 대조했다.

## 장면 검색 실패의 정확한 의미

실제 조건은 다음과 같다.

- endpoint/collection: Planetary Computer / `sentinel-2-l2a`
- 기간: **2024년6월1일~9월30일**
- 최대 장면 구름비율: **20%**
- 검색 상한20개·품질 후보 상한5개
- 최소 SCL 후보 유효율: **0.9**

report의 `stac_response_filter`는 filtered_count0·cloud_cover_response_verified=true이고, 선택할 items가 없어 `해당 AOI/연도/계절의 장면 없음`으로 종료했다. **SCL 후보0.9 검사나 선정 scene/B02 실제 픽셀 읽기에 도달하지 않았다.** 엄격한0.9 기준 때문에 모든 후보가 탈락했다는 설명은 근거가 없다. 이 검색 조건에서 선택 장면0이라는 뜻이며 고론탈로2024의 위성영상이 전혀 없다는 결론도 아니다. 원격 검색을 다시 수행하거나 계절/구름/품질 기준을 변경하지 않았다.

로컬 라벨의 나지273픽셀은 실행 전 제안 값이다. 대응하는 새 Sentinel 영상과 최종 지원 마스크를 확보하지 못했으므로 이를 실제 나지 픽셀이나 기여 패치로 더하지 않는다.

## 계상·산출물·원본 보존

실제 계상은 **metadata319바이트·COG0바이트·합계319바이트**다. worker metadata budget, window-state, worker charged_bytes, 중앙 settled 행이 모두 일치한다. 이319바이트를 raster 다운로드량으로 표시하지 않는다. source batch의 설정/이력/report/receipt와 빈 patch leaf는 보존됐지만 새 TIFF 패치는 없다.

검토 시점13:41:44.770 KST에 확인한 내용은 다음과 같다.

- 기존 **1,667개 scene 행이 고정 source와 정확히 동일**하고 새 행0개
- 기존 원장의 모든 batch 행이 동일하며 새203 batch만 settled로 추가
- 기존 반텐2023·서자바2023 pending 두 행·**136,314,880바이트 예약 전액** 원형 보존
- manifest 적격 누계 **1,333개** 유지, 새 나지 기여0개
- lock 없음·관련 collector process 없음·429 비활성
- 원본/원장 두 차례 읽기 안정
- 잔여 예산 **1,963,547,538바이트**

신규 batch의 상한65MiB 예약을319바이트로 정산한 기존 제품 동작과, 과거 미정산 pending 전액을 보존한 사실을 구분한다. 검토 담당이 환불·삭제·정산값을 수정하지 않았다. 실제 물리 수1,668개는196의 미등록 보존 패치까지 포함하는 이전 검증 범위이며 이번 새 패치0으로 늘지 않았다. 광역 물리 목록을 다시 스캔하지 않았다.

## 원본 SHA가 달라진 이유

source의 scene 행은 그대로지만 **`source_manifests`에 이번 실패 report 참조1개를 추가**하면서 전체 JSON 지문은 바뀌었다. 전후 다른 최상위 key 변화는 없다. 정상적으로 남긴 실행 이력이며 새 적격 자료를 확보한 변화가 아니다.

| 구분 | SHA256 |
|---|---|
| 실행 전 source | `1a12b7bca384dd09d73a04cc31df21f75377fc34c332b501a6ee37508dd46fb5` |
| 종료 후 source | `39bb0245e586342bd116f5b052428fcf857fb26eae0ee1413c9c5f5275c40ba9` |
| 실행 전 ledger | `f49d7e778359c1f60743f617edb599fe2ba3170e9e9243a3459211aa4bc9b0fe` |
| 종료 후 ledger | `024f5eabb2cadf88af4f34661fab6e6c209bf9aa8d105c2d1fbadf10f1c0dae3` |

고정193 후보의 source 시점과 현재 source 지문은 다를 수 있다. scene 행이 같다는 이유로 pointer/receipt의 pin 검사를 생략하거나 현재 source 일치로 위조하지 않는다. 후속 후보·UI 상태는 Root가 별도로 인계한다.

## 근거와 범위

실행 근거는 `evidence/integration/target203-launch-root-20261018.json`, `target203-live-root-20261018-stdout.log`, `target203-terminal-root-20261018.json`이다. 독립 보존·정산 결과는 `target203-native-root-20261018.json`에 있다. 해당 파일명과 무관하게 `native_validation_complete=false`, `native_patch_checks=0`을 명시한다.

201의 preflight 차단과 달리203은 실제 worker가 검색을 시도하고 metadata 비용을 정산했다. 다만 두 경우 모두 새 적격 나지 성과는0이다. 196 재감사·167 전체 support·193 후보 native QA·검색 재시도는 수행하지 않았다. 독립 검토 담당의 추가 HTTP·collector 실행·운영 원장 쓰기·모델/라벨 변경·학습 승인은 없다. 후속 수집과 원본 고정 해제는 Root만 결정한다.
