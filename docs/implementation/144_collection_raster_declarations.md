# 144 — 새 수집 영상의 밴드 description과 scene 품질 마스크 선언

상태: **TESTED_SYNTHETIC**. 이번 변경은 `scripts/collect_samples.py`의 `collect_windows`가 **새로 쓰는** image.tif와 scene quality-mask.tif에 한정된다. 실제 수집·다운로드·학습·운영 자료 재작성은 실행하지 않았다. STAC 검색과 COG 읽기를 명시 mock으로 대체한 Temp 실행에서 실제 GTiff를 만들고 읽어 검증했다.

소유 범위는 기존 collect_samples.py의 작은 부분, 신규 집중 시험, 이 문서다. 기존 143 이하의 준비/저장/Registry/실행 gate, main/API/UI, `collect_training_grid`의 label+AOI mask는 수정하지 않는다. collect_samples.py는 실제 LF 파일이며 LF 형식을 유지했다. 제품 diff는 **8줄 삽입·3줄 삭제**이고 collect_windows의 지정 쓰기 부분만 바꿨다.

## 밴드 순서와 description

기존 선택·정합을 마친 arrays를 한 번 stack으로 만들고 **기존 순서 그대로** image에 기록한다. 각 실제 asset 이름에 `pc_band_keys.get(asset, asset)`를 적용한 description을 설정한다.

| 알려진 논리 이름 | description |
| --- | --- |
| blue / green / red | B02 / B03 / B04 |
| nir / swir16 / swir22 | B08 / B11 / B12 |

이미 물리 이름 B02/B03/B04/B08/B11/B12라면 그대로다. 알 수 없는 asset은 이름을 그대로 기록하며 Sentinel-2 이름을 추정하지 않는다. 요청 순서가 바뀌었다면 그 순서를 그대로 유지하고 소비자의 고정 순서 검사에서 판단하도록 한다. EarthSearch/Planetary Computer의 기존 asset 선택 규칙도 바꾸지 않는다. row의 기존 bands·logical_bands·band_processing은 같은 asset 순서를 유지한다.

description이 존재한다는 것은 명시 이름 metadata를 기록했다는 뜻이다. 기관 원출처·실제 분광 반응·물리 보정·연차별 방사 정합을 인증하지 않는다. 기존 image DN nodata=0, float32 정합 및 raw DN 값을 유지하며 reflectance_conversion_verified와 각 scale_offset_applied는 계속 false다. 알 수 없는 이름이나 순서가 다른 영상이 신규 6밴드 consumer를 통과하도록 추정·재배열하지 않는다.

## scene-level 0/1 mask

기존 nonzero 조건에 finite 검사를 더해 다음 조건을 계산한다.

```python
valid = np.all(np.isfinite(stack) & (stack != 0), axis=0)
```

어느 image band든 0, NaN, +Inf, -Inf이면 해당 픽셀을 invalid로 한다. 그 뒤 기존 SCL nearest 정합과 **0, 1, 3, 8, 9, 10, 11 제외** 코드를 그대로 적용한다. SCL이 없으면 기존 quality_unverified와 cloud 미검증 상태를 유지한다. finite/nonzero만으로 구름을 판정하거나 quality_eligible을 새로 부여하지 않는다. 기존 threshold·quality_status 계산과 라벨의 valid-mask 적용 방식도 그대로다. 새 finite 조건 때문에 NaN/Inf 위치는 downstream label에서도 기존 valid-mask 적용 코드에 의해 0이 될 수 있으며, 이를 모든 새 label 바이트가 보강 전과 동일하다는 주장으로 확대하지 않는다.

새 scene quality-mask.tif는 count 1, uint8, 실제 값 0/1이고 **nodata=None**이다. 0은 명시 invalid 저장값이지 “저장된 값이 없는 픽셀”이 아니므로 GDAL의 기본 all_valid band mask에서도 읽을 수 있어야 한다. description은 `binary_validity`다. nodata나 description만으로 그 픽셀의 물리적 참/거짓이나 기관 품질을 인증하지 않는다.

새로 생성한 row에는 exact4 선언을 넣는다.

```json
{"schema_version":1,"kind":"binary_validity","valid_value":1,"invalid_value":0}
```

필드 이름은 `quality_mask_semantics`다. 이는 **이 scene-level SCL + finite/nonzero image mask**의 계산 계약을 설명한다. source.mask_semantics GMAIS manifest를 자동 만들거나 보고서·Registry·기관 QA·연차 전체 학습 준비를 생성하지 않는다. 기존 nodata_only_cloud_unverified 문구는 유지되지만 실제 계산에는 이번 finite 조건이 추가됐음을 이 문서에서 구분한다.

