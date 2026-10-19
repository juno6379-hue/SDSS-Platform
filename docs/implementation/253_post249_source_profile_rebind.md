# 253 — 249 후 현재 원본 결속과 재검증 시점 보존

상태: **VERIFIED_REAL / 실제 API 완료**, 브라우저는254 별도 후속이다. 249는 SCL을 통과한 장면이 B02 정렬 가드에서 차단돼 최종 패치0이었다. 이번 단위는 새로운 후보 QA나 학습 승인이 아니다.

Root는249 run2 좁은 감사의 모든 체크와 SHA `6beed046a69e8cddce35df65fa2ea1ae6c16199dd42808d71a3045d7ef64146c`를 확인한 뒤,247과 동일한 명시 재결속 절차를 현재 source에만 적용했다. `profile253-post249-root-20261018.py`는 oldconfig5ce66…c08f를 원바이트 archive하고 같은 descriptor의 source SHA만 갱신했다. 자동 크기 감지·한도 상향·pointer 승계·QA 반복은 없다.

- 현재 source: `6899f9019670e9eff3e40cd9e5441a91bbaf11fae236cbbc8c2eac27ffa31e15`, 66,827,175B.
- 원장: `c7ef4985a0c7f55a4a0a48c1db2b8ab4bef8d87be3a91e5175a948f56d613f4f`.
- 새 명시 설정: `160303e874228acbec2e37ee52ca4bd3305353e414163fae75ee5d2de3356026`.

`profile253-selection-root-20261018.json`과 기존 설정 archive, API 원문·검사 JSON을 보존했다. 원본/원장/후보/나지 pointer4개의 지문은 변경 전후 동일했다. 저장된 후보의 source SHA를 바꿔 최신 검증처럼 꾸미지 않았다.

17:26:53.571 KST 재고와17:26:54.229 예산의 실제 GET1회는200/17.562초였다. 단일 관측이며 SLA·최대128MiB 성능 검증이 아니다.11개 체크가 모두 통과했다: 적격1358/셀21,게시1342/차단3/학습false,후보와나지50검토모두source불일치,잔여1,893,950,211B,oldpending2전액136,314,880B 보존이다. 응답 SHA는`1f6472c2371c3308e25643c6b3e4c08a23e15d60870d98894108a0de650bfde0`다.

235·249 실제 비용 합계2,994,744B를 신규 자료 수로 해석하지 않는다. 기존 pending은 사용액에 이미 포함된다. API·Frontend 재시작·원장/모델/고정split 변경·동일후보QA는0이다. [249 실제 차단과 감사](249_bounded_collection_supervisor.md), [251 순수 메타데이터 검토](251_survey_binding_root_review.md)를 함께 참조한다. 브라우저·이해자료 후속과255 진단 보완의 적용 검증은 각각 별도 근거로 마감한다.
