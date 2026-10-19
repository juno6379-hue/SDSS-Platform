# 265 — 메타데이터 정책·필터의 양방향 결속과 독립 시험 배치

상태: **IMPLEMENTED / TESTED_SYNTHETIC**, 새 격리판에만 구현. 공유 main 적용·운영 자료 조회·실제 STAC·수집·API/UI 검증은 하지 않았다. 260 동결판과 최초 실패/최종 합격 로그·문서는 그대로 보존한다. 260의 역사 90 PASS는 그 판의 시험 증거이며 독립263이 발견한 필수 결함의 해소 증거가 아니었다.

## 두 결함과 보완

첫째, 260 collector는 callback이 전달된 경우에만 정책을 검사했다. 그러므로 `candidate_metadata_policy`가 설정되어도 callback=None이면 예전 경로로 실행할 수 있었다. 265는 **설정 키와 callback 중 어느 하나라도 있으면 정확한 정책과 필터 연결을 함께 요구**한다. 둘 다 없는 기존 기본 경로는 그대로다.

| 설정 | callback | 동작 |
|---|---|---|
| 정책 키 없음 | None | 기존 기본 동작 유지 |
| 정확한 marker | callable + side1024 + search<=20 | 명시 선별 경로 |
| 정확한 marker | None/비callable | 네트워크 전 차단 |
| unknown/bool/None/숫자/list/dict marker | 어떤 값이든 | 네트워크 전 차단 |
| 정책 키 없음 | None 이외 | 네트워크 전 차단 |
| 정확한 marker+callable | side256 또는 search>20 | 네트워크 전 차단 |

오류는 기존 고정 `CENTER_METADATA_CALLBACK_INVALID`다. marker는 정확한 str `DEFICIT_AOI_BBOX_CONTAINS_V1`만 허용한다. key가 존재하면서 null인 상태를 key가 없는 기본값으로 간주하지 않는다. dry-run도 잘못된 명시 계약을 통과시키지 않는다. 기존 위치에서 검증하므로 root 폴더 준비는 먼저 일어날 수 있으나 search·SCL·asset 요청 전이다. 이 검사는 전체 coordinator의 예약 전 proof 검사를 대신하지 않는다. 정책이 없는 v1/default와 부모256 출력은 유지하고, marker가 있는 설정을 임의로 legacy fallback시키지 않는다.

둘째, 신규 test260은 `ROOT/baseline/...`에서 비교 코드를 읽었다. main에 시험만 배치하면 그 외부 디렉터리가 없어 실패한다. 새 격리판은 원바이트 역사 코드 두 개를 시험 전용 fixture로 보존하고 고정 SHA를 검증한 뒤 같은 bytes를 메모리에서 compile/exec한다. 제품 코드는 이 fixture나 loader를 import하지 않는다.

## 격리판과 정확한 파일 목록

작업공간: `evidence/integration/selection265-workspace-20261018`.

260의 최종 코드·시험 및 필요한 import/config 입력 41파일을 복사했고, `baseline265/`와 `baseline265.json`에 수정 전 원바이트/SHA를 보존했다. 운영 data/model/ledger는 복사하지 않았다. config/example은 기존 프로젝트 상대 경로를 유지한다. 260 대비 변경은 기존 2개와 신규 5개, 총 7파일이다.

- 제품 변경 1개: `scripts/collect_samples.py`의 양방향 결속 검사.
- 기존 시험 변경 1개: `tests/test_deficit_metadata_selection260.py`의 두 baseline 로드를 fixture loader로 교체.
- 신규 test loader: `tests/selection265_fixtures.py`.
- 신규 시험: `tests/test_selection265_contract.py`.
- 신규 fixture/manifest 3개: `tests/fixtures/selection265/{guard.py.fixture,collector.py.fixture,manifest.json}`.

