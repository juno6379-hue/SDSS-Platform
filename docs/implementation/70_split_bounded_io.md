# 70. Split JSON IO의 선택적 크기·안정성 제한

상태: **TESTED_SYNTHETIC**, **VERIFIED_REAL_FIXED_JSON_METADATA_ONLY**. 기존 planner·validator·writer에 명시적 `io_policy`를 전달할 때만 엄격한 bounded JSON IO를 사용한다. 후보 orchestrator나 새 CLI는 아직 구현하지 않았으며 이번 단위에서 실제 후보를 생성하지 않았다. Root의 실제 검증은 기존 세 JSON을 읽는 validator 1회로 제한했다.

## Root 실제 읽기 전용 검증

`VERIFIED_REAL_FIXED_JSON_METADATA_ONLY`: 저장 계획·원본 manifest·기존 readiness의 세 고정 JSON에 위 선택 정책을 명시하여 validator를 1회 실행했다. 종료0, 48.609초, `METADATA_INTEGRITY_VERIFIED/plan_integrity_valid=true`다. 근거는 `evidence/integration/split-bounded-io-live-20261017.json`(3,929바이트, SHA256 `f17695093b5be51cfaa34326a6673e7b0711c158a8d127738cc0da6ec834f36a`)와 같은 접두사의 `live-run` 로그다. 세 입력의 기존 고정 SHA를 전후 대조했다.

source 64MiB/readiness 16MiB/saved_plan 4MiB/candidate 64MiB, 출력 plan 4MiB/candidate 64MiB, 깊이32를 설정했다. 후보를 입력하지 않았으므로 `candidate_validation.status=NOT_REQUESTED`, 무결성값과 참조는 null이다. 기존 계획의 제외16/예상적격1095(628/217/250)를 재계산했으며, 실제 원본1384행/기존 적격1111(628/233/250)은 변하지 않았다. 과거44의 실제 validator JSON에서 CLI 전용 `caller_policy` 래퍼만 제외한 전체 결과와 타입까지 일치함을 확인했다. 구버전 검증을 중복 실행하지 않았다.

이번 읽기 검증은 전체 계획 메타데이터 재계산을 수행한다. 69의 선택된 계보 연결(`full_planner_recomputation=NOT_PERFORMED`)과 구분해야 한다. 실제 writer·후보 산출물 생성·등록·raster/기하/정확 클래스 재검사·훈련·승인은 수행하지 않았다.

전체 회귀는 **691개/690 PASS/기존1 SKIP/298.655초/종료0**이다. 관련45 PASS/15.560초와 독립 신규20 PASS/5.243초·기존25 PASS/11.972초는 같은 시험의 반복 검증이며 전체 건수에 중복 합산하지 않는다. 보호 참조134개·기존 계약26개·고정 입력3개의 SHA와 catalog14행 canonical SHA가 불변이다. 기존 추적 backend/scripts/tests/data/frontend 변경은 지정한 `split_planning.py`, `split_validation.py` 두 파일뿐이다. 신규 helper·시험·문서를 별도 추가했다. 전체 workspace 파일 불변이나 물리 원본 인증을 의미하지 않는다. 근거는 `evidence/integration/split-bounded-io-live-integrity-20261017.json`과 `split-bounded-io-full-tests-20261017.log`이다.

## 구현 호환 상세

수정한 기존 코드는 `backend/app/ml/split_planning.py`, `backend/app/ml/split_validation.py` 두 파일이다. 공유 구현은 신규 `backend/app/ml/split_json_io.py`, 합성 시험은 신규 `tests/test_split_bounded_io.py`다. 기존 policy·분할 선택·학습 gate·후보 schema를 바꾸지 않는다.

다음 함수에 keyword-only 선택 인자를 추가했다.

- `plan_split_repair(..., io_policy=None)`
- `write_plan(..., derived_manifest=None, io_policy=None)`
- `validate_split_repair_plan(..., candidate_sha256=None, io_policy=None)`
- `digest(path, *, io_policy=None, role='source')`
- `load_json_document(path, *, io_policy=None, role='saved_plan')`

`io_policy=None`은 기존 읽기·직렬화 분기를 사용한다. 기존 positional 호출과 반환 JSON의 key·상태·분할·계수를 유지한다. 일반 `digest`의 기존 byte 해시는 그대로이며, 선택적 bounded digest는 JSON으로 엄격히 파싱한 뒤 SHA를 반환한다. 이 차이는 opt-in 사용에 한한다.

## 정책 계약

