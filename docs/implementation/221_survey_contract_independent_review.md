# 221 라벨 전용 SURVEY 순수 계약 독립 검토

## 결론과 검토 범위

220은 요청·영수증의 **선언 일관성만 검사하는 순수 내부 계약**이다. 현 소스에는 아래 두 구현 보완 사항이 있다. 이 검토는 코드 읽기에 근거한 정적 판단이며, 추가 시험·재현 실행은 하지 않았다. 실제 파일 진실·SHA·원장·래스터·네트워크·성능을 검증한 결과가 아니다. 현재 실행·수집·학습 권한은 모두 false로 유지해야 한다.

읽은 대상은 220 소스·시험·구현 문서·freeze다. 장면 검사의 실제 의미를 확인하기 위해 순수 의존 함수 `references.esri_annual_plan`과 공식 주별 split 상수 선언도 좁게 읽었다. 운영 데이터·원장·지원 영상은 읽지 않았으며 코드 변경·collector 실행·HTTP·추가 시험은 모두 0회다.

freeze에 기록된 세 제품 파일의 실제 SHA 일치를 읽기 검산했다.

| 파일 | 동결 SHA-256 |
|---|---|
| `backend/app/data/bare_label_survey_contract.py` | `a0470b489db19a9c4ccafcada3374e87675e116af3a592068b7dfcda64cf9096` |
| `tests/test_bare_label_survey_contract.py` | `a1b2b913c7e225d9225833923d697af7c9866db142933e8d1b1b3104f953251e` |
| `docs/implementation/220_bare_label_survey_pure_contract.md` | `b7e3a2fc9096fa09758cb441e5d853b2a2d78c2e45d997b8f9f6ea962b739a65` |

freeze의 합성 60 PASS는 기존 담당의 시험 기록이다. 독립 검토 담당이 다시 실행한 시험으로 합산하지 않는다.

## F1 — 장면 ID의 달력·전체 형식·관측 시각 결속이 부족함

위치: `_scene`, 현 동결 소스 115~125행. ID 전체 문자 집합을 검사한 다음 `S2[ABC]_MSIL2A_<year>숫자4자리T숫자6자리_`의 시작 부분만 검사한다. 이후 `esri_annual_plan`은 문자열 안의 `_T<zone><latitude band><square>_` 부분을 검색한다. 이 의존 함수는 전체 Sentinel-2 ID 형식이나 날짜를 검증하지 않는다.

따라서 정적 제어 흐름상 다음 조합이 거부되지 않는다. 실제 실행 재현은 하지 않았다.

```text
id = S2A_MSIL2A_20249999T999999_x_T51MXR_x
source_group = southeast_sulawesi/<위 id>
datetime = 2024-06-01T00:00:00Z
```

ID의 월·일·시각이 존재하지 않아도 숫자 자리와 MGRS substring은 맞는다. datetime은 별도로 유효한 동년 시각이면 된다. 정상 ID에서도 ID 안의 관측일과 같은 해의 다른 `datetime`을 섞을 수 있다. 선언 datetime을 기간 안으로 두고 실제 ID 관측일은 기간 밖으로 두는 내부 모순이 발생할 수 있다. 실제 STAC 파일을 읽지 않는 한계와 별개로, 입력 선언 자체에서 확인 가능한 모순이다.

보완 제안은 허용하는 Sentinel-2 ID 변형을 명시한 전체 문법, 달력 파싱, MGRS zone 01~60 검증, ID 관측 시각과 선언 UTC datetime의 일관성 검증이다. 실제 STAC 표현에는 초 이하 시간이 있을 수 있으므로 후속 스키마의 허용 정밀도를 먼저 정하고 합성 `00:00:00` 형식만 실데이터 전체 규칙으로 오인하지 않아야 한다. source_group과 Esri 동년 supercell 결속은 유지한다.

추가 시험 제안: 불가능한 월/일/시각, prefix만 정상인 불완전 ID, zone 00/99, acquisition 날짜와 datetime 불일치, ID 관측일만 기간 밖인 입력, 허용하는 실제 STAC ID 형태와 시각 정밀도 경계. 현재 시험은 주로 다른 연도와 receipt/request 상이한 scene을 막으며 같은 request 내부 모순은 다루지 않는다.

## F2 — 잘못된 Unicode·동시 변경이 고정 오류 경계를 벗어날 수 있음

위치: `_copy`, 현 소스 55~76행 및 두 공개 validator의 호출 경계. 문자열은 길이만 검사하고 `ensure_ascii=False`로 직렬화한 뒤 UTF-8로 인코딩한다. Python 문자열에 lone surrogate가 있으면 `text.encode('utf-8')`에서 `UnicodeEncodeError`가 발생한다. 이를 `SurveyContractError`의 고정 코드로 변환하는 경계가 없다. 이 값은 Python dict 입력뿐 아니라 escaped surrogate를 허용하는 일부 JSON parser에서도 들어올 수 있다.

예를 들어 정상 request의 `seed.justification_ref.path`를 `evidence/integration/` 뒤에 `chr(0xD800)`이 포함된 문자열로 교체하면 길이·primitive walk를 통과한 뒤 UTF-8 변환에서 실패하는 정적 경로가 있다. 오류가 고정 코드라는 문서 계약과 맞지 않으며, 상위 호출자가 `SurveyContractError`만 처리하면 처리되지 않은 예외가 된다.