최종 **공유 적용 검토용 union**은 runtime 3개(`deficit_candidate_guard.py`, `collect_deficit_guarded.py`, `collect_samples.py`)와 시험 bundle 6개(위 시험2개·loader·fixture3개)다. runtime 앞의 두 개는 260 최종 판과 원바이트 같다. 265 delta 7개와 향후 main union 9개는 다른 기준이며 합산하지 않는다. 이 문서는 별도 설명 자료다. Root가 검토할 `application265-manifest.json`은 대상·baseline·최종 SHA를 제시할 뿐 적용 완료를 뜻하지 않는다.

260의 v2 requestcanonical/configSHA/source binding, cloud 안정정렬 후 metadata 제외→최대5, search20/SCL5, candidate_limit1, 모두 제외 시 읽기0/fallback0, 소수초 원문·baseline 보존은 유지한다. 기존 split/support/품질/B02정렬/255진단·global4GiB/2worker/공유2초/첫429/물리3000/metadata1+COG64 상한·원장 정산·모델 gate는 변경하지 않는다. 246 strict 소수초 정책도 보존한다.

## 시험 전용 역사 fixture 계약

| role | 파일 | bytes | SHA256 |
|---|---|---:|---|
| guard | guard.py.fixture | 22548 | `a90ba9a70bb0b0eecf529a10961e12edd1d9519b881913eed2e997c52c182071` |
| collector | collector.py.fixture | 47009 | `68d4b986b5500cb19eb810c5b086f668fc698d124551a268c190cdf5a5211301` |

두 fixture는 부모260의 baseline 원바이트다. 현재 제품으로 바꾼 비교 대상이나 새 구현을 복제한 기대값이 아니다. `manifest.json`은 299바이트, SHA `b0398658098475f9788a11d9a8f7fa9cbc6c077847e8f896b513bf0aa39d0163`이며 loader 상수에 고정했다.

`load_legacy(role, *, fixture_root=None)`는 guard/collector 두 role만 받는다. 기본 경로는 loader 옆 `fixtures/selection265`이며 optional 경로는 Temp 변조 시험용이다. 다른 workspace·부모 baseline·main 코드로 fallback하지 않는다. manifest와 fixture를 각각 열기 전 크기 제한(64KiB), 정확 byte수, 일반 파일·symlink 제외, 읽기 전후 identity/size/mtime와 bounded 실제 읽기를 확인한다. manifest SHA 확인 후 해당 fixture SHA를 확인하고, 검증한 동일 bytes만 실행한다. 읽기/무결성 실패는 고정 `SELECTION265_FIXTURE_*` 오류이며 누락을 skip하지 않는다. raw path나 예외 문구를 오류에 넣지 않는다. 이는 신뢰된 시험 코드 pin이며 원격 자산 인증이나 운영 출처 검증과 무관하다.

원문 bytes를 fixture에 보존하여 CRLF 차이도 지문에 포함한다. manifest/fixture 변조를 발견하면 기대값을 새 제품 코드에 맞춰 자동 갱신하지 않는다. 260 fixture 의존을 제거한 test260은 같은 assertion을 유지한다. 역사 fixture는 시험 bundle만 배치하며 runtime 파일로 복사하지 않는다.

## 시험 증거와 이동성 배치

집중 시험: 신규265 6개+기존260 16개, **22 PASS / unittest12.059초 / exit0**, `focused265.log`. 정확 marker+None/unknown/bool/null/비callable, 콜백만 존재, 256/search21, 정상 명시 선별, unmarked256 출력 exact legacy, manifest/각 fixture 누락·변조 실패, 역사 bytes/SHA를 검사했다. 기존260의 v1 full proof 비교도 새 loader를 통해 유지한다.

`run_portable265.py`는 **검증 runner이며 제품 bundle 대상이 아니다**. 기준 코드·시험·config와 fixture 46파일만 완전히 별도 Temp/project에 복사한다. 그 배치에는 baseline/baseline265/이웃 selection260 디렉터리가 없음을 assert한다. PYTHONPATH는 Temp 코드 경로와 공용 설치 dependency `.runtime`만 사용한다. 공용 `.runtime`은 Python dependency 경로이며 외부 비교 baseline이 아니다. 모든 배치 파일과 원본 input SHA를 실행 전후 비교한다. 운영 자료를 가져오지 않는다.