## 유지한 producer 경계

raw-source-crops의 원래 쓰기와 metadata는 바꾸지 않는다. SCL/라벨 원본의 nodata=0, label 결과 nodata=0, nearest·bilinear 선택과 20m SWIR 정합, WorldCover/Esri taxonomy·label/AOI 결합 정책은 그대로다. 예산 예약·실측 정산·HTTP429 회로·retry·후보 선택·resume 상태·기존 SHA 검증 경로도 수정하지 않는다. 실제 원장·lock·예약을 조정하지 않았다.

여기서 label 정책 유지란 작성 코드와 nodata·정합·분류 규칙을 바꾸지 않았다는 뜻이다. 새 finite valid를 기존 `aligned[~valid] = 0` 코드가 소비하므로 **새로 생성하는 파생 label**의 NaN/Inf 위치는 이전 코드로 생성했을 때와 달리 0이 될 수 있다. 기존 저장 원본·기존 산출물은 다시 쓰지 않으며, raw crop 바이트 보존과 신규 파생 label 전체 바이트 동등성을 서로 다른 주장으로 구분한다.

기존 SHA 검증 뒤 skip되는 image/label과 saved row는 그대로 반환한다. description이 없거나 quality mask가 옛 nodata=0이고 quality_mask_semantics가 없는 구산출물도 이번 코드가 재작성하거나 역채움하지 않는다. 그 자료가 새 consumer에서 차단되면 명시적인 새 자료/버전 준비가 별도로 필요하다. 기존 quality mask를 검산하지 않는 resume 정책도 이번에 강화했다고 주장하지 않는다.

## 검증

최종 집중은 **7 PASS / 3.086초 / exit 0**, `evidence/integration/collection-raster-declarations-agent-20261018.log`다. 모든 collect_windows execute=True는 Temp root에서 수행했고 search_stac/read_cog_window를 mock했다. 실제 외부 검색·네트워크 전송은 없다.

- Planetary Computer 논리 6밴드와 EarthSearch 논리/물리 asset에서 실제 6밴드 description·픽셀 순서·DN nodata=0을 확인했다.
- unknown asset과 reordered band를 그대로 기록하고 B03 등을 발명하지 않음을 확인했다.
- 실제 4×4 GTiff에 0/NaN/±Inf와 SCL 제외값을 넣어 mask **valid 5 / invalid 11 / total 16**, uint8·0/1·nodata=None·all_valid·description을 확인했다. SCL 없는 별도 fixture는 12/16이고 cloud 미검증을 유지했다.
- label/원본 crop의 기존 nodata와 정합·source metadata·reflectance false를 확인했다. 명시 Temp legacy fixture를 만든 뒤 resume에서 STAC/COG 호출 0·구파일 바이트 불변·누락 선언 역채움 0을 확인했다.
- 별도 시험 caller가 report metadata와 source.mask_semantics·고정 manifest를 명시하고 Temp Registry 3건을 setup한 뒤, 131/133 소비가 **5/11/16**을 반환하고 DB/전체 파일이 바뀌지 않음을 확인했다. 이 setup은 collector의 자동 보고서/Registry 기능이 아니다. 과학/실행 flag는 false다.

초기 집중은 **7 실행 / 6 PASS / 1 ERROR / 4.672초**였다. 시험이 UTF-8 window-state.json을 Windows 기본 cp949로 읽은 구성 오류였고, `collection-raster-declarations-agent-initial-20261018.log`를 보존했다. 시험 read_text에 UTF-8을 명시한 뒤 최종 시험을 통과했으며 제품 소스는 그 오류 때문에 바꾸지 않았다. 초기·최종·관련·독립 수치를 합산하지 않는다.

동결 source SHA는 `a78d0293736780e70402b85714f38964c2ef09e1253cf7453e292ca9a2551c98`, test SHA는 `469ff453b37a91a4f6d7cf890e5721b9c0aeec31df2a28b215c1017e9f8c821e`다. Root는 기존 producer 회귀·원본 보존·공통 인계/Git과 이해 에이전트 배정을 맡는다. 이해 담당은 검증된 코드·실제 Temp GTiff·mock 경계를 읽고 해설·발표 대본·FAQ·INDEX·변경 이력을 갱신한다.

독립 최종 `collection-raster-declarations-independent-20261018.py/.json/.log`는 **7 PASS / 0 SKIP / 실패·오류 0 / 4.4893717초 / exit 0**이다. baseline bd03292e의 기존 15개 파일 Git·전후 바이트가 같고, collect_windows 외 top-level AST가 동일함을 확인했다. baseline 원문을 격리 실행한 별도 Temp와 비교해 raw crop 6개의 바이트가 동일했고, nonzero만 보던 구 유효값 15/16이 finite 조건에서 12/16으로 바뀌는 차이를 관측했다. 이는 명시한 비유한 값 보강이며 기존 원본의 변환이 아니다.

