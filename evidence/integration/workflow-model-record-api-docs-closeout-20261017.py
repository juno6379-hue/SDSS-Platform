"""Update implementation and handoff documents from verified current evidence."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
e=ROOT/'evidence/integration'
proof=json.loads((e/'workflow-model-record-api-live-integrity-20261017.json').read_text('utf-8'))
ui=json.loads((e/'workflow-model-record-api-live-ui-20261017.json').read_text('utf-8'))
r=proof['full_regression']
assert all(x['pass'] for x in ui['checks'])
section=f'''## Workflow 모델 레코드 대조 API·UI 검증 완료 (105/106)

별도 수동 진단 POST와 실행계획 검토 화면의 ‘모델 레코드 초안 대조’를 연결했다. API 담당은 strict parsing·크기 한도·원문 SHA·nested exact typed 재검증을, UI 담당은 공통 SVG·명시 클릭·오래된 응답 폐기·안전 오류를 구현했다. 기존 RFC1/RFC2 결과와 승인 gate를 보존한다. producer의 103 호출 1회와 독립 validator의 추가 1회를 구분하며, record 원문 파싱은 89 gate보다 먼저다.

관련 API 101 PASS·독립 15 PASS, 프론트 관련/독립 각19 PASS·전체191 PASS, 빌드96 modules/28.34초다. Root 최종 전체 backend는 {r['tests_run']}건/{r['passed']} PASS/기존 Windows symlink {r['skipped']} SKIP/{r['seconds']}초/exit0다. 첫 전체 실행은 기존101 AST 보존 시험의 새 router 허용목록 부재로 실패1건이었다. 정확한 두 연결만 허용하는 시험 호환 수정 후 전체를 재실행했고, 최초 실패 로그도 보존했다. 제품 동작 오류와 시험 호환 수정은 구분한다.

Root는 합성 원문으로 실제 HTTP 10건(200×6/400×3/413×1)과 브라우저 {len(ui['checks'])}개 확인·수동 진단 POST4회를 수행했다. 미제공·일치 미검증·공백400·null 미제공, 입력/Workflow 편집의 결과 폐기와 화면 이동/뒤로가기를 확인했다. 원래 Workflow 원문은 정확히 복원하고 새 node/job/record 필드는 비웠다. desktop 제목 겹침·가로넘침0/제목·버튼 SVG 정상, 시험 이후 수집된 최근20 warn/error 중 새 항목0이다. 지연·동시성 방어는 격리 시험 근거이며 실제 back 확인은 완료 응답 이후다. 표시 중단은 서버 취소가 아니다.

보호141·이전 증거736·catalog14·기존 Job 본문을 보존했다. 계약기준73개 중72개는 byte 불변이며 나머지 GeoQuery1개는 허용된 import/sibling 두 조각만 제거하면 원문 byte와 정확히 같다. 기존제품의 허용 변경은 main router import/include와 GeoQuery sibling 배치이며 추가 기존 시험1개 호환 수정은 별도 사전 byte 근거를 남겼다. 운영 등록/Job 생성·Workflow 제출·수집/새 운영 QA/정식 학습/배포0, 원본/원장/lock/예약136314880B/분할/모델 보존·QA차단4/학습BLOCKED 유지다. 이 진단은 metadata 관계만 관측하며 기관 권위·실바이트·과학 정확도·실행 승인·모델 인증을 입증하지 않는다. 성공 화면 PNG도 합성 입력 진단 예시다.

완료 코드·시험·실제 화면 근거를 이해 에이전트에 전달해 쉬운 설명·발표 대본·FAQ·INDEX·변경 이력을 함께 갱신했다. 다음은 Workflow 입력 연결 대기열 검토(PLANNED)이며 전체 개발은 미완료다. geoai-2 예약 ACTIVE와 실제 worker 실행은 다르다. 최종 로컬 프로세스 관측의 수집/학습 후보는0이며 원격/숨은 worker까지 보장하지 않는다. 8002는 실제 진단 요청으로 새 경로를 확인했고8000/8001은 유지·새 코드 로딩 미확인이다. 지속 개발과10분 담당별 보고를 유지한다.

근거: `evidence/integration/workflow-model-record-api-live-integrity-20261017.json`, `evidence/integration/workflow-model-record-api-live-api-20261017.json`, `evidence/integration/workflow-model-record-api-live-ui-20261017.json`, `evidence/integration/workflow-model-record-api-runtime-final-20261017.json`. 최종 문서 감사와 rawSHA snapshot은 `evidence/integration/workflow-model-record-api-closeout-20261017.json`을 따른다.

'''
for name in ['CONTINUOUS_DEVELOPMENT.md','docs/implementation/00_next_session_handoff.md','docs/implementation/workstream_ownership.md']:
 p=ROOT/name
 text=p.read_text('utf-8')
 first,sep,rest=text.partition('\n')
 p.write_text(first+'\n\n'+section+rest.lstrip('\n'),'utf-8')
links='''
### 105/106 후속 연결 및 검증

별도 비변경 진단 API와 수동 UI를 연결했다. 기존 RFC1/RFC2 결과·승인 경계를 유지한다. 새 계약·원문/한도·생산과 검증 호출 수·실제/합성 시험 및 한계는 [API105](105_workflow_job_model_record_handoff_api.md), [UI106](106_workflow_model_record_handoff_ui.md)를 따른다. 최종 전체 회귀·브라우저·보존 근거는 `evidence/integration/workflow-model-record-api-live-integrity-20261017.json`과 `evidence/integration/workflow-model-record-api-live-ui-20261017.json`이다. 이해자료·인계서도 같은 단위로 갱신했다. metadata 일치는 실바이트·권위·과학/실행 승인이 아니며 운영 Job 생성/등록은 없다.
'''
for pattern in ['07_*','08_*','89_*','94_*','104_*']:
 for p in (ROOT/'docs/implementation').glob(pattern+'.md'):
  p.write_text(p.read_text('utf-8')+links,'utf-8')
for pattern in ['105_*','106_*']:
 for p in (ROOT/'docs/implementation').glob(pattern+'.md'):
  p.write_text(p.read_text('utf-8')+'\n'+section,'utf-8')
print('Root implementation, related contracts, ownership and handoff updated from verified evidence.')
