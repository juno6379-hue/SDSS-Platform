# 329 고정 역할 atomic JSON 저장기 — 격리 구현

상태: **TESTED_SYNTHETIC / 운영 연결 BLOCKED / 공유 적용 0**. 2026-10-19 KST에 마감했다. 산출물 식별자는 Root가 배정한 `target329-workspace-20261018`을 유지한다. 328 설계 중 저장기 한 부분만 구현했으며 CollectionLedger·170·worker·JSONL·stdout은 연결하지 않았다.

## 쉬운 설명과 범위

기존 JSON 파일을 즉시 덮어쓰면 중간에 디스크 오류나 예산 소진이 생겼을 때 반쪽 파일이 남을 수 있다. 이 저장기는 같은 폴더에 독점 임시파일을 만들고, 검증된 전체 내용을 쓴 뒤 기존 파일과 새 파일을 다시 확인해서 교체한다. 사용자는 반드시 교체할 기존 파일의 정확한 SHA256을 제공한다. 처음부터 없는 파일을 새로 생성하는 API는 이번 범위에 없다.

파일을 안전하게 교체하는 기능과 수집 예산을 정산하는 기능은 별개다. 이번 구현은 임시 합성 JSON만 대상으로 시험했다. 운영 원본·원장·모델·label 읽기/복사/쓰기, HTTP, collector, native, 모델 학습은 모두 0이다. 원격 예산 4GiB, COG 및 물리 패치 제한, 고정 split, 나지 및 품질 기준을 바꾸지 않는다. 내부 함수이므로 API·UI 변경이 없고 현재 서버 반영도 주장하지 않는다.

## 파일과 불변 기준

새 제품은 격리 사본의 `backend/app/data/targeted_atomic_json.py` 하나다. 새 시험은 `tests/test_target329_atomic_json.py` 하나다. 실행에 필요한 기존 `manifest_resource_profile.py`와 `split_json_io.py` 두 파일만 325 동결판에서 원바이트 복사했다. 이 두 파일은 main과도 같은 SHA임을 기준 작성 시 확인했으며 최종 동결에서 다시 대조한다. 운영 자료는 복사하지 않았다.

- 공통 profile: `73c9ba94cda1722ae87e7729ecd655ba5e9584fcb735c8c1f0e06734f8357d01`
- split JSON I/O: `81a40a9990d4fe0adfbb04c26030ccc5b0c26cbf460c1f02b3560c5bbc687ff8`
- 부모 freeze325: `c908ea546e8029dfc669fd716a34def18eb932e612922e33bf6381603cf6ee4e`

`baseline/`과 `baseline-manifest329.json`은 검토용 원판이다. 시험은 이 폴더를 읽지 않으며 빈 임시 배치에도 제품3개/시험1개만 복사해 실행했다. 325/319/328 문서·freeze는 수정하지 않았다.

## API와 고정 역할

```python
replace_json(root, target, payload, *, role, expected_sha256, manifest_profile)
replace_json_value(root, target, value, *, role, expected_sha256, manifest_profile)
```

첫 API는 정확한 `bytes`만 받으며 원문 그대로 검증·해시·저장한다. 두 번째는 정확한 JSON 기본형(dict/list/str/int/bool/None/유한 float)으로 입력을 분리한 뒤 `ensure_ascii=False`, 키 정렬, 공백 없는 JSON으로 직렬화한다. 사용자 정의 dict/list 하위형, 비문자열 키, cycle, 비유한 수, UTF8 surrogate를 거부한다. 두 API 모두 기존 파일 SHA와 정확한 profile 마커가 필수이며 caller가 numeric cap을 전달하는 인자는 없다.

| 내부 역할 | 최대 바이트 | 기존 공통 reader 역할 |
| --- | ---: | --- |
| config | 2,097,152 | local_config |
| ledger | 8,388,608 | status_report에 명시 narrow cap |
| source | 134,217,728 | source |

표와 마커는 불변 mapping이다. 다른 역할, bool 역할, 누락/오염/추가 key 마커, 다른 descriptor SHA, 누락/대문자/잘못된 SHA 입력을 거부한다. 마커는 `bounded128m-3000-v1`, SHA `db44041c31fd28ef05c3157725fb07356e0799014f7d3300361d0f985ce6afe4`다. 역할별 한도를 128MiB로 일괄 확대하지 않는다.

