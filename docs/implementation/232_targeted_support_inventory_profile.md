# 232 — 179 검토·170 나지256 수집의 명시 로컬 지원3GiB profile

상태: **IMPLEMENTED / TESTED_SYNTHETIC — 관련103PASS/32.239초·skip0**. 신규8개가 포함된 최종 회귀 수치다. 실제 운영 support inventory·native·HTTP·수집·원장 접근은0이다. 이 변경이 실제 나지 확보·현재 전체 inventory 성공·실행 승인을 의미하지 않는다.

## 쉽게 설명과 막히는 지점

기존 `inspect_targeted_inventory`는 과거 영상·확대 SCL/SWIR/B02·미정산 지원 파일을 빠짐없이 모은 뒤 파일 크기 합계를 검사한다. 기본값은2GiB다. 기존179와170은 이 함수에 상한을 따로 전달하지 않아, 합이2GiB를 넘으면 `INVENTORY_LIMIT`에서 막히는 코드 경로였다. 나지 픽셀이나 품질이 나쁘다는 뜻이 아니라 로컬 사전 검산의 자원 제한이다.

이번 담당은 운영 지원 파일을 다시 읽어 합계를 재측정하지 않았다. “현재 지원 합이2GiB를 넘는다”는 Root의 선행 관측과, 위 기본값/호출 경로를 구분한다. Temp의 작은 TIFF들에64MiB stat 크기만 모의해2GiB 초과에서 기존 경로가 차단되고 명시3GiB에서는 검증되는 것을 시험한다.

원격 다운로드 비용을 늘리는 기능이 아니다. 이미 로컬에 있는 지원 파일 전체를 검산할 때 사용할 합계 상한만, 지문으로 고정한 명시 요청에서3GiB로 선택한다. 파일 일부를 빼거나 과거/미정산 자료를 생략하지 않는다.

## 변경 파일과 수정 전 보존

변경은 `scripts/review_bare_targets179.py`, `scripts/collect_targeted_bare.py`, 신규 순수 helper `backend/app/data/targeted_inventory_profile.py`, 신규 시험 `tests/test_targeted_inventory_profile232.py`다. 공용167 inventory·부모256 live guard·199의 고정3GiB 경로·targeted plan 코드는 수정하지 않았다.

수정 전 두 파일은 `evidence/integration/targeted232-20261018/baseline/scripts/`에 원바이트 보존했다. `baseline-manifest.json`에는 수정 전 SHA와 보호 파일 지문이 있다.

| 수정 전 파일 | SHA256 |
|---|---|
| review_bare_targets179.py | `cd6c353d57a9daffc117c3187bc8b4ff2ff74806a220019db5d44ba2ad1cb94a` |
| collect_targeted_bare.py | `643a3e8327a30ebac671267f451636bf3ce18828cce42855ef643d9945694581` |

## v1 보존과 명시 v2 계약

v1은 기존 키·정수 schema_version1·원래 오류를 유지하고 inventory 호출에 새 kwargs를 전달하지 않는다. 따라서 공용 함수의 default2GiB가 그대로 적용된다. 새 profile 필드를 v1에 추가하면 기존 추가필드 오류처럼 거부된다. 기본 결과에 profile/canonical 필드를 추가하지 않았다.

v2는 기존 필드에 **`local_support_profile` 하나만** 추가하며 값은 정확히 `{name,sha256}`여야 한다. 이름은 **TARGETED_LOCAL_SUPPORT_3G_V1**이다. bool·숫자·문자열 하나만 전달하기·알 수 없는 이름·지문 불일치·추가 키·임의 max_bytes·bool schema_version을 거부한다. 지문은 아래 descriptor의 sorted compact JSON SHA256이다.

```json
{
  "name": "TARGETED_LOCAL_SUPPORT_3G_V1",
  "max_files": 10000,
  "max_support_bytes": 3221225472,
  "max_file_bytes": 67108864
}
```

marker를 만드는 사용법은 다음과 같다. 실제 수집 실행 명령은 이 문서의 승인 범위가 아니다.

고정 descriptor SHA는 `062bf36199ee4e0f142cb117cad2f0c5b25411eb3ddd43ed37b30ca3b7a75a7a`다. 이 지문은 자원 계약 식별이며 수집 승인 서명이 아니다.

```python
from app.data.targeted_inventory_profile import MARKER
request_v2 = {**request_v1, "schema_version": 2,
              "local_support_profile": dict(MARKER)}
```

179 요청의 정확한 키는 `schema_version/proposal_ref/manifest_ref/ledger_ref/boundary_ref/local_support_profile`이다. 170 요청은 `schema_version/plan/ledger_ref/maximum_batches/local_support_profile`이다. **내부256 plan은 기존 schema_version1**을 유지한다.179의 select_plan이 profile을 plan에 숨겨 전달하지 않으므로170 외부 요청에서도 명시 선택해야 한다. 새1024 계획을 이 경로로 실행할 수 없다.

