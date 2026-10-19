# 260 — deficit1024의 명시적 AOI 전체 포함 메타데이터 선별

상태: **IMPLEMENTED / TESTED_SYNTHETIC**, 격리 작업공간에서만 구현. 공유 main 제품 적용·실제 STAC 호환성·실수집은 **미검증/미실행**이다. Root 독립 검토와 명시 적용 전 수집 승인은 없다.

## 목적과 동작 변경

249·258의 원인 설명은 Root/감사 담당의 인계다. 이번 담당은 운영 자료를 새로 읽거나 과거 COG 좌표를 재구성하지 않았다. 검색의 bbox는 교차 조건이며 부분 교차 장면의 중심 창이 이동할 수 있다. 260은 선택 가능한 장면의 **선언 bbox가 요청 AOI 전체를 포함하는가**를 SCL 읽기 전에 검사한다. bbox 선언은 실제 polygon·B02 pixel bounds·NoData·품질·support 겹침 통과의 증거가 아니다.

이 정책은 기본값을 바꾸지 않는다. 명시 v2에서만 검색 응답 최대 20개를 기존 cloud 순서로 안정정렬하고, 메타데이터 제외 후 최대 5개를 선택한다. 따라서 기존 응답 순위 **6~20의 장면도 새 5개 풀에 들어올 수 있다**. 이는 명시적인 선택 정책 변경이다. 검색·pagination·재검색·실패 후 refill을 추가하지 않으며 SCL 시도는 여전히 최대 5개다. 나지 또는 적격 패치 확보를 보장하지 않는다.

## 작업공간과 소유

격리 경로는 `evidence/integration/selection260-workspace-20261018`이다. Python import를 정적으로 추적한 필요한 코드·시험 및 기존 합성 config 입력 40파일/468958바이트를 복사하고 `baseline/` 원판과 `baseline260.json`에 지문을 보존했다. 운영 data/model/ledger는 복사하지 않았다. 이 공간의 `data`가 생기더라도 시험의 임시 자료를 운영 입력으로 간주하지 않는다. 실제 시험 쓰기는 TemporaryDirectory에 한정한다.

제품 수정은 격리판의 다음 3개뿐이다.

- `backend/app/data/deficit_candidate_guard.py`: v2 요청 정책, config/binding 생성, 순수 `filter_candidate_pool`.
- `scripts/collect_samples.py`: 기본 None인 optional callback의 선별 시점과 결과 요약.
- `scripts/collect_deficit_guarded.py`: v2 config/binding 검산과 worker callback 연결.

새 시험 `tests/test_deficit_metadata_selection260.py`를 추가했다. 기존 시험 원판을 변경하지 않았다. 공유 main의 255·246 제품은 동결 SHA로 대조하고 편집하지 않는다. 최종 patch manifest/diff/freeze는 격리판만 인계한다.

## 요청·정확한 config SHA 계약

v1은 기존 정확 key 집합과 schema_version=1을 유지한다. v2는 기존 key 집합에 아래 **정확한 문자열 하나**를 추가한다.

```json
{"schema_version":2,"candidate_metadata_policy":"DEFICIT_AOI_BBOX_CONTAINS_V1"}
```

이는 요청 전체가 아니라 기존 요청에 적용할 두 필드의 예시다. kind와 proposal/current_manifest/ledger/boundary/config/prior refs, selected, maximum_batches는 기존처럼 필요하다. 알 수 없는 정책·bool·누락·v1에 정책 추가는 거부한다. request canonical digest는 기존 `_digest(request)`/coordinator `digest(request)`로 전체 요청을 해시하므로 schema와 정책이 포함된다. 변경된 request SHA는 job key에도 포함된다.

producer `prepare_deficit_candidate_jobs()`는 기존 job_config를 만들고 **v2일 때에만** `job_config['candidate_metadata_policy']=정확한 marker`를 넣은 후 기존 식 `hashlib.sha256(json.dumps(job_config, sort_keys=True).encode()).hexdigest()`로 `config_sha256`을 계산한다. 정책을 추가하기 전 config를 해시하거나, `.load_config()`가 만든 실행용 periods를 새로 섞어 expected digest를 계산하면 안 된다. producer의 config 원문을 기준으로 한다.

job의 별도 `candidate_metadata_binding`은 정확한 `{policy, request_sha256, source_sha256}`이다. source는 고정 요청 `current_manifest_ref.sha256`이며 coordinator는 실제 고정 입력 검산을 마친 source_pin과 비교한다. 이 binding은 source의 특정 픽셀을 읽었다는 증거가 아니다. worker에서 현재 eligible 통계가 달라지더라도 요청의 고정 source provenance를 바꾸지 않는다. 원장 reserve·게시 전 source 변경 검사는 기존대로 유지한다.

