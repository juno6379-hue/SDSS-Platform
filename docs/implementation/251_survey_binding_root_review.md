# 251 — 246 순수 출처 결속 검토와 시험 증거 보존

상태: **TESTED_SYNTHETIC / Root 정적 검토 완료**. 원격 출처 인증·실제 STAC 호환성·영상품질·수집 연결은 미검증이다.

Root는246 신규 모듈·시험·문서3개를 읽고 strict request 재사용, 원문 바이트 SHA, 장면·시각·제품·정확 SCL URL, immutable 결과, false 운영 gate, 오류·입력 크기 경계를 검토했다. 이 작은 독립 모듈 범위에서 필수 제품 수정은 발견하지 않았다. 실제 서버의 현재 스키마나 모든 URL 레이아웃을 지원한다고 승인하지 않는다. PC Sentinel2 SCL20 경로에 한정하며 signed query·다른 provider·소수초 불일치는 보정 없이 거부한다.

담당45개 시험 결과는 대화 stdout에만 있어, Root는 영구 시험 로그 근거를 남기려고 같은 신규13+기존32 집합을 단1회 기록 실행했다. `survey246-root-regression-20261018.log`에서45개/exit0/OK를 확인했다. Root 전체 subprocess 관측은1.265초이며 담당의0.216초 시험 실행 시간과 같은 측정 범위가 아니다. 동일45개를90개로 합산하지 않는다. source3개 지문은 전후 동일했다.

근거 `evidence/integration/survey246-root-review-20261018.json`, 시험 로그 SHA `1e6c3adc34d8dc90715e4c2933a2147fe705273c8c362b12ab94d28e721610d7`다. Root 작업은 실제 운영 source/ledger 읽기·HTTP·collector·native 래스터 검사를 수행하지 않았다. 기존246 동결 문서·원판은 수정하지 않았다.

이 모듈은 caller가 SHA로 고정한 메타데이터의 일치만 검사한다. 파일 정체성·실측 전송·registry/173/175/170 소비 연결은216 후속 범위이며, 지금 실행 가능한 SURVEY 수집기로 표현하지 않는다. UI/API에서 호출하지 않는 순수 내부 함수라 화면 수정·서버 재시작이 필요 없다. 완료 소스와 한계를 별도 understanding_agent에 전달해 쉬운 설명·대본·FAQ·INDEX·변경 이력을 갱신한다.
