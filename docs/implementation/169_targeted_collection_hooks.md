# 169 — 기존 수집 소비 경로의 선택적 scene/window 보호 callback

- updated_at: 2026-10-18 KST
- source_commit: 신규 hook 작업 트리, Root 통합 커밋에서 고정
- evidence_paths: `evidence/integration/targeted-collection-hooks-agent-20261018.log`, `evidence/integration/targeted-collection-hooks-related-20261018.log`
- confidence: mock transport/header·기존 수집 회귀 시험 범위
- status: TESTED_SYNTHETIC / 실제 표적 수집 통합은 별도

## 목적과 변경 범위

`scripts/collect_samples.py`와 `backend/app/data/service.py`에 기존 소비 경로에서 사용할 수 있는 선택적 callback을 추가했다. 별도 다운로드 loop나 대체 원격 reader를 만들지 않고 기존 예약·실측·실패 정산 경로를 그대로 사용한다. guard를 전달하지 않는 기존 일반 수집 호출은 위치 인수 개수와 동작을 유지한다. 실행 중인 일반 collector 프로세스를 재시작하거나 실제 원격 자산을 요청하지 않았다.

이 hook 자체는 scene split·inventory·bbox 포함·품질 검증 알고리즘이 아니다. callback이 실제 검사를 수행하고 실패 시 예외를 발생시켜야 한다. 반환값 false만으로는 거부되지 않는다. 연결만으로 execution_supported 또는 학습 준비 상태를 true로 바꾸지 않으며 실제 적격 나지 패치 확보로 계산하지 않는다.

## 소비자 계약

```python
collect_windows(config, root, execute=False,
                selection_context=None, collection_guard=None)

collection_guard.on_scene(item, aoi, year)
collection_guard.on_window(original_asset_url, geometry)

read_cog_window(url, bbox, side=256,
                max_transfer_bytes=32*1024*1024, window_guard=None)
```

`collect_windows`는 선정한 STAC item 이후, 해당 item의 row metadata 갱신·`stac-item.json`·제품 XML 저장 전 `on_scene`을 호출한다. year는 기존 periods 키 문자열이다. 후보가 여러 개이면 SCL 사전선별은 이미 실행되었을 수 있다. 따라서 scene veto를 “모든 네트워크 요청 전에 실행되는 가드”로 설명하면 안 된다. 검색·SAS·HEAD·COG header도 네트워크 비용이 있을 수 있다.

fetch는 guard가 있을 때만 `window_guard=lambda geometry: collection_guard.on_window(url, geometry)`를 넘긴다. 후보 SCL·영상 각 밴드·참조 라벨 등 기존 fetch 소비에 동일하게 적용된다. root가 제공할 guard는 현재 선택 단계와 자산 역할을 구분할 책임이 있다. on_window의 URL은 원래 자산 URL이며 SAS로 해석된 URL을 새 로그에 쓰지 않는다. callback도 민감 query를 저장하거나 예외 문자열로 반사하면 안 된다.

guard가 None이면 `read_cog_window(url,bbox,pixels,reservation)`의 기존 4개 위치 인수를 보존한다. 서비스 wrapper도 None일 때 `_read_cog_window_impl(url,bbox,side,max_transfer_bytes,holder)`의 기존 5개 위치 인수를 보존한다. CLI flag·API endpoint·기본 설정은 추가하지 않았다.

## 실제 raster header에서 관측하는 geometry

기존 impl은 같은 `HTTPRangeReader`와 rasterio opener로 자산을 열고 실제 CRS에 AOI 중심을 투영하여 기존 Window를 만든다. 그 뒤 **명시적인 `src.read(window=...)` 직전** callback에 다음 JSON형 값을 전달한다.