**미래 Root wrapper는 v1 template에서 파생한 205/249/258 expectedconfig를 그대로 재사용하면 안 된다.** 새로운 v2 요청·canonical SHA·예상 config SHA·approval·실행 코드핀을 재발급해야 한다. 과거 v1 proof나 실행 승인은 이 정책 검증 또는 실행 승인으로 전용하지 않는다. Root의 명시 적용 검증 전 main 반영·실수집은 금지다.

## 새 내부 API와 실패 계약

```python
accepted, summary = guard.filter_candidate_pool(response, aoi, year)
# coordinator의 v2 worker만 다음 optional 인자를 전달한다.
collect_windows(..., candidate_metadata_filter=guard.filter_candidate_pool)
```

`filter_candidate_pool()`은 파일·HTTP·래스터를 읽거나 쓰지 않는다. 먼저 기존 `_binding()`으로 1024/고정 split/AOI/native footprint 결속을 검산하고 정책/config/binding과 요청 year를 확인한다. 원격 응답은 현재 관측된 메타데이터이며 고정 source manifest와 같은 종류의 증거가 아니다.

고정 PC 정책의 조건:

- response.source는 정확히 `https://planetarycomputer.microsoft.com/api/stac/v1/search`, items는 최대 20개의 list다. endpoint/collection은 PC/Sentinel-2 L2A만 지원한다.
- cloud 값은 bool이 아닌 유한 숫자 0~100이다. 기존 cloud 안정정렬과 같은 동률 순서를 유지한다. 응답 구조/잘못된 cloud/20초과/잘못된 binding은 고정 오류로 전체 선별을 중단한다.
- 각 item과 raw `stac_feature`는 동일한 ID·collection `sentinel-2-l2a`·datetime·bbox를 선언해야 한다. raw는 Feature이고 properties는 dict여야 한다. ID는 ASCII 제한 길이의 원문을 비교하며 baseline 추가·정규화·alias를 만들지 않는다. 제품 진위나 전체 STAC 스키마를 검증하는 API는 아니다.
- datetime은 유효 UTC Z/최대 6자리 소수초이고 요청 연도와 같아야 한다. 원문 소수초를 반올림/삭제하지 않는다. 이 필터는 연도를 확인하며 관측 ID의 초 부분과 같다는 246의 더 강한 결속을 대신하지 않는다.
- bbox는 정확히 4개의 유한 nonbool WGS84 숫자, west<east/south<north다. 6D bbox·날짜변경선·역전·누락·NaN/Infinity는 미지원/제외다. item과 raw bbox가 다르면 제외한다.
- 포함은 `sceneW<=aoiW`, `sceneS<=aoiS`, `sceneE>=aoiE`, `sceneN>=aoiN`의 정확 비교다. 네 경계가 같은 장면은 포함된다. 반올림 coverage ratio·epsilon·부분 포함 fallback은 없다.

Root가 별도 감사한 원문 SHA `b59e97e567c54aecd2709291487b0cf352ae2e1f5c05932a4993c53de1e5b2e6`의 관측 예시를 메시지로 제공했다: ID `S2B_MSIL2A_20240813T021349_R060_T51MUR_20240813T055551`, datetime `2024-08-13T02:13:49.024000Z`. 이 담당은 해당 운영 파일을 읽지 않았다. normalized/raw가 원문 그대로 같다면 이 시각은 260의 연도·문법 조건에는 허용된다. **ID의 초 단위 시각과 동일하다고 판정한 것이 아니다.** 반면 246에 초 단위 요청 시각을 선언하면 `.024000Z`와 불일치하므로 기존 strict 차단을 유지한다. 246 코드는 수정하지 않았다. 메시지의 예시는 260 실제 파일/공급자 호환성 PASS의 근거가 아니며 bbox 조건·기존 모든 실가드도 별도로 남는다.

개별 identity/time/bbox 오류나 부분 교차는 해당 장면만 제외하고 고정 사유를 기록한다. 통과 0이면 `metadata_coverage_insufficient`/`quality_unverified`로 종료하며 SCL/선택 scene/B02 읽기 0, 원래 첫 장면 fallback 0이다. 통과 후보가 있지만 최대 5개의 품질 검사에서 모두 실패하면 기존 `quality_insufficient`를 유지하며 6번째 후보를 추가로 읽지 않는다. candidate_limit=1 경로도 선별을 먼저 수행한다. empty search 응답은 기존 장면 없음 오류를 유지한다.

callback이 None이면 기존 collector 경로와 출력이 그대로다. 새 callback 사용은 1024·명시 config marker·search<=20 조건을 요구한다. coordinator v1은 optional keyword 자체를 넘기지 않는다. 부모 256·기본 collector에는 자동 적용하지 않는다.

## URL 없는 bounded 선별 요약

