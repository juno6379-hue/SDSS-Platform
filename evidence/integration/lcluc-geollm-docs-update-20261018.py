from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
text = (ROOT/'evidence/integration/lcluc-geollm-full-tests-20261018.log').read_text('utf-8')
match = re.search(r'Ran (\d+) tests in ([\d.]+)s', text)
assert match and re.search(r'^OK \(skipped=1\)$', text, re.M), text[-2000:]
count, seconds = int(match[1]), float(match[2])
section = f'''## 2026-10-18 — Data·ML 실제 연결 보완과 GeoLLM 진단 (111~114)

사용자는 6주 Data Pipeline·LCLUC ML/Agent·오케스트레이터·MLOps/staging/보안/UAT의 병행 개발을 요청했고, 이어 기존 정상 기능을 유지한 GeoLLM 실제 상태·후보 조합·ID/EN 실측 기술검토를 우선 지시했다. 데이터 담당은111, ML 담당은112, 이해/통합검토 담당은113·114와 이해자료, Root는 로컬 GeoLLM 평가·통합시험·문서/보존·Git을 맡았다. 아래는 이번 단위 완료이며 전체 프로젝트 인수가 아니다.

- **Data111:** 명시 `--registry-manifest`로 검증 수집 report를 공통 DatasetVersion에 실제 등록하는 CLI 연결. RAW/STAGED 문서만, 고정 직접 부모·source3종 파일 SHA·경로/변조/버전충돌 검사. 옵션 없는 legacy 동작 보존, 운영등록0. 신규12·관련51·독립23 PASS. 원본1384/적격1111·36셀 자료 존재, 후보1095·QA차단4와 class7 부족 유지. AOI 일부 patch를 주 전체 확보로 계산하지 않는다.
- **ML112:** 실제 안전한 weights_only 체크포인트 조사로 기존 TinyUNet/RGB3밴드/29,833 parameter 확인. U-Net++는 미구현이며 기존 모델은 현재6밴드 후보가 아니다. 완료best epoch의val/test 오류분석·FP/FN/미예측·오분류쌍·JSON/CSV3종을train report에 연결했다. 신규12·관련29·독립12 PASS, 합성16×16 CPU fixture 포함·운영학습0. 기존weights/split·선택정책 보존. 오류표UI와인증다운로드는후속이며artifact bundle 원자성 미보장.
- **GeoLLM114:** 현재 서비스 LLM없음·`predefined-pattern`, SQLite·정책RAG/toolcalling미연결. 별도 Ollama0.40.5에 설치2Qwen 실제추출12시도/응답11, native계획4시도/응답3, BGE실제7×1024 embedding을검증. 1.5b의공격요청may_execute=true·정책의도오분류·빈/잘못된citation·4b timeout을보존했다. Qwen3:8b미설치/N/A, 후보가현행실사용모델인것처럼표현하지않는다. BGE검색은내부코드4문서 top1 2/3·top2 3/3로공식BIG/RDTR·운영RAG성능아님. evaluator 신규/독립17 PASS. Ollama·Postgres프로세스/PostGIS설치파일과앱연결·DB활성은구별한다.
- **Root통합:** 전체 backend {count}건 중 {count-1}PASS/기존 Windows1SKIP·{seconds:.3f}초·exit0. 신규/관련/독립과중복합산하지않는다. 신규실자료QA·수집·정식학습·운영Job/등록·배포0. 기존GeoQuery/main/gmais/frontend변경0이라front/build/browser는이번재실행없음. 보호141·이전증거829·catalog14·원본/원장/예약136314880B/lock/분할/모델보존은최종integrity를따른다.

완료소스와시험을이해에이전트가읽어쉬운설명·발표대본·FAQ·INDEX·변경이력을갱신했다. [111](docs/implementation/111_data_pipeline_completion.md)·[112](docs/implementation/112_lcluc_ml_completion.md)·[113](docs/implementation/113_lcluc_integration_acceptance.md)·[114기술검토](docs/implementation/114_geollm_technical_review.md)에수락범위가있다. 상대링크는각문서위치에맞춰아래에서변환한다.

다음 내부 핵심은 LCLUC전용 실제 orchestration의고정Registry입력→승인/배포모델→기존시계열추론→동일Result/Trace 연결과실패/멱등·재시작정책이다. Root의해당새실행기는사용자GeoLLM우선검토에따라아직미착수/PLANNED다. 현재승인모델/독립검증라벨·공식RAG근거/staging권한·기관UAT가없는데실제승인·배포·정확도를완료로대체하지않는다. 외부5실행기미연결은사용자확인사항이며LCLUC범위에집중한다. 지속개발과10분보고예약ACTIVE는유지하고실제worker/활성담당과구분한다.

근거: `evidence/integration/lcluc-geollm-full-tests-20261018.log`, `evidence/integration/geollm-local-evaluation-20261018.json`, `evidence/integration/geollm-native-tools-20261018.json`, `evidence/integration/geollm-independent-review-20261018.json`. 문서·스냅샷·보존 최종근거는 `evidence/integration/lcluc-geollm-closeout-20261018.json`을 따른다.

'''
for name in ('CONTINUOUS_DEVELOPMENT.md', 'docs/implementation/00_next_session_handoff.md', 'docs/implementation/workstream_ownership.md'):
    path = ROOT/name
    old = path.read_text('utf-8')
    first, _, rest = old.partition('\n')
    local = section
    if name != 'CONTINUOUS_DEVELOPMENT.md':
        local = local.replace('(docs/implementation/', '(')
    path.write_text(first+'\n\n'+local+rest.lstrip('\n'), 'utf-8')
