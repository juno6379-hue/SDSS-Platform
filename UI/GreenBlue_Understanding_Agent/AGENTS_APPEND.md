# 프로젝트 루트 AGENTS.md에 *추가할* 이해 에이전트 운영규칙

> 기존 AGENTS.md를 덮어쓰지 말고 아래 내용을 기존 파일의 적절한 위치에 병합한다.

## Understanding Agent — 개발 이해 및 발표 설명 담당

- 역할 규격: `docs/agents/UNDERSTANDING_AGENT.md`를 참조한다.
- Root는 의미 있는 Gate/기능 구현을 완료할 때, 해당 규격에 따른 이해자료 작업을 배정한다.
- 사용 가능한 멀티에이전트/서브에이전트 기능이 있다면 `understanding_agent`라는 별도 작업자로 **완료된 구현 변경을 읽게** 한다. 별도 에이전트 기능이 없으면 root가 같은 역할을 순차적으로 수행한다.
- 코드 변경과 이해자료 작성은 같은 소스 파일을 동시 편집하지 않도록 분리한다.
- `docs/understanding/` 하위에 `쉬운 설명 → 이론적 배경 → 코드/데이터 동작 → 테스트 증거 → 발표 스크립트 → Q&A` 순서로 기록한다.
- 발표자가 오해하지 않도록 VERIFIED_REAL, TESTED_SYNTHETIC, IMPLEMENTED_UNVERIFIED, BLOCKED, PLANNED 상태를 명시한다.
- 데이터/모델/API/보안 요구사항이 변경되면 관련 이해자료·용어집·발표 자료를 함께 갱신한다.
- BIG, 컨소시엄, 모델별 책임과 운영 승인 등 미확정 사실을 확정으로 표현하지 않는다.
