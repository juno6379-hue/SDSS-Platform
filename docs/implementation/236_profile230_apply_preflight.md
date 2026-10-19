# 236 명시 profile 합성 적용 전 읽기 전용 준비

상태: 준비 완료 / 적용 미승인 / 제품 변경 0.

## 적용 전 읽기 전용 준비 — 230 동결 후 후속

`apply-preflight230.json`은 228 전 baseline에서 230 최종 파일까지의 합성 적용 대상 18개를 비교했다. 현재 main 기존 14개 모두 baseline SHA와 일치했고 신규 4개 경로는 존재하지 않았다. 충돌은 0개이며, 이 관측을 적용 승인이나 운영 성공으로 해석하지 않는다. 파일별 before/main/final SHA와 관측 중 안정성, 232 네 파일·공용167/199 제외를 JSON에 기록했다. 운영 data/원장/모델 읽기, main 쓰기, 추가 시험, HTTP, 수집은 모두 0이다.

Root가 독립 검토 뒤 정확 baseline archive·최소 적용·검증을 결정한다. 중첩되는 228/230 패치를 순서만 믿고 덮어쓰지 않고, 합성 대상의 pre228 SHA를 적용 직전에 다시 검사해야 한다. 실행 중인 서버가 이전 메모리 코드를 사용 중인지 여부는 이 파일 SHA 검사로 판단하지 않는다.

원 doc230에 후속 절을 잠시 추가했으나, Root의 별도 문서 분리 지시에 따라 freeze SHA가 정확히 일치하는 격리 docs/ISOLATED230.md 원바이트로 복구했다. 현재 원 doc230의 SHA는 동결 시점과 다시 정확히 같다. freeze230·patch230-manifest·patch230.diff·제품·시험·고정 로그는 변경하지 않았다.

증거: `evidence/integration/preprocess230-workspace-20261018/apply-preflight230.json`, SHA `8aed954cbd4d328811ddfb0633b2bbb777d33ecfb5677cb4f671aca5cb9e1ef5`.

## Root 후속 — 현재 원본 구조의 별도 관측

230 독립 리뷰는 JSON 읽기 누락 5범주로 적용을 차단했고, 별도 237 격리 보완을 진행한다. 위 18파일 충돌 0 관측을 237 적용 가능 판정으로 사용하지 않는다.

2026-10-18 16:42:01 KST `current-manifest-structural-preflight-root-20261018.py`가 현재 원본 JSON만 읽어 구조를 관측했다. 원본 SHA `9c24eec337a17f95855d190918c9999c25aeb1925a7642b1ade26afa4e20d987`, 66,826,849바이트, 1,715행·history 0행, container 깊이 8, `_tree`와 같은 key/value/container-leave 방문 수 2,860,976이다. 예정된 3,000행·깊이32·4,000,000방문 제한 안이다.

전후 실제 JSON 읽기는 133,653,698바이트, 4.312초이고 지문·파일 상태는 같았다. 결과 JSON은 `evidence/integration/current-manifest-structural-preflight-root-20261018.json`이다. RSS는 관측하지 않았고 128MiB rich metadata의 성능을 검증한 것도 아니다. 새 profile 활성화·readiness QA·raster 읽기·HTTP·수집·원본/원장 쓰기는 모두 0이다. 현재 구조 관측이 새 패치나 모델 품질 승인을 대신하지 않는다.