for name in ('04_gap_analysis.md', '08_model_type_validation_sops.md', '109_area_completion_audit.md', '26_dataset_version_registry_core.md'):
    path = ROOT/'docs/implementation'/name
    path.write_text(path.read_text('utf-8')+'''
### 2026-10-18 후속: 실제 등록·ML 오류분석·GeoLLM 기술검토

[111](111_data_pipeline_completion.md)은 수집 source report를 RAW/STAGED 문서로 공통 버전에 연결한 명시 CLI이며 운영등록/AI-ready 승인이 아니다. [112](112_lcluc_ml_completion.md)는 기존 TinyUNet RGB 체크포인트를 확인하고 완료best 모델의 val/test 오류분석을 실제 학습 report에 연결했다. class7·QA차단과 독립 검증 라벨 미확보를 해제하지 않는다. [113](113_lcluc_integration_acceptance.md)의 LCLUC전용 새 orchestration은 후속PLANNED다. [114](114_geollm_technical_review.md)는 현재 앱에 LLM/RAG 미연결임을 확인하고 설치된 Ollama 모델의 별도 실응답·실패·임베딩과 Qwen3:8b 후보/N/A를 구분한다. 기존 정상 GeoLLM API/UI·운영 DB/원장은 변경하지 않았다. 최신 전체 시험·보존·이해자료·다음 수락 조건은 인계서의111~114 절을 따른다. 이 변경만으로 Data/ML/운영·기관UAT 전체 완료를 선언하지 않는다.
''', 'utf-8')
readme = ROOT/'README.md'
readme.write_text(readme.read_text('utf-8')+'''
### LCLUC·GeoLLM 개발 검토 (2026-10-18)

- [GeoLLM 실제 모델·RAG·도구 호출·지연 기술검토](docs/implementation/114_geollm_technical_review.md): 현행은 LLM 없는 정형 조회. 설치 모델의 별도 실측과 Qwen3 8B 개발 후보를 구분합니다.
- [수집 결과→공통 DatasetVersion 등록](docs/implementation/111_data_pipeline_completion.md)
- [실제 TinyUNet 아키텍처·최종 오류분석](docs/implementation/112_lcluc_ml_completion.md)
- [LCLUC 통합·staging·보안·UAT 수락 조건](docs/implementation/113_lcluc_integration_acceptance.md)
''', 'utf-8')
print(f'Common handoff/gaps/SOP/registry/README updated; full {count-1} PASS/1 SKIP.')
