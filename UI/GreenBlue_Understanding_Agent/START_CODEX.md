# Codex에 입력할 최초 실행 명령

현재 LCLUC 기반 GeoAI–MLOps–SDSS 통합 플랫폼 프로젝트에 **Understanding Agent(개발 이해·기술해설 에이전트)** 역할을 추가하라.

1. 기존 저장소의 `AGENTS.md`와 기존 에이전트/개발 작업방식을 먼저 분석하라. 기존 지침을 덮어쓰지 말고 `AGENTS_APPEND.md`의 내용을 병합하라.
2. `docs/agents/UNDERSTANDING_AGENT.md`를 읽고 이해 에이전트의 역할과 출력 규칙을 적용하라.
3. 가능한 멀티에이전트 실행환경이면 코드 개발과 충돌하지 않는 **읽기·문서 작성 전담 하위 에이전트**로 배정하라. 불가능하면 Root가 기능 완료 직후 동일 지침을 순차적으로 실행하라.
4. 현재 실제 코드와 테스트, TECH-4, GMAIS v0.2, 최근 LCLUC 수집/학습/화면 개발 기록을 조회하라. 자료가 없는 부분은 미확인이라고 명시하라.
5. 첫 산출물로 `docs/understanding/INDEX.md`, `CURRENT_ARCHITECTURE.md`, `GLOSSARY_KO_EN.md`, `presentations/1MIN_5MIN_SCRIPT.md`, `presentations/FAQ.md`를 작성하라.
6. 기존 개발 Gate부터 기능별 쉬운 설명·이론적 배경·실제 코드와 검증 증거를 연결하여 정리하라. `docs/understanding/GATE_TEMPLATE.md`를 템플릿으로 사용하라.
7. 모델이 실제 운영 가능한 것처럼 과장하지 말고 LCLUC 학습 준비도, 공식 데이터·모의 데이터, 외부 5개 Agent 미구현, 사용 승인 상태를 반드시 구분하라.
8. 향후 Gate마다 개발 완료 보고와 **발표 준비 보고**를 함께 제출하게 하라.
9. 분석·자료생성 결과를 보여주고, 현재 플랫폼을 설명하는 **5분 발표 대본과 예상 질문 10개**를 먼저 제시하라.

목표: 내가 Codex 결과를 그대로 읽는 사람이 아니라, 각 모듈의 원리·설계 근거·작동범위·검증 결과를 이해하고 BIG 및 컨소시엄 앞에서 설명할 수 있게 만들어라.
