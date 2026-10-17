"""Write this unit's integration handoff after its actual checks have passed."""
from pathlib import Path
import datetime,json
ROOT=Path(__file__).resolve().parents[2]
e=ROOT/'evidence/integration'
proof=json.loads((e/'model-version-api-live-integrity-20261017.json').read_text('utf-8'))
full=proof['full_regression']
environment_path=e/'model-version-api-test-environment-20261017.json'
environment=json.loads(environment_path.read_text('utf-8'))
environment['corrected'].update({'status':'PASSED','tests_run':full['tests_run'],'passed':full['passed'],'skipped':full['skipped'],'seconds':full['seconds'],'exit_code':0})
environment_path.write_text(json.dumps(environment,ensure_ascii=False,indent=2),'utf-8')
now=datetime.datetime.now().astimezone().strftime('%H:%M KST')
section=f'''## {now} — Draft 등록 API·UI의 명시 모델 버전 선택 연결 검증 완료 (98/99)

- **API 담당:** 기존 endpoint는 model_version 키 존재시에만 원형 keyword를 전달한다. 생략·null 구분, 기존 인증/잠금·201/422·파일 오류 우선순위를 유지했다. 관련48 PASS·독립11 PASS이며 성공 등록은 AST 격리/TempStore/mock 범위다.
- **UI 담당:** 기존 Model Registry 폼에 기본off/빈버전 선택을 연결했다. off는 기존 body, on은 원문 버전만 추가한다. busy·중복 클릭·route/back/unmount 늦은 표시 방어와 서버201 뒤 refresh실패 안내를 분리했다. 관련16·전체153·독립16 PASS, 실제 겹침 발견 후 전용CSS로 보완하고 관련16/전체153 재통과·최종build90 modules/27.52초다. 기존 로그를 덮지 않았다.
- **실제 브라우저/서버:** API의 없는 보고서4회422·브라우저 음성1회422, 실제화면8체크·완료422뒤 back복귀·가로넘침0·SVG·제목겹침0을 확인했다. 편집중 일시 HMR오류1건을 보존하고 reload뒤 정상표시/카탈로그복귀를 확인했다. 최종폼은 빈값/off다. 성공등록·지연동시성·refresh실패는 격리시험만으로 구분한다. 없는파일422는 버전검사 성공경로 증거가 아니다.
- **Root 전체·보존:** backend {full['tests_run']}건/{full['passed']} PASS/기존Windows symlink {full['skipped']} SKIP/{full['seconds']}초/exit0. 보호141·불변core+schema70·이전증거·catalog14/기존Job본문 변경0. 기존소스 수정은 사전기준선과 비교한 main.py/ModelReview.tsx뿐이며 신규adapter/CSS/test를 추가했다. 원본·원장/lock·예약136314880B·분할·모델보존, 운영성공등록/Job/Workflow·수집/정식학습/배포0이다.
- **회귀 실행 이력:** 최초 Root 실행은 PYTHONPATH 누락으로648건/327.484초/import errors31이었다. 최초 model-version-api-full-tests-20261017.log를 보존하고 지정 .runtime;backend;tests 환경으로 corrected 로그에 재실행한 최종 결과만 위 통과 수치로 사용한다. 제품 코드를 바꿔 import 오류를 우회하지 않았다.
- **문서·이해자료:** 신규98/99와 관련07/08/97, 원장·소유권·인계서를 갱신했다. understanding_agent가 완료코드·실제/합성시험을 읽고 쉬운설명·이론·코드데이터·시험·발표대본·FAQ·INDEX·변경이력을 갱신했다. 최종문서감사/rawSHA snapshot은 model-version-api-closeout-20261017.json을 따른다.
- **한계·다음:** caller 선언은 기관권위·원본인증·과학/실행승인이 아니며 omitted raw필드도 같은shape를 가질수 있다. 실제model resolver/전역immutable/트랜잭션은 미구현이다. dataset_version 추정·역채움 금지와 기존 QA차단4/학습BLOCKED를 유지한다. 다음은 읽기전용 등록 출처 진단 계약 검토(PLANNED)이며 구현/실행승인0이다. 전체개발 미완료·지속개발/10분보고 유지, 예약ACTIVE와 실제작업을 구분한다.

근거: `evidence/integration/model-version-api-live-integrity-20261017.json`, `evidence/integration/model-version-api-live-api-20261017.json`, `evidence/integration/model-version-api-live-ui-20261017.json`, `evidence/integration/model-version-ui-desktop-final-20261017.png`.

'''
for name in ['CONTINUOUS_DEVELOPMENT.md','docs/implementation/00_next_session_handoff.md','docs/implementation/workstream_ownership.md']:
    p=ROOT/name
    old=p.read_text('utf-8');head,rest=old.split('\n',1)
    p.write_text(head+'\n\n'+section+rest.lstrip('\n'),'utf-8')
p=ROOT/'docs/implementation/98_model_version_registration_api.md'
p.write_text(p.read_text('utf-8')+'\n## 통합 실제 검증·전체 회귀\n\n'+section.replace('## '+now+' — ','### '),'utf-8')
review={'recorded_at':datetime.datetime.now().astimezone().isoformat(),'status':'PLANNED_REVIEW_ONLY','next':'read-only model registration provenance diagnostic contract','observed_sources':['backend/app/experiment_registry.py','backend/app/gmais_api.py','backend/app/main.py','docs/implementation/97_model_version_declaration.md'],'reason':'Caller declaration and copied raw training fields are not authenticated provenance; existing model_ref validation does not establish registry authority. Define explicit unverified/absent/conflict observations before any resolver.','implementation_changes':0,'operating_registrations':0,'constraints':['No authority inference from declaration source/shape','No dataset_version replacement or backfill','No approval or executor connection','Review contract before implementation']}
(e/'model-version-api-next-review-20261017.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({'updated_operations_documents':3,'updated_api_document':True,'next_review_only':True}))