row의 `candidate_metadata_filter`에는 schema_version, 정책/request/source SHA, input/retained/excluded/selected_pool count, 최대 20개의 `{input_index,cloud_rank,reason}`만 남긴다. index와 rank는 0부터 시작한다. reason은 `METADATA_CONTAINS_AOI`, `METADATA_IDENTITY_INVALID`, `METADATA_TIME_INVALID`, `METADATA_BBOX_INVALID`, `METADATA_PARTIAL_OR_DISJOINT` 중 하나다. URL·scene 원문·raw geometry·서명 query·임의 예외문을 새 요약에 복사하지 않는다. 기존 candidate_selection 오류 계약을 새 요약으로 바꾸지는 않았다.

기존 guard callback은 유지한다. metadata가 합격해도 SCL support window overlap, 선택 scene/split claim, 선택 B02의 1024/10m/10.000001m 정렬, support/pending, 최종 품질에서 여전히 차단될 수 있다. 기존 255 B02 진단도 유지한다. global4GiB·2worker·2초·첫429·3000물리패치·metadata1MiB+COG64MiB·5SCL·20search 상한은 늘리지 않았다. 운영 승인/학습/독립 정답 gate를 true로 바꾸지 않는다.

## 검증과 잔여

시험은 격리 작업공간 import를 우선하여 실행하며 provider는 fake 응답이고 파일/정산은 Temp 자료다. 실제 운영 source·ledger·model·STAC·native 읽기/HTTP/collector/실API/브라우저는 0이다. 시험 지문·정확한 실행 결과는 최종 freeze와 아래 마감 절에 기록한다.

새 시험은 v1 full proof를 archive 모듈과 직접 비교, 기본256 dry report 동등, v1 optional callback 부재, v2 request/config/source binding·오염 예약 전 차단, cloud 동률/20개 정렬, 누락/오염/raw 불일치/부분 교차/경계 포함, 후보6~20 유입·실제 selector SCL 최대5/refill0, candidate_limit1, 전부 제외 SCL0/fallback0, 기존 support veto 유지, 기존 정산/oldpending 보존을 확인한다. 공급자 현재 실응답과의 호환성, metadata 선언 자체의 정확성, bbox 내 유효 pixels, 성공 확보량과 실성능은 미검증이다.

이력: 최초 집중 12 PASS/11.250초, 확대 집중 16 PASS/14.378초는 중간 판이다. 첫 관련 회귀 90개/56.640초에서 기존 격리 CLI 2개가 실패했다. 새 policy 파싱을 fresh proof 실패분류 전에 호출하여, mock 빈 요청의 기존 `DEFICIT_LOCAL_PROOF_INVALID_*` 오류를 `CENTER_REQUEST_INVALID`로 가린 순서 문제였다. 원 실패 로그 `regression260.log`를 보존하고, 기존 proof 실패분류 후 합격 proof에만 policy를 검사하도록 좁게 수정했다. 예약 전 정책/바인딩 검증은 그대로다. 최종 재회귀 결과와 중간 합격 수치를 합산하지 않는다.

최종 판 실행은 아래 6모듈 **90 PASS / unittest 58.025초 / exit0 / skip0**, `regression260-final.log`에 보존했다. 전판의 실패 2개도 같은 시험 그대로 통과했다. skip이나 오류 기대값 변경으로 숨기지 않았으며 기존 시험 파일은 원판 그대로다. 경과시간은 unittest 자체 보고값이고 최대 RSS·운영 20장면 처리시간은 측정하지 않았다. 시험 중 기존 rasterio PendingDeprecationWarning은 있었다.

```powershell
# 작업 디렉터리와 PYTHONPATH의 코드 경로는 격리 workspace를 지정한다.
python -X utf8 -m unittest test_deficit_metadata_selection260 test_deficit_candidate_guard test_collect_deficit_guarded test_targeted_collection_hooks test_targeted_candidate_quality_policy test_data_recovery -q
```

최종 `freeze260.json`은 40개 baseline/archive/main 대조, 255·246 동결 지문, 실제 수정 3제품+신규시험1·이 문서, 모든 시험 로그와 최소 `patch260.diff`를 고정한다. `patch260-manifest.json`의 대상 경로는 **향후 Root 검토용 상대 경로**이며 공유 main에 반영했다는 뜻이 아니다. 자체 SHA는 자기참조를 피하여 별도 인계한다.

이 단위는 API/UI에 연결되지 않은 격리 내부 선택 정책이다. Root 독립 검토·소유 파일 baseline 비교·명시 적용 검증·새 요청/approval 발급이 끝나야 실실행 후보가 된다. 이해자료는 Root 검토 후 별도 담당이 쉬운 설명·대본·FAQ·INDEX·이력을 갱신한다. 전체 프로젝트나 수집 목표 완료로 보고하지 않는다.
