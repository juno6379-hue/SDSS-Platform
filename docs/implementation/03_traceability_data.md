# §3/G0/G1 데이터 요구 추적과 실제 v0.2 대조

소유:data_pipeline. 기준: 내부마스터v1.0(2026-10-16),실제제출TECH-4,`contracts/upstream/GMAIS-v0.2/`불변복사본. GMAIS는**GreenBlue내부제안/컨소시엄·BIG미승인**이며승인된계약/TOR를대체하지않는다. 패키지34개SHA일치를독립확인했다. 초기SOURCE_MISSING은발견/복사후해소했고기존초기evidence는보존했다.

| requirement_id | source_section | source_type | subsystem | owner_proposed | acceptance_evidence | current_state | gap | decision_required |
|---|---|---|---|---|---|---|---|---|
| DATA-G0-01 | 마스터§1.2/G0 | internal development instruction | source inventory | data_pipeline/root | inventory분할문서,read-onlyaudit JSON,TECH4실물 | 조사완료 | Git없음/공식계약·기관자료미확인 | root전체Baseline/계약자료확인 |
| DATA-G0-02 | 마스터§1.1/§3.3 | internal proposal GMAIS0.2 | Dataset Contract | root/integration | vendoreddataset schema/profile/34SHA | 실물확인·정적대조완료 | legacyrowas-is불일치;formalvalidator하위환경없음 | 공통schemafreeze/adapter결정 |
| DATA-3.1-01 | §3.1 connector interface | internal development instruction | connectors | data_pipeline | service.py검색/다운로드/등록,데이터시험55PASS이전근거 | PARTIAL | 7메서드플러그interface없음;OGC기관현장미구현;GeoTIFF외FileImport없음 | 기관API/권한TBD,공통Connector profile |
| DATA-3.1-02 | §3.1 HTTP429 | internal instruction/TECH4수집운영취지 | collection safety | data_pipeline | budget.py/parallel.py/nativeHTTP회로,oldSHA2일치,현재pending2·429false | 로컬기능구현·실수집진행 | 운영기관SLA/인증/장기재개인수미검증 | 제공자제한/SLA승인 |
| DATA-3.2-01 | §3.2,TECH4§2.2.5~8 | submitted proposal + instruction | raw/staging/QC | data_pipeline | nativeband/SCL/연차LC/STAC/XML,sha/profile,독립감사별도 | PARTIAL | 모든단계별불변Dataset ID/version없음;ISO프로파일미구현 | v0.2 projection/단계정의/RFC |
| DATA-3.2-02 | §3.2 transformation | instruction/scientific processing | raster alignment | data_pipeline | nearest라벨/SCL,bilinear20m→10m,calibration XML증거,patchaffine | 기존LCLUC기능구현 | 10m격자는20mSWIR새관측아님;DN→반사도학습변환은별도 | 모델입력단위/품질승인분리 |
| DATA-3.3-01 | §3.3;GMAIScross-reference | internal proposal | ID/hash/lineage | root/data_pipeline | patch SHA,source_window/rawcrop/STAC/XMLrefs,Store datasets6 | PARTIAL | 등록된모든raw/processed id+version+sha사슬미완성;genericStore upsert가불변버전규칙아님 | 비파괴적version registry/lineageAPI |
| DATA-3.4-01 | §3.4;TECH4§2.4.1 | instruction + submitted proposal | LCLUC dataset | data_pipeline/ml_pipeline | snapshot848물리/676manifest적격,31/36셀,실제6band·동년Esri | 수집진행/학습BLOCKED | 1000하한·대표성·독립평가미달;5미확보주연도셀 | 학습준비성gate와별도과학승인 |
| DATA-3.4-02 | §3.4 labels | instruction/scientific integrity | annual reference | data_pipeline | WC2020/21전용,Esri2020~25실연차URL/버전,명시taxonomy,docs19 | LCLUC지원 | DW실EE실행미검증;Esri는위성모델약한참조 | 독립라벨/기관제공/라이선스메타충돌검토 |
| DATA-G1-01 | G1 existing compatibility | internal development instruction | migration/API | root/data_pipeline | 기존/api/data/*,原수집자료/old원장불변,이조사쓰기0 | 기존호환유지 | v0.2 dataset projection/registry·공통API마이그레이션미구현 | root공통스키마결정후추가계약시험 |

## 실제 Dataset Manifest schema의 정확한 제약

`schemas/dataset-manifest.schema.json`은Draft2020-12,`schema_version`=`0.2.0`,top-level`additionalProperties:false`이다. 필수는`schema_version,dataset_id,version,source,data_type,spatial,temporal,quality_status,access_class,sha256,artifact_uri,lineage`이다. `source`필수institution/product/license,`spatial`필수bbox4개/crs(EPSG또는OGC:CRS84),`temporal`필수start/end(date-time)/calendar이다. lineage각parent는id/version/sha256필수이다.

정확enum:

- data_type: raster/vector/timeseries/table/document.
- quality_status: RAW/STAGED/STANDARDIZED/VALIDATED/REJECTED. **APPROVED는이dataset enum에없다.** 모델승인이나TECH4품질단계와같다고매핑하면안된다.
- access_class: PUBLIC/RESTRICTED/CONFIDENTIAL.

현재`register_local`결과는status/path/sha256/bytes/metadata/source(문자열)/license/manifest등이며공통dataset_id/version/schema_version이없다. patch row역시scene_id/연도/source_window/normalization/quality_status=`quality_eligible`같은수집계약이다. 이를v0.2로이름만바꾸거나추가속성전체를넣으면source타입/required/enum/additionalProperties에서거부된다. 기존rawmanifest는보존하고새고정ID/version을갖는별도projection을검증해등록해야한다. 이번조사에서는projection을임의구현하거나source schema를수정하지않았다.

| 실제v0.2필드 | 현재근거 | 안전한후속매핑/미결정 |
|---|---|---|
| dataset_id/version/sha256/artifact_uri | 실제파일SHA/path,카탈로그id일부,source/patchID | root정책으로고정dataset ID·불변version과로컬URI프로파일결정. sourcepath만ID로대체금지 |
| source.institution/product/license/source_uri | STAC제공자/assetURL/라이선스,docs19 | 원본제공자와플랫폼호스팅제공자구분. 서명query제거. 미확인기관/권한추정금지 |
| spatial/resolution/no_data | rawprofile CRS/bounds/res/nodata,patchaffine/native해상도 | bbox좌표계해석을freeze해야함. 아래실물예시충돌기록참조 |
| temporal | 영상datetime/label_year/연차제품기간 | 영상취득시각과연차합성기간을별도dataset으로등록;gregorian/timezone명시 |
| quality_status/quality_report_ref | SCL/NoData/polygon/라벨적격,독립정합감사 | quality_eligible는공통VALIDATED/과학승인이아님. 정책매핑필요 |
| access_class/limitations | 공개제품/라이선스근거·메타충돌·모델한계 | 공개다운로드성공만으로모든목적권리승인완료처리금지 |
| lineage | rawsource/SHA/STAC/XML/sourcewindow/bands/patchwindow | parent별등록된id/version/sha보장필요;sourcehash만있다고완전Registry lineage아님 |

## Cross-reference profile와 결정항목

실물`templates/cross-reference-profile.md`는dataset/model id+version+sha고정,latest는탐색전용,blob/등록ID/권한/retired무결성,query→trace→workflow→job→dataset/model→result→layer/report사슬을요구한다. 또원본/가공독립버전과`parent_refs,process_version,parameters_hash,executed_at,actor,result_hash`lineageevent를명시한다. 현재수집manifest는원본/변환/해시근거가있지만이공통이벤트스키마/Registry 전체사슬은아직없다. sourcefileSHA/stacID를운영계약완료로해석하지않는다.

미결정/RFC후보:

1. **BBOX_CRS_INTERPRETATION**: upstream의실제`examples/dataset-example.json`은bbox경도106/위도-6값과`spatial.crs=EPSG:32748`를함께쓴다. schema는수치4개와CRS패턴만검증하여이의미불일치를막지못한다. 실제rasterCRS의bounds를쓸지WGS84bbox를별도표시할지root/commonprofile에서확정해야한다. 예시를그대로실자료에복제하지않는다.
2. **QUALITY_VS_APPROVAL**: datasetenum에APPROVED가없으며scientific_validation/deployment_approval은별도상태다. 수집80%/95%또는schemaPASS를과학승인으로승격하지않는다.
3. **EXTENDED_METADATA_LOCATION**: top속성추가불가이므로affine/band원해상도/scaleoffset/classlegend/Verticaldatum/ISO19115필드를어떤버전있는참조프로파일로연결할지root합의필요. source스키마를조용히확장하지않는다.
4. **IMMUTABLE_LINEAGE**: genericSQLite`INSERT OR REPLACE`기존정책과id/version불변기록을비파괴adapter/별도table로구분해야한다. 기존원장/카탈로그/체크포인트초기화금지.

## 검증범위와차단

실제v0.2패키지34개SHA검사/코드대조/진행중수집원장2개pinnedSHA일치/표본6파일SHA재계산/readonlySQL을수행했다. formalJSONSchema/OpenAPI참조시험은이하위환경에jsonschema가없어실행하지않았다. 이사유는서버차단/모델readiness/데이터부족과별도이며root의패키지계약시험환경에서확인해야한다. 실수집session89858,원장,수신파일,collector코드에수정0/새네트워크0이다.
