import { useEffect, useState } from 'react';
import { api, agentApi } from './api';
import { pendingIntegration, readinessAxes, isMockOnly, evidenceIdentity } from './integrationAdapter';
import type { EvidenceRecord, ReadinessRecord } from './integrationAdapter';

export default function AgentCenter({ tools, models, jobs, onNavigate }: { tools: EvidenceRecord[]; models: EvidenceRecord[]; jobs: EvidenceRecord[]; onNavigate: (step: number) => void }) {
  const [selected, setSelected] = useState('lcluc');
  const [modelId, setModelId] = useState('');
  const [review, setReview] = useState<ReadinessRecord>();
  const [dataset, setDataset] = useState<boolean | null>(null);
  const [error, setError] = useState('');
  const [agents, setAgents] = useState<EvidenceRecord[]>([]);
  const [agentId, setAgentId] = useState('');
  const [agentReadiness, setAgentReadiness] = useState<EvidenceRecord>();
  const [standardError, setStandardError] = useState('');
  const [standardJobId, setStandardJobId] = useState('');
  const [standardJob, setStandardJob] = useState<EvidenceRecord>();
  const [standardResult, setStandardResult] = useState<EvidenceRecord>();
  const [registryRefresh, setRegistryRefresh] = useState(0);
  const [standardCapabilities, setStandardCapabilities] = useState<unknown>();
  const [standardLoading, setStandardLoading] = useState(true);
  useEffect(() => {
    let active = true; setStandardLoading(true); setStandardError(''); setAgents([]); setAgentReadiness(undefined);
    agentApi<unknown>('/v1/agents').then(value => {
      const rows = Array.isArray(value) ? value : value && typeof value === 'object' && 'items' in value && Array.isArray(value.items) ? value.items : value && typeof value === 'object' && 'agents' in value && Array.isArray(value.agents) ? value.agents : [];
      if (active) setAgents(rows as EvidenceRecord[]);
    }).catch(e => {if (active) {setAgents([]);setStandardError(String(e));}}).finally(() => {if (active) setStandardLoading(false);});
    return () => {active = false;};
  }, [registryRefresh]);
  useEffect(() => {
    let active = true; setAgentReadiness(undefined); setStandardCapabilities(undefined);
    if (agentId) agentApi<EvidenceRecord>(`/v1/agents/${encodeURIComponent(agentId)}/readiness`).then(value => {if (active) setAgentReadiness(value);}).catch(e => {if (active) setStandardError(String(e));});
    if (agentId) agentApi(`/v1/agents/${encodeURIComponent(agentId)}/capabilities`).then(value => {if (active) setStandardCapabilities(value);}).catch(e => {if (active) setStandardError(String(e));});
    return () => {active = false;};
  }, [agentId,registryRefresh]);
  const tool = tools.find(row => row.id === selected);
  const model = models.find(row => row.id === modelId);
  useEffect(() => {
    let active = true;
    api<{training_readiness?: {ready_for_training?: boolean}}>('/data/collection-status').then(result => {
      if (active) setDataset(typeof result.training_readiness?.ready_for_training === 'boolean' ? result.training_readiness.ready_for_training : null);
    }).catch(e => { if (active) { setDataset(null); setError(String(e)); } });
    return () => { active = false; };
  }, []);
  useEffect(() => {
    let active = true; setReview(undefined);
    if (modelId && selected === 'lcluc') api<ReadinessRecord>(`/models/${encodeURIComponent(modelId)}/readiness`).then(value => { if (active) setReview(value); }).catch(e => { if (active) setError(String(e)); });
    return () => { active = false; };
  }, [modelId, selected]);
  return <section className="panel"><span className="eyebrow">AGENT CENTER · COMPATIBILITY VIEW</span><h2>모델 Agent 준비 상태</h2>
    <p className="hint">실제로 확보한 GMAIS v0.2 내부 제안 OpenAPI의 /v1과 기존 /api 호환 정보를 구분합니다. 컨소시엄/BIG 확정 표준이나 과학적 검증 완료라는 뜻은 아닙니다.</p>
    <h3>표준 /v1 Agent Registry</h3><p className="help">Agent readiness와 모델 승인 상태는 별도입니다. 실제 응답이 없으면 연결 성공으로 표시하지 않습니다.</p>
    <button className="secondary" onClick={() => setRegistryRefresh(old => old + 1)}>표준 Registry 재조회</button>
    <label>표준 Agent 선택<select value={agentId} onChange={e => {setAgentId(e.target.value);setStandardError('');}}><option value="">Agent 선택</option>{agents.map(row => <option key={String(row.agent_id)} value={String(row.agent_id)}>{String(row.agent_id)} · {String(row.readiness)} · 모델 {String(row.model_approval_status || '미제공')}</option>)}</select></label>
    {standardLoading && <p role="status" className="help">표준 Agent Registry 조회 중…</p>}
    {!standardLoading && !agents.length && <p className="empty">등록 Agent 응답 없음 · 아래 기존 Toolbox를 표준 Agent 연결 성공으로 해석하지 않습니다.</p>}
    {agentReadiness && <><p className="hint">Agent {String(agentReadiness.agent_id || agentId)} · 준비도 {String(agentReadiness.readiness)} · 모델 승인 {String(agentReadiness.model_approval_status || '미제공')}</p><pre className="json">{JSON.stringify(agentReadiness,null,2)}</pre></>}
    {standardCapabilities !== undefined && <details><summary>선택 Agent의 실제 Capability</summary><pre className="json">{JSON.stringify(standardCapabilities,null,2)}</pre></details>}
    <label>표준 Job ID<input autoComplete="off" spellCheck={false} name="standard-job-id" value={standardJobId} onChange={e => setStandardJobId(e.target.value)} placeholder="실제 발급된 job_id"/></label><button className="secondary" disabled={!standardJobId.trim()} onClick={async () => {setStandardError('');setStandardJob(undefined);setStandardResult(undefined);try {setStandardJob(await agentApi<EvidenceRecord>(`/v1/jobs/${encodeURIComponent(standardJobId)}`));}catch(e){setStandardError(String(e));}}}>Job·Trace 실제 조회</button>
    {standardJob && <p className="hint">Job {String(standardJob.job_id)} · {String(standardJob.status)} · Trace {String(standardJob.trace_id || '미제공')}<br/>{JSON.stringify(standardJob)}</p>}
    {standardJob && <button className="secondary" disabled={!['CREATED','VALIDATING','QUEUED','RUNNING'].includes(String(standardJob.status))} onClick={async () => {setStandardError('');try {setStandardJob(await agentApi<EvidenceRecord>(`/v1/jobs/${encodeURIComponent(String(standardJob.job_id))}/cancel`,{}));setStandardResult(undefined);}catch(e){setStandardError(String(e));}}}>이 Job의 취소 요청</button>}
    {standardJob && <button className="secondary" disabled={standardJob.status !== 'SUCCEEDED'} onClick={async () => {setStandardError('');setStandardResult(undefined);try {setStandardResult(await agentApi<EvidenceRecord>(`/v1/jobs/${encodeURIComponent(String(standardJob.job_id))}/results`));}catch(e){setStandardError(String(e));}}}>동일 Job의 실제 Result 조회</button>}
    {standardResult && standardResult.job_id === standardJob?.job_id && <><p className="hint">Result {String(standardResult.result_id)} · 과학적 상태 {String(standardResult.status)}</p>{isMockOnly(standardResult) ? <p className="readiness-warning">MOCK_ONLY · 의사결정 지도·보고서 게시 차단</p> : <><pre className="json">{JSON.stringify(evidenceIdentity(standardResult),null,2)}</pre><p className="help">표준 Result의 자산·Layer/Report 게시 Adapter는 아직 연결되지 않았습니다. URI로 임의 지도를 생성하지 않습니다.</p></>}</>}
    {standardError && <p className="error" role="alert">{standardError}</p>}
    <h3>기존 LCLUC 실행·모델 호환 정보</h3>
    {!tools.length && <p className="empty">서버 Toolbox 목록이 없습니다. Agent 연결 상태를 추정하지 않습니다.</p>}
    <div className="agent-grid">{tools.map(row => <button key={String(row.id)} className={selected === row.id ? 'agent-card selected' : 'agent-card secondary'} onClick={() => { setSelected(String(row.id)); setModelId(''); setError(''); }}><strong>{String(row.id)}</strong><span>{row.implemented === true ? 'LCLUC 기존 실행 코드' : '외부 모델 연결 대기'}</span><small>{String(row.status || '상태 미제공')}</small></button>)}</div>
    {tool && <><h3>{String(tool.id)} 검토</h3>{tool.implemented === true ? <><label>검토할 등록 모델<select value={modelId} onChange={e => setModelId(e.target.value)}><option value="">모델 선택 · 미선택 상태는 미검증</option>{models.map(row => <option value={String(row.id)} key={String(row.id)}>{String(row.id)} · {String(row.status)}</option>)}</select></label><div className="readiness-axes">{readinessAxes(tool, dataset, model, review).map(axis => <article key={axis.id}><strong>{axis.label}</strong><code>{axis.state}</code><p>{axis.detail}</p></article>)}</div>{review?.blockers?.length ? <div className="readiness-warning">{review.blockers.map((value, i) => <p key={i}>{typeof value === 'string' ? value : JSON.stringify(value)}</p>)}</div> : null}<div className="button-row"><button onClick={() => onNavigate(0)}>실제 데이터 준비도 확인</button><button className="secondary" onClick={() => onNavigate(6)}>모델 승인·배포 검토</button><button className="secondary" onClick={() => onNavigate(4)}>기존 공간 추론 입력</button></div></>
    : <p className="readiness-warning">BLOCKED · 외부 기관 모델 Adapter·실행 이미지·검증 증거가 연결되지 않았습니다. 이 모델의 실행·결과 지도·성과를 생성하지 않습니다.</p>}
    <details><summary>서버 Toolbox 원본 계약</summary><pre className="json">{JSON.stringify(tool, null, 2)}</pre></details></>}
    <h3>실제 Job 상태·Trace</h3><p className="help">기존 작업 목록입니다. 공통 Orchestrator DAG·재시도·권한별 Trace API는 아직 연결되지 않았습니다.</p>
    {jobs.length ? <div className="table-scroll"><table className="inventory-table"><thead><tr><th>Job ID</th><th>상태</th><th>실패·차단 근거</th><th>Trace ID</th></tr></thead><tbody>{jobs.map(row => <tr key={String(row.id)}><td><code>{String(row.id)}</code></td><td>{String(row.status)}</td><td>{row.error ? JSON.stringify(row.error) : '서버 오류 기록 없음'}</td><td>{String(row.trace_id || '미제공')}</td></tr>)}</tbody></table></div> : <p className="empty">등록된 작업이 없습니다.</p>}
    <details><summary>미연결 공통 Adapter 요구 계약</summary><pre className="json">{JSON.stringify(pendingIntegration, null, 2)}</pre></details>
    <details><summary>거버넌스·운영 화면의 남은 범위</summary><p className="help">토큰 기반 API 연결과 기존 모델 검토 gate를 사용합니다. 기관별 로그인·RBAC 화면, RDTR/RTRW 근거 검토, 이의제기·전문가 Feedback, 운영 롤백·지원 기록 API는 아직 연결되지 않았습니다.</p><button className="secondary" disabled>Feedback API 미연결</button><button className="secondary" disabled>운영 롤백 API 미연결</button></details>
    {error && <p role="alert" className="error">{error}</p>}
  </section>;
}
