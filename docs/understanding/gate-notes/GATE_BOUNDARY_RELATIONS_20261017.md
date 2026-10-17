# Gate Boundary Relations 20261017 — 같은 파일의 feature쌍 교차 진단

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-17 23:36 KST — Git 상태 메타데이터 정정; 본문은 해당 Gate 기준 |
| source_commit | d474d5bce6c2a6c4bd8ba141c9256d15f6004631 (108까지 구현 검토 기준; 이 메타데이터 정리는 후속 문서 커밋) |
| evidence_paths | `backend/app/data/recovery_boundary_relations.py`; `scripts/inspect_recovery_boundary_relations.py`; `tests/test_recovery_boundary_relations.py`; `evidence/integration/recovery-boundary-relations-tests-20261017.log`; `docs/implementation/54_recovery_boundary_relations_validation.md`; `evidence/integration/recovery-boundary-relations-independent-20261017.log`; `evidence/integration/recovery-boundary-relations-live-final-20261017.json`; `evidence/integration/recovery-boundary-relations-full-tests-20261017.log`; `evidence/integration/recovery-boundary-relations-live-integrity-20261017.json` |
| confidence | 코드·합성시험·실제 같은파일15쌍; 다른파일/공식/독립성 미검증 |
| status | VERIFIED_REAL: 같은파일15쌍·부분coverage; TESTED_SYNTHETIC: 15시험; 학습/실행 BLOCKED |

## 쉬운 설명

각 지도조각이 스스로 유효한지 본 뒤 같은 지도파일 안의 조각을 둘씩 놓고 떨어져 있는지, 끝만 닿는지, 면적으로 겹치는지 확인한다. 겹침을 발견해도 행정경계가 잘못됐다고 단정하거나 도형을 지우고 고치지 않는다. 다른 파일 사이의 조각은 이번 범위 밖이다.

## 이론과 분류

같은파일 feature의 모든 무순서쌍 `i<j`를 계획한다.6feature면15쌍이다. 기본쌍예산64·hard상한8,128이며 전수계획이 예산을 넘으면 일부만 검사하지 않고 쌍작업 전에 거부한다. manifest/raw SHA·strict구조·지역연결과 모든feature topology가 통과해야 pair진단을 시작한다. geometry는 feature당1회 shape해 캐시하고 intersection은 pair당1회 호출한다.

| 관계 | 진단 기준 |
|---|---|
| DISJOINT | intersection이 empty이고 면적0 |
| BOUNDARY_CONTACT | empty가 아니지만 면적0이며 touches=true. 점/선 접촉을 빈교차와 구분 |
| POSITIVE_AREA_OVERLAP | 유한면적이 정확히0보다 큼. contains/equal도 포함하고 tiny positive를 숨기지 않음 |
| UNKNOWN | 음수/NaN/비유한면적·empty/면적/touches모순·엔진예외로 판정 불가 |

면적은 평면degree²진단이며 m²/km²·공식/측지면적이 아니다. 양수중첩은 finding이며 `administrative_boundary_error_determined=false`다. 공식성·기관권한·오류원인은 진단에서 자동결정하지 않는다.

```mermaid
flowchart LR
 A[pin·동일raw1회 SHA/구조/지역검사] --> B[같은파일 i<j 전수계획·예산]
 B --> C[feature별 topology·geometry캐시]
 C --> D[각pair intersection1회]
 D --> E[떨어짐/접촉/양수중첩/UNKNOWN]
 E --> F[finding·부분coverage·BLOCKED]
```

## 코드와 범위

`recovery_boundary_relations.inspect_recovery_boundary_relations(data_root, expected_manifest_sha256, max_pairs=64, **limits)`와 내부CLI가 구현이다. boundary코어의 strictUTF8/깊이·bounded read·SHA/구조·지역키와 topology helper를 변경 없이 재사용한다. source legacy80 UNKNOWN을 추정으로 채우지 않는다.

입력/구조issue면 shape/쌍작업을 하지 않고, feature하나라도 topologyinvalid/unknown이면 모든pair를 시작하지 않는다. runtime import와 버전조회는 있을 수 있어 시도0을 import0으로 말하지 않는다. 엔진없음·전체참조없음·singlefeature의 pair0은 NOT_CHECKED_ENGINE_UNAVAILABLE/NO_RECORDED_REFERENCES/NO_PAIR_CANDIDATES로 구분한다.

다른파일 사이pair는 OUT_OF_SCOPE이며 별도개수를 기록한다. 같은파일의 전수쌍만 진단한다. boundary4MiB/16파일/128feature/100,000position/depth32·manifest별도64MiB/처음·종료2read를 유지하며 입력상한은 hard CPU시간보장이 아니다. 논리target/stat/manifest를 전후확인하지만 원자snapshot/OSlock은 아니다. repair/buffer/make_valid·재투영·geometry쓰기·네트워크·픽셀해석은 없다.

## 시험과 최종 실제근거

