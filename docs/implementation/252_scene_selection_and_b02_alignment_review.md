# 252 — 235 장면 선별과 249 B02 기하 차단의 분리 조사

상태: **READ_ONLY_ANALYSIS_COMPLETED**. 저장된 실제 보고서의 값과 코드 동작을 대조했다. 수집 재실행·수정·품질 재측정·해결 검증을 뜻하지 않는다.

## 쉽게 설명하면

235는 “이 위치가 구름 등에 가려져 쓸 만한가?”라는 예비 검사에서 다섯 장 모두 탈락했다. 249는 다른 위치에서 네 번째 사진이 예비 검사를 통과했지만, 그 사진에서 잘라 내려는 실제 창이 사전에 승인한 위치와 맞지 않아 다음 안전장치가 중단했다. **두 작업 모두 신규 자료는 0장이지만, 중단 원인은 다르다.**

사진 전체의 구름 비율이 낮아도 우리가 원하는 작은 위치에는 구름이 몰릴 수 있다. 반대로 그 작은 영역의 구름 검사를 통과해도, 경계에서 잘라낸 창이 승인한 위치와 정확히 일치한다는 뜻은 아니다. 현재 구현은 이 두 검사를 순서대로 수행한다.

252에서는 원격 조회, 원본 aggregate/source·원장 읽기, 래스터 배열 읽기, 신규 inventory/native 검사, 프로세스 조회, 수집 실행, 제품 변경을 모두 **0회**로 유지했다. Root가 승인한 완료 고정 batch의 JSON·선택 STAC와 소스코드만 읽었다. 별도 255 변경의 성공을 이 조사로 인증하지 않는다.

## 읽은 근거와 출처

메타데이터/코드 파일별 경로·바이트·SHA와 후보 수치는 `evidence/integration/selection252-readonly-analysis-20261018.json`에 기록했다.

| 고정 근거 | SHA-256 | 의미 |
|---|---|---|
| `deficit235-native-root-20261018.json` | `faecb6ee76e6537fe767fe850e4b9c83e2f6bc9cfb37d412d0014a50738b4b2e` | 235 완료 감사 |
| `deficit249-native-root-20261018-run2.json` | `6beed046a69e8cddce35df65fa2ea1ae6c16199dd42808d71a3045d7ef64146c` | 249 완료 정정 감사; 초기 INCOMPLETE 보고서와 구분 |
| 235 batch `annual-window-report.json` | `9ace6635a2c974d63371a13677a3bb10fdc97fd03a58a87e55a31d560a11d8b5` | 다섯 후보 SCL 선별 결과 |
| 249 batch `annual-window-report.json` | `2283e97995423ecd046849274d9bdc5160d478077ea4d8e7a02d4a00c5c7845b` | 네 후보 선별과 후속 기하 실패 |
| 249 선택 `stac-item.json` | `b59e97e567c54aecd2709291487b0cf352ae2e1f5c05932a4993c53de1e5b2e6` | 선택 장면의 선언 메타데이터 |

235 batch 디렉터리는 `data/first-group-training-esri-v1/sources/center1024-southeast_sulawesi-2024-fc824e2465d1-41f9ed9a/`, 249는 `.../center1024-southeast_sulawesi-2024-7fdcb4d284c6-991dcd39/`다. 249 선택 파일은 그 아래 `centers182-southeast_sulawesi-f5fa8f8ccc4f-2024/stac-item.json`이다. 표의 상대 경로는 프로젝트 루트 기준이다.

**VERIFIED_REAL:** 저장된 후보 비율·선택 장면·실패 코드·감사 정산 값이다. SCL TIFF의 SHA는 저장 보고서에 적힌 값이며 252가 다시 TIFF를 읽어 검산하지 않았다. 코드 근거는 evidence에 기록한 읽기 시점 판본이다. 조사 중 255 담당의 제품 변경이 진행되므로 현재 파일과 동일한 SHA라고 자동 승계하지 않는다.

## 다섯 후보가 정해지는 과정