독립의 별도 caller manifest/semantics/report metadata setup은 새 수집 파일 → 140 저장 → 141 읽기 점검 → 142 Temp 등록 → 133 소비를 실제 수행해 **9/7/16**을 확인했다. 담당 집중의 **5/11/16**과 서로 다른 fixture이며 같은 실측으로 표현하지 않는다. 영상·마스크 bytes는 소비 중 그대로였고 reordered 영상은 129의 고정 순서 검사에서 차단됐다. STAC/COG 응답만 mock이며 실제 GTiff/파일/SHA/임시 SQLite는 사용했다. 운영 네트워크 수집·학습·원본 재작성은 0이고, 내부 소비 성공을 기관 QA·물리 보정·모델 승인으로 확대하지 않는다.

Root 관련 16개 모듈은 **156 실행 / 155 PASS / 1 SKIP / 69.832초 / exit 0**, `collection-raster-declarations-root-related-20261018.log`다. SKIP은 기존 test_collection_recovery의 실제 symlink 권한 미확보다. 수집 retry/resume·예산·기존 label/grid와 품질 보고서·소비 관련 회귀를 이번 보강과 함께 확인했다. Root의 source-scope 검증은 지정한 세 변경 블록만 역변환하면 baseline source와 정확히 같고, 다른 AST 및 LF 형식을 유지함을 확인했다. 신규 metadata를 제외한 다른 수집 동작 변경으로 확대하지 않는다.

기존 producer를 수정했으므로 Root가 이번에는 **전체 backend 회귀도 실제로 실행**했다. 결과는 **1426 실행 / 1425 PASS / 1 SKIP / 296.344초 / exit 0**, `collection-raster-declarations-full-20261018.log`다. 제외된 한 건은 기존 Windows 실제 symlink 권한 시험이며 초기 전체 실패나 전체 재실행은 없었다. 이 수치는 이번 144의 전체 회귀 근거이고 이전 137 전체 시험이나 집중·관련·독립 묶음과 합산하지 않는다. 자동시험 통과는 실제 운영 수집 재개·자료 확보·과학적 정확도 검증을 뜻하지 않는다.

최종 `collection-raster-declarations-live-integrity-final-20261018.json` 보존 감사는 **기존 소스 총 327개 중 승인한 collector 1개 변경·나머지 326개 불변**, 보호 파일 141개·이전 증거 1381개·catalog 14행 canonical SHA·운영 dataset_versions 0·예약 136314880바이트 유지로 구분한다. 최초 snapshot의 소스 326개에는 collect_samples.py 자체가 빠져 있어 처음 감사 JSON은 “326개 불변·변경 0”만 기록했다. 이를 collector도 변경되지 않았다는 뜻으로 해석하지 않는다. Root는 pinned Git bd03292e의 collector blob을 별도 기준으로 추가하고 source-scope의 승인한 세 블록 검증과 결합해 327/1/326으로 감사를 보완했다. 최초 JSON은 `-initial`로 보존하고 보완 이유를 기록하며, 제품이나 시험을 바꾸지 않아 source/test 재실행은 하지 않는다.

새 밴드/scene-mask metadata는 기존 main/HTTP/137 계약·UI·모델 metadata를 바꾸지 않는다. 이번 frontend/build/browser 재실행은 필요하지 않고 기존 UI 수치를 새 결과로 표현하지 않는다. 실제 운영 프로세스가 이 새 코드를 적용해 수집했다는 검증도 없다. 원본·분할·모델·원장·lock·예약을 보존하며, 독립 라벨·전연차 확보·기관 품질 및 모델 승인·정식 per_scene 실행은 여전히 별도 후속이다.

후속 145 후보는 patch image의 band description 전파와 label 지원 mask·순수 scene 품질 mask의 구분을 실제 producer/consumer에서 검토하는 단계다. 이번 144는 그 patch 경로를 수정하지 않았으며, label/AOI 결합 mask를 scene binary validity와 같은 의미라고 재분류하지 않는다.

## 후속145 patch 선언

[145 격자 패치 보강](145_grid_patch_declarations.md)은 원본 영상 밴드 description을 전파하고 label/AOI가 결합된 patch 지원 마스크를 scene 순수품질 선언과 구분한다. 기존 원본/scene 보고서·운영 파일을 재작성하지 않았고 기존 materializer의 지정 경로 덮어쓰기 가능성은 유지한다.
