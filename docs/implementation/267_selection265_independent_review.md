# 267 — 265 명시 선별 계약·portable 시험 묶음 독립 리뷰

## 결론과 범위

판정은 **STATIC_REVIEW_COMPLETED / NO_BLOCKING_FINDINGS_IN_REVIEWED_SCOPE**다. 263의 F1 제품 소비 계약 공백과 F2 main 시험 포장 공백이 265에서 해소된 것으로 정적 확인했다. 이는 Root의 공유 적용·실제 수집 승인과 별개이며, 실제 공급자 응답 호환성이나 영상 품질 성공을 증명하지 않는다.

최종 격리판의 소스·최소 diff·신규/이관 시험·fixture loader·portable runner·동결 문서·기존 결과 로그만 읽었다. 추가 시험·운영 source/원장·래스터·HTTP·collector·공유/격리 코드 수정은 모두 0회다. 이전 260 동결판은 변경하지 않았다.

## 동결 판과 배치 범위

실제 작업공간은 `evidence/integration/selection265-workspace-20261018`이다. 요청에 적힌 application-manifest의 실제 파일명은 **`application265-manifest.json`**이며 freeze도 같은 파일을 지목한다. 경로 표기 차이 외 지문 불일치는 없었다. 중복 경로를 제거한 최종 파일·문서·근거 20개의 지문을 독립 검산해 모두 일치했다.

| 대상 | SHA-256 |
|---|---|
| freeze265.json | `718e757240a69c1351f5ffbbfa1ec248fc1daab2493720d0e5ea23419be1922e` |
| application265-manifest.json | `368ed88ec4b23c14bc55de1139b58f8f6c80ea653fd0ed19343cd42f64c33f1f` |
| guard | `4052759b683f6f4f545a629466f2d4145e3ad9cc2ad8e6cdf5b1e3c0004a5dd2` |
| coordinator | `9ae5ba986d3d48e89cfb269d8a242ffd6189d281649d98a11614c03e5ab3c9ab` |
| collector | `9ce6cf2a520edb14d8c67260e79fc5f605f11eab03d9d6773117e0fd193eb165` |
| 265 구현 문서 | `a60e54d136d285d7e6acf54b891cceadca3db404a6e6023a1bc12490869f5397` |

260 대비 delta 7개와 향후 공유 적용 union 9개는 다른 범위다. application manifest는 **runtime 3개+test bundle 6개=9개**를 정확히 구분하며 기존 의존 입력을 적용 대상으로 섞지 않는다. guard/coordinator 두 파일은 260 최종판과 같고, 제품 차이는 collector의 양방향 계약 검사뿐이다. 기존 test260 변경도 baseline import 두 곳을 loader 호출로 바꾸는 데 한정되며 비교 assertion은 보존됐다.

## F1 해소 — 정책과 callback의 양방향 차단

`collect_windows`는 `candidate_metadata_policy` 키의 **존재**를 먼저 확인한다. marker가 있거나 callback이 None 이외이면 다음 조건을 모두 요구한다.

- marker가 정확한 str `DEFICIT_AOI_BBOX_CONTAINS_V1`
- callback이 callable
- side가1024, search_limit이20 이하

따라서 marker+None, key가 있으면서 null/빈 문자열/unknown/bool/숫자/list/dict인 값, marker 없는 callback, side256/search21는 `CENTER_METADATA_CALLBACK_INVALID`로 끝나는 구조다. root 폴더 생성은 먼저 일어날 수 있지만 `service.search_stac` 및 asset 요청보다 앞선 검사다. marker도 callback도 없는 legacy 경로는 원래 동작을 유지한다.

263에서 지적한 “정책 marker가 있는데 실제 callback을 생략하고 legacy 풀로 진행”하는 경로는 차단됐다. 신규 시험은 None·unknown·오염 값·callable/비callable·범위 조건에서 search/COG/callback 미호출을 확인한다. 빈 문자열도 소스의 exact marker 비교로 거부된다. 기존 v2 정상 연결 및 limit1·20개 안정정렬→metadata 제외→최대5·refill0 시험은 유지돼 있다.

## F2 해소 — 외부 baseline 없는 시험 묶음

공유 적용 test bundle에는 test260·신규 test265·loader·고정 manifest·역사 guard/collector fixture 두 개가 모두 포함된다. main 프로젝트에 없는 `ROOT/baseline/...`를 직접 읽는 두 경로는 제거됐다.

