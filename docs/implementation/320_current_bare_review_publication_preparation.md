# 320 현재 나지 로컬 검토 게시 준비

## 2026-10-18 23:27 KST — 실제 게시·reader 검증 완료

이 절이 아래 준비/미실행 상태를 대체한다. 원준비판은 `evidence/integration/doc320-preparation-before-actual-root-20261018.md`에 원바이트 SHAca39e23a04a266f840b7a20a78557612ab5d1fb3242ac89400714d08b743f344로 보존했으며 기존freeze/코드는 소급 바꾸지 않았다. 321 독립정적검토 SHA21522d20b0f4b7f70a837d83feb8edc6188ae17ac50b76a03421bd1bdfe13713의 추가차단없음과 Root 전체코드/고정6참조핀/실OS/lock 검토 뒤 Root별GO fe175d0019ccffcd2d5acaf1492f84e7c54c86ef84b0767e7885c29bf2fb9329로 정확1회 실행했다.

실행exit0/결과23:27:25.512160 KST, `evidence/integration/bare320-publication-root-20261018.json` SHA54737ef0a93326797e9b10331da287bfcf6f23a8ee4b63453a6e9a2a2694e69a는 LOCAL_ONLY_REVIEW_PUBLISHED_READER_VERIFIED다. 원316report16b923a42c28d89e26b2003c24ab4ca46e9bb9b28e95f2d8a1e8d3f25b1f9093/707005B를 새DATA파일에 원바이트 복사했다. oldbarepointer1018b59294871df8f9e339d63695f08632a5632419b3831e47bdeb2f88c785ab는 archive 후 새pointer5f23cc3760766e3994ac1e4f6d099d5dadbb694e7675d586aad5cb201cd63972로 승계했다. 원234report와 과거37/50 검토는 보존했다.

reader는 현재source0c149일치/50후보·35겹침15clear/상호56쌍·6주행·localinvalid0·실품질/집행/과학검증false를 확인했다. inventoryBLOCKED 첫target겹침과 전체검산3true를 유지했다. 후보1391pointer25d7/원본source/ledgerd5 불변·수집/학습/원격0이다. 같은128scope/누적JSONIO215219012B(최종publication쓰기 전)<16GiB를 확인했다. 아직 이 게시결과 자체는 API·실브라우저를 검증한 것이 아니며322/323 후속과 구분한다.

## 준비 상태

상태는 **IMPLEMENTED_UNVERIFIED — Root 최종 GO 전 실행0**이다. 원 bare234-publish-root-20261018.py를 원바이트 archive하고 새 bare320-publish-root-20261018.py와 diff를 작성했다. 원판의 unbounded read_bytes/read_text와 rawhash 방식은 새 코드에 재사용하지 않았다. 현재 운영 source/ledger/pointer/report/result를 직접 읽지 않았고,Root가 전달한 exact schema·핀·수치와 제품 reader 코드만 사용했다.compile만 했으며 import/실행·HTTP/API/브라우저·native/QA·게시·원본원장 쓰기는0이다. 기존50/37보고서와 oldpointer를 덮어쓰지 않는다.

## 게시할 검토의 범위

게시 대상은 기존 나지 제안50개를 현재 post304/309 source에서 다시 로컬 검사한316 보고서다. 새50개 제안을 찾거나 원격 영상을 취득했다는 뜻이 아니다. result 고정SHA는aaa97f9b64fca9e6a11d8fe9f07a4e649c224ed69fbae599605d28f49490887e,report는16b923a42c28d89e26b2003c24ab4ca46e9bb9b28e95f2d8a1e8d3f25b1f9093·707,005바이트다.50개 중 과거 support와 겹침35/clear15·후보상호겹침56쌍이며,inventory/pending footprint/source pin 검증3개 true와native_label_recheck true를 확인할 계획이다.

result의 LOCAL_FULL_REVIEW_COMPLETE_EXECUTION_UNAPPROVED와 report의 LOCAL_NATIVE_REVIEW_COMPLETE_EXECUTION_UNAPPROVED는 로컬 검토 완료다. result inventory_status=BLOCKED/issue=EXISTING_SUPPORT_OVERLAP는 기존 첫 선택의 집행차단이며 전체 로컬 관측 근거를 없애는 상태가 아니다.이를집행승인으로 바꾸지 않는다. execution_supported/actual_quality_eligible/scientifically_verified_bare는 false이며 network_requests0이어야 한다. 원격 SCL·B02·실제 신규 품질은 여전히 미검사·집행 미승인이다.