| 필드 | 의미 |
|---|---|
| schema_version | 1 |
| crs | 실제 src.crs.to_string(), 없으면 null |
| source_bounds | 실제 src.bounds 네 좌표 |
| source_transform | 실제 src.transform의 앞 6개 원소 |
| source_width / source_height | 실제 원본 크기 |
| requested_bbox_wgs84 / requested_side | 검증된 입력 bbox와 side |
| window | col_off, row_off, width, height |
| window_transform | src.window_transform(window)의 앞 6개 원소 |
| window_width / window_height | 실제 잘린 Window의 정수 크기 |

geometry에는 URL·서명 query가 없다. 기존 reader는 중심 창을 선택하며 자체적으로 전체 bbox 포함을 판정하도록 변경하지 않았다. 필요 시 guard가 원본 bounds·actual Window·transform을 비교하여 잘린 창, 전체 bbox 미포함, 고정 계획 불일치를 거절해야 한다. 이 단계는 remote dataset header를 읽은 뒤라 Range 본문 실측은 0이 아닐 수 있다. GDAL 내부 캐시·header block 전송을 포함하여 “원격 raster 관련 바이트 전체 0”이라고 보장하지 않는다.

## 실패와 예산·429 보존

callback 직전 holder stage를 `window_geometry_guard`로 설정하고 성공 후 기존 `range_raster_read`로 복원한다. 거부 예외는 기존 `AssetTransferError` wrapper를 통과한다. reader의 `transferred`·`measurement_known`·`last_error`가 기존과 같은 방식으로 보존된다. collector는 실측이 알려진 경우에만 현재 상한 예약 차액을 돌려주며, 알 수 없으면 전액 예약을 유지한다. 기존 429 공유 중단과 retry 정책을 변경하지 않았다.

거부를 재시도하지 않아야 하는 계약 실패는 ValueError 등 기존 `payload_or_response_contract`로 분류되는 예외를 사용해야 한다. 임의 RuntimeError는 기존 분류와 설정에 따라 transient retry 후보가 될 수 있으므로 caller guard 설계에서 명확히 구분해야 한다. hook이 원장 환불·정산을 직접 수행하지 않는다.

## 시험 근거와 한계

`tests/test_targeted_collection_hooks.py` 집중 **10 PASS, 0.529초**다. 기존 위치 인수 보존, callback keyword 전달, 실제 src.read 전 거절과 known 97B 회계, 전달 geometry·서명 query 부재, HEAD 429 원인·0B 보존, scene 거절 전 metadata/픽셀 저장 0, collector known/unknown 예약 정산, SCL 사전선별 순서, dry-run 무호출을 검사했다. transport·header는 mock이며 원격 HTTP는 수행하지 않았다.

`PYTHONPATH=backend;.runtime;tests`에서 `python -m unittest test_targeted_collection_hooks test_data_service test_data_collection test_data_training_grid test_data_candidates test_collection_raster_declarations test_data_annual_budget test_data_parallel -v`로 관련 회귀를 수행한다. 결과는 related 로그에 기록한다. 기존 원본 데이터·모델·원장·예약·분할을 수정하는 시험이 아니며 임시 디렉터리의 mock 산출물만 생성한다.

관련 회귀 최종 결과는 **64 PASS / 0 SKIP, 27.033초**다. Rasterio PendingDeprecationWarning은 기록되었지만 실패가 아니다. 기존 429·미측정 실패 전액 정산·동시 worker 회귀가 포함되며, 프로젝트 전체 시험 또는 실제 원격 다운로드 성공으로 확대하지 않는다.

Root 후속은 167 전체 inventory/footprint, 166 예약·claim, 실제 선택 자산과 고정 계획 pin, 기존 metered coordinator·공유 429·품질 전처리·최종 정산 연결이다. 이 hook만으로 나지 표적 집행이 완성되거나 운영 승인이 확보된 것으로 설명하지 않는다. 내부 hook으로 API/UI 응답 계약은 바뀌지 않아 직접 화면 변경은 필요 없다. 이해자료에는 “검사를 호출할 실제 소비 지점은 연결됨, 표적 가드와 실제 수집 성과는 별도”로 인계한다.