loader는 자기 파일 옆 `tests/fixtures/selection265`만 기본 경로로 사용한다. manifest 299바이트와 고정 SHA를 확인하고, 거기에 고정된 역사 코드의 byte수·SHA를 확인한 뒤 **읽은 동일 bytes**를 메모리에서 compile/exec한다. 누락·변조 시 고정 `SELECTION265_FIXTURE_*` 오류를 발생시키며 main 소스나 이웃260/외부 baseline으로 fallback하지 않는다. loader 자체는 sys.path를 바꾸거나 실제 제품 모듈을 sys.modules에 덮어쓰지 않는다.

역사 코드 지문은 다음과 같다.

| fixture | byte수 | SHA-256 |
|---|---:|---|
| guard.py.fixture | 22,548 | `a90ba9a70bb0b0eecf529a10961e12edd1d9519b881913eed2e997c52c182071` |
| collector.py.fixture | 47,009 | `68d4b986b5500cb19eb810c5b086f668fc698d124551a268c190cdf5a5211301` |

guard fixture의 별도 모듈명은 `app.data._selection265_legacy_guard`, package는 `app.data`라서 기존 상대 import 문맥을 유지한다. collector fixture도 독립 alias를 사용한다. fixture는 역사 모듈 한 개의 비교 기준이며, 전체 의존 패키지의 과거 실행 환경을 복원하는 장치는 아니다. 제품 runtime은 이 시험 loader/fixture를 import하지 않는다.

`run_portable265.py`는 46개 코드·시험·config를 독립 Temp/project에 복사하고 baseline/baseline265/이웃260 부재를 검사한다. subprocess의 cwd와 PYTHONPATH는 Temp 프로젝트 코드 경로 및 설치 dependency `.runtime`이다. 기존 shell PYTHONPATH를 그대로 이어받아 외부260을 넣지 않는다. 원본/배치 파일 지문을 실행 전후 대조하며 원격·운영 자료를 복사하지 않는다. runner 자체는 향후 runtime 적용 파일이 아니다.

고정 로그는 **7모듈 96 PASS / unittest39.035초 / subprocess wall40.531초 / exit0 / skip0**를 기록한다. 누락·변조 실패와 fallback0 시험도 포함된다. 기존 집중22개와 최종96개의 중복을 합산하지 않는다. 이 독립 리뷰에서 다시 실행하지 않았으며 RSS·실 운영 속도를 검증한 수치도 아니다.

## 유지된 보호와 남은 한계

260에서 읽은 v2 exact schema/requestcanonical/config/source binding과 예약 전 검산, v1/default/부모256 동등성, SCL support·scene/split claim·B02 실제 정렬·255 진단·품질/주내 gate·실측 정산·oldpending·global4GiB·2worker·공유간격·첫429·물리3000의 보호 조건을 바꾼 추가 delta는 없다. 265 최종 guard/coordinator는 260 판과 동일하다. 기본 경로를 바꾸거나 bool marker를 opt-in으로 인정하지 않는다.

여전히 metadata bbox 포함은 실제 polygon·B02 crop·NoData·주내95%·유효80%·나지 기여의 성공 증거가 아니다. 공급자 실제 응답의 현재 호환성·최종 취득·실성능·학습 준비·모델 정확도는 미검증이다. 246의 acquisition 시각 계약도 별도로 유지된다.

Root는268에서 공유 대상 baseline·신규 test 경로 부재·실제 배치 layout을 다시 확인하고 명시 적용을 결정해야 한다. 신규 v2 request/config SHA·approval·실행 code pin을 별도로 발급해야 하며, 과거205/249/258 v1 승인을 재사용하지 않는다. main 반영·프로젝트 실제 배치 회귀·후속 수집/단일 감사·API/UI 반영 여부는 각각 별도 근거다.

완료 결론과 지문을 Root에 전달했다. 공통 이해자료에는 **263의260 결함은 역사로 보존 / 265의 두 보완은 격리 합성 검증·정적 독립 확인 / 공유 적용과 실취득은 별도**로 기록해야 한다. 아직 API/UI에 적용하지 않은 내부 선별·시험 배치이므로 이번 리뷰의 UI 변경은 없다.
