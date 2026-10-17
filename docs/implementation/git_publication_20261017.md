# GitHub 연결·게시 범위 — 2026-10-17

사용자 지정 저장소는 https://github.com/juno6379-hue/SDSS-Platform 이다. 기존 `main`의 `d483d25e190d5fa413f6e5e3ce1075ce1915a487`를 fetch한 뒤 로컬 파일을 덮어쓰지 않고 그 이력을 기반으로 변경을 준비했다. 강제 push나 원격 이력 교체는 하지 않는다. 실제 게시 commit SHA와 원격 HEAD 일치는 Git 실행 결과로 확인한다.

구현 게시 기준은 `d474d5bce6c2a6c4bd8ba141c9256d15f6004631`이다. `main` push 성공 후 원격 HEAD가 이 SHA와 일치함을 확인했다. 이 구현을 가리키도록 이해자료80개의 source_commit을 정정하는 문서 후속 커밋을 별도로 만든다. 후속 커밋은 구현 기준 커밋을 대체하는 새 과학·운영 검증이 아니다. 게시 근거는 `evidence/integration/git-publication-verification-20261017.json`을 따른다.

## 포함·제외

소스·설정 예시·계약·문서·시험·UI 참조·선별된 개발 증거를 포함한다. 원본 `data/`, 모델/영상 원본, 로컬 `.env`/`.env.*`, 실행환경·의존성·빌드 캐시·임시 시험 폴더는 새로 추가하지 않는다. 원격에 이미 있는 데이터 기록은 이 게시에서 수정하거나 제거하지 않는다. 16MiB를 넘는 신규 raw evidence JSON은 선별 대상에서 제외한다. 대용량 자료를 포함한 완전한 실행 재현에는 별도 로컬 데이터와 승인된 접근이 필요하다.

기존 `.gitignore`의 `data/`는 `backend/app/data/` 소스도 무시하므로 `/data/`로 고쳤다. `/tmp/`, `/evidence/tmp*/`, `*.tsbuildinfo`와 로컬 환경파일 제외도 명시했다. Windows의 `core.autocrlf=true`로 고정 SHA 증거가 변하지 않도록 `.gitattributes`의 `* -text`로 원문 바이트를 보존한다. 스테이징 blob과 로컬 원문의 Git SHA를 비교한다.

## 검증 범위

- 107 전체 backend: 1069건/1068 PASS/기존 Windows 1 SKIP/354.650초.
- 108 신규12 PASS·관련66 PASS·독립26 PASS, 별도 완전탐색 29001분포/1015집계. 독립 산술과 실제 저장 보고서 CLI 결과 일치.
- 108은 새 독립 module/CLI이며 기존 코드 변경0이므로 이번 전체/backend·front/build/browser 재실행은 없다. 앞의 107 전체 결과는 이전 근거로 구분한다.
- 108 이해자료·발표·FAQ·INDEX·변경 이력과 Git 연결 메타데이터를 갱신했다. [영역별 완료·잔여 과제 감사](109_area_completion_audit.md)는 완료·외부 차단·내부 대기열과 수락 조건을 구분한다.
- 알려진 private-key/GitHub/provider/AWS 토큰 패턴을 검사한다. 이 검사는 모든 비밀정보·취약점 부재를 보증하는 전체 보안 감사는 아니다. 값은 로그에 출력하지 않는다.

이 게시가 실제 수집·정식 학습·과학 검증·기관 운영 인수 완료를 뜻하지 않는다. 기존 QA차단4·모델 Draft·실행 승인 제한은 유지한다. 후속 내부 개발과 담당별 중간 보고를 계속한다.
