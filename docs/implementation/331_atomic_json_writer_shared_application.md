# 331 — 고정 역할 JSON 저장기의 공유 적용

## 문제와 결과

명시 128MiB 사전검사 뒤에도 실제 수집기의 원장·상태 저장 경로는 전체 JSON I/O 계측에 연결되지 않았다. 이번 단위는 그 연결에 사용할 기존 파일 교체 저장기를 공유 코드에 추가한다. 실제 원장 연결은 다음 격리 단위로 남긴다.

Root는 329 동결판과 330 독립 검토를 읽고 16개 동결 참조·기존 공통 모듈 2개 지문·새 파일 부재를 확인했다. 새 `backend/app/data/targeted_atomic_json.py`와 `tests/test_target329_atomic_json.py`만 원바이트 복사했다. 기존 제품 파일을 덮어쓰지 않았으며 329 격리 원판·실패 로그·freeze는 보존한다.

## 계약과 사용 범위

`replace_json(root, target, payload, *, role, expected_sha256, manifest_profile)`은 bytes를, `replace_json_value`는 분리된 JSON 기본형을 저장한다. 기존 파일 SHA와 정확한 마커가 필수다. config2MiB/ledger8MiB/source128MiB 고정 역할만 허용한다. source의 scenes+history3000/depth32/node4M와 동일 16GiB scope를 적용한다.

기존 파일 실제 읽기·임시 파일 실제 부분 쓰기·임시/기존 파일 재해시·교체 후 재해시를 같은 누적 예산에 계상한다. temp는 독점 생성한 unbuffered regular file이며 임의 외부 stream이나 JSONL/stdout용 helper가 아니다. 불명확한 쓰기는 해당 청크 상한으로 보수 계상하고 중단한다. 자동 재시도나 rollback은 없다.

## 독립 검토의 한계 인계

330 문서 SHA a39b4eba4f078e197be275f30f6df7b7f3e85290048b9a9861a376c34369e508은 이 저장기 범위에서 필수 차단 결함을 발견하지 않았다. 다음 한계를 그대로 유지한다.

- UNKNOWN은 미적용이 아니다. replace가 실제 적용된 뒤 예외가 났을 수 있다. committed=False만 보고 원상태라고 판단하지 않는다.
- temporary_preserved=True는 안전한 cleanup을 확인하지 못했다는 보수 상태다. 실제 temp 경로 존재를 검사한 증거가 아니며, UNKNOWN에서는 이름이 이미 사라졌을 수 있다.
- JSON 저장 보호는 old pending의 업무 규칙 보존을 대신하지 않는다. 원장 caller가 기존 pending/행/history와 정확한 예약·정산 차액을 별도로 검증해야 한다.
- 값 API는 역할 검증 뒤 메모리 분리·직렬화를 하고 최종 bytes 함수에서 마커와 SHA를 검사한다. 잘못된 입력에도 일부 메모리 처리가 먼저 일어날 수 있으나 파일 I/O 전에는 거부한다.
- 최종 검사와 OS replace 사이의 비협력 외부 변경을 원자 CAS로 막지 않는다. 전원 차단 영속성·디렉터리 fsync·다중 파일 트랜잭션을 보장하지 않는다.

## 검증 증거

329 최초 집중24건 통과 뒤 확장30건 중1ERROR가 있었다. Windows가 열린 temp의 부모 이동을 거부한 fixture 시점 문제였으며 원 로그와 수정 전 시험을 보존하고 시험 시점만 교정했다. 최종 집중30건 4.878초·portable 같은30건4.437초가 통과했다. 두 실행은 같은 사례이므로 60건으로 합산하지 않는다.

공유 적용 뒤 해당 시험 **30건 모두 통과: unittest2.484초/wrapper3.860초**. 공유 로그 SHA174a0d6eb7cb80c38da5c724752d9468e17cc17503d5fd355db348d8fd0eafc4. 기존 공통 모듈은 지문이 같고 새 저장기를 호출하는 기존 제품 경로가 없으므로 이전146건 전체 회귀와 큰 파일 벤치마크·운영 native/QA는 반복하지 않았다.

`evidence/integration/target331-application-root-20261019/application.json`은 적용 당시 시험 전 상태를 보존한다. `completion.json` SHA f3c72cbe7115f9a44d4c4c2e159001b75774dfdcfcc1117f89812842b888ac67은 새 제품·시험/공통2·운영5 지문의 불변과 30건 통과를 확인한다. 운영 확인은 해시 읽기이며 운영 파일 변경·전수 물리 재검사·운영 preflight가 아니다.

## UI·후속·미완료

새 API route나 화면 계약이 없는 내부 함수다. 서버 재시작·새 화면 조회를 하지 않았고 실행 중 서버가 새 함수를 사용한다고 주장하지 않는다. 마지막 실제 API/브라우저323 증거를 보존한다.

332는 별도 격리 사본에서만 CollectionLedger의 명시 adapter와 업무 규칙 검산을 연결한다. 기존 metadata_io=None의 기본 동작을 보존하고 실제 운영 원장 초기화·예약·환불·원격·수집·170/worker 연결은 하지 않는다. 독립 검토 전 공유 반영하지 않는다.

원본1407/최소수량 부족0·후보1391·나지3차단/학습false·잔여1799757940B·oldpending136314880B 사용 포함과 원본·모델·고정 split·187 archive·4GiB/2worker/공유2초/첫429/물리3000/batch64COG+1metadata를 보존한다. 전체 개발과 독립 정답·나머지5모델 확보는 미완료다. 별도 이해자료에 실제 공유 적용과 위 한계를 후속 반영한다.
