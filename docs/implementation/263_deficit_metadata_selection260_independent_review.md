# 263 — 260 명시 메타데이터 선별 최종판 독립 정적 리뷰

## 결론

상태는 **STATIC_REVIEW_COMPLETED / CHANGES_REQUIRED_BEFORE_SHARED_APPLICATION**이다. v2 coordinator의 정상 연결과 기존 실가드 유지에는 명확한 근거가 있다. 다만 **정책 marker가 있는데 callback이 없는 collector 경로**와 **main에 존재하지 않는 baseline fixture를 읽는 신규 시험 포장**을 보완해야 한다. 제품 계약 공백과 시험 배치 공백을 구분한다. 260 동결판·공유 main은 수정하지 않았다.

이번 검토는 최종 코드·diff·시험·문서·동결 지문만 읽었다. 추가 시험·운영 data/원장·래스터·HTTP·collector·실 API/브라우저는 0회다. 기존 90 PASS를 독립 재실행한 결과로 합산하지 않는다.

## 고정한 검토판

격리 위치는 `evidence/integration/selection260-workspace-20261018`이다. 아래 지문과 freeze에 기록된 4개 변경 파일·문서·7개 근거 파일의 실제 지문이 모두 일치했다. 실제 실행은 하지 않고 바이트를 해시한 결과다.

| 대상 | SHA-256 |
|---|---|
| freeze260.json | `66d25b903db870ca6607bb56dc76bf8117b56d468f12ffafd1a20843e9313a8b` |
| patch260-manifest.json | `39dd0e517d871702c0e1ba79b926b01fd7199b3658570db359a02d922cb0bd4d` |
| patch260.diff | `cb44fcc78cf63d5bb03caed8ab19d099fd5ce6da056dafc9cf79b783584ff9d9` |
| guard 최종판 | `4052759b683f6f4f545a629466f2d4145e3ad9cc2ad8e6cdf5b1e3c0004a5dd2` |
| coordinator 최종판 | `9ae5ba986d3d48e89cfb269d8a242ffd6189d281649d98a11614c03e5ab3c9ab` |
| collector 최종판 | `eac2c2ea7a21f809328ea7572f490584ff7313c2b1ff95191ee976204ac2b424` |
| 신규 시험 | `c3c129ce5c95882df5dc9381c360629f325d931233f080982471ee19f7300f45` |
| 260 구현 문서 | `85cece0cfbc99dbc899d3e87889fe7d1b80305430b3077f1d5180c593f5562a4` |

최종 기록은 6모듈 90 PASS/58.025초/skip0이며, 이전 90개 중 실패 2건의 로그도 보존돼 있다. 실패 원인의 분류 순서를 복구한 최종 diff를 확인했다. 과거 중간 집중 통과 수치와 최종 결과를 합산하지 않는다. 기존 시험 파일을 수정한 delta는 없고 제품 3개·신규 시험 1개만 patch manifest 대상이다.

## F1 — marker가 있는데 callback이 없으면 조용히 legacy 경로 실행

위치: 격리 `scripts/collect_samples.py`, `collect_windows`의 callback 검증부(약 247행), metadata_pool 생성부(약 362행). 현재 조건은 다음과 같다.

```python
if candidate_metadata_filter is not None and not (...정확 marker/1024/search<=20...):
    raise ValueError('CENTER_METADATA_CALLBACK_INVALID')
```

callback이 None이면 조건 전체를 건너뛴다. 따라서 v2 producer가 만든 `candidate_metadata_policy='DEFICIT_AOI_BBOX_CONTAINS_V1'` 설정을 넘기되 callback을 빠뜨린 직접 Python 호출이나 기존 bounded collector CLI 경로는, marker가 있어도 `metadata_pool=None`으로 기존 첫 후보/상위 5개 풀을 사용한다. 요청 AOI 전체 포함 선별이 실행되지 않은 상태로 SCL 또는 선택 scene 단계에 들어갈 수 있다.

**정상 v2 coordinator는 callback을 항상 전달한다.** 예약 전 request/schema/config/binding 검산도 수행하므로 해당 정상 경로에서 바로 생기는 누락은 아니다. 문제는 opt-in 설정을 표시하면서 실제 collector의 선택 동작을 생략해도 이를 감지하지 못하는 공개 소비 경계다. `collect()`/CLI의 기존 bounded_windows dispatch는 callback을 전달하지 않는다는 점도 코드로 확인했다. 실제 호출 재현은 하지 않았다.

보완 제안은 양방향 계약이다. 정확 marker를 가진 config는 callable callback을 반드시 요구하고, callback을 받으면 정확 marker·1024·search≤20을 요구한다. 모르는 non-null marker도 명시적으로 차단해야 한다. marker가 없는 legacy config+callback None의 기존 출력은 그대로 유지한다. 이 검사는 `service.search_stac` 호출 전에 있어야 한다.

추가 시험 제안: marked config+callback None, unknown marker+None, callback+marker 누락/오염 각각에서 네트워크 전 고정 오류 확인. v2 coordinator 정상 연결, v1/default/256 동등성과 limit1 선별 선행 시험도 그대로 유지한다. 문서의 “명시 정책 누락 시 failclosed” 범위를 wrapper만으로 오해하지 않도록 적어야 한다.