179 CLI의 `--request-sha256`는 기존처럼 **실제 요청 파일 바이트 SHA**이며 marker가 그 파일에 포함된다. v2 report에는 별도로 sorted canonical request SHA인 `request_sha256`과 marker를 기록한다.170의 `digest(request)`/`--expected-request-sha256`도 기존 canonical 방식을 그대로 유지해 marker를 포함한다. 이전 v1 핀을 v2에 재사용하면 예약 전에 실패한다. 원본/라벨/경계/원장 pin 검사는 바꾸지 않았다.

## 실제 전달 범위와 출력

179는 label/lineage/경계 native 검산 후 실행하는 **전체 inventory1회**에 `max_files=10000,max_bytes=3GiB`를 전달한다.170은 `validate_request` 안의 **모든 선택 target inventory**에 같은 kwargs를 전달한다. 타깃이2개면 두 호출 모두 같은 cap을 받는다. 일부분만3GiB로 바뀌거나 기본값으로 돌아가는 추가 inventory 호출은 없다.

v2의179 report는 schema_version2·marker·canonical request SHA를 표시하지만, `ui_summary`와 plan의 기존 계약은 유지한다.170의 검산 결과와 dry-run/실행 결과도 v2에서만 marker를 표시한다. 모든 cap/권한 선택은 검증된 요청을 따르며 artifact에서 임의 숫자를 읽어 적용하지 않는다.

profile의3GiB는 공용 inventory 함수가 기존에 허용한 최대4GiB 안이다. 파일 수10000·개별 지원 파일64MiB·라벨64MiB·179 label 합768MiB·label파일128개·기존 source JSON/lineage/request 한도는 그대로다. source JSON의128MiB 명시 profile 개발230과도 별도 계약이다. **로컬 support 합계3GiB와 source JSON64/128MiB는 서로 다른 한도**다.

## 그대로 유지한 수집 보호

원격 COG64MiB+metadata1MiB/batch·추가전역4GiB·최대2worker·공통2초·첫429 중단·재시도0·기존 pending 전액·단일 execution lock·실측 정산·물리3000 상한은 수정하지 않았다. 전체 SCL/SWIR/B02 지원 겹침·선택 B02·공유 scene/window claims·고정 split·최종 품질80%/주내95%·나지256·과학/학습 false도 그대로다.

profile 오류는 request 검증 단계에서 거부되며 원본 source 읽기·CollectionLedger 생성/예약·worker/HTTP로 넘어가지 않는다. 기존 execute 경로는 검증보다 먼저 Temp/운영 execution lock을 잡는 원래 순서이므로, 오류 시 기존 finally에서 자기 lock을 해제한다. 새 예약이 없다는 것과 lock을 전혀 만들지 않는다는 것을 혼동하지 않는다.

## 시험 근거와 한계

집중7개 시험의 초기 최종 결과는7PASS/7.652초다. 최초 실행의1건 오류는 mock fixture가 `issue` 필드를 빠뜨린 문제였으며 원로그 `focused.log`를 보존했다. 제품 운영 실행 실패나 자동 수집 재시도가 아니다. 그 후 정상 v2 CLI positive 계약 시험을 추가해 **신규8개 포함 관련103PASS/32.239초·skip0**를 확인했다. 전체 로그는 `evidence/integration/targeted232-20261018/regression-final.log`다. 기존179·170·167·256 live guard·나지 계획·선택 품질 정책 회귀가 포함되며 집중7개를 다시 더하지 않는다.

신규 시험은 descriptor/marker 엄격성·오염 거부·canonical profile binding·두 target cap 전달·보존 원판과 v1 review/plan/collector 검산 결과 정확 동등·profile 잘못 선택 시 예약0·부모256 규격·실 CLI subprocess의 Temp 요청/출력을 검증한다. positive CLI에서 무거운 inventory/실수집은 명시 mock이며179는 Temp의 작은 label만 읽는다.170 CLI는 dry-run으로 원장/원본 바이트 불변과 lock 미생성을 확인한다.

34개×64MiB stat=2.125GiB 모의는 v1 차단·v2 통과,49개×64MiB=3.0625GiB 모의는 v2도 차단됨을 확인한다. 실제 수GiB 파일을 생성·읽거나 운영 지원을 스캔한 시험이 아니다. 개별64MiB cap은 기존 inventory `_snapshot`에 계속 전달된다. 실제 운영fullreview 성공과 현재 지원 합계가3GiB 안이라는 보장은 Root의 후속 한 번의 검토가 필요하다.

## 인계와 운영 경계

직접 API/UI 계약을 바꾸는 작업은 아니므로 프론트 build·실서버·실브라우저 확인은0이다. Root가 실제 v2 request를 새 파일로 고정하고 review/수집 여부를 별도 판단한다. 과거 요청/report/receipt/pointer를 바꾸지 않는다. 현재 원본 크기와 남은 source JSON 여유는 Root 선행 관측이며 이 담당이 운영 파일을 읽지 않았다. 최대1patch 검토도 실제 성공을 보장하지 않는다.

최종 코드/시험/freeze를 Root와 이해 담당에 전달해 로컬/원격 예산 구분·v1/v2 사용법·실취득 미검증·발표/FAQ/INDEX/이력을 갱신한다. 이 단위 완료를 나지 부족 해결·모델 학습·운영 승인·전체 개발 완료로 보고하지 않는다.
