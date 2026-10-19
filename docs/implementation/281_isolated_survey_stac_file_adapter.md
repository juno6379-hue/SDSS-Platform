# 281 — SURVEY 고정 STAC 파일의 안전한 읽기 어댑터

상태: **IMPLEMENTED_ISOLATED / TESTED_SYNTHETIC**. 공유 main 적용·실운영 호환·라벨전용 수집 연결은 **PLANNED**다. 운영 원본/source·원장·모델 읽기/복사·HTTP·수집·원장쓰기0이다. 실제 나지 자료를 새로 확보한 작업이 아니다.

## 쉬운 설명과 선정 이유

220/224/226은 SURVEY 요청·영수증의 선언 형식을 검사하고,246은 전달받은 STAC 바이트에 장면·시각·제품·SCL 주소가 서로 맞게 적혔는지 검사한다.246은 파일을 열지 않으므로 호출자가 잘못된 경로나 바뀌는 파일을 읽어 전달하는 문제는 해결하지 않는다. 이번에는 그 사이의 작은 연결부 하나, **“정확히 고정한 로컬 STAC 파일을 제한 안에서 읽어 기존 검증기로 넘기기”**를 구현했다.

실제 원격 수집 전에 필요한 보호 장치 하나가 늘어난 것이다. 나지가 많다는 판정, 원격 출처 인증, 공유 원장의 예약/정산, 영상 품질 검사를 만들지 않았다. 일반 patch 증가를 나지 보완 성공이라고 표현하지 않는다.

검토한 설계는216 `label_only_survey_contract`,220 순수계약,224 복사/엄격시각 보완,226 두 장면ID 문법,246 STAC 출처 선언 결속과 현재 CONTINUOUS_DEVELOPMENT다. Root279의 collector/원장/좁은 감사는 다른 담당 소유이므로 접근하지 않았다.281 번호와 소유 경로에 기존 동일 작업 충돌이 없음을 확인하고 Root에 범위·baseline SHA를 먼저 전달해 승인받았다.

## 격리 소유와 원판 보존

새 workspace는 `evidence/integration/survey281-workspace-20261018/`다. 필요한 기존 코드8개만 새 디렉터리에 원바이트 복사했다. data/model/ledger와 전체 프로젝트를 복사하지 않았다. `input-manifest281.json`에 파일별 SHA/크기를 고정했다.

| 핵심 baseline | SHA-256 |
|---|---|
| `bare_label_survey_contract.py` | `e035cc1afb77b9461f1e5df1256dcf58bf82199e4dbb5fdba4af6e1518f8dd60` |
| `bare_survey_stac_binding.py` | `16a1d8684e47b2d7f1cb63e062f9fe1e2831f10eb4bd68eedae6e6ee7e788b4a` |
| `references.py` | `6c99a43d5a3df69d33e2e84fb1ceefd9bfe690b62ec576a261146dc9ee451d76` |
| `readiness_connectivity_witness.py` | `6c56cca4ce94d6ebeec1808b3ec82b4ba77a9e7744bb1442bb943cac17c2760e` |

새로 작성한 격리 소스는 다음2개 파일뿐이다.

- `backend/app/data/bare_survey_stac_file.py`
- `tests/test_bare_survey_stac_file281.py`

위 경로는 격리 workspace 기준이며 공유 main 파일을 생성한 것이 아니다. 기존226/246 모듈·시험·문서/freeze는 보존했다. 최종 patch manifest는 이 신규2개만 후속 검토 대상으로 지정하며 baseline 사본·과거 시험·로그는 운영 제품 적용 목록에 넣지 않는다. Root의 독립검토/별도승인 전에는 main에 적용하지 않는다.

## API와 명확한 권한 경계

```python
from app.data.bare_survey_stac_file import read_pinned_survey_stac

checked = read_pinned_survey_stac(
    local_root, request, selected_asset,
    maximum_read_bytes=1024**2,
)
result = checked.to_dict()
```

`root`는 절대 `Path`이며 요청은 기존226 검증기에 합격해야 한다. selected_asset은246과 같은 정확 `{key,source_url,product_uri}` 선언이다. 변경 가능한 원입력을 보관하지 않고 검증/분리한 request와 primitive asset 사본만 사용한다.