## F2 — 신규 시험의 baseline fixture가 공유 main 배치에 없음

위치: `tests/test_deficit_metadata_selection260.py` 약 68행과 156행. `ROOT`는 시험 파일의 부모 프로젝트이며 다음 파일을 importlib로 직접 실행한다.

```text
ROOT/baseline/backend/app/data/deficit_candidate_guard.py
ROOT/baseline/scripts/collect_samples.py
```

격리 공간에는 이 원판이 있지만 공유 프로젝트의 두 경로는 정적 존재 확인 결과 모두 없었다. patch manifest에도 두 fixture는 포함되지 않는다. 따라서 신규 시험 1개만 main/tests에 복사하면 두 동등성 시험은 FileNotFoundError로 끝나는 구조다. 90 PASS는 격리 공간의 유효한 증거지만 main 시험 포장 성공의 근거는 아니다.

이는 **main 시험 배치 차단**이며 제품의 bbox/SCL/예산 가드가 약화됐다는 뜻은 아니다. Root 계획에 따라 동결 260을 수정하지 않고 별도 265 portable test bundle에서 두 원판 fixture를 명시 경로·고정 SHA와 함께 제공하는 방식이 적절하다. fixture 누락·변조는 실패해야 하며, 현재 main 소스로 fallback하거나 시험 skip으로 숨기면 원판 비교의 의미가 사라진다. 관련 fixture의 상대 import 문맥과 main 테스트 배치도 별도 검증해야 한다.

## 정적 읽기에서 확인한 적절한 연결

v1은 exact 기존 key/schema를 유지하고 v2는 정확한 정책 필드 하나만 추가한다. unknown/bool/누락·v1에 marker 추가는 producer에서 거부한다. v2 정책은 config에 넣은 뒤 기존 정규화 식으로 config SHA를 계산하고, request 전체 canonical·job key에도 반영된다. coordinator는 fresh proof 실패분류를 먼저 보존하고, 합격 proof 뒤 예약 전에 config 정책과 `{policy, request_sha256, source_sha256}`를 실제 source pin에 결속한다.

정상 v2 worker는 같은 live guard의 bound callback을 전달한다. 검색 응답 20개 상한·cloud 유한 nonbool 0~100·PC endpoint와 collection·normalized/raw ID/datetime/bbox 일치·동년 UTC 시각·유효 bbox를 확인하고 cloud 안정정렬을 유지한다. 잘못된 개별 identity/time/bbox와 부분 교차를 제외한 뒤 최대 5개를 SCL 풀에 넣는다. **기존 순위 6~20도 새 풀에 들어오는 의도된 정책 변경**이며 추가 pagination·실패 후 refill은 없다. 이 변화는 260 문서에 명시돼 있다.

후보 전체 제외 시 `metadata_coverage_insufficient / quality_unverified`이며 첫 장면 fallback이 없다. limit1도 callback이 연결된 경우 scene 선택 전에 metadata 선별을 거친다. 요약은 고정 reason·index/rank·count·정책/지문과 최대 20항목뿐이어서 새 URL·scene 원문·서명 query를 복사하지 않는다.

기존 `on_window`·scene/split claim·지원영역 겹침·선택 B02 1024/10m/10.000001m 정렬 및255 진단·물리3000·글로벌4GiB·COG64MiB+metadata1MiB·재시도0·공유간격·첫429·실측 정산·oldpending 보존의 조건을 바꾼 delta는 발견하지 않았다. 새 callback은 선별을 앞에 추가할 뿐 그 뒤의 실가드를 대체하지 않는다. v1 optional keyword 미전달과 기본256 dry 동등성의 합성 시험도 확인했다.

## 검증 한계와 적용 조건

선언 bbox가 AOI 전체를 덮어도 실제 polygon·B02 crop/grid·NoData·주내95%·유효80%·나지 기여가 검증된 것은 아니다. ID는 제한된 ASCII 문자열의 normalized/raw 일치만 검사하며246의 strict acquisition ID 시간 결속을 대신하지 않는다. raw properties.datetime의 소수초를 원문 그대로 허용하는 정책은 문서와 코드가 맞고, 실제 공급자 현재 응답 호환성·성능은 이번 범위에서 미검증이다.

이 리뷰의 source hash 검산과 코드 읽기는 실행 승인 또는 수집 성과가 아니다. Root는 F1 제품 소비 계약과 F2 시험 배치를 각각 보완·동결·검토한 뒤 새로운 v2 request/config SHA·approval·code pin을 발급해야 한다. v1의205/249/258 expected config를 그대로 재사용하면 새 정책 지문이 빠지므로 안 된다. 수정판은 별도 후속 증거로 남기고 이번 260 원판·실패 로그를 보존해야 한다.

F1/F2를 Root에 전달했으며 263 담당의 코드 수정·재시험·운영 데이터 읽기·원장·HTTP·collector는 모두 0이다. 공통 이해자료에는 현재 **격리 합성 구현 완료 / 독립 리뷰 보완 필요 / 공유 적용 차단 / 실 공급자 호환·실취득 미검증**을 반영한다. UI 영향은 아직 없으며 실제 적용·실수집 이후 Root가 API/UI 담당에게 새 계약을 인계한다.
