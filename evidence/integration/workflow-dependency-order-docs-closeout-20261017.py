from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
proof=json.loads((ROOT/'evidence/integration/workflow-dependency-order-live-integrity-20261017.json').read_text('utf-8'))
r=proof['full_regression'];related=proof['related'];independent=proof['independent'];focused=proof['focused']
section=f'''## Workflow 의존 순서 공통화 검증 완료 (107)

계획 API·현재 계보·차단 전파에 중복되어 있던 Kahn 의존 순서 계산을 순수 `topological_order` 함수로 모았다. 원래처럼 ready 한 계층 전체를 정렬·제거한 뒤 다음 계층을 계산한다. a:[],b:[a],z:[]은[a,z,b]이며 전역 heap 순서[a,b,z]로 바꾸지 않는다. helper는 입력 set을 복사하고 stuck이면None, 빈map이면[]을 반환한다. 기존 caller가 schema/duplicate/self/unknown·한도·오류 우선순위·한국어 오류·Store/manifest 접근 시점을 책임진다.

구현 담당은 helper·세 호출부·동등성 시험·문서107을 완료했다. 검토/UI 담당은 기존 원문과 새 호출부를 독립 검토하고 시험했다. 관련 {related['passed']} PASS/{related['seconds']}초, 신규 {focused['passed']} PASS/{focused['seconds']}초, 독립 {independent['passed']} PASS/{independent['seconds']}초다. 묶음 중복을 합산하지 않는다. Root 전체 backend는 {r['tests_run']}건/{r['passed']} PASS/기존 Windows {r['skipped']} SKIP/{r['seconds']}초/exit0이다. 시험은 합성·격리 fixture이며 운영 Workflow 실행이나 과학 검증이 아니다.

이 변경은 기존 응답/오류/승인 제한을 유지하는 내부 공통화다. 신규 API·화면·자동 실행·resolver·동적 predecessor binding은 없다. UI 담당이 영향 읽기와 backend 동등성 근거로 UI 수정이 필요 없음을 확인했고 기존 프론트 byte는 보존했다. 이번 front/build/browser 재시험은 하지 않았다. 이전105/106의191PASS/빌드96modules·28.34초/브라우저11체크는 이전 근거다. 86/89/104의dag_validated=false를 새 공통 함수로 바꾸거나 승인하지 않았다.

보호 대상 {proof['protected_references_checked']}개·이전 증거 {proof['previous_evidence_files_checked']}개·catalog14건·기존 Job 본문은 보존했다. 기존 제품의 허용 변경은 세 caller 파일뿐이며 각 원문 사본을 남겼다. 원본/원장/lock/예약136314880B/분할/모델·QA차단4/학습BLOCKED를 유지한다. 운영 Job/모델 등록·수집·새 운영 QA·정식 학습·배포는0이다. 예약 ACTIVE와 실제 worker 상태는 별개이며 로컬 명령 패턴의 수집/학습 후보0은 원격/숨은 worker 부재까지 보장하지 않는다.

완료 코드와 시험 근거를 이해 에이전트에 전달해 쉬운 설명·이론·코드/데이터·시험·발표·FAQ·INDEX·변경 이력을 갱신했다. 다음은 실제 Workflow 입력 연결 대기열 재검토(PLANNED)이며 전체 프로젝트는 미완료다. 지속 개발과10분 담당별 보고를 유지한다.

근거: `evidence/integration/workflow-dependency-order-live-integrity-20261017.json`, `evidence/integration/workflow-dependency-order-runtime-start-20261017.json`. 최종 문서 감사·rawSHA snapshot은 `evidence/integration/workflow-dependency-order-closeout-20261017.json`을 따른다.

'''
for name in ['CONTINUOUS_DEVELOPMENT.md','docs/implementation/00_next_session_handoff.md','docs/implementation/workstream_ownership.md']:
 p=ROOT/name;t=p.read_text('utf-8');head,_,tail=t.partition('\n');p.write_text(head+'\n\n'+section+tail.lstrip('\n'),'utf-8')
for pattern in ['28_*','29_*','40_*']:
 for p in (ROOT/'docs/implementation').glob(pattern+'.md'):
  p.write_text(p.read_text('utf-8')+'''\n### 107 의존 순서 공통화

기존 Kahn sorted-ready-layer 순서만 순수 helper로 공통화했다. caller의 검증 우선순위·오류·응답·Store/manifest 접근·승인 제한은 유지한다. 내부 구현·입력 전제·회귀 근거와 한계는 [107 구현 문서](107_workflow_dependency_order.md)를 따른다. UI·API 추가나 실제 실행 승인이 아니다. 전체·독립·보존 근거: `evidence/integration/workflow-dependency-order-live-integrity-20261017.json`. 이해자료와 인계서도 같은 단위로 갱신했다.
''','utf-8')
p=ROOT/'docs/implementation/107_workflow_dependency_order.md';p.write_text(p.read_text('utf-8')+'\n'+section,'utf-8')
print('107 related contracts, implementation, ownership and handoff updated.')