반환값은 frozen `SurveyStacFileBinding`이다. request digest·raw STAC SHA·실제로 반환받은 read 바이트·canonical JSON·상태를 담고 `to_dict()`는 매번 새 사본을 준다. `local_file_pin_and_identity_verified=true`와 내부246 `metadata_consistency_verified=true`만 새 관측 범위다. execution/source authenticity/remote asset/raster header/ledger/quality/training/registry/target consumer는 모두 false다. 클래스 직접 생성이나 typed 결과 자체가 실행 승인 토큰이 되지 않는다.

호출자가 제공한 `maximum_read_bytes`는 int0..1MiB만 허용한다. bool·float·음수·상한 증가는 거부한다. 이것은 **한 호출의 로컬 파일 read 한도**다. 원격 metadata1MiB 계측·COG64MiB·65MiB 선예약·전역4GiB 원장을 대체하거나 그 예산에 환불/추가 credit을 만들지 않는다. 상태 공유가 없는 API이므로 병렬 두 호출은 서로 다른 두 allowance이며 하나의 누적 budget이라고 주장하지 않는다. 미래 coordinator가 전체 누적 IO와 실행 횟수를 별도로 제한해야 한다.

## 읽기 순서와 변경 차단

1. 기존226 request 검증·분리복사를 먼저 수행한다. STAC path는 canonical `data/` 상대 경로만 받고 source/boundary/ledger/config/seed근거의 대소문자 alias를 파일 open 전에 거부한다. 다른 ref 파일은 열지 않는다.
2. 루트부터 파일 부모까지 lstat/resolve로 디렉터리·symlink/reparse 여부와 identity를 확인한다. 파일도 단일 regular file·link count1이어야 한다. 실제 여러 hardlink가 있는 파일은 보수적으로 거부한다.
3. stat 크기2B..1MiB와 호출자의 잔여 read allowance를 **os.open 전에** 검사한다. 초과하면 open0/read0이다. 파일/부모가 없는 경우도 고정 오류로 닫힌다.
4. O_RDONLY와 플랫폼이 지원하는 binary/no-follow 옵션으로 descriptor를 한 번 연다. fstat가 앞서 확인한 파일과 같아야 한다. 최대64KiB chunk로 stat 크기만 읽으며 Python이 반환받은 바이트를 누적한다. 짧은 read·성장·파일 교체·handle identity 변화를 거부하고 finally에서 descriptor를 닫는다. EOF 확인을 위한 cap+1 추가 read는 하지 않는다.
5. 논리 경로와 부모 identity를 다시 확인하고 SHA를 원요청 ref와 비교한 뒤에만 기존246 pure binding을 호출한다. validator가 처리하는 사이 변경될 수도 있으므로 반환 직전에도 파일/부모를 다시 확인한다.

원본 바이트를 다시 읽거나 hash 용도의 두 번째 descriptor를 열지 않는다. growth는 identity/stat 변화로 차단하며 추가된 부분을 읽어 허용량을 넘기지 않는다. 검사 사이 모든 악의적 filesystem 경합에 대한 원자 transaction이나 Windows 커널 수준의 디렉터리 고정을 보장하는 기능은 아니다. 실제 coordinator에는 동일 global lock·고정 입력/출력 소유권·검증판본 결속이 여전히 필요하다. 부모 디렉터리에 다른 변경이 있어도 보수적으로 차단될 수 있으며 자동 재시도하지 않는다.

## 오류와 부분 read 관측

실패는 `SurveyStacFileError(ValueError)`와 `SURVEY_FILE_*` 고정 코드다. `.actual_read_bytes`는 **그 호출에서 Python에 반환된 로컬 바이트**를 기록한다. 디스크 장치의 물리 IO나 원격 전송량이 아니다. 오류를0바이트 또는 환불 근거로 바꾸지 않는다. 첫64KiB 반환 뒤 두 번째 os.read가 실패/EOF이면65,536B를 유지한다. 예외문에 경로/URL/서명/원예외문은 넣지 않는다.

