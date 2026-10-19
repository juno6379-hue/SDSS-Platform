# 237 명시 profile 전체 metadata I/O 누락 보완 — 격리 revision

상태: IMPLEMENTED_UNVERIFIED(공유 적용·운영 검증 전), TESTED_SYNTHETIC(Temp 시험). 230/228 동결 원판과 공유 main은 변경하지 않았다. 실제 운영 data/원장/모델 읽기·복사, HTTP, collector, 운영 QA는 0이다. 새 작업은 `evidence/integration/preprocess237-workspace-20261018/`의 고정 코드 사본에서만 수행했다.

## 쉬운 설명

230은 큰 source 목록과 주요 복사 경로를 계측했지만, 같은 작업이 읽는 작은 경계·설정·과거 보고서와 UI 포인터 일부를 빠뜨렸다. 237은 실제로 파일을 읽을 때마다 같은 로컬 자원 예산에 합산한다. 작다고 빼지 않고, 다시 읽으면 다시 합산한다. 캐시에 있어 실제로 읽지 않는 경우는 파일 크기를 다시 합산하지 않는다. 자원 초과가 나면 일부 빈 결과를 성공으로 이어 가지 않고 그 작업을 중단한다.

이것은 원격 다운로드 예산이나 품질 승인 변경이 아니다. source/candidate128MiB의 명시 선택, 미선택64/v1, scenes+history3000, depth32/node4M, 로컬 metadata I/O16GiB를 유지한다. 원격 추가4GiB, COG64MiB+metadata1MiB, 개별 raster/label/header64MiB, 품질80/95·나지256·분할·학습 false gate는 그대로다.

## 입력과 소유

최종 독립 리뷰 `231_manifest_profile_followup230_review.md` 12755B/SHA `6f47181a067963cd7f05d42e63a9c1a435c8754d05f773bbed230fb53d441e4f`를 직접 검산한 뒤 고정 누락5범주만 수정했다. 237 입력 manifest는 230 동결판에서 복사한 코드/설정/시험333개를 기록한다. operational data/model/ledger는 복사하지 않았다. 기존 baseline-code는 기본 출력 비교용 코드 사본이다.

소유 제품은 공통 `manifest_resource_profile.py`, `find_bare_targets173.py`, `propose_deficit_centers182.py`, `app/data/candidates.py`, `collection_status.py`, `collection_priority_status.py` 여섯 파일과 신규 `test_manifest_profile237.py`다. 232179/170/profile/test4파일, 공용167/199, collector/원장은 변경·적용 목록에 포함하지 않는다. patch237은 동결230에 대한 delta이며 main에 디렉터리 통째로 복사하면 안 된다.

## 의미별 상한·API

| 명시 역할 | 상한 | 적용 호출 |
|---|---:|---|
| source / candidate | 각각128MiB | source manifest, 게시 고정3파일의 source/candidate hash |
| boundary | 2MiB |173 boundary 전후 pin,182 및 validator 경계 |
| local_config / local_plan / proposal | 각각2MiB |182 설정/기존안/신규안 및 validator |
| readiness | 16MiB | 저장 QA/readiness report·그 hash |
| evidence | 2MiB | normalization evidence, 게시 bare report |
| pointer | 64KiB | 게시 candidate/bare 포인터 |
| status_report | 16MiB | 과거 run/reference 등 UI 상태 보고서 |

`status_report16MiB`는 기존 unbounded status 읽기를 **명시 profile 안에서만** 제한하는 새 상한이다. 기존 작은2MiB/64KiB/16MiB는 늘리지 않았다. historical annual은 호출 위치에서 source, readiness는 readiness로 구분한다. 파일 크기·확장자를 보고 source128로 자동 분류하지 않는다.

`read_metadata(path,role,expected=None)`는 공통 bounded digest/capture를 통해 한 번 읽어 `(document,digest,raw)`를 반환한다. 열기 전 regular/role cap/잔여량을 검사하고 최초 stat 크기만 chunk로 읽어 실제 byte를 계상한다. descriptor/path/stat 전후 검산·명시 pin·strict UTF8/중복키/유한숫자/깊이·node/row를 확인한다. 성장·교체·다른 pin은 canonical ProfileResourceError로 중단한다. 기존 오류 detail/path를 API 응답에 새로 노출하지 않는다.

`metadata_identity(path,role)`는 stat-only cache 검산 API다. cache key는 논리경로+role+size/mtime/ctime/device/inode이며 hit 뒤에도 같은 논리경로/identity인지 확인한다. role 없는 metadata hash는 `MANIFEST_JSON_ROLE_REQUIRED`로 막는다. 이전 legacy cache를 명시 profile cache로 무계측 승계하지 않는다. 이 캐시는 metadata identity의 안정성을 신뢰하는 기존 최적화이며 모든 identity 필드를 위조하는 외부 행위까지 탐지한다고 주장하지 않는다.

## 누락5범주의 연결과 오류 경계