## Root 승인과 bounded 계상

새 approval은 절대 evidence 경로 JSON으로 받고 kind=ROOT_BARE320_LOCAL_REVIEW_PUBLICATION_GO,approved 정확히 true,result/report/source/ledger/currentcandidate/oldbarepointer SHA의 정확한 키집합과 값을 요구한다. source는0c149628ccfa916ee976e561c5da05f9ccc810cbeab7d233a05b9bc7eff54658,ledger는d5ee31ff7970adaaa6b166805c240616efa8e9af713bb8394c7a166346f21c91,current1391 candidate pointer는25d7bf6d37a7c96ab6a9eaa2a74e78b94f52e8186b22a8ac705184ff96b5832e다. source는 actual current raw manifest를 bounded_json_digest로 직접 해시해 report.request.manifest_ref와 ui_summary.current_manifest_sha256까지 일치해야 한다. 운영 원본/원장/후보 pointer는 게시 전후 보존한다.

모든 JSON 입력·hash·파일출력은 동일 scope(NAME)의 명시128MiB/누적16GiB ContextVar 아래 read_metadata/bounded_json_digest/write_new_json_bytes 역할을 사용한다. source128MiB/status_report16MiB/local_plan2MiB/pointer64KiB가 각 파일의 역할상한이다. 원본 전체 parse나 native를 실행하지 않고 source는 bounded digest로만 검산한다. existing bare_target_review의 내부 report 읽기는 기존 evidence역할2MiB를 같은 active scope에서 사용한다. stdout 출력도 write_measured로 같은 예산에 계상한다. descriptor를 바꾸거나 size 기반 자동 상향하지 않는다. OS/collector 부재와 source hold는 Root 책임이며 lock 부재 관측을 원자잠금으로 부르지 않는다.

## 원본 보존과 교체 순서

old latest-bare-review pointer SHA1018b59294871df8f9e339d63695f08632a5632419b3831e47bdeb2f88c785ab를 기대값으로 읽고,그 report 참조가 정확히 bare-review234-20261018.json/SHA c936575e2937d5c8ec9f1e4675de89eed0f5dbabce26bbd26bea8661c4b18458인지 검사한다. old report 자체도 bounded digest로 확인한다.

새 data/first-group-training-priority/bare-review320-20261018.json에316 report 원바이트를 exclusive 복사하고 지문을 검산한다. oldpointer 원바이트 archive는 bare-review-pointer-before320-20261018.json,새receipt는 bare-review-receipt320-20261018.json,독점temp는 latest-bare-review320.tmp다. 시작 전 새4경로와 publication 산출물 부재를 확인한다. 모든 바이트 쓰기는 bounded writer로 수행하고 temp를 flush/fsync한다.교체 직전 oldpointer/current source/ledger/currentcandidate 및 원본316report·새DATAreport SHA와 lock 부재를 다시 확인한 뒤 os.replace한다.

후검사 reader는 current source true·후보50·report지문·overlap35/clear15/local_invalid0·실행/품질/과학검증 false를 요구한다. currentcandidate pointer와 source/ledger핀,oldreport·newreport핀도 다시 확인한다.즉 기존 후보1391 QA/receipt를 새로 게시하거나 변경하지 않는다.

## 결과·실패·후속

새 evidence/integration/bare320-publication-root-20261018.json은 LOCAL_ONLY_REVIEW_PUBLISHED_READER_VERIFIED,oldpointer보존·새reader view·source/ledger/candidate핀·고정report/result핀·3가지 false권한·remote0·범위와 JSON계측을 기록한다. old proposal50을 current309 source에서 재검토했다는 provenance도 명시한다. BLOCKED 첫target와 clear15의 로컬 관측을 구별하며 candidate상호겹침56쌍을 잊지 않는다.

교체 뒤 reader/결과쓰기/계측 출력이 실패하면 새 pointer가 이미 적용됐을 수 있다. archive·새 report·receipt·부분증거를 보존하고 적용과 검증 실패를 구분한다.자동rollback/retry·옛보고서 덮어쓰기·임의환불은 없다.Root가 최종 코드·독립리뷰·정확GO·현재source/ledger/pointer/OSlock을 검토해야 한다.실API/브라우저 확인은 별도단계이며 이 준비판이 완료했다고 주장하지 않는다.후속 이해자료와 UI는 로컬 검토 current 갱신과 원격 미검사·집행미승인을 함께 설명해야 한다.학습/모델/독립정확도·전체 개발 완료는 승인하지 않는다.
