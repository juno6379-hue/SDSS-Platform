# 312 최종 후보 승계 준비

## 2026-10-18 23:06 KST — 실제 게시·reader 검증 완료

이 절이 아래 준비/미실행 상태를 대체한다. 원준비판은 `evidence/integration/doc312-preparation-before-actual-root-20261018.md`에 원바이트 SHA766b2fd6b98a00d9fd9a8d08bc1d7e4966c5466c501be41ea596476a27ee7fb5로 보존했다. 기존 freeze와 코드 지문을 소급 수정하지 않았다.

309 최종QA exit0/1608.765초·source314.125/candidate343.078초와 인계검산11output·3v2receipt·exactpartition/lineage/history·5526파일SHA불일치0·원본원장보존을 Root가 확인했다. 실제 summary1359667f4ef2316b8bfffc52a939cd626ca6b87be10139ec192c0abe5b47ec3b/handoff8c02c1831358e684c6788a8820e79173464a0f47d3d860199ec5b1a97f8831f1/terminalf5fa44070eeb071c7c5cb1105908dd6d6110e335ccda9cab58b47a97957b8a30를 읽고 별도 approval5d1a0b1f313bdc946c24996156744bd154e44da283f82dc72e5d82b9d94e948e를 발급했다. 314 독립 정적검토 SHA4efd5803c7b6783ad725d22dc36627860158f389f757a95c140f03434068237f의 추가차단없음과 Root 전체코드/실OS/lock 검토 뒤 단1 실제 승계했다.

session36009 exit0, 실제 결과 `evidence/integration/priority312-publication-root-20261018.json` SHAae247af18730fc9d391b8c5730d5db5c72772b1545d2b5112a8aa6f1a7bf0356/23:06:11.607432 KST는 COMPLETED_QA_PUBLISHED_AND_PROFILE_READER_VERIFIED다. old1360 pointer996a88de2034e9803381d7ae4e906a0d1f418075675d13ef796fb5648bb472c0를 원바이트 archive한 뒤 새1391(865/276/250) pointer25d7bf6d37a7c96ab6a9eaa2a74e78b94f52e8186b22a8ac705184ff96b5832e로 승계했다. 현재source0c149 일치/reader availabletrue·충돌0/차단3·readyfalse를 확인했다.

동일128 scope·role-aware json_role callback·교체직전3참조/원본/원장 핀을 유지했다. 게시작업 JSONIO840543869B(최종결과쓰기 전)이며16GiB 이내다. 이 값은 앞선 QA+handoff5076287859B와 다른 작업 범위다. 원본1779행은 보존하고 후보에서만 동일scene16행을 제외해1763행/1391적격으로 게시했다. 학습·registry·API·브라우저·profile변경0이다.

다음313이 실publication SHA에 결속해 oldprofile을 보존하고 현재source로 명시 재결속·실API를 확인한 뒤315 실화면을 검증한다. 그전에는 현재 UI 반영 완료를 주장하지 않는다. bare50는 과거source 검토라 stale·미검사/집행미승인을 유지하며, 나지3차단/학습false·전체개발 미완료도 변하지 않는다.

## 상태와 경계

**IMPLEMENTED_UNVERIFIED — 실행 전 준비**다.309 실QA가 끝나기 전 현재 검증된293 게시 코드를 새312 경로로 최소 파생했다. 실제309 terminal/summary/handoff·부분 산출물·운영 source/ledger/pointer는 읽지 않았다.새 후보 수·분할·파일 수는 미확정이다. 실제 승계·QA·native·HTTP·모델/Registry·설정 변경은0이다. Root가 최종 결과를 검토하고 별도 정확한 publication GO를 발급하기 전 실행하지 않는다.309 QA GO나304 native GO를 승계 승인으로 재사용하지 않는다.

원판 evidence/integration/priority293-promote-root-20261018.py SHA08f58cf98db254c73679f27d1fd6ef4b99be96e90f94c49aed1c271d2fbfd789는 보존했다.원바이트 사본 priority312-before293-20261018.py,새 priority312-promote-root-20261018.py,최소diff priority312-minimal-diff-20261018.patch를 별도 작성했다. 변경은312/309 번호·고정 source/ledger/oldpointer·기존 split834/276/250·현재 원본 범위 설명뿐이다.공유 제품 코드는 수정하지 않았다.메모리 compile과 정적 읽기만 수행했으며 import/실행/새 시험은0이다.

## Root 승인 입력

