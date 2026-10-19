# 314 — 312 승계·313 profile/API 준비 독립 정적검토

판정: **정적 검토 범위에서 실행 전 필수 코드 수정 발견 없음 / 실제 승계·API·실화면 미검증**. 309 단1 QA는 별도 진행 중이며 이 검토 때문에 재실행·추가QA하지 않았다. 검토는 동결된 코드·준비문서·archive·freeze/최소diff의 읽기와 SHA/bytes 대조뿐이다. 운영 source/ledger/pointer/config·모델·309 부분결과의 추가 읽기0, 시험/import/승계실행/HTTP/제품편집0이다. 담당QA 최소 log/OS 관측과 검토 입력은 구분한다.

## 동결 지문

-312 runner `3460bbfd863162e15f40b8fc622fb24bc4d0b46ae3e1d5645ec24075262ab13e`, freeze `22fd10fbe7f2dcb8cb9b738b875170bd698ff3e8f2a0f56eb5d89c65b6c3d01a`.
-313 runner `7f630140edf01bb7f79992ba948167258cfe70925f023717b0e30869d6169b27`, freeze `6e6a6b3fcdb2b2fe869bf1f446485567e4aa5e464bd06705413cf7da5bb25c25`.

두 freeze 자체SHA 및 참조7파일의 bytes/SHA가 모두 일치했다.312의293 archive SHA08f58c…d789,313의294 archive SHAa75fda…5928a도 freeze에 결속돼 있다.312 최소diff와313 원판 대비 새source/ledger/oldconfig/기대 API 값 변화는 미래 후보 수량을 상수로 넣지 않는다. 검토 당시 shared 원본/실제 profile의 내용이 현재 이 지문과 같다는 운영 검증은 Root 소유다.

## 312 승계 검토 근거

`priority312-promote-root-20261018.py:19–36`에서 동일 명시128 profile scope 안 exact GO schema/status/approved true·고정 source0c/ledgerd5/oldpointer996a·lock 부재를 요구한다. 승인 summary/terminal/handoff는 역할별 expected SHA로 읽으며 terminalexit0·완료status·정확marker·충돌/실SHA불일치0·ready/training/registryfalse/network0을 확인한다. handoff 자체 semantic 내용을 모두 재검사하는 대신 Root가 발급한 정확 지문과 뒤의 독립 행/출력 검산을 신뢰하는 계약이다.

37–46행에서11개 output path 집합과 각개별 bytes/SHA를 역할별 cap으로 검산한다. 세 receipt의 schema2/정확128marker와 source/candidate/plan/QA의 후속 read에 expected SHA를 전달한다. source128/candidate128/readiness16 등 역할이 보존되며 기본64 digest로 돌아가지 않는다. hash만먼저확인한뒤 중간무핀read로 다시 읽는 공백은 이 경로에서 발견하지 못했다.

47–53행 retained/excluded는 list·정확int(bool제외)·범위·중복없음·전체 partition을 검산하며 candidate.scenes가 source retained와 정확 같아야 한다. source/후보/제외 row 수 및 split별 적격/차단목록도 summary/QA와 대조한다. lineage 자체 재대조는312에 추가돼 있지 않으나 앞선 승인된309 handoff의 exactlineage검산 및 실제retained row검산을 전제로 한다. 이 정적검토를 미래309 handoff성공으로 확대하지 않는다.

55–67행 oldpointer996a/834·276·250을 검산하고 원바이트 exclusive archive→새 schema1 reader용receipt→exclusive tmp/flush/fsync→교체직전 oldpointer/source/ledger/lock 및 최종3참조 재핀→os.replace 순서다. 최종3참조는 source/stagecandidate/readiness이며11중간파일 전체를원자snapshot으로묶은것은아니다.68–73행의 same_hash callback은 keyword-only json_role을 받아 동일profile bounded digest로 전달하여 candidate_quality 후reader의128경로를 유지한다. 실제 split·총수·차단·readyfalse·current source 및 source/ledger후핀을 검사한다.

publication 출력 status는 `COMPLETED_QA_PUBLISHED_AND_PROFILE_READER_VERIFIED`, source_snapshot_sha256/pointer_sha256/candidate_view/manifest_profile/exact_retained_rows/partition_complete/file_sha_mismatches이며 아래313의 소비명과 일치한다. pointer schema1과실행receipt3개의schema2는서로다른역할이다.

## 313 소비·설정·API 검토 근거

`profile313-post309-root-20261018.py:15–28`에서312 publication을 Root 전달 exact SHA로 읽고 완료status/marker/retained/partition/SHA0·실제정수 eligible/count3·sourcecurrent·readyfalse를 요구한다.현재source0c/ledgerd5/pointer=publication핀과lock부재를검산한다. oldconfigb9a2…17f9e/source9e635에서source0c149로 바꾸며 descriptor를 크기로 자동선택하거나 cap을 늘리지 않는다. oldconfig는 source만교체하기 전원바이트archive로보존한다.

29–38행 새4출력부재→exclusive archive/tmp/fsync→config 및4운영핀 재대조→replace→selectionreceipt 순서다. publication의필드명을312와맞춰읽고 후보수는 candidate_view실제값에서받는다. stale한예상후보수를확정값으로넣지않는다. profile적용의호출권한은Root의별도실행결정이며이스크립트에별도GO인자검증을추가한계약은아니다.

39–49행 localhost8002/Origin5174의단1GET/timeout150초·응답2MiB상한/no retry를유지한다. raw1407/gap0·publication실후보수·current source·나지3차단false·bare50stale·잔여1799757940/oldpending136314880·운영4핀/config보존11검사를실API결과로확인한다. 이는예정검사이며현재PASS가아니다. 313 scope의누적16GiB와역할별cap도유지한다.

## 실패·검토 한계와 후속

312는pointer교체뒤reader/결과쓰기에서실패할수있고313은config교체뒤selection기록/API/검사에서실패할수있다. 오류가났다고이미적용된pointer/config가자동복구됐다고추정하면안된다. archive·tmp·receipt·selection과현재핀을Root가좁게확인하고적용완료/검증미완료를분리한다. 자동rollback/재시도/부분결과삭제를하는코드는없다. readonlyAPI실패는학습gate우회근거가아니다.

원자적다중파일snapshot/동시외부쓰기차단·OS전역중복검사는이wrapper들이보장하지않는다. Root가QA종료·고정handoff/최종summary/terminal지문·원본hold/OSlock·312새출력미존재·실제oldprofile/핀을확인해야한다. 이번검토는제품모듈전체재감사·309실결과확정·성능/최대RSS/HTTP성공검증이아니다. 실제실행과API 뒤브라우저/콘솔/overflow는web_ui별도검증이며독립정답·학습·전체개발완료승인이아니다.의미있는완료결과는Root가이해자료/대본FAQINDEX이력에별도인계한다.