JSON은 중복 키, BOM/NUL, 비유한 수, invalid UTF8을 거부한다. 최대 depth32/node4,000,000은 기존 parser를 재사용한다. source는 scenes가 list여야 하고 `scenes + historical_noneligible_patches <= 3000`을 적용한다. source 이외는 exact JSON object가 필요하다. 이번 시험에서는 3000행 통과/3001행 차단과 depth 초과를 확인했다. 실제 128MiB rich JSON·4M node 경계의 새 대형 성능시험은 반복하지 않았다.

`replace_json_value`의 분리는 발견 가능한 중간 변경을 검사하고 결과를 caller와 공유하지 않는다. 원시 객체에 대한 원자 snapshot이나 변경 후 복원(ABA)을 보장하지 않는다. 분리된 결과만 직렬화하므로 이후 caller 변경을 저장하지 않는다. 직렬화는 같은 scope 안에서 수행하지만 메모리 연산을 디스크 I/O로 계상하지 않는다. 문자열/JSON encoder의 메모리 사본과 escaping 임시 할당이 발생할 수 있으며 128MiB peak RSS 보장은 없다.

## 실제 쓰기와 누적 예산

두 진입점은 동일한 명시 profile scope와 재진입 가능한 `io_transaction()`을 사용한다. 이미 활성 scope가 있으면 같은 Budget 객체를 재사용하며 16GiB를 새로 지급하지 않는다. 공통 helper의 default/legacy 동작과 기존 `write_measured`는 수정하지 않았다.

정상 순서는 다음과 같다.

1. payload의 byte cap·JSON 구조를 파일 open 전에 검사한다.
2. local 경로·각 부모 dev/inode·기존 regular file의 identity를 확인한다. symlink/reparse/hardlink를 거부한다. 기존 파일을 실제로 읽어 caller SHA와 일치하는지 같은 scope에서 검산한다.
3. 같은 폴더의 `.<이름>.target329.tmp`를 `xb`, `buffering=0`으로 독점 생성한다. 기존 temp가 있으면 즉시 실패하며 지우지 않는다.
4. 최대 65,536B 청크를 쓸 때마다 예산 여유를 먼저 검사한다. 우리가 만든 regular temp의 현재 size와 append offset이 실제 누적 쓰기량과 같은지 확인한다. 실제 write 반환값과 전후 size 차가 일치해야 한다. 정상 short write는 실제 바이트만 계상한 뒤 중단하며 재시도하지 않는다.
5. 예외 중 실제 size 차를 확인할 수 있으면 그 바이트를 계상하고 원 예외를 전파한다. fd/identity/반환량 측정이 불명확하면 시도 청크 전체를 보수 계상하고 `ATOMIC_JSON_WRITE_MEASUREMENT_UNKNOWN`으로 중단한다. 측정 불명 값을 0바이트로 보고하지 않는다.
6. flush/fsync 후 temp 전체 SHA와 identity, 기존 파일 전체 SHA와 identity, 부모 identity를 다시 확인한다. 새 파일을 교체 후 다시 읽을 예산까지 미리 확인한다. 이 모든 실읽기와 실쓰기 계상은 같은 잠긴 Budget 안에서 수행한다.
7. `os.replace()`를 한 번 호출하고 교체된 파일 전체 SHA를 실제 재검산한다. 성공 결과는 SHA/실쓰기량/그 시점 누적 JSON I/O/최대 예산/committed/coordinator_connected=False를 반환한다.

이 size 차 계측은 **우리 함수가 독점 생성한 unbuffered regular temp의 순차 append**에만 적용한다. 원 destination overwrite, seek 가능한 외부 임의 stream, opaque/pipe, JSONL/stdout의 일반 쓰기 helper로 사용할 수 없다. 원 파일을 같은 크기로 덮어써 size 차 0을 실제 쓰기 0으로 해석하는 경로가 없다. known partial cleanup도 읽을 예산이 있을 때 같은 scope에서 prefix SHA를 확인한 뒤에만 temp를 지운다.

정상 작은 시험의 계측식은 `reads=2×old_bytes+2×new_bytes`, `writes=new_bytes`다. 기존 Budget의 선행 7B를 넣은 합산도 확인했다. old SHA 최초검사/교체직전 재검사, temp SHA, 교체 후 SHA가 모두 포함된다. 실패 cleanup에 prefix를 읽었다면 그 읽기도 추가된다. stat/fsync와 메모리 SHA 연산 자체는 JSON body byte 계측에 포함하지 않는다.

## 실패·취소·경쟁의 해석

원 예외 클래스는 가능한 한 유지하며 resource error와 KeyboardInterrupt를 성공으로 바꾸거나 삼키지 않는다. temp 생성 이후 오류에는 다음 속성을 붙인다.