Root는 실제309 완료 terminal·summary·handoff 지문을 검산한 뒤 절대 evidence 경로의 승인 JSON을 제공한다. 정확한 키는 kind,approved,summary_sha256,handoff_sha256,terminal_sha256,source_sha256,ledger_sha256,previous_pointer_sha256이며 kind는 ROOT_POST309_PUBLICATION,approved는 정확히 true다. source는0c149628ccfa916ee976e561c5da05f9ccc810cbeab7d233a05b9bc7eff54658,ledger는d5ee31ff7970adaaa6b166805c240616efa8e9af713bb8394c7a166346f21c91,oldpointer는996a88de2034e9803381d7ae4e906a0d1f418075675d13ef796fb5648bb472c0의 고정 tuple과 맞아야 한다. 준비 담당자의 현재 운영 파일 재조회 값이 아니라 Root 인계 기대값이다.

309 terminal은 완료/exit0,summary는 완료·동일 profile MARKER·파일SHA 불일치0·남은 source identity 충돌0·훈련/Registry/네트워크0·ready false여야 한다.현재 source/ledger를 실제 기대핀과 비교하고 lock 부재를 요구한다. Root는 실제 QA/collector 부재와 원본 hold를 유지한다. 이 스크립트의 lock 부재 관측이 수집기 원자잠금을 대체하지 않는다.

## 128MiB와 고정11개 산출물

전체 동작은 기존 scope(NAME)의 명시128MiB/3000행·depth32·node4M·누적 JSON16GiB 안에서 역할별 read_metadata/bounded_json_digest를 사용한다. source/candidate가 기본64MiB를 넘더라도 같은 scope가 끝까지 유지된다. 자동 상향·실QA 재실행은 없다.

11개 역할 map은 source,source-readiness,split-plan,candidate-package plan/candidate/receipt,staged candidate/receipt,policy,QA readiness/receipt다. summary.outputs가 이 정확한 경로 집합이어야 하고 모든 byte/SHA가 맞아야 한다. 이후 receipt/candidate/plan/readiness를 다시 읽을 때도 summary의 기대 SHA를 지정한다. candidate-package/staging/QA의3receipt는 schema2와 동일 profile MARKER를 요구한다.

retained/excluded는 list이며 bool이 아닌 정수·범위 안의 index들로 전체 source 행을 중복 없이 정확히 분할해야 한다.실 candidate.scenes가 source retained 행들과 정확히 같아야 한다.행 수·제외 수·split 적격·차단목록은 summary/QA와 일치해야 한다.후보 수와 blocker 수는 실제 완료summary에서 소비하며 미래 값을 예상해 삽입하지 않는다.초기 핀 검사와 교체 직전 최종3참조 재검사를 구별하고 모든 중간 파일의 원자 snapshot이라고 표현하지 않는다.

## 기존1360 보존과 교체

old pointer는996a 지문 및 split834/276/250으로 검산한다. 원바이트를 candidate-pointer-before312-20261018.json에 exclusive archive하고 지문이 같은지 확인한다. 새 candidate-receipt312-20261018.json과 latest-candidate312.tmp를 exclusive 기록·flush·fsync한다.교체 직전 oldpointer/source/ledger와 lock 부재 및 최종source/staged candidate/readiness3참조의 summary핀을 재확인한 뒤 os.replace한다.

후검사 candidate_quality callback은 same_hash(path,pin,*,json_role)를 받아 역할별 bounded_json_digest로 전달한다.동일128 scope 안에서 source/candidate/readiness를 검증하고 실제 split·총적격·차단수·ready false·source current 일치를 요구한다.이전 json_role 누락이나 기본64MiB callback으로 돌아가지 않는다.후검사 뒤에도 source/ledger핀을 다시 확인한다.

완료 evidence는 priority312-publication-root-20261018.json에 status=COMPLETED_QA_PUBLISHED_AND_PROFILE_READER_VERIFIED,pointer_sha256,source_snapshot_sha256,candidate_view,manifest_profile,exact_retained_rows,partition_complete,file_sha_mismatches 등 기존293 결과schema로 남긴다.외부 pointer는 기존 reader용 schema1이며 실행receipt3개의 schema2와 구별한다. API/브라우저/profile 재결속은 이 스크립트가 수행하지 않는다.

## 부분 실패와 후속 인계

이미 있는 archive/receipt/tmp/result는 덮어쓰지 않는다.교체 뒤 reader나 결과 쓰기가 실패할 수 있으므로 pointer가 이미 바뀐 적용 사실과 검증 미완료를 구분해야 한다.부분 산출물을 지우거나 같은승계를 자동 재시도·rollback하지 않는다.Root가 실제 실패 위치·현재 지문을 좁게 확인해 다음 조치를 정한다.

준비 freeze는 evidence/integration/priority312-preparation-freeze-20261018.json이다. 최종309 지문과 후보 수는 아직null이며 Root 실행 승인과 별도 독립 정적검토가 후속이다. 실제 완료 뒤 oldpointer보존·정확분할/행·11핀/3receipt·source/ledger불변·새reader 결과를 검산하고 관련profile 재결속·실API/브라우저·이해자료를 별도 소유로 인계한다.나지 부족·readyfalse·독립 정확도 미검증과 전체 개발 미완료를 유지한다.