`collect_samples.load_config`, `collect_windows`, `select_quality_candidate`와 `service.search_stac`를 대조했다.

1. 235는 2024년 `season_start=06-01`, `season_end=09-30` 설정이다. `load_config`가 `periods`를 생성하므로 원 config에 `periods`가 없다는 사실은 기간 누락이 아니다. 실제 검색 기간은 2024-06-01 00:00:00Z부터 09-30 23:59:59Z다.
2. Earth Search에 collection·요청 bbox·기간·장면 전체 구름 비율 60% 이하·반환 상한 20·구름 오름차순 정렬을 요청한다. bbox 검색은 전체 포함 보증이 아니다.
3. 서비스는 한 응답만 읽고 최대 20개 feature를 처리한다. 반환 구름 값의 유효성과 60% 상한을 다시 확인한다. 다음 페이지를 따라가지 않는다. 정렬 요청과 실제 원격 카탈로그 전체가 올바르게 정렬됐다는 검증은 구분한다.
4. 수집기가 반환된 유효 항목을 다시 구름 비율 오름차순으로 정렬하고 앞의 최대 5개만 선택한다. 동률은 반환 순서가 유지된다. SCL 결과를 미리 알고 좋은 다섯 장을 고르는 방식은 아니다.
5. 각각 SCL을 읽어 1024 대상에 대응하는 512 크기 예비 창을 검사한다. SCL 0·1·3·8·9·10·11을 제외한 비율이 65% 이상인 **첫 장면**을 선택한다. 다섯 장 중 최고 유효 비율을 끝까지 비교하지 않는다.
6. 다섯 장이 모두 미달이면 해당 AOI/연도를 `quality_insufficient`로 종료한다. 6~20번째 후보로 이어가는 코드가 없다. 선택 뒤 B02 기하 등에서 실패해도 남은 후보를 다시 순회하지 않는다.

235에는 전체 검색 응답/실제 반환 개수/다음 페이지 내용이 남아 있지 않다. 따라서 “20개가 실제로 반환됐다”, “6번째에는 좋은 사진이 있었다”는 주장은 할 수 없다. `filtered_count=0`도 실제 후보가 20개였다는 증거가 아니다. 선택 장면이 없으므로 선택 후에 쓰는 `stac-item.json`도 생성되지 않는 경로다.

## 235: 다섯 장 모두 예비 SCL 미달

| 순서 | 장면 촬영일(UTC) | 장면 전체 구름 비율 | 저장 SCL 유효 비율 | 결과 |
|---|---|---:|---:|---|
| 1 | 2024-06-19 | 21.468797% | 34.243011% | 65% 미달 |
| 2 | 2024-08-03 | 23.492284% | 48.893738% | 65% 미달 |
| 3 | 2024-09-12 | 24.449630% | 53.482819% | 65% 미달 |
| 4 | 2024-08-13 | 24.531983% | 56.833649% | 65% 미달 |
| 5 | 2024-07-29 | 43.929020% | 21.070480% | 65% 미달 |

구름 순위와 목표 창의 유효 비율 순위는 일치하지 않는다. 이 실행은 선택 B02 승인 전에 끝났다. 신규 patch/eligible 0, 저장 정산은 COG 1,245,184B + metadata 169,282B = **1,414,466B**다. exit0은 수집기가 결과·정산 절차를 마쳤다는 뜻이며 자료 확보 성공이 아니다.

## 249: 네 번째 장면 통과 뒤 B02 정렬 실패

| 순서 | 촬영일 | 저장 SCL 유효 비율 | 결과 |
|---|---|---:|---|
| 1 | 2024-06-19 | 10.772705% | 65% 미달 |
| 2 | 2024-08-03 | 54.079437% | 65% 미달 |
| 3 | 2024-09-12 | 46.969604% | 65% 미달 |
| 4 | 2024-08-13 | 81.554794% | 선택; 다음 기하 단계에서 실패 |

