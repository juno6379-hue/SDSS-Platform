# 214 — 고정된 라벨 refs만 선택하는 로컬 나지 탐색 API

상태: **TESTED_SYNTHETIC / 운영 선택 스캔 미실행**. 기존 `find_bare_targets173.discover`에 Python keyword `label_refs=None`을 추가했다. 전체 현재 manifest와 coverage는 유지하면서 caller가 명시한 실제 라벨 파일만 읽는다. 새 CLI 옵션·원격 취득·full support/native 재검증·학습·원장 쓰기는 없다.209의 새2개 확대 라벨을 읽는 실제215 작업은 Root의 별도 GO와 고정 요청으로 수행한다.

## 쉬운 설명

기존 탐색은 주를 지정해도 그 주의 모든 저장 라벨을 읽었다. 새로 들어온 라벨2개만 살펴보려면 예전112개 등 기존 파일을 다시 읽을 수 있었다. 새 선택 인자는 **전체 자료 목록에서 실제 존재하는 파일2개를 SHA까지 지정**해 그 파일들만 탐색한다.

여기서 전체 자료의 지역·연도별 적격 패치 수를2개 파일에 맞춰 줄이지 않는다. 후보 우선순위를 정하는 coverage는 원래 전체 manifest에서 계산하고, raster 탐색 범위만 줄인다. 결과에는 실제 읽은 라벨 범위와 생략한 파일 수를 구분해 기록한다. 나지 후보를 발견해도 현재 영상 품질·support 비겹침·집행 승인이 되는 것은 아니다.

## API와 입력 계약

```python
discover(root, manifest, manifest_sha, boundary, boundary_sha,
         limits=None, window_stride=256, provinces=None, label_refs=None)
```

추가 인자는 keyword-only다. 미지정 또는 명시None은 기존 동작/전체 출력과 동일하다. CLI는 변경하지 않았다.

```python
selected = [
    {"path": "data/.../raw-esri_io.tif", "sha256": "<64자리 lowercase SHA256>"},
    {"path": "data/.../raw-esri_io.tif", "sha256": "<다른 실제 crop의 SHA256>"}
]
proposal = discover(root, source_path, source_sha, boundary_path, boundary_sha,
                    window_stride=128, label_refs=selected)
```

선택값은 다음 조건을 모두 충족해야 한다.

- 정확한 builtin list 길이1~256. 빈 목록·bool·문자열·dict·257개 이상은 거부한다.
- 각 항목은 exact `{path, sha256}` dict다. path는 workspace DATA 아래 상대경로, sha256은64자리 lowercase hex 문자열이다. bool SHA·unknown 키·절대경로·상위경로는 거부한다.
- canonical path가 같은 항목을 중복 지정할 수 없다. `/`와 `\\` 표기만 다른 동일 경로도 중복이다.
- 전체 manifest의 현재 province scope에 존재하는 `source_window.raw_source_crops['raw-esri_io.tif']`와 path/SHA가 정확히 일치해야 한다. 파일이 DATA에 실제로 있더라도 해당 source 행에서 참조하지 않으면 거부한다.
- source 행의 동년 Esri lineage·label_year·URL/공식 연도 규칙을 계속 검산한다. `provinces`로 제외한 주의 ref를 별도로 넣으면 범위 불일치로 거부한다.

타입/형식/중복 경로 오류는 manifest/boundary pin 읽기 전에, 목록 내 누락 ref/SHA 불일치/province 범위 충돌은 선택 raster pin 읽기 전에 거부한다. 실제 선택 파일 바이트가 manifest SHA와 달라진 경우는 기존 pin 단계에서 거부한다. 선택값은 새 내부 dict로 구성하며 입력 목록을 수정하지 않는다.

## 전체 분모와 부분 raster 범위를 구분한다

전체 source/boundary SHA를 먼저 검산한다. coverage는 이전과 같이 전체 `scenes+historical_noneligible_patches`에서 계산한다. 그 뒤 province scope의 source 라벨 참조를 metadata index로 만들고, 요청한 refs가 전부 일치한 경우에만 해당 파일 집합을 raster loop로 넘긴다.

따라서 선택하지 않은 파일의 실제 raster 바이트나 native header는 읽지 않는다. 그 파일의 과거 source metadata를 검토했다는 사실을 실제 파일 품질 검증으로 확대하지 않는다. 전체 manifest의 행/동년 lineage 검사와 선택 raster의 실제검사는 구분한다.

기존 max_files·max_total_bytes·max_windows·max_candidates 및128/256 stride는 선택된 파일 집합에 계속 적용한다. 예를 들어 전체 참조2개 중1개를 선택하고 max_files=1이면 실행할 수 있지만, 같은 cap에서 미지정 전체2개를 읽는 것은 계속 거부된다. byte/window 상한도 선택 스캔을 제한한다. 선택 raster는 읽기 전후 SHA, source/boundary는 전체 실행 전후 pin을 확인한다.

## 결과 필드와 하위 소비 경계

`label_refs`를 지정했을 때만 다음 필드가 추가된다.

|필드 |뜻 |
|---|---|
|`label_ref_filter` |실제로 선택한 source 참조의 canonical 상대경로+SHA 목록 |
|`label_filter_scope` |`ONLY_SELECTED_MANIFEST_LABEL_REFS` |
|`available_label_crops_in_province_scope` |파일 필터 전, 주 범위의 metadata 참조 수 |
|`label_crops_excluded_by_filter` |선택하지 않아 raster를 읽지 않은 참조 수 |
|`requested_province_filter` |caller가 허용한 주 범위; 미지정이면6주 |
|`province_filter` |실제 선택 라벨이 속한 주만 표시.6주를 허용했어도 반텐 라벨1개만 읽었다면반텐만 기록 |

