# 301 현재 재고 profile 재결속 독립 정적 검토

상태는 **IMPLEMENTED_UNVERIFIED — 실행 전 정적 검토**다. 코드·원282 사본·최소diff·doc301·freeze만 읽었으며 추가 실행 차단 결함을 발견하지 못했다. 운영 source/ledger/profile/pointer 및 native 산출물 본문을 읽지 않았고 HTTP·새 시험·실QA·collector·설정 교체는0이다. 기존297 native와290 QA도 반복하지 않았다. 제품 코드 수정0이며 이 문서만 작성했다.

freeze evidence/integration/profile301-preparation-freeze-root-20261018.json SHA7071b1a63208194d488169fa764318a44a02dccf52a462f3b50467ab01edb16b의4파일 byte/SHA를 확인했다. 새 profile301-post297-root-20261018.py SHA3ba91d7c37e51f26d59341dd54f57c2cce364dc5734a37c46956a5e2d0d17993,원282 사본df34e0c865f5184055b7d71807bfd566aa090eacefccf942236b285803ec2be5,최소diff a195e7b169b462b8e07d2a5c34060bd36f04fcfe2768fc8f9655724dd6f6e817,doc301 SHA71ad259ee49220c04e516f1e799da1c7d8fa1e421222c43e315d05b606a71d99가 일치했다.

301은282의 검증된 절차를 유지하고297 양수 감사와 현재 지문·정량값에 결속한다. 입력 native 감사는 기대 SHA로 bounded read하고 COMPLETED_BOUNDED_NATIVE_AND_TRACE_CHECKED/native true/16검사·15적격/원행·history·pending 보존/두읽기 안정 조건을 요구한다. source9e63564c87647a144665bbb6bbe49b4a95d09bbd2c3bc0f3725861c54d5e7109와 ledger574d382dd9da51ae56dc8fb135532f8f2e5c542b2c4cafdf73a6ee8dd9c6045f를 고정하며 후보1360 pointer996a88de2034e9803381d7ae4e906a0d1f418075675d13ef796fb5648bb472c0를 보존한다. 실제 자료핀의 현재 일치는 Root가 실행 전 검사할 책임이며 이 검토에서 운영 파일을 다시 읽은 것은 아니다.

같은 scope(NAME)의128MiB source/candidate 역할 및 누적 JSON16GiB ContextVar 안에서 기존 helper를 사용한다. 이전 configa644b5b2cdf8917d13028f7a89ceeb4996d5ad5dc54af2b6fb2c9fda2c98f9de와 그 source9d491e6ede51cf29407add25b83919cc5d4150576a694c5019814b973d20c2b7를 확인해 원바이트 archive하고 source_manifest_sha256만9e로 바꾼다. descriptor·후보 pointer·receipt를 변경하지 않는다. 새 출력 미존재 선검사와 독점 temp·flush/fsync,replace 직전 기존 config 및 source/ledger/후보/bare4운영핀 재확인을 유지한다. 적용 selection을 API 전에 남긴다.

정적 urlopen callsite는1개이며 기존8002 collection-status GET만 수행한다. 기대값은 원본1391/셀 부족1,기존 검증 후보1360/source_matches_current_manifest 정확히 False,미준비false·나지3차단,bare50도 stale,잔여1,822,603,826바이트,원pending136,314,880바이트와4운영핀/새config 보존이다. 원pending은 사용액에 이미 포함돼 재차감하지 않는다. 실제 응답은 최대2MiB/150초이며 재시도 루프가 없다. 설정 적용 뒤 timeout·검산 실패가 발생할 수 있어 archive/selection을 보존하고 적용과 API 검증 미완료를 분리해야 한다. 자동 rollback/retry/restart는 없다. source hold·실제 collector 부재는 Root 운영 배타성에 의존하며 lock 부재 사전 관측이 원자 잠금을 대신하지 않는다.

전략 변경은 현재 재고 표시를 갱신하되 기존1360 후보를 고정9d의 검증 결과로 남기고,동자바2025 마지막 셀 부족1의 소규모 수집을 먼저 수행한 뒤 최종 source에서 후보 QA를 한 번 하는 것이다.301 자체는 이 다음 수집이나 최종 QA를 실행하지 않는다.297의 새15적격은 native 검사된 원본 범위이며290의 기존 후보 QA에 포함된 자료라고 표현하지 않는다.1391 원본과1360 후보의 차이는 현재와 고정 후보의 범위 차이이며,전부 미검증 신규31개로 단순 해석하면 안 된다. 기존16개 scene 누출 제외 등 후보 전처리 범위도 유지된다.

새 후보 게시 없이 후보와bare의 source 불일치를 정확히 False로 요구하므로 stale 해제를 위조하지 않는다. 고론2025 최소량 충족과 나지 클래스 준비·학습 승인도 구별한다. 실제 API 성공과 브라우저 확인은 별도 실행 근거를 받아야 하며 이 정적 문서는 실화면 완료를 뜻하지 않는다. 실제 적용 뒤 Root가 doc301 후속·web_ui 및 이해자료 인계를 마감해야 한다. 전체 개발과 나지 부족 해결은 미완료다.