또한 `_copy`는 원 dict/list를 순회한 뒤 **같은 원 입력**을 다시 직렬화한다. 호출자가 동시에 dict를 변경하면 `item.values()` 순회 또는 JSON 직렬화 과정에서 `RuntimeError`가 발생할 수 있고, 현재는 고정 오류로 닫히지 않는다. 순회와 직렬화 사이에 구조가 바뀌면 앞서 확인한 depth/node 제한과 실제 복사한 객체가 달라질 수도 있다. 이것은 이미 반환된 canonical 문자열의 가변 참조 누출과는 다른, 복사 시점의 입력 경쟁 문제다.

보완 제안은 제한을 적용하면서 detached primitive 사본을 만들고 그 사본만 직렬화하는 것이다. Unicode 변환·입력 변경 관련 알려진 실패를 고정 코드로 변환하되 원래 입력이나 예외문은 포함하지 않는다. 기존 `SurveyContractError`의 상세 고정 코드는 보존한다. 실제 I/O는 필요 없다.

추가 시험 제안: 값·키의 lone surrogate, 복사 중 dict 변경으로 인한 RuntimeError, 실패 후 정상 요청의 검증 가능 여부, 반환 메시지의 입력/경로 비누출, 문자열/노드/깊이 cap을 복사한 객체에도 적용하는지 확인. 이 검토에서 해당 시험은 실행하지 않았다.

## 확인한 적절한 부분

정적 읽기에서 다음 계약은 명확하게 구현돼 있다.

- request와 receipt는 exact key set을 검사하고 불필요한 실행 필드를 허용하지 않는다. 주요 숫자는 `type(...) is int` 또는 bool을 배제한 유한 숫자 판정으로 오염을 막는다.
- 4GiB는 기존 추가 예산의 상한 선언이고, 65MiB는 한 batch의 COG 64MiB+metadata 1MiB 예약이다. `new_charged_bytes` 안에 포함된 pending을 잔액 계산에 다시 더하는 중복 차감 코드가 없다. 실제 원장과 pending 금액의 진실은 검사하지 않는다고 문서에 구분했다.
- 실측 선언은 metadata·COG 각각의 cap과 정확한 합계를 요구한다. 미정산 선언은 65MiB 전액과 실측 null만 허용하므로 계측 불명을 0원·부분환불로 바꾸지 못한다.
- 정책 값과 타입을 함께 검사하여 worker batch 수·요청 간격·재시도·첫429 중단을 요청으로 완화하지 못하게 했다. 218의 3GiB 로컬 검산 profile과 원격 수집 예산을 섞는 필드는 없다.
- receipt의 request/config/scene/batch key 결속, Esri v003 동년 URL·version·license 결속, 선택 scene의 SCL 정확히 1개 제한이 있다. 임의 URL 또는 다른 후보 장면의 SCL을 묵인하지 않는다.
- 경로는 lexical relative 경로와 SHA 형식을 제한하고 traversal·ADS·역슬래시·Windows device·빈 segment를 막는다. URL은 Esri 계획값과 exact 비교한다. 문자열·컨테이너·깊이·노드·canonical byte cap도 선언돼 있다. 실제 reparse/alias·파일 정체성은 후속 I/O 가드의 책임이다.
- 모든 승인 필드는 `is False`, 패치 수는 int 0으로 고정한다. 반환 객체는 frozen dataclass 안의 문자열·bool만 보관하고 `to_dict()`가 새 JSON 사본을 반환한다. 정상 반환 후 내부 dict/list를 통한 mutable escape는 발견하지 않았다.

직접 dataclass 생성이나 Python의 강제 속성 조작을 검증/권한의 보안 경계로 삼아서는 안 된다. 문서도 직접 생성을 검증 대체로 인정하지 않으며 receipt validator는 원 request를 다시 검증한다.

## 설계상 한계와 후속 연결 조건

현재 `SPLITS`는 공식 `FIXED_PROVINCE_SPLITS`와 값은 같지만 별도 mutable dict로 중복 선언돼 있다. 실제 불일치는 발견하지 않았다. 후속 소비자 연결 전에는 기존 canonical 선언을 재사용하거나 상호 불변 계약을 명시해 split 규칙이 서로 달라지지 않게 하는 편이 좋다. 이것은 F1/F2와 구분되는 유지보수 권고다.

grid 선언은 유한 north-up, 허용 UTM EPSG, 해상도·크기, 두 자산의 CRS 동일성만 검사한다. 실제 footprint·선택 장면 tile과의 지리적 정합·데이터 타입·픽셀·주내 범위·SCL 지원영역·B02와의 정렬을 증명하지 않는다. budget 선언도 실제 남은 예산·원 pending 2건 보존을 증명하지 않는다. SHA 형식 검사는 실제 파일 SHA 검증과 다르다. 이러한 한계는 220 문서에 대체로 정직하게 명시돼 있다.

실제 runner·원장·registry·173/175 소비자에 연결하려면 고정 파일 읽기·실제 SHA/CRS/grid·scene/footprint/alias·공유 lock/예산429·실측 정산과 실패 복구를 별도 검증해야 한다. 이번 정적 리뷰나 기존 합성 60 PASS만으로 실수집·정산 진실·나지 품질·성능·학습 승인을 주장할 수 없다. UI 변경도 없는 내부 계약이다.

F1/F2와 시험 제안을 Root에 전달했다. 코드 수정은 별도 224 담당 범위이며 221 담당은 소스·시험·기존 문서를 수정하지 않았다. 공통 이해자료에는 현재 **순수 계약 구현/기존 합성 시험 완료, 독립 정적 검토 보완 필요, 실행 연결 PLANNED** 상태를 반영해야 한다.