관련 7모듈은 test_selection265_contract/test_deficit_metadata_selection260/test_deficit_candidate_guard/test_collect_deficit_guarded/test_targeted_collection_hooks/test_targeted_candidate_quality_policy/test_data_recovery다. 최종 결과와 실제 경과시간은 마감 절 및 `portable265-result.json`/`portable265-regression.log`에 기록한다. 집중 시험과 관련 회귀의 겹치는 집합은 합산하지 않는다. RSS는 관측하지 않는다.

최종 별도 배치 회귀는 **96 PASS / unittest39.035초 / 실제 subprocess wall40.531초 / exit0 / skip0**다. 외부 baseline 없는 46파일 배치와 원본 입력의 전후 SHA가 모두 같았다. 기존 rasterio PendingDeprecationWarning은 있었고 오류는 없었다. 265에서 실패한 시험을 skip하거나 기존 기대값을 바꾸지 않았다. 정확한 양방향 누락 처리는 collector의 config 검증 위치에서 `CENTER_METADATA_CALLBACK_INVALID`를 발생시키며, 시험의 `search_stac.assert_not_called()`/`read_cog_window.assert_not_called()`와 callback 미호출이 **네트워크 전** 차단 증거다. 운영 실행의 stage를 관측한 증거는 아니다.

공유 검토용 시험 bundle의 정확한 6경로는 다음과 같다.

```text
tests/test_deficit_metadata_selection260.py
tests/test_selection265_contract.py
tests/selection265_fixtures.py
tests/fixtures/selection265/manifest.json
tests/fixtures/selection265/guard.py.fixture
tests/fixtures/selection265/collector.py.fixture
```

`application265-manifest.json`은 runtime3에 main 현재 SHA, 위 시험6에 신규 부재 조건을 각각 분리한다. 기존 config/import code는 적용 대상이 아닌 필요 입력으로만 baseline 지문을 제시한다. `patch265-manifest.json`/`patch265.diff`는 부모260 대비 7파일 delta이고, `freeze265.json`은 제품·시험·문서·baseline·로그·runner·검증결과의 최종 지문이다. 역사260의 모든 baseline/code/test/log/doc 및 freeze는 재검산하며 바꾸지 않는다. 문서와 freeze 자체의 SHA는 Root 인계에서 별도 전달한다.

## 적용 전 조건과 한계

main 제품 수정·운영 source/ledger/model/래스터 조회·HTTP·실collector/native QA·모델 학습·실API/브라우저는 0이다. 시험에서 쓰는 정산/래스터는 Temp 합성 자료다. main255/246 동결과 부모260의 code/test/freeze/log/doc 지문을 별도로 재검산한다.

Root 독립 재검토와 소유 파일 baseline 비교 후에만 명시 공유 적용을 결정한다. 새 v2 요청·approval·expectedconfig SHA·실행 코드핀은 여전히 다시 발급해야 하며 과거 v1의 205/249/258 예상config나 실행 proof를 재사용하지 않는다. 실제 PC 응답의 선별 호환성·전체 AOI 실제 픽셀 포함·SCL/나지 확보·B02 정렬 성공은 미검증이다. 단일 내부 계약/시험 배치 완료를 수집 성공이나 학습 준비 완료로 표현하지 않는다.

UI/API 동작 변경은 없고 제품도 아직 격리판이다. Root 검토 뒤 이해 담당의 쉬운 설명·대본·FAQ·INDEX·이력 갱신이 남는다. runtime/시험 bundle의 고정 지문·최소 delta·원판 archive·관련 회귀를 인계하고, Root의 다음 명시 적용 검증 전 추가 운영 실행은 하지 않는다.