선택 ID는 `S2B_MSIL2A_20240813T021349_R060_T51MUR_20240813T055551`이다. 네 번째에서 선택을 반환하므로 다섯 번째 SCL을 검사했다고 보고하면 안 된다. 235와 249는 위치가 달라 같은 장면의 SCL 비율도 다르다.

저장된 실패는 `AssetTransferError(stage=window_geometry_guard)` → `ValueError(CENTER_B02_ALIGNMENT_SHORTFALL)`이며 분류는 `payload_or_response_contract`다. 이는 HTTP 429나 SCL 미달 코드가 아니다. B02 헤더를 얻기 위한 원격 바이트가 발생할 수 있으므로 “B02 관련 HTTP가 전혀 없었다”는 뜻도 아니다. 선택 B02의 픽셀 `src.read`는 이 guard 뒤에 있다.

`DeficitCandidateLiveGuard.on_window`는 요청 bbox의 결속, metric CRS, 1024×1024 창, 10m 격자를 확인한 다음 실제 창의 네 경계와 계획 footprint의 네 경계를 비교한다. 어느 한 경계라도 **10.000001m** 허용값을 넘으면 이 코드를 발생시킨다. `b02_checked`와 창 확정은 통과 뒤에만 설정한다. 저장 결과 `live_b02_checked=false`, 신규 patch/eligible 0이다.

서비스의 실제 창은 WGS84 bbox 중심을 래스터 CRS로 변환해 픽셀 인덱스를 구하고, 원본 가장자리에서 행·열을 제한해 만든다. 계획 footprint는 미터 좌표에서 정한 10,240m 정사각형이다. 투영된 중심 차이·픽셀 반올림·경계 제한은 정적 코드상 점검 대상이지만 **이번 실제 어느 작동이 몇 m 차이를 만들었는지는 미확정**이다. 실패 당시 B02 bounds/window transform/offset/delta가 저장되지 않았다. SCL 또는 Esri bounds를 B02 실제 값으로 바꾸어 쓰지 않는다.

### 저장 카탈로그만으로 확인되는 경계 위험

249 요청 bbox는 `[121.72930337706629,-3.6716552086746117,121.82161437453668,-3.5789105806457218]`이고 선택 STAC bbox는 `[121.1971527,-4.6113932,122.1878144,-3.6167214]`다. 요청 북쪽 끝이 선언 장면 북쪽 끝보다 북쪽에 있으므로 **선언 bbox는 요청 창 전체를 포함하지 않는다.**

경위도 직사각형끼리 단순 계산한 겹침 면적/요청 면적은 약 59.23%다. 이는 선언 사각형 비교 값이며 실제 지표면 면적·유효 픽셀 비율·SCL 결과·실제 B02 창 손실률이 아니다. 저장 asset의 `proj:transform/shape`도 카탈로그 선언이며 실패 B02 실측 헤더로 인증하지 않았다. 이 관측은 “교차 검색과 전체 창 포함은 다르다”는 위험 근거다. 정확한 실패변·미터 오차를 확정하는 대체 증거는 아니다.

249 완료 감사 정산은 COG 1,310,720B + metadata 269,558B = **1,580,278B**다. 두 실행 합계 2,994,744B, 신규 확보 0이다. 완료 감사 기준 기존 1,715행/history·old pending2 전액 보존·적격 1,358/셀 부족 21 유지이며 252가 현재 운영 원장을 다시 읽은 결과가 아니다.

## 현재 사용할 수 있는 옵션과 없는 옵션

