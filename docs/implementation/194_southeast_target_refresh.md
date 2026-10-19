# 194 — 192의 고정 지원자산으로 기존 남동술라웨시8표적 수치 재판정

상태: **VERIFIED_REAL_PINNED_REPORTS / NUMERICAL_REFRESH_COMPLETE_UNAPPROVED**. 실제 새 영상·라벨·전체 inventory 감사가 아니라, 검증된192 support 목록을 재사용한 수치 겹침 관측이다. 기존 남동 clear8개 중 현재 캐시 기준 clear4/blocked4를 확인했다. 집행·실품질·과학·학습 승인은 아니다.

## 쉽게 설명

과거179 검토에서 남동술라웨시의 여덟 위치는 그때까지 받은 영상과 겹치지 않았다. 이후 수집으로 상황이 달라졌으므로192에서 실제 확인한1,233개 지원자산의 위치와 여덟 위치를 다시 비교했다. 네 위치는 이제 과거 지원과 겹치고, 네 위치는 그 목록 기준으로 여전히 겹치지 않는다.

이 작업은 이미 확인한 지도상의 범위를 다시 대조한 것이다. 새 위성영상을 내려받거나 나지의 픽셀 수·구름 상태를 다시 검사한 것이 아니다. 뒤의 표에 있는 나지 수치는 **고정된 과거179 native 검사값**이며, 미래에 받을 영상의 나지/품질 성과가 아니다.

## 소유와 실행 범위

Root가192 완료 후 명시적으로 배정했다.193 고정 후보QA 동안 원본·원장을 고정 유지하고 실제 collector는 시작하지 않았다.192 full support 검토 완료를 보존하고 기존 `TargetedWindowClaims(assets).claim`을 사용했다. 각 표적마다 독립 claim 객체를 새로 만들어 과거 지원과의 겹침만 비교했다.

**full167 inventory0회 / product179 review0회 /165 native 감사0회 / 라벨 재계수0회**다. 최초 과거지원8개 비교 후 Root가 요청한 clear4개 사이6상호쌍도 같은 수치 guard로 별도 확인했다. 기존 report·pointer·원본·원장·collector·모델·제품 소스를 수정하지 않고 요청한 새 증거JSON과 이 문서만 추가했다. 공개API나 화면 상태를 바꾸지 않는 내부 판정이므로 UI 수정·build·브라우저 재시험은 필요하지 않다.

## 입력과 핀

192가 검증한 재고 시점은191 종료 후 **1,666행 / 저장 적격1,333 / 지역연도 계획부족33**이다.

| 고정 입력 | SHA256 |
|---|---|
| 현재 source | `ab745b908e2e0adce80907554216c0529e950c7e0123a7f85ee664cf26d50d0f` |
| 현재 ledger | `7839929111f3e70e8b9ba2bda3eb0972bc8c0055bb8c03b9273f4c0b381e353f` |
| 과거179 report | `36aaf1107292eee74b0f6a2ce462d90e40a22de498ca31aaff1c1ded636775f0` |
| 현재192 report | `857b1384c09e3cc8d921ed5a03c445e6464a0805f457cd40bc2a24d1a8e2ec0a` |

네 파일 SHA를 실행 전후 모두 확인했다.192 request의 manifest/ledger SHA가 위 운영핀과 같고, `inventory_verified`, `pending_footprints_verified`, `source_pins_verified` 모두true이며 support/assets 계수1,233이 일치함을 확인했다. 기존179에서 `province=southeast_sulawesi`이고 과거 `historical_overlap=false`인 정확히8개만 선택했다.

표적의 native4꼭짓점으로 만든 polygon이 유효한 직사각형인지 확인하고 그 CRS/bounds를 기존 live guard에 전달했다. `LIVE_SUPPORT_WINDOW_OVERLAP`만 예상 차단 이유로 받아들이며 다른 예외를 비겹침으로 바꾸지 않았다. 전체 지원자산 바이트를 다시 읽거나 라벨·lineage를 새로 검증하지 않았다. 현재 asset 목록의 canonical JSON SHA도 증거에 담아 어떤 캐시를 사용했는지 구분한다.

## 실제 결과

**31.078초·종료0**, 독립 claim8개·cached assets1,233개다. 다음 index는 **과거179의50 proposal index**이며190의37 proposal index와 섞으면 안 된다.