주요 코드는 BUDGET_INVALID/BUDGET_EXCEEDED/BYTE_LIMIT/REQUEST_INVALID/REFERENCE_ALIAS/PATH_UNSAFE/PARENT_UNSAFE/NOT_SINGLE_REGULAR/CHANGED_BEFORE_READ/CHANGED_DURING_READ/REPLACED/PARENT_CHANGED/PIN_MISMATCH/METADATA_BINDING_INVALID/CHANGED_AFTER_BINDING/INPUT_OR_IO_INVALID이며 모두 고정 접두사를 가진다. 246 실패의 원문 입력을 노출하지 않고 어댑터의 METADATA_BINDING_INVALID로 분류한다. 상위 순수 검증기 API 자체는 바꾸지 않았다.

## 합성시험과 실제 한계

임시 디렉터리의 합성 STAC 파일만 사용했다. 실제 프로젝트 `data`·source·ledger·모델·원격 STAC·래스터는 열지 않았다.16개 신규 시험은 단일descriptor와 실제 바이트/불변 사본, 저예산/과대파일의 before-open 차단, 정확1MiB whitespace 경계, hash 불일치 시 validator0호출, ref alias, 실제 hardlink, 모의 reparse/부모교체, 실제 growth/파일교체, partial read 관측, 엄격 시간/제품, validator 중 변경, app/backend 두 import, 병렬 독립 호출을 검사한다. 실제 Windows junction을 만들어 탐지하는 시험은 없으며 reparse attribute 거부는 합성으로 검증했다.

초판 focused281.log는 **16개 중15통과/1실패·1.714초**이며 원바이트 보존한다. 파일 descriptor가 열린 동안 os.replace를 시도한 fixture가 Windows의 공유삭제 제한으로 먼저 OSError 차단되어 기대한 REPLACED 코드와 달랐다. 제품 보호가 통과한 결과가 아니며 시험이 의도한 후경로 검사에 도달하지 못했다. descriptor close 직후/후stat 직전에 실제 교체하도록 fixture만 수정했다. 제품 source와 cap은 변경하지 않았다.

최종 `final281.log`는 **61PASS/3.963초·skip0**이다. 신규16개와 기존226/246 순수 계약 회귀를 한 번 함께 실행했다. 운영 성공이나 실제 PC STAC 호환성 시험이 아니다. 단위 시험의 초판/최종 횟수는 합산하지 않는다. 앱/서버/UI를 수정하거나 실제 QA를 반복하지 않았다.

226의 엄격 시각 결속은 그대로다. 예컨대 raw STAC의 nonzero 소수초를 초 단위 요청에 맞춰 자르거나 반올림하지 않는다.246의 PC/Sentinel-L2A/SCL20 정책에 맞지 않는 provider/layout도 자동 지원하지 않는다. 실제 공급자 자료의 호환성·진위는 미검증이며 이 어댑터 때문에 BLOCKED를 해제하지 않는다.

## 다음 실제 연결 조건

Root 독립검토 뒤에도 별도 SURVEY coordinator가 필요하다. 정확한 source/ledger/seed·현재예산을 동일global lock 안에서 검산하고 새65MiB 예약·실측metadata/COG 분리·2초/첫429·finally 미계측전액보존·trace/terminal/정산·안전한 신규 파일/registry 게시를 연결해야 한다. 이번 어댑터는 그중 로컬 STAC 파일 입력만 담당한다.

실라벨/SCL의 header·연도·공식 class·native footprint/주내95%·기존/pending/survey support와 scene/window/split 겹침은 별도 가드다. 이후173/175에는 explicit SURVEY lineage branch로만 연결하고 RGB완료행을 위장 생성하지 않는다. 실제 target 이미지 품질80%·나지256·각split0.5%/기여5·독립정답은 실제 취득/native/QA 이후 검증해야 한다. 지금 발견된 나지 후보나 실제 확보 증가량은0이며 학습 false다.

이 내부 격리 API는 UI 응답이나 운영 보유량을 바꾸지 않으므로 화면 수정은 필요 없다. Root에 소스/시험/로그/최종지문을 인계해 이해자료에서 “로컬 출처 파일 보호 연결부”와 “실제 나지 취득”을 구분하도록 요청한다. 이해자료 갱신은 Root의 별도 담당 인계이며 본 문서로 대신 완료했다고 보고하지 않는다.