관련15 PASS/1.791초·독립15 PASS/1.764초의 보존로그를 읽었다. 최종 전체 `scripts/test.ps1`은 **490건 중489 PASS·1 SKIP/107.418초/종료0**다. SKIP은 기존 OS symlink 생성 권한이며 deterministic 경계 시험은 통과했다. 관련15 PASS/1.791초·독립15 PASS/1.764초는 전체490에 중복 합산하지 않는다. 보호132참조와 기존 계약15SHA는 불변이고 이전 추적 코드·데이터·계약 변경0이다. 경계1파일의 stat·처음16바이트와1부모 파일목록 관측 변화도0이다. 이는 순차 진단이며 원자적 snapshot은 아니다. 이해자료 작성은 보존 근거를 읽었고 재실행하지 않았다. fixture는 모든pair1회/cache·예산선거부·점/선접촉·동일/포함/미세양수중첩·모순/음수/비유한·선행issue때시도0·다른파일범위밖·대상0과pair0·runtime/변경/출력보호를 검증한다. 실제최종CP949 CLI exit0에서maxpairs15로계획15/시도15이며13 DISJOINT+2 BOUNDARY_CONTACT·양수면적중첩0·issue0이었다. 접촉은south_sulawesi–southeast_sulawesi와banten–west_java이며교차면적0이다. Shapely2.1.2/GEOS3.13.1·경계1파일482,365B SHA일치·6validtopology·1,304지역링크와legacy80UNKNOWN으로 KNOWN_RELATIONS_DIAGNOSED_PARTIAL/INCOMPLETE_REFERENCES·BLOCKED다. crossfile은OUT_OF_SCOPE이고실제제외쌍0이다. 이해자료 작성에서는 시험/실자료조사를 실행하지 않았다.

## 한계·승인·UI

쌍진단은 공식ADM1/기관권한·raster포함·기하/장면/분할독립·과학성능 승인이 아니다. source80 UNKNOWN·원본적격1,111/계획후보1,095·기존5ML blocker·baseline Draft·terminal없는2건/예약136,314,880B·exactly-once UNKNOWN은 그대로다. BLOCKED·학습/실행/정산/자동재개/과학 승인false·환불0이다. 이전featuretopology의crossfeaturefalse는 그모듈범위 그대로이며 새 within-filepair범위와 구분한다.

공개API/화면계약 없는 내부CLI라 UI수정·실행frontend반영·브라우저재검사는 불필요하다. 전체개발과10분보고는 계속한다.

## 발표 1분

“유효한 경계조각을 같은 파일 안에서 둘씩 비교해 떨어짐과 점·선 접촉, 면적중첩을 나누는 진단을 추가했습니다. 전수쌍계획이 예산 안에 들어와야 시작하고 도형은 한 번 구성해 재사용합니다. 작은 양수중첩도0으로 숨기지 않고 같은도형이나 포함관계도 중첩으로 기록합니다. 하지만 중첩발견이 행정경계오류의 확정은 아니며 평면degree제곱을 실제면적으로 발표하지 않습니다. 다른파일쌍·공식권한·영상포함·공간독립성은 범위 밖이고 도형을 자동수정하지 않습니다. 실제15쌍은13개떨어짐과2개접촉·양수면적중첩0이었으나부분coverage이며 학습·정산·재개는 계속차단합니다.”

## 발표 5분·10분

1. **0~1분:** 지도조각을 둘씩 놓는 비유와 자동수정없음을 소개한다.
2. **1~2분:** 같은파일 i<j·전체쌍예산·선행구조/지역/topology검사를 설명한다.
3. **2~3분:** empty/contact/엄밀양수중첩·equal/contains·UNKNOWN 차이를 말한다.
4. **3~4분:** 최종실제/runtime·관련/독립/전체/보호의 확정수치와 legacy80 UNKNOWN을 제시한다.
5. **4~5분:** finding≠행정오류·다른파일범위밖·degree²/독립성/공식승인한계와 BLOCKED·UI불필요를 말한다.

10분은1회shape/intersection캐시·모순/NaN/음수면적·no-ref/pair0·미세양수fixture·입력상한과CPU/원자snapshot차이를 덧붙인다.

## Q&A

**면적으로 겹치면 행정오류인가?** 발견사항이며 기관오류나 원인을 확정하지 않는다.

**접촉도 중첩인가?** empty아닌면적0접촉과 양수면적중첩을 별도분류한다.

**작은겹침은 버리나?** 정확히양수면적이면 기록하며 임의threshold로0처리하지 않는다.

**다른파일경계도 비교하나?** OUT_OF_SCOPE이며 같은파일내쌍만 검사한다.

**왜 계속BLOCKED인가?** 공식권한·raster포함·장면독립·학습/정산승인은 별도이며 기존차단을 해소하지 않았다.

## 이후 갱신

문서54·독립/실제/runtime/전체/보호 최종근거를 받아 기능해설·구조/용어·발표/FAQ/시연·INDEX·CHANGELOG를 함께 확정했다. 후속검증은 별도Gate로 범위를 구분한다.

## 다음 작업의 현재 상태

다음 source_window 원본영상의 헤더 기반 footprint·주 연결 최소 진단은 **PLANNED**다. 실제 소비 CRS/affine/변환 계약을 먼저 확인하고 고정 manifest·명시 경계·한도를 유지하는 계획이며 현재 수행 결과가 아니다. 임시 파생 footprint는 픽셀 내부 포함 비율·면적 정확성·표본 독립성 증명이 아니고 원본 raster·geometry·분할은 변경하지 않는다.
