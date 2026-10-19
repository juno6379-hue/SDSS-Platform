# 293 게시와294 source profile 소비 계약 독립 정적 검토

## 결론과 지문

상태는 **IMPLEMENTED_UNVERIFIED — 동결 코드의 정적 검토**다. 293 게시 준비 코드와294 소비 코드의 schema 및128MiB 처리 경로에서 추가 실행 차단 결함을 발견하지 못했다. 운영 source·ledger·부분 QA 산출물·후보 실제파일은 읽지 않았다. HTTP·제품 시험·실제 QA·게시·설정 변경은0이며 최종 후보 수를 확정하지 않는다.

293 freeze SHA708b593d0b52109c5b0eb878253aa26af98cdb56443567d7e371f95e71c8a491를 확인하고 그4개 파일 byte/SHA가 전부 일치함을 확인했다. runner는08f58cf98db254c73679f27d1fd6ef4b99be96e90f94c49aed1c271d2fbfd789,275 최소 diff는1c3015d269883aa71a9d295349012692db59de5b682b88744fee552b2a5a12b9다. 원275와 사본 원판의 SHA는d5ba83bf030a97c85e5570aba9b7b87a6ccda743672254e88ae561c4536f61a8로 보존된다. 함께 검토한294 코드는a75fdac5f66830ba5c322aa1bd7237ad4939b6b644f73edc6fd340b303d5928a다. 정적 검토 담당자의 코드 수정은0이다.

## 128MiB와 역할별 읽기 경로

293 main 전체는 manifest_resource_profile.scope(NAME) 안에서 동작한다. approval·terminal·summary·handoff와 정확한11개 출력 map을 각 JSON 역할로 읽고 hash를 대조한다. source/candidate 역할은128MiB, 다른 역할은 각각의 기존 상한을 사용하며 동일 ContextVar 누적16GiB 예산을 유지한다. 전달받은 candidate 크기67,599,006바이트는 기본64MiB를 초과하지만128MiB 안이다. 이 크기는 Root 인계값으로만 사용했으며 실제 후보파일을 준비 검토에서 읽지 않았다.

후보는 stage/candidate.json을 role='candidate'로 읽고, 최종 pointer의 source/candidate/readiness3개 파일 SHA도 같은 역할 map으로 고정한다. 교체 뒤 candidate_quality가 active profile을 확인해 pointer를 역할 기반으로 읽고 same_hash(path,pin,*,json_role=...)를 호출한다. callback은 전달받은 json_role로 bounded_json_digest를 호출하므로 candidate 참조가 기본64MiB 검사로 떨어지지 않는다. 최종 QA readiness도 같은 scope에서 고정 SHA로 읽는다. backend.app 계열 import가 일치하며 profile 자체도 app/backend 별칭이 동일 ContextVar를 공유하는 구조다. 이 정적 경로에는 과거 keyword json_role 누락이나 기본64MiB 회귀를 발견하지 못했다. 실제 누적 JSON 입출력·메모리·시간 성공은 실행 후 관측해야 한다.

## 고정 입력·산출물과 정확한 retained 행

approval의 정확한 키 집합과 approved 정확히 true를 요구하고 source9d491e6ede51cf29407add25b83919cc5d4150576a694c5019814b973d20c2b7, ledger4a4f4a47b522b9497b944ac00b29d2368a977c1a4eb6dfe972a34959fcc68722, old pointer1aee2e01583a024c508d6fdac0d3c4fac2260bbd449ea12269d5e033c1dcc7b4의 고정 tuple을 확인한다. terminal·summary·handoff는 approval SHA,11개 출력은 고정 summary의 byte/SHA로 결속한다. 기대 출력 경로 집합과11개 map이 정확히 같아야 한다.

candidate-package/receipt,stage/staging-receipt,qa/qa-receipt의3개 실행 receipt는 schema2 및 동일 profile MARKER를 요구한다. source/candidate/plan/readiness를 다시 읽을 때도 기대 SHA를 지정한다. retained/excluded는 list이고 각 index는 bool이 아닌 정수·범위 안이며, 양쪽 합이 중복 없이 모든 원행 index를 정확히 분할해야 한다. candidate.scenes가 source의 retained index 행들과 정확히 같고 총행·제외 수·split 적격·차단목록도 summary/QA와 같아야 한다. 최종 외부 pointer는 기존 reader용 schema1 형식이며 실행 profile receipt3개의 schema2와 혼동하지 않는다.

old pointer는 고정 SHA 및 기존 split822/276/250에 결속한다. 원바이트를 별도 archive에 exclusive 저장하고 SHA를 검산한다. 새receipt·임시 pointer를 exclusive 기록·fsync한 뒤, 교체 직전 old pointer/source/ledger와 lock 부재 및 최종 참조3개의 summary SHA를 재확인한다. os.replace 뒤 role-aware reader의 source 일치·실제 split/총적격·차단 수·ready false를 확인하고 source/ledger도 다시 검사한다. 모든 중간 출력의 초기 고정 SHA 대조와 최종 참조3개의 교체 직전 재확인은 구별하며, 모든 과거 파일을 원자 snapshot으로 검사했다고 표현하지 않는다.

## 294와의 publication schema 호환

293 결과는 COMPLETED_QA_PUBLISHED_AND_PROFILE_READER_VERIFIED,status·pointer_sha256·source_snapshot_sha256·candidate_view·manifest_profile·exact_retained_rows·partition_complete·file_sha_mismatches를 출력한다. 294가 기대하는 필드와 이름·타입 계약이 맞는다. candidate_view는 typed split 합으로 정수 eligible_total을 만들고 source_matches_current_manifest=true,ready_for_training=false,정수 blocker_count를 제공한다. 294는 최종 게시의 실제 eligible_total을 소비하며 예상 후보 수를 고정하지 않는다. 단,294의 blocker_count=3 요구는 의도한 현재 계약이며 실제293 결과가 다르면 재결속 전에 차단된다.

294는 publication SHA·동일 marker·원본/원장 고정핀·게시 pointer핀을 확인하고 원profile 원바이트 archive 후 source_manifest_sha256만 재결속한다. 교체 전에 기존 config와4운영핀을 다시 검사하고, 적용 selection을 먼저 남긴 다음 단1회 API GET을 한다. 따라서 API timeout·검산 실패가 설정 미적용을 뜻하지 않는다. archive/selection 및 부분 응답을 보존하고 설정 적용과 API 검증 미완료를 따로 보고해야 한다. 자동 rollback·GET 재시도·서버 재시작은 없다. 293도 pointer 교체 뒤 후검사가 실패하면 새 pointer가 이미 게시됐을 수 있으므로 실제 상태와 실패 위치를 별도 확인해야 한다.

## 실행 전후 책임과 한계

Root는 최종290 terminal/summary/handoff 실제 완료 지문을 받은 뒤에만293을 승인하고 실행해야 한다. 293 성공 지문이 나온 뒤에만294가 실행 가능하다. source/ledger hold와 실제 collector 부재는 Root 책임이며 lock 부재의 관측 자체가 운영 배타성을 보장하지 않는다. 새 후보 수·정확 파일 SHA·원본/원장 보존·API 성공·실브라우저 반영은 해당 실행 후 실제 증거로 확정한다. 이 검토 자체는 준비 코드와 참조 reader의 연결 확인이며 전체 프로젝트 완료·훈련 승인·모든 파일 전역 불변성을 뜻하지 않는다. 실제 완료 후 web_ui와 이해자료 담당에게 지문·상태·한계를 함께 인계한다.