```python
io_policy = {
    'input_caps': {
        'source': 64 * 1024**2,
        'readiness': 16 * 1024**2,
        'saved_plan': 4 * 1024**2,
        'candidate': 64 * 1024**2,
    },
    'output_caps': {
        'plan': 4 * 1024**2,
        'candidate': 64 * 1024**2,
    },
    'max_depth': 32,
}
```

정책은 위 세 키만 허용하고, input/output 역할 집합도 정확히 일치해야 한다. 각 byte cap은 exact `int` 1~256MiB, depth는 exact `int` 1~64다. bool/float·0/음수·추가/누락 키를 거부한다. 생성 시 정책의 역할 map을 복사하고 읽기 전용 mapping으로 보관한다. 원본 정책 dict를 나중에 바꿔도 이미 시작된 IO context의 한도는 바뀌지 않는다. 공개 호출에 dict를 전달하면 새 context를 만든다. validator가 내부 planner와 동일 context를 공유하여 중첩 호출의 첫 입력 binding을 보존한다. context를 의도적으로 재사용해도 기존 첫 바이트/target/stat binding을 초기화하지 않으며 변경 입력을 거부한다.

`source`·`readiness`의 `_load_bound`는 기본/opt-in 모두 **명시 SHA가 필수**다. opt-in은 exact string 소문자 64hex를 파일 open 전에 검사한다. 초기 구현은 범용 reader의 `expected=None`을 그대로 넘겨 필수 pin이 없는 planner가 통과할 수 있었다. 독립 합성 검토로 발견하여 `_load_bound`에서 필수 검증을 복구했고, source/readiness의 None·bool·int·대문자·잘못된 형식을 planner/writer 양쪽 회귀로 확인했다. 범용 digest/load는 pin 없는 로컬 JSON 읽기를 허용하지만 이 예외를 planner의 필수 출처 pin에 적용하지 않는다.

## 읽기 방식과 재검증

opt-in은 원래 logical 경로를 resolve 전에 보관한다. UNC/URL·drive-relative·ADS·Windows 장치명·끝점/공백 등 모호한 경로는 사전에 거부한다. 일반 로컬 파일인지, stat 크기가 역할별 cap 이하인지 확인하고 descriptor를 열어 동일한 size/mtime/ctime/device/inode를 확인한다.

각 read는 고정 크기 요청(최대 65,536바이트)을 반복하며 최대 `cap+1` 바이트까지만 반환받는다. 사전 크기 초과는 파일을 열기 전에 거부하고, 읽는 동안 성장해 cap을 넘거나 descriptor/stat·logical→resolved 대상이 달라지면 거부한다. 입력의 실제 읽기 길이와 최초 stat 크기도 같아야 한다. SHA는 이 bounded read의 바이트로 계산한다.

파싱 전 strict UTF-8/no BOM/NUL과 문자열 quote·escape를 고려한 container 깊이 scan을 적용한다. UTF16/32로 깊이 검사를 우회할 수 없으며 중복 키·NaN/Infinity·비유한 float·유효하지 않은 surrogate 문자열을 거부한다. container root를 깊이1로 세고 scalar/key는 container 깊이를 추가하지 않도록 read와 output 검사 기준을 통일했다.

context는 logical 경로의 최초 resolved target/stat/SHA를 유지한다. planner의 source/readiness 재읽기, validator 초기 SHA/문서 읽기·planner 재계산·종료 SHA 검증, writer 출력 전 source/readiness 재읽기·마지막 입력 검증에 같은 bounded 정책을 전파한다. bounded 분기에서는 `Path.read_bytes()`를 사용하지 않는다. `verify()`는 저장된 입력을 다시 bounded read·strict decode하여 첫 SHA와 target/stat가 같은지 확인한다.

**각 read의 cap은 전체 호출의 누적 IO 예산이 아니다.** validator의 중첩 planner와 최종 확인으로 동일 JSON을 여러 번 읽을 수 있다. 전체 바이트 예산·IO 횟수 또는 hard CPU/time/memory cap은 이번 계약에 포함하지 않는다. 전후 상태와 SHA 대조는 OS 원자적 다중 파일 snapshot이나 적대적 경로 교체의 완전한 원자 방어를 뜻하지 않는다.

## writer의 두 출력 사전 측정

opt-in writer는 기존 후보 문서를 기존 방식으로 구성한다. status는 `PLANNED_DERIVED_CANDIDATE`, `executed=false`, `learning_ready=false`이며 원본 scene deep copy와 retained index·source/policy lineage를 보존한다. 파일 생성은 기존 writer만 수행하고 중복 후보 writer를 만들지 않는다.

