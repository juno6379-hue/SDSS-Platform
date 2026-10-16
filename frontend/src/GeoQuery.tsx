import { useState } from 'react';
import { api, agentApi } from './api';
import { evidenceIdentity, isMockOnly } from './integrationAdapter';
import type { EvidenceRecord } from './integrationAdapter';

type QueryResponse = { mode?: string; answer?: string; evidence?: EvidenceRecord[]; trace_id?: string; status?: string; plan_id?: string; scientific_status?: string };
export default function GeoQuery({ analyses, onReviewResult, onAgentCenter }: { analyses: EvidenceRecord[]; onReviewResult: (id: string) => void; onAgentCenter: () => void }) {
  const [kind, setKind] = useState('evidence');
  const [question, setQuestion] = useState('모델 정확도와 버전을 보여주세요');
  const [analysisId, setAnalysisId] = useState('');
  const [answer, setAnswer] = useState<QueryResponse>();
  const [datasets, setDatasets] = useState<EvidenceRecord[]>();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [plan, setPlan] = useState<unknown>();
  const [planJson, setPlanJson] = useState(() => JSON.stringify({schema_version:'0.2.0',workflow_run_id:`ui-${crypto.randomUUID()}`,trace_id:`trace-${crypto.randomUUID()}`,nodes:[{node_id:'n1',agent_id:'lcluc-agent',capability_id:'landcover.change_detection',depends_on:[],input_bindings:[]}],policy:{on_blocked:'STOP_DEPENDENTS',max_parallel:1,require_human_approval:true}},null,2));
  async function inspectPlan() {
    setError(''); setPlan(undefined); setBusy(true);
    try {setPlan(await agentApi('/v1/workflows/plan', JSON.parse(planJson)));}
    catch(e) {setError(String(e));} finally {setBusy(false);}
  }
  async function run() {
    setError(''); setAnswer(undefined); setDatasets(undefined); setBusy(true);
    try {
      if (kind === 'data') setDatasets(await api<EvidenceRecord[]>('/datasets'));
      else if (kind === 'evidence') setAnswer(await api<QueryResponse>('/query', { question, ...(analysisId ? {analysis_id: analysisId} : {}) }));
    } catch (e) { setError(String(e)); } finally { setBusy(false); }
  }
  return <section className="panel"><span className="eyebrow">GEOLLM · EVIDENCE / NO-LLM FALLBACK</span><h2>실행 상태와 출처를 함께 확인하는 질의</h2>
    <p className="hint">현재 질의 API는 승인된 정형 읽기 패턴입니다. LLM·정책 RAG·자연어 임의 코드 실행을 사용하지 않습니다. 외부 GeoLLM 서비스가 연결되었다고 표시하지 않습니다.</p>
    <label>질의 유형<select value={kind} onChange={e => { setKind(e.target.value); setAnswer(undefined); setDatasets(undefined); setError(''); }}><option value="data">데이터 조회만 · 실제 Catalog 읽기</option><option value="execution">LCLUC 분석 실행 요청 · 준비도 검토</option><option value="evidence">결과·모델 출처 설명 · 정형 읽기</option></select></label>
    <div className="query-flow" aria-label="질의 실행 경로"><span>요청 유형</span><b>→</b><span>도구·준비도</span><b>→</b><span>실제 응답 근거</span><b>→</b><span>동일 Result ID 지도·보고서</span></div>
    {kind === 'execution' ? <><p className="readiness-warning">실행 전 검토 · 자연어 질문만으로 Draft 모델의 추론·정책 분석을 실행하지 않습니다. 아래는 서버가 계산한 계획·차단 근거 조회이며 실제 Job 실행과 별도입니다.</p><p className="help">GMAIS v0.2 Workflow Plan 스키마를 사용합니다. POST /v1/workflows/plan은 원본 OpenAPI에 없는 RFC 확장 경로입니다. 예시 Agent·Capability를 실제 Registry와 확인하고 input_bindings에 실제 ID·버전·SHA를 넣으세요. 빈 근거를 실제 데이터로 채워 추정하지 않습니다.</p><label>Workflow 계획 JSON<textarea className="editor" value={planJson} spellCheck={false} onChange={e => {setPlanJson(e.target.value);setPlan(undefined);}}/></label><div className="button-row"><button disabled={busy} onClick={() => void inspectPlan()}>{busy ? '서버 검토 중…' : '실제 실행계획·차단 근거 조회 (RFC)'}</button><button className="secondary" onClick={onAgentCenter}>Agent Center 준비도 확인</button><button className="secondary" disabled>자동 Job 실행 미연결</button></div>{plan !== undefined && <><h3>서버 계획 응답·Trace</h3><pre className="json">{JSON.stringify(plan,null,2)}</pre></>}</>
    : <>{kind === 'evidence' && <><label>질문<textarea maxLength={2000} value={question} onChange={e => setQuestion(e.target.value)}/></label><label>근거 분석 ID<select value={analysisId} onChange={e => setAnalysisId(e.target.value)}><option value="">모델 기록 조회 또는 분석 미선택</option>{analyses.filter(row => !isMockOnly(row)).map(row => <option key={String(row.id)} value={String(row.id)}>{String(row.id)}</option>)}</select></label><p className="help">지원: 모델 정확도/버전, 완료된 변화 분석 면적·통계. 분석의 AOI·기간·분류체계가 질문과 일치하는지 원본 근거를 확인하세요.</p></>}<button disabled={busy || kind === 'evidence' && !question.trim()} onClick={() => void run()}>{busy ? '실제 응답 조회 중…' : kind === 'data' ? '실제 Dataset Catalog 조회' : '근거 답변 조회'}</button></>}
    {datasets && <><h3>조회된 데이터셋 {datasets.length}개</h3><p className="help">GET /api/datasets · 읽기 전용 · 승인/라이선스/품질은 각 실제 기록을 확인하세요.</p>{datasets.map(row => <details className="job" key={String(row.id)}><summary>{String(row.id)} · {String(row.status || '승인 상태 미제공')}</summary><pre className="json">{JSON.stringify(row, null, 2)}</pre></details>)}</>}
    {answer && <><p className="hint">응답 모드 {answer.mode || '서버 미제공'} · Trace {answer.trace_id || '미제공 · 공통 추적 연결 필요'}</p><p>{answer.answer || '서버 답변 없음'}</p>
      {!answer.evidence?.length && <p className="empty">인용 가능한 실제 근거가 없습니다. 지도·정책·모델 성과를 보충 생성하지 않습니다.</p>}
      {answer.evidence?.map((record, i) => <article className="job" key={String(record.id || i)}><h3>Evidence ID {String(record.id || '서버 미제공')}</h3>
        <p className="help">과학적 상태 {String(record.scientific_status || record.result_classification || '미제공')} · 독립 평가 {record.independent_evaluation === true ? '기록 있음·체크포인트 검토 필요' : '미확인/미완료'} · 모델 상태 {String(record.status || '미제공')}</p>
        {isMockOnly(record) ? <p className="readiness-warning">MOCK_ONLY · 정책 지도·보고서로 게시하지 않습니다.</p> : <pre className="json">{JSON.stringify(evidenceIdentity(record), null, 2)}</pre>}
        {!isMockOnly(record) && analyses.some(row => row.id === record.id) && <button className="secondary" onClick={() => onReviewResult(String(record.id))}>동일 분석 ID의 지도·보고서 검토</button>}
      </article>)}
      <p className="help">Metadata/Policy RAG·문서 버전·기관별 ACL 근거 API는 아직 연결되지 않았습니다. RDTR/RTRW를 인용하거나 정책 적합성을 추정하지 않습니다.</p></>}
    {error && <p className="error" role="alert">{error}</p>}
  </section>;
}
