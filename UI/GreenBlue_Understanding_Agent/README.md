# GreenBlue Understanding Agent — Codex 통합 패키지

Codex로 개발 중인 LCLUC 기반 GeoAI–MLOps–SDSS 플랫폼에서 코드 설명, 이론 해설, 근거 검증, 발표 및 질의응답 자료를 **개발 Gate마다** 작성하게 하는 문서형 에이전트 패키지입니다.

## 파일 구성

- `AGENTS_APPEND.md` — 프로젝트 루트 AGENTS.md에 병합할 운영 규칙. **덮어쓰기 금지**
- `docs/agents/UNDERSTANDING_AGENT.md` — 독립 역할 규격(설명 방식·근거·산출물·상태 분류)
- `docs/understanding/GATE_TEMPLATE.md` — Gate별 설명 보고서 템플릿
- `START_CODEX.md` — Codex에 처음 전달할 실행 지시문

## 적용 방법

1. 위 파일을 기존 프로젝트에 동일 경로로 복사(현재 AGENTS.md는 보존).
2. `AGENTS_APPEND.md` 내용을 기존 프로젝트 루트 `AGENTS.md`에 **추가**한다.
3. Codex에서 `START_CODEX.md`를 읽고 실행하도록 요청한다.
4. 작업 Gate 완료마다 root가 변경파일·시험로그를 Understanding Agent에게 전달하여 발표자료를 갱신하게 한다.
5. 코드와 다른 문서는 분리하여 `docs/understanding/` 하위에만 기본 쓰기권한을 허용한다.

## 운영상 주의

`AGENTS.md`로 지침을 읽는 기능과 **독립 서브에이전트를 실제 생성해 병렬로 실행하는 기능**은 동일하지 않습니다. Codex 환경에 따라 멀티에이전트를 사용하거나 root가 같은 역할을 순차 수행해야 합니다. 이 문서만 배치한다고 백그라운드 작업이나 자동 알림이 예약되지 않습니다.

개발 에이전트가 생성한 기능은 무조건 완료로 판정하지 않습니다. 실제/모의/합성 시험의 차이, LCLUC 모델 Draft 상태, 컨소시엄 외부 5개 모델의 통합 대기 등을 명확히 구분해야 합니다.