| 속성 | 의미 |
| --- | --- |
| atomic_json_commit_outcome | NOT_ATTEMPTED / APPLIED / UNKNOWN |
| atomic_json_committed | os.replace가 정상 반환했는지 |
| atomic_json_temporary_preserved | 우리 temp를 안전하게 삭제하지 못해 보존했는지 |
| atomic_json_measurement_known | 쓰기 측정이 확정됐는지 |

교체 전 실패는 기존 파일을 우리 코드로 변경하지 않는다. 외부 코드가 기존 파일을 교체했다면 그 외부 파일을 덮어쓰지 않으며, 이를 원파일 보존 성공으로 꾸미지 않는다. temp는 부모·소유 inode·size·known prefix SHA가 모두 같고 cleanup 읽기 예산이 있을 때만 지운다. 외부 temp로 바뀌거나 예산이 없거나 측정 불명이면 남긴다. 부모가 이동되면 이전 폴더를 찾아가 삭제하지 않는다.

`APPLIED` 후 검증 실패는 새 내용이 이미 적용됐을 수 있으므로 자동 rollback/재시도하지 않는다. replace 호출이 예외를 던지면 호출자가 실제 적용 여부를 확정할 수 없으므로 `UNKNOWN`이다. 시험은 실제 replace 후 예외를 던지는 모형으로 이 구별을 확인했다. committed=False만 보고 미적용으로 단정하면 안 된다. 그 후에는 Root의 별도 bounded 복구 판정이 필요하다.

같은 Budget에서는 전체 I/O 구간을 직렬화하고, 다른 Budget의 협력 writer는 같은 독점 temp 이름으로 경쟁하여 한 번에 한 writer만 준비할 수 있다. 최종 SHA 확인과 OS replace 사이를 악의적인 외부 writer에 대해 원자 CAS로 잠그지는 못한다. OS별 강한 디렉터리 handle 고정/파일 잠금, 디렉터리 fsync와 전원 차단 영속성, 다중 파일 정산 트랜잭션은 이번 보장 범위가 아니다.

## 시험 근거와 이력

- 최초 집중판: 24 PASS / unittest 2.273초. `focused329-first.log` 보존.
- 확장판 최초: 30건 중 29 PASS·1 ERROR / 6.497초. 열린 temp의 부모 rename을 Windows가 WinError5로 거부한 fixture 시점 오류다. `focused329-parent-fixture-failure.log`와 수정 전 시험 원판을 보존했다.
- 제품 기준을 바꾸지 않고 temp close 직후 첫 부모검사 hook에서 rename하도록 시험만 수정했다.
- 최종 집중판: **30 PASS / 4.878초**, wrapper 6.819954초, skip0.
- 외부 baseline 없는 임시 배치: **동일 30 PASS / 4.437초**, wrapper 7.202484초, skip0. 고유 60사례로 합산하지 않는다.

시험은 정상 실제 byte 계측·scope 재사용·3역할·잘못된 marker/role/pin·oversize 전 open0·JSON 오염·3000행/history·depth·기존 ledger8MiB 초과 사전 차단·temp 충돌·partial/unknown 쓰기·취소·fsync 실패·외부 destination/temp/parent 교체·교체전 예산 소진·postcommit 실패·replace outcome 불명·동일 파일 writer 경쟁·hardlink·없는 destination·분리 직렬화를 다룬다. 운영 함수나 네트워크를 호출하지 않았다. Linux RSS를 측정하지 않았고 Windows RSS/peak도 이번 단위는 관측하지 않았다. wall은 위 wrapper 실측이며 성능 SLA가 아니다.

실행 명령은 격리 workspace를 cwd로 `python -X utf8 -m unittest discover -s tests -p test_target329*.py -v`다. portable 배치는 baseline/외부 workspace 없이 runtime3개와 시험1개만 새 Temp 폴더로 복사했다. 결과 JSON은 그 복사 지문과 baseline 부재를 기록한다.

## 다음 인계와 남은 차단

`patch329-manifest.json`, `patch329.diff`, `freeze329.json`이 최종 제품/시험/로그/문서와 원판 불변 지문을 결속한다. 독립 정적 검토와 Root baseline 대조 전에 main으로 복사하지 않는다. 다음 가장 작은 단위는 별도 승인 후 writer 오류 상태를 caller 정산 상태와 연결하는 격리 계약이며, 실제 CollectionLedger/170 연결은 아직 없다. 전체 metadata16GiB 연결 완료, 원격 품질 통과, 나지 확보, 학습 준비 완료로 해석하면 안 된다. 이해자료는 Root가 검토 완료 후 별도 understanding_agent에 이 문서와 freeze를 전달한다.