마지막 두 필드를 나눠 부분 라벨 탐색을 전체6주 raster 탐색처럼 표현하지 않는다. `source_row_count`, 후보별 `cell_eligible_at_snapshot/cell_deficit_to_28`는 전체 고정 manifest 기준이다. 같은 파일 내용 SHA의 다른 실제 복사본에서 생긴 중복256창은 기존 `(sha,x,y)` 중복 제외 정책을 그대로 사용한다.

기존 ranked window 형식·256나지 threshold·inside95%·정렬 정책을 바꾸지 않았다.213의 더 높은 밀집 비율 정책·새 원격 label-only 모드는 이번 구현에 포함하지 않는다. 명시 부분 탐색의 candidate consumer_scope는 기존175/176 fresh 검증 요구를 기록한다. `execution_supported/actual_quality_eligible/scientifically_verified_bare/ready_for_training`은 계속false이며 network/collection/training/source writes는0이다.

179/170에 넘기기 전에 현재 source/ledger/전체support/pending·실제scene·SCL·B02·최종품질을 별도로 확인해야 한다. 이번 옵션은 SCL 예외·기존 pending 환불·새 수집 승인이나 기관 권한을 추가하지 않는다. 새 결과를 UI에 게시한다면 요청 주 범위와 실제 읽은 주/라벨 범위의 차이를 그대로 전달해야 한다. 이번에는 API/UI 파일이나 게시 pointer를 수정하지 않았다.

## 시험과 baseline 근거

집중 시험은 **20 PASS /4.248초**다(신규214 8개+기존12개). 실제 Temp GeoTIFF를 사용하며 운영 자료를 스캔하지 않았다.

1. 기본 미지정과 명시None을214 직전186 포함 source의 전체 결과와 비교한다. 기본256 및128/province 지정 결과를 모두 대조한다.
2.2개 중1개만 raster pin/read하며, 비선택 파일의 바이트가 깨졌어도 해당 바이트를 읽지 않음을 호출 기록으로 확인한다.
3.1개 crop만 읽어도 전체28행의 coverage28/셀 부족0을 유지한다.
4. 빈/타입/257개/extra/잘못된SHA/중복 경로/절대·상위 경로를 파일 pin 전에 거부한다.
5. manifest에 없는 파일·요청 SHA 불일치·province 범위 충돌을 raster pin 전에 거부한다.
6. 실제 선택 파일의 바이트 변조를 기존 pin으로 거부한다.
7. 선택 cap·byte cap·128 stride window cap을 유지한다.
8. 입력 refs·라벨/경계 바이트 불변 및 source의 잘못된 label_year가 필터로 우회되지 않음을 확인한다.

집중 로그는 `evidence/integration/bare214-focused-final-20261018.log`다. 당시 Git의 최신173 변경 commit51194는186 추가 이전이어서 최초 legacy 비교 시험의128 인자가 TypeError였다. 제품 회귀 실패가 아니라 baseline 선정 오류다. 편집 전 직접 관측한 source SHA `a8524dc457fd2945fe4845b69757af3b6ba2dd32be5248383175dca1fed964e0`를 기준으로214 최소 diff를 메모리에서 역적용했고, 그 SHA와 정확히 같음을 확인한 뒤 `evidence/integration/bare214-before-source-20261018.py`를 새 보존본으로 저장했다. 테스트는 이 고정 bytes/SHA를 검산하고 실제 legacy 함수를 실행한다. 작업 소스를 되돌리거나 움직이는HEAD를 baseline으로 사용하지 않았다.

초기 로그 `bare214-focused-20261018.log`와 중간 관련 회귀는 보존하며 최종 수치와 합산하지 않는다. 실제 읽은 주 범위와 요청 주 범위를 분리한 마지막 결과 필드 보강은 최종 관련 회귀에서 확인한다.179 review/175 plan 관련 최종 결과와 source/test/doc pin은 아래 마감 절 및 freeze JSON에 기록한다.

운영 새2개 label 스캔은 아직0이다. Root215가 현재 source/label refs를 고정하고 별도로 실행해야 실제 후보 수·선언 나지량을 알 수 있다. 그 후보도 실제 새 영상/독립 정답/학습준비로 세지 않는다. Root는 완료 코드·시험·부분범위 한계를 이해 담당에게 전달해 설명·대본·FAQ·INDEX·변경 이력을 갱신한다.

### 최종 관련 회귀와 동결

최종 관련 회귀는 **50 PASS /40.937초**다.173/186/214의20개와179 review·175 local target plan을 함께 실행했으며 `evidence/integration/bare214-related-final-20261018.log`에 보존했다. 집중20개는50개에 포함되므로 합산하지 않는다. 이전 관련50PASS/38.355초는 실제 읽은 주/요청 주 필드 분리 보강 전 이력이다.

source/test/doc 및 baseline archive의 SHA는 `evidence/integration/bare214-freeze-20261018.json`에 고정한다. 테스트가 고정 baseline archive를 읽으므로 그 검증 보존본도 같은 단위로 인계/커밋해야 한다.214 담당은 CLI·기존source image/라벨·운영원장/잠금·support 예외·UI/API를 변경하지 않았으며 운영 스캔/HTTP0을 유지했다.