1.173 `pin`은 boundary JSON과 label binary를 명시 구분한다. boundary 전후·CLI proposal 최종 재해시는 같은 예산에 계상하고, 기존 label raster 읽기는 기존 binary scope를 유지한다. CLI 새 JSON 쓰기는230의 실제 쓰기 계측을 유지한다.
2.182 입력 tuples에 source/boundary/local_config/local_plan 역할을 결속한다. 초기와 두 번 후속 검산을 모두 계상하고 최종 proposal 직접 read_bytes 해시를 공통 bounded hash로 바꾼다.
3.validator는 active profile에서 boundary와 prior/proposal2MiB reader를 쓴다. 파싱한 document digest와 마지막 해시가 같아야 하며 boundary도 마지막 재검산한다. legacy 기본 함수 반환·출력은 그대로다. keyword json_role은 local_plan/proposal만 허용한다.
4.status의 과거 annual/run/readiness/reference 보고서는 호출 위치의 명시 역할로 읽는다. same_hash cache miss JSON을 계상하며 normalization_qa는 evidence로 연결한다. collection_manifest라는 kind는 QA가 받은 입력 manifest를 뜻하여 staged candidate일 수도 있다. status는 current/명시 source 보고서의 정확 경로 context로만 source 역할을 정하고, 게시 candidate는 별도 고정3파일의 candidate 역할을 사용한다. kind만 보고 임의 입력을 source로 지정하지 않는다. input_image/label/quality_mask/official XML은 명시 binary scope다. kind 없는 미분류 파일은 explicit scope에서 역할 요구 오류로 중단하여 JSON을 무계측으로 우회하지 않는다.
5.게시 candidate/bare pointer/report도 공통 reader를 쓴다. candidate 고정3파일의 의미는 순서에 결속된 source/candidate/readiness다. 실제 QA report 재읽기는 다시 계상하며 앞선 파일 pin과도 맞춰야 한다. v1 게시 cohort와228 v2 comparison은 섞지 않는다. 현재 source와 다른 과거 게시 cohort의 available/source_matches_current=false 의미를 보존한다.

read_report/candidate_quality/bare_target_review의 일반 ValueError catch 앞에서 canonical 자원 예외를 재전파한다. current source pin 오류도 부분 빈 inventory로 계속하지 않고 configured wrapper에서 전체 UNCONFIRMED가 된다. 일반 legacy malformed 보고서의 기존 unknown/unavailable 처리는 바꾸지 않는다.

## 시험과 관측 경계

Temp의 작은 JSON을 실제 byte-reader wrapper로 관측하여 계상량과 물리 read byte 합이 같은지 비교했다. 182 전체 경로의 반복은 source3회/boundary7회/config3회/prior5회/proposal3회다. validator도 boundary/plan 각각 파싱+최종 재해시를 계상한다. 낮은 예산·개별 cap 초과는 open 전에 거절하고, 성장 파일은 최초 크기만 읽은 뒤 중단한다. cache hit는 실제 read0/계상0이며 role 변경이나 inode 교체는 새 읽기를 요구한다.

최초 새 집중16개는6.916초에 통과했다. 초기 inherited40 시험의1건은 공유 pin이 label도 읽는다는 호출 구분을 드러냈다. label에 명시 binary, boundary에 명시 JSON 역할을 주어 바로잡았다. 보호 cap을 완화하지 않았다. 최종 추가 시험은 validator 교체 중단,182 기본 proposal 원바이트 동등, status 기본 결과 동등, 양 import의 동일 예외/예산, v1 게시 분리, 전체 UNCONFIRMED 전파를 포함한다. 최종 관련 수·시간·log SHA는 freeze237에 기록한다.

새 실제128MiB 부하나 rich3000행 QA는 실행하지 않았다. sparse cap+1 파일은 읽기 전 거절 시험이며 전체 payload를 읽은 성능 근거가 아니다. peak RSS를 새로 측정했다고 주장하지 않는다. 228 역사 whitespace 부하를237 성능으로 확대하지 않는다. 동기 공통 scope/RLock 계약을 유지하며 임의 await/외부 I/O까지 지원하지 않는다.

## 사용과 인계

사용자의 CLI/profile/API 선택 방법과 Root 내부 고정 config 갱신 절차는230 계약을 따른다.237은 새 자동 선택·서버 설정·브라우저 기술 옵션을 추가하지 않는다. 내부 보호 보완이며 실제 UI 서버 반영은0이다. 이후 고정 revision의 독립 검토와 Root의 명시 적용/검증 뒤에만 main 적용을 판단한다. 이해 담당은 누락5범주·새 status cap·미분류 kind failclosed·시험과 운영 미검증을 설명/FAQ/INDEX에 반영한다. UI 소비자에게는 UNCONFIRMED 전체 오류 계약을 전달하며 실제 화면 반영과 시험 반영을 구분해야 한다.

## 최종 마감 근거

최종 **109 PASS / 39.174초** (`profile237-related-final.log`)에는 새237 집중19개,230/228 profile 회귀,173/182, status/priority/budget 회귀가 포함된다. 독립된 수로 합산하지 않는다. 앞선108회귀의1오류는 기존214 legacy 비교가 요구하는 구 source 코드 archive를 격리 입력 복사에서 빠뜨린 것이다. 부모230의14061B/SHA `a8524dc457fd2945fe4845b69757af3b6ba2dd32be5248383175dca1fed964e0` 코드만 그대로 복사하고 `input-test-code-supplement237.json`에 고정했다. 운영data를 복사하거나 cap/보호를 완화하지 않았다. 실패 로그도 보존한다.

단1 live test-process 관측은 PID40644/CPU11.625초/RSS106172416B/그 시점 peak108896256B였다. `resource237-live-observation.json`의 중간 관측이며 전체 종료 peak/RSS 보장이나 rich128 성능 시험이 아니다. 최종 wall time은 unittest109 결과의39.174초다. 추가 부하/실QA 재실행0이다.

Root가 별도 수행한 현재 source 구조 실관측은 이 담당의237 시험과 구분한다. 전달된 결과는 source66826849B/1715행/history0/2860976 tree visits/깊이8로 기존 행·node·depth 경계 안이지만 새profile 활성·실128 QA 성공을 의미하지 않는다. 이 담당은 해당 운영 파일을 읽지 않았다.
