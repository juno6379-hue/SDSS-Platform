# 230 명시 metadata profile·소비자 연결 격리 보완

상태: IMPLEMENTED_UNVERIFIED(공유 제품 적용·운영 검증 전), TESTED_SYNTHETIC(최종 시험 결과는 freeze 참조). 실제 원본/원장/모델 읽기, HTTP, 운영 QA, 수집 실행은 0이다. 모든 제품 수정은 `evidence/integration/preprocess230-workspace-20261018/` 안에만 있다. 228 원판과 역사 88 PASS/단일 whitespace 부하 31.148초·peak 406MiB는 보존하며, 이를 230의 실제 rich manifest 성능으로 확대하지 않는다.

## 쉬운 설명과 범위

현재 큰 목록 파일이 기존 64MiB에 가까워 다음 수집 뒤 목록을 읽지 못할 수 있다. 이번 변경은 운영자가 정확한 목록 SHA와 고정 profile을 명시했을 때만 source/candidate JSON을 최대 128MiB로 처리하는 연결이다. 용량을 보고 자동으로 상향하지 않는다. 선택하지 않으면 기존 64MiB 및 v1 산출물 계약이 유지된다. 원격 COG 64MiB+metadata 1MiB, 추가 원격 예산 4GiB, 개별 label/raster/header 64MiB, 물리 3000, 품질·분할·학습 승인 기준은 변경하지 않는다.

## 231 독립 리뷰 F1–F4 보완

- F1: staging `_copy_bytes`는 source 읽기와 destination 쓰기를 각각 실제 계측한다. 전체 양방향 잔여량을 새 출력 생성 전에 확인하고, 공유 예산 잠금 안에서 검산→I/O→계상을 수행한다. 부분 쓰기 예외는 unbuffered 파일의 실제 크기로 기록한다. 측정 불가능하면 시도량을 보수적으로 잡고 고정 오류로 중단한다.
- F2: `bounded_json_digest`는 확장자가 아닌 명시 역할(source/candidate/evidence/readiness/saved_plan/receipt/policy)로 cap을 선택한다. stat cap 검사를 open보다 먼저 수행하고 최초 크기만 읽으며 전후 descriptor/path/SHA 결속을 검사한다. 164 snapshot 복사와 JSON output도 같은 사전 검산·실제 부분 쓰기 경계를 따른다. normalization evidence는 기존 2MiB, readiness는 16MiB, receipt는 64KiB 등 더 작은 역할 상한을 유지한다. TIFF/XML은 별도 기존 범위다.
- F3: profile 자체가 source/candidate 128MiB, depth32, 총 scenes+historical_noneligible_patches 3000, tree visits 4M, 누적 metadata I/O 16GiB를 강제한다. caller 256MiB/depth64는 거절하고 더 작은 정책은 유지한다. descriptor·marker는 read-only다.
- F4: 공유 `ProfileResourceError`와 고정 자원 오류코드는 normalization의 일반 scene 오류 catch를 통과하여 전체 작업을 중단한다. 잘못된 개별 metadata 내용은 기존 scene 차단 동작을 유지한다. 자원 초과를 일부 행 제외 후 QA 완료로 바꾸지 않는다. app.ml/backend.app.ml 이중 import도 같은 예외 class/ContextVar를 사용한다.

## 동시성 계약

독립 요청은 `independent_operation`으로 scope를 새로 시작하고 finally reset한다. 명시 profile의 공유 Budget은 RLock으로 알려진 동기 I/O 전체를 직렬화한다. copy_context로 같은 Budget을 공유한 두 thread는 잔여량을 함께 검산하고 두 번째 read를 열기 전에 차단한다. 독립 thread/async scope, child task ContextVar 전파/reset은 합성 회귀 범위다. 임의의 await를 RLock 구간에 넣거나 모든 외부 비동기 I/O를 안전하게 만든다는 주장은 하지 않는다. 이것은 로컬 JSON 자원 guard이며 원격 CollectionLedger/운영 lock과 다르다.

## 173/182 Python·CLI 계약

173 discover와 182 propose는 keyword `manifest_profile=None`을 유지하며 CLI `--manifest-profile bounded128m-3000-v1`을 명시할 수 있다. source만 확장하고 선택 결과에 marker를 추가한다. 미지정 산출물에는 marker를 추가하지 않는다. source 원본/고정 사본의 전후 SHA를 검사하며, 173 CLI source/boundary 고정 사본·proposal/receipt 및 182 proposal의 새 JSON 쓰기는 명시 역할별 사전 검산/실제 쓰기로 계상한다.  label/header 파일 및 경계·config·proposal의 기존 개별 제한과 실행 false 상태는 유지한다. 임의 profile 이름은 argparse/함수 경계에서 거절한다.

## 225 예산·collection-status 내부 Root 설정

새 `collection_source_profile.py`가 작은 로컬 strict JSON을 요청마다 read-only로 읽는다. Root는 서버 시작 때 `app.state.collection_source_profile_path`에 DATA root 안의 고정 경로를 지정한다. 경로만 고정하므로 이후 수집에서 source SHA가 달라지면 서버 재시작 대신 Root가 새 SHA를 확인한 후 설정 파일을 명시 갱신한다. 쓰기 API나 브라우저 기술 옵션은 추가하지 않는다. 설정 예:

```json
{"schema_version":1,"kind":"ROOT_SELECTED_SOURCE_MANIFEST_PROFILE","manifest_profile":{"name":"bounded128m-3000-v1","sha256":"db44041c31fd28ef05c3157725fb07356e0799014f7d3300361d0f985ce6afe4"},"source_manifest_sha256":"ROOT가_검산한_현재_source의_소문자64자리_SHA"}
```

예의 source 값은 설명용이며 실행 가능한 설정이 아니다. 정확한 4개 top-level 키, profile name+descriptor SHA, 소문자64자리 source SHA만 허용한다. 4096B/깊이8/중복키·비유한숫자 거절, 로컬 regular 경로/전후 identity+SHA 검산을 적용한다. 설정 없음은 legacy64, 오염·변경 중·source pin 불일치는 UNCONFIRMED다. 현재 source가 바뀌어도 자동 추적·승계하지 않는다. 설정이 새로 생기거나 관측 중 바뀌어도 실패 폐쇄한다. 원장은 읽기만 하며 8MiB 제한/산식/old pending 보존 계약은 유지한다.

API budget/collection-status 두 reader가 같은 내부 선택을 쓴다. status 안 budget SHA와 source SHA가 다르면 수집 target 사용 가능성을 낮춘다. source가 커졌다는 이유로 frontend가 profile을 선택하지 않는다. 실제 서버 설정/재시작·브라우저 적용은 이번 단위에 포함하지 않는다.

## 게시 후보와 현재 source의 구분

`collection_priority_status.candidate_quality`는 기존 v1 pointer의 고정 3개 파일 SHA와 16MiB report를 보는 독립 UI 경로다. 228의 v2 QA comparison query와 혼용하지 않는다. 고정 cohort 검산이 성공해도 현재 source가 다르면 `source_matches_current_manifest=false`이고 이를 현재 품질 검증으로 표현하지 않는다. 게시 pointer의 파일 변조는 unavailable이다. 기존 1339/1342 게시 결과를 v2로 재판정·재발행하지 않았다.

## 사용·수락 및 적용 전 조건

격리 workspace의 `.runtime` 의존 경로로 Temp 합성 시험만 실행한다. 최종 log/freeze에 정확한 시험 수·시간·SHA를 기록한다. 핵심 수락 범위는 양방향/부분 실패 계측, cap-before-open/growing-file, explicit128/미선택64/오염 config, rows/depth/nodes/JSON I/O, 이중 import, 동시 scope, CLI 전달, pointer 구분, 기존 materialization/staging/QA/consumer 회귀다. 228 단일 부하는 whitespace 위주 경계 검증이며 복잡한 3000행/128MiB 실제 QA wall/RSS 보장은 없다. 해당 성능은 향후 별도 승인된 고정 입력으로 측정해야 한다.

`patch230-manifest.json`은 228 동결판 대비 변경만 기록한다. 232 소유 review_bare_targets179.py/collect_targeted_bare.py/targeted_inventory_profile.py/해당 시험, 공용 targeted_inventory·199·원장은 포함하지 않는다. 독립 리뷰와 Root의 별도 적용 승인 전 공유 제품 적용 0이다. 이후 Root가 이해 담당에게 코드·시험·한계·운영 미적용을 전달해 설명/FAQ/INDEX를 갱신한다. 현재 UI는 실제 반영하지 않았으므로 화면 완료로 보고하지 않는다.

## 시험 이력 해석

- 228 역사: 88 PASS / 74.061초, 단 한 번 whitespace 경계 부하 31.148초. 231 네 결함 발견 전 판이므로 안전성 완료 증거로 확대하지 않는다.
- 230 F1–F4 및 snapshot/output 보완 전 관련 174 PASS / 138.266초는 `profile230-related-pre-final-output-fix.log`로 보존한다.
- 164 snapshot/common output까지 보완한 관련 176 PASS / 181.901초는 `profile230-related-176-before-cli-output-final.log`다.
- 마지막 173/182 JSON 출력 계측 연결 뒤에는 해당 CLI·기존 consumer·공통 profile·230 집중 회귀를 추가한다. 전체 176을 마지막 코드판에서 다시 수행했다고 합산하지 않는다. 최종 추가 시험 결과와 정확한 SHA는 freeze230.json을 따른다.

예산 카드 source reader는 원본 내용으로 품질을 재계산하지 않는 스트리밍 SHA 관측이다. 선택된 128MiB 상한·현재 source pin·전후 안정성을 확인한다. rows/depth/nodes는 JSON 내용을 해석하는 164/173/182/status 및 materialization/QA reader가 검증한다. 예산 숫자가 표시되는 사실을 3000행 품질 QA나 모델 학습 승인으로 해석하지 않는다.

최종 173/182 출력 계측 연결 판은 **60 PASS / 31.711초** (`profile230-final-cli-output-check.log`)다. 앞선 동일 60개 실행에서는 신규 fixture를 DATA 밖에 둔 1건이 경로 보호에 거절되어 실패했고, 경로 보호를 유지한 채 Temp fixture를 DATA 안에 배치한 뒤 1건 독립 통과(0.471초)와 최종 60개 통과를 확인했다. 실패 로그/제한 진단도 보존한다. 최종 파일판을 전체176개가 다시 통과했다고 표현하지 않는다. 코드+문서는 같은 격리 단위로 마감하며 이해자료/실 UI 적용은 Root 후속 인계 사항이다.