| 과거179 index | target_id | 연도 | 과거179 native 나지 픽셀 | 현재192 assets 기준 |
|---:|---|---:|---:|---|
| 0 | local-rank0-2021 | 2021 | 1,112 | 겹침 차단 |
| 1 | local-rank1-2025 | 2025 | 840 | 과거 지원 비겹침 |
| 2 | local-rank2-2024 | 2024 | 814 | 겹침 차단 |
| 10 | local-rank10-2025 | 2025 | 321 | 과거 지원 비겹침 |
| 12 | local-rank12-2024 | 2024 | 266 | 과거 지원 비겹침 |
| 18 | local-rank18-2020 | 2020 | 1,171 | 겹침 차단 |
| 23 | local-rank23-2023 | 2023 | 816 | 겹침 차단 |
| 48 | local-rank48-2023 | 2023 | 281 | 과거 지원 비겹침 |

차단4개는 모두 `LIVE_SUPPORT_WINDOW_OVERLAP`다. 기존814픽셀의 남동2024 표적을 다시 수집할 근거로 과거179의 clear 결과를 그대로 쓰면 안 된다. 새 검토 후보로는2025의840/321,2024의266,2023의281이 남는다. 최초 과거지원 비교 단계에서는 상호 겹침을 검사하지 않았으며, Root의 추가 요청으로 아래 별도 후속을 수행했다.

## 추가 요청 — clear4개의 상호6쌍 수치 검사

Root는 남동2024의 계획부족17·2021의1·2025/2023의0을 전달하며, 나지와 부족을 함께 보완할 index12/2024/266을 우선 검토하고 index1/2025/840과의 상호 겹침을 특히 확인하도록 했다. 같은 고정179 target geometry에서 한 후보를 단일 support로 넣고 다른 후보를 독립 `TargetedWindowClaims`로 비교했다. 여섯 쌍을 각각 한 번 검사했고 source/ledger/179/192 네 핀을 전후 재확인했다. 원 full inventory·라벨·native 감사는 추가 실행하지 않았다.

| 과거179 index 쌍 | target 연도 | 수치 상호 결과 |
|---|---|---|
| 1 /10 | 2025 /2025 | 비겹침 |
| **1 /12** | **2025 /2024** | **비겹침** |
| 1 /48 | 2025 /2023 | 비겹침 |
| 10 /12 | 2025 /2024 | 비겹침 |
| 10 /48 | 2025 /2023 | 비겹침 |
| 12 /48 | 2024 /2023 | 겹침 차단 |

결과는 **비겹침5쌍 / 겹침1쌍**이다. rank12-2024/266과 rank1-2025/840의 수치 비겹침을 확인했지만 실제 집행·신규 장면 품질·과학적 공간 독립성을 승인한 것은 아니다. 네 후보를 모두 동시에 또는 독립 공간 네 곳으로 세지 않는다. JSON의 최초 단계 `mutual_target_overlap_rechecked=false`는 당시 사실로 보존하고, 별도 `mutual_followup.mutual_target_overlap_rechecked=true`와 여섯 쌍의 결과를 추가했다.

## 산출물·후속 판단

새 파일은 `evidence/integration/bare194-southeast-refresh-20261018.json`이다. 최초 단계15,577바이트/SHA `775bebfb34532236bab8b3058824757e068fb71bc2df85f1dd56e31f5c6ecda8`는 JSON의 `initial194_result_bytes`/`initial194_result_sha256`에 보존했다. Root의 추가 요청에 따라 상호쌍 단계를 추가한 **최종18,939바이트 / SHA256 `cc21c4ed5a5a560fd31ea81a85ac4c8242f507da0dd9ebe8b26a9885b07d71eb`**를 최종 참조로 사용한다. 실행 KST·고정4핀·asset 캐시 지문·여덟 표적의 실제 ref/좌표/CRS/window·나지값 출처·clear/blocked 이유·여섯 상호쌍을 기록했다.

Root는 사용자 지시인 남동→고론탈로 우선순위와 현재 지역연도 부족을 함께 보고 하나를 선택할 수 있다. 선택 이후에도175/176/170에서 **최신 입력핀·전체 지원재고·상호 겹침·실제 scene/B02 격자·구름/품질·예산/중단 기준**을 다시 통과해야 한다. 이 수치 관측을 full inventory 재검증이나 집행 승인으로 사용하지 않는다.

원격 요청·실제 수집·학습·원운영 source/ledger/lock/pointer 쓰기는0이다. 기존 native/지원 파일은 다시 감사하지 않았고 운영 승인·독립 현장 정답·과학적 공간 독립성도 미검증이다. 순차 SHA 관측과 collector hold는 OS 다중 파일 원자 snapshot 보증이 아니다. 공통 원장·인계·이해자료·INDEX/대본/FAQ 갱신은 Root/understanding 담당에게 이 증거와 한계를 전달한다.