먼저 plan과 선택적 candidate **두 문서 모두**에 대해 JSON 타입·유한 값·깊이·cycle/문자열 Unicode를 확인하고, `JSONEncoder(ensure_ascii=False, indent=2, allow_nan=False).iterencode()`로 실제 UTF8 byte 수를 측정한다. 어느 출력이라도 한도를 넘거나 직렬화가 실패하면 부모 mkdir과 첫 출력 생성 전에 예외를 낸다. JSON encoder가 거대한 단일 문자열 fragment를 만들 수 있고 후보 deep copy도 있으므로 streaming이 전체 메모리 hard cap을 보장한다고 주장하지 않는다.

입력 재검증과 출력 logical target/parent·기존 파일/깨진 symlink/입력 별칭 검사를 마친 뒤 부모를 만들고 경로를 다시 확인한다. 출력은 `xb` exclusive로 생성하여 각 chunk 쓰기 직전 byte cap과 측정 길이를 다시 제한한다. 플랫폼 newline을 적용하므로 기존 text writer의 Windows CRLF를 포함한 바이트 형식을 합성 fixture에서 동일하게 확인했다. 기본 None 분기도 그대로다.

candidate를 먼저, plan을 다음에 쓰는 기존 순서를 유지한다. 마지막 입력 재검증이 실패하거나 디스크/쓰기 오류가 나면 함수가 예외를 발생시킨다. 부분 새 파일·이미 끝난 sibling 파일은 자동 삭제하지 않으며 기존 입력·원장·lock도 정리하지 않는다. **함수 예외 후 남은 파일은 검증 완료 후보가 아니다.** 이번 단위는 성공 receipt·등록·공개를 만들지 않으므로, 다음 orchestrator가 roundtrip validator 성공 후 별도 완료 근거를 생성해야 한다. 두 파일의 원자 commit도 보장하지 않는다.

## 시험과 실제 사용 범위

최종 관련 합성 회귀: **45 PASS / 15.560초 / 종료0**. 신규 bounded IO 20건 + 기존 planning 8건 + 기존 validation 17건이며, 중간 17/19/42/44건 실행과 중복 합산하지 않는다.

```powershell
$env:PYTHONPATH="$PWD\.runtime;$PWD\backend;$PWD\tests"
python -m unittest test_split_bounded_io test_ml_split_planning test_ml_split_validation -v
```

로그: `evidence/integration/split-bounded-io-related-20261017.log`. 작은 임시 JSON만 사용했다. exact 정책·역할별 input cap·사전 open 차단·cap+1 성장·descriptor/논리retarget·strict UTF8/깊이/중복/비유한/surrogate·필수 pin·재계산 중 변경·bounded 재읽기·원본 바이트 보존·정책 복사/재사용 binding·기본/opt-in JSON 결과 및 writer byte 동일성·양출력 mkdir 이전 측정·stream 한도 재검사·부분 쓰기·출력 후 입력 변경 예외를 확인했다. 기존 17 validation 및 8 planning 회귀도 통과했다.

실제 호출 예시는 다음과 같다. 실제 입력의 SHA를 caller가 별도 신뢰 근거로 고정해야 하며, 저장 plan에서 꺼낸 SHA만 믿는 형태로 바꾸지 않는다.

```python
result = validate_split_repair_plan(
    saved_plan, source_manifest, expected_source_sha256,
    province_splits=fixed_province_splits,
    readiness_path=old_readiness,
    readiness_sha256=expected_old_readiness_sha256,
    data_root=data_root,
    io_policy=io_policy,
)
```

Root가 실제 saved-plan/source/old-readiness 세 JSON을 읽는 검증 1회와 전체 회귀·보존·운영 인계/이해자료를 맡는다. 담당은 실제 후보 생성·assess·raster/pixel·학습·수집·다운로드·Registry·원장/lock/예약·분할·모델 변경을 수행하지 않았다. 새 API/UI나 실행 중 서버 연결을 추가하지 않는 내부 IO 정책이므로 화면 변경은 필요 없다. 다음 후보 orchestrator/roundtrip receipt는 **PLANNED**이며 이 단위 완료가 전체 개발 완료나 학습 준비성 승인은 아니다.

## 후속 실제 후보 패키지 — 구현 71

[71 후보 생성·재검증](71_candidate_materialization.md)에서 기존 bounded writer/validator를 연결하여 새 evidence 후보1368행과 마지막 완료receipt를 실제 생성·대조했다. 원본1384행은 보존하며 후보계획 적격1095는 실제 raster 준비성 결과가 아니다. 후보는 PLANNED_DERIVED_CANDIDATE/learning_ready=false/executed=false, 미등록·readiness NOT_ASSESSED다. 이 문서의 이전 미생성/PLANNED 기록은 해당 단위의 역사이며, 최신 생성 상태는71의 고정 SHA/근거를 참조한다.