| 경로 | 코드상 가능 여부 | 핀/검증 영향과 한계 |
|---|---|---|
| 다른 이미 제안된 위치·연도 선택 | 기존 strict request의 `selected`로 가능 | 최신 source/ledger/proposal/config 핀과 scene/window/split 검증을 새로 충족해야 한다. 이전 source 사본을 현재와 같다고 취급할 수 없다. 품질 성공 보장 없음 |
| 계절 범위 변경 | 고정 base config의 `season_start/end`를 기존 loader가 소비 | 새 config 파일/SHA, 그 config를 결속한 새 proposal·request/canonical SHA·job identity 필요. 조사 중 생성/실행 0. 같은 5개 상한을 지키며 검색 집합만 달라질 수 있고, 구름·정렬 문제 해결 보장 없음 |
| cloud/search/candidate/예비 최소값을 base config에서 바꾸기 | 현 deficit coordinator에서는 효과 없음 | `deficit_candidate_guard`가 60%/20/5/65%로 고정한다. 일반 수집기 설정과 혼동 금지 |
| 256 나지 plan의 `minimum_candidate_valid_fraction` | 다른 bare256 경로에만 존재 | 1024 deficit 선별에 자동 적용되지 않는다. 이번 작업에서 기준 변경 승인 없음 |
| 장면 제외/index 지정·기하 오차 허용·자동 중심 이동·다음 후보 fallback | 현재 deficit CLI 옵션 없음 | 기존 플래그 하나로 249를 고치는 방법은 없다. 별도 설계/시험/승인 필요 |

다음은 **명령 형태 설명**이며 입력 placeholder는 실제 승인 핀이 아니고 실행하지 않았다. 새 계절 config가 필요하다고 판단될 경우에만 Root가 새 로컬 계획·실행 범위를 별도로 정해야 한다.

```powershell
python -X utf8 scripts/propose_deficit_centers182.py --source <fixed-source.json> --source-sha256 <sha> --boundary <boundary.json> --boundary-sha256 <sha> --config <new-season-config.json> --config-sha256 <sha> --prior-plan <prior.json> --prior-plan-sha256 <sha> --target southeast_sulawesi:2024 --manifest-profile bounded128m-3000-v1 --output <new-proposal.json>
python -X utf8 scripts/collect_deficit_guarded.py --request <new-strict-request.json> --expected-request-sha256 <canonical-sha>
```

첫 명령도 로컬 header/inventory를 소비할 수 있으므로 252에서는 실행하지 않았다. 두 번째는 `--execute`가 없어도 fresh 로컬 전체 검산이 발생한다. 요청 파일은 proposal 결과가 자동으로 대신하지 않으며 strict refs/selected/최대 batch를 별도로 결속해야 한다. 실제 원격 집행은 Root의 새 승인 뒤 `--execute`를 붙이는 별도 단계다. 단독 `diagnose_stac`나 `collect_samples --search-only --execute`는 이 coordinator의 공유 원장 보호를 자동 승계하지 않으므로 우회 대안으로 제안하지 않는다.

## 다음 단계와 미확정 사항

**PLANNED:** 255 담당의 제한된 B02 기하 진단 저장을 검토·시험·동결한 뒤 Root가 다음 수집 여부를 정한다. 이번 249에 없던 값을 사후 생성하지 않는다. 이후 기하 기반 후보 선별이나 선택 후 다음 장면 재시도를 검토하려면 기존 장면/창 claim, 최대5개, 공유 예산·2초/첫429, 품질·분할·물리 cap을 보존하는 별도 계약이 필요하다. 현재 설계가 곧 실행 승인은 아니다.

이번 조사는 기준 완화·후보 상한 확대·무작정 같은 위치 반복을 제안하지 않는다. 실제로 이미 승인된 다른 위치를 선택하는 방법은 존재하지만, 그 위치에서 구름/전체 창 조건을 만족하는 장면이 나오는지는 원격 실행 전에는 미확인이다. 235의 전체 검색 응답이 없어 나머지 후보의 존재·품질은 모르며, 249의 정확한 B02 경계 차이도 아직 모른다.

시험: 제품 변경이 없는 읽기 전용 분석이므로 추가 단위시험·운영 QA를 실행하지 않았다. 근거 SHA 대조와 저장 수치 산술만 수행했다. 기존 UI/API/학습 동작 변경이 없어 화면 수정은 필요 없다. Root에 완료 근거를 인계하여 이해자료에서 “235는 SCL 탈락 / 249는 SCL 통과 뒤 기하 차단 / 신규0”을 구분하도록 요청한다. 이해자료 자체 갱신은 Root의 별도 담당 작업이며 이 문서로 완료를 대신하지 않는다.
