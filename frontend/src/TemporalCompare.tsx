import { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import { api, API_BASE } from './api';

type PaletteEntry = { value: number; color: string; label?: string };
type AnnualLayer = { year: number; layer_id: string; bbox: [number, number, number, number]; source?: unknown; reference_kind?: string; palette?: PaletteEntry[]; synthetic?: boolean };
type Series = { id: string; province: string; title: string; kind: 'annual_reference' | 'model_prediction'; class_names?: string[]; palette?: PaletteEntry[]; years: AnnualLayer[]; missing_years?: number[]; synthetic?: boolean };
type Inventory = { series: Series[]; limitations?: string[] };

function sourceText(value: unknown) { return typeof value === 'string' ? value : value ? JSON.stringify(value) : '출처 미제공'; }

function AnnualMaps({ left, right, swipe, position }: { left: AnnualLayer; right?: AnnualLayer; swipe: boolean; position: number }) {
  const container = useRef<HTMLDivElement>(null);
  const leftContainer = useRef<HTMLDivElement>(null);
  const rightContainer = useRef<HTMLDivElement>(null);
  const maps = useRef<{ left?: maplibregl.Map; right?: maplibregl.Map }>({});
  const viewport = useRef<{ center: [number, number]; zoom: number; bearing: number; pitch: number } | undefined>(undefined);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!leftContainer.current || !container.current) return;
    setError(''); setLoading(true);
    const prefix = `${API_BASE}/data/landcover-layers/`;
    function create(target: HTMLDivElement, layer: AnnualLayer) {
      const map = new maplibregl.Map({ container: target, attributionControl: false,
        style: { version: 8, sources: { annual: { type: 'raster', tiles: [`${prefix}${encodeURIComponent(layer.layer_id)}/tiles/{z}/{x}/{y}.png`], tileSize: 256 } },
          layers: [{ id: 'blank', type: 'background', paint: { 'background-color': '#e5ebe8' } },
            { id: 'annual', type: 'raster', source: 'annual', paint: { 'raster-resampling': 'nearest', 'raster-fade-duration': 0 } }] },
        center: viewport.current?.center || [(layer.bbox[0] + layer.bbox[2]) / 2, (layer.bbox[1] + layer.bbox[3]) / 2],
        zoom: viewport.current?.zoom || 9, bearing: viewport.current?.bearing || 0, pitch: viewport.current?.pitch || 0,
        transformRequest: url => {
          // 토큰은 정확한 자체 API 타일 경로에만 첨부한다. 타사 지도 URL에는 전달하지 않는다.
          const token = sessionStorage.getItem('geoai_token');
          return { url, ...(url.startsWith(prefix) && token ? { headers: { Authorization: `Bearer ${token}` } } : {}) };
        } });
      map.on('error', () => { setError('연차 타일을 불러오지 못했습니다. 서버 연결·권한·해당 레이어 상태를 확인하세요.'); setLoading(false); });
      return map;
    }
    const a = create(leftContainer.current, left);
    const b = swipe && right && rightContainer.current ? create(rightContainer.current, right) : undefined;
    maps.current = { left: a, right: b };
    if (!viewport.current) a.fitBounds(left.bbox, { padding: 35, duration: 0, maxZoom: 18 });
    const sync = () => {
      const center = a.getCenter();
      viewport.current = { center: [center.lng, center.lat], zoom: a.getZoom(), bearing: a.getBearing(), pitch: a.getPitch() };
      b?.jumpTo(viewport.current);
    };
    a.on('move', sync); a.on('load', sync);
    b?.on('load', sync);
    a.on('idle', () => setLoading(false));
    const observer = new ResizeObserver(() => { a.resize(); b?.resize(); sync(); });
    observer.observe(container.current);
    return () => { observer.disconnect(); maps.current = {}; a.remove(); b?.remove(); };
  }, [swipe]);
  useEffect(() => {
    // 프레임마다 WebGL 지도를 다시 만들지 않고 실제 타일 소스만 교체해 카메라를 유지한다.
    setLoading(true);
    const listeners: (() => void)[] = [];
    for (const [map, layer] of [[maps.current.left, left], [maps.current.right, right]] as const) {
      if (!map || !layer) continue;
      const update = () => {
        const source = map.getSource('annual') as maplibregl.RasterTileSource | undefined;
        source?.setTiles([`${API_BASE}/data/landcover-layers/${encodeURIComponent(layer.layer_id)}/tiles/{z}/{x}/{y}.png`]);
      };
      if (map.isStyleLoaded()) update(); else map.once('load', update);
      listeners.push(() => map.off('load', update));
    }
    return () => { listeners.forEach(remove => remove()); };
  }, [left.layer_id, right?.layer_id, swipe]);
  return <><div className="temporal-map" ref={container}>
    <div className="temporal-map-canvas" ref={leftContainer}/>
    {swipe && <div className="temporal-map-canvas temporal-right" ref={rightContainer} style={{ clipPath: `inset(0 0 0 ${position}%)` }}/>}
    <span className="temporal-year temporal-year-left">{swipe ? '왼쪽 ' : ''}{left.year}</span>
    {swipe && <><span className="temporal-year temporal-year-right">오른쪽 {right?.year}</span><span className="temporal-divider" style={{left: `${position}%`}}/></>}
    {loading && <span className="temporal-loading" role="status">실제 타일 불러오는 중…</span>}
  </div>{error && <p className="error" role="alert">{error}</p>}</>;
}

export default function TemporalCompare() {
  const [data, setData] = useState<Inventory>();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [id, setId] = useState('');
  const [mode, setMode] = useState<'animate' | 'swipe'>('animate');
  const [frame, setFrame] = useState(0);
  const [rightIndex, setRightIndex] = useState(1);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1500);
  const [position, setPosition] = useState(50);
  const series = data?.series.find(row => row.id === id);
  const years = [...(series?.years || [])].sort((a, b) => a.year - b.year);
  const left = years[Math.min(frame, years.length - 1)];
  const right = years[Math.min(rightIndex, years.length - 1)];
  async function refresh() {
    setBusy(true); setPlaying(false); setError('');
    try {
      const result = await api<Inventory>('/data/landcover-series');
      setData(result); setId(old => result.series.some(row => row.id === old) ? old : result.series[0]?.id || '');
      setFrame(0); setRightIndex(1);
    } catch (e) { setData(undefined); setId(''); setError(String(e)); } finally { setBusy(false); }
  }
  useEffect(() => { void refresh(); }, []);
  useEffect(() => { setPlaying(false); setFrame(0); setRightIndex(1); }, [id, mode]);
  useEffect(() => {
    // 가용 연도 배열만 순환한다. 누락 연도 프레임이나 중간 분류를 생성하지 않는다.
    if (!playing || years.length < 2 || mode !== 'animate') return;
    const timer = window.setInterval(() => setFrame(old => (old + 1) % years.length), speed);
    return () => window.clearInterval(timer);
  }, [playing, speed, years.length, mode]);
  const palette = left?.palette || series?.palette || [];
  return <section className="panel temporal-panel"><div className="section-title"><div><span className="eyebrow">ANIMATE / SWIPE</span><h2>확보된 연차 지도 비교</h2></div><button className="secondary" disabled={busy} onClick={() => void refresh()}>{busy ? '조회 중…' : '레이어 재조회'}</button></div>
    <p className="help">실제로 등록된 래스터만 표시합니다. 연차 참조 라벨과 모델 예측은 별도 시리즈이며, 화면 비교가 독립 변화 정확도를 입증하지 않습니다.</p>
    {error && <p className="error" role="alert">{error}</p>}
    <label>연차 시리즈<select value={id} onChange={e => setId(e.target.value)}><option value="">시리즈 선택</option>{data?.series.map(row => <option key={row.id} value={row.id}>{row.title} · {row.kind === 'annual_reference' ? '연차 참조' : '모델 예측'}</option>)}</select></label>
    {data && !data.series.length && <p className="empty">표시 가능한 연차 레이어가 없습니다. 실제 수집·분류 산출물이 등록된 후 다시 조회하세요.</p>}
    {series && <><p className="hint">{series.kind === 'annual_reference' ? '연차 참조 라벨 · 모델 예측 아님' : '모델 예측 · 지상 독립 정답 아님'} · {series.province}</p>
      {(series.synthetic || left?.synthetic) && <p className="readiness-warning">합성 fixture · 실제 관측·모델 정확도 아님</p>}
      <p className="help">확보 연도: {years.map(row => row.year).join(', ') || '없음'} · 누락 연도: {series.missing_years === undefined ? '서버 미제공' : series.missing_years.length ? series.missing_years.join(', ') : '없음'}</p>
      <div className="button-row"><button className={mode === 'animate' ? '' : 'secondary'} onClick={() => setMode('animate')}>Animate 자동 재생</button><button className={mode === 'swipe' ? '' : 'secondary'} onClick={() => setMode('swipe')}>Swipe 좌우 비교</button></div>
      {years.length < 2 && <p className="readiness-warning">실제 확보 레이어가 {years.length}개입니다. 자동 재생과 두 연도 비교는 두 개 이상의 연도가 필요합니다.</p>}
      {left && <>{mode === 'animate' ? <div className="temporal-controls"><button disabled={years.length < 2} onClick={() => setPlaying(old => !old)}>{playing ? '일시 정지' : '재생'}</button><label>재생 간격<select value={speed} onChange={e => setSpeed(Number(e.target.value))}><option value={500}>0.5초</option><option value={1500}>1.5초</option><option value={3000}>3초</option></select></label><label>표시 연도 {left.year}<input aria-label="애니메이션 연도" type="range" min={0} max={Math.max(0, years.length - 1)} value={frame} disabled={years.length < 2} onChange={e => { setPlaying(false); setFrame(Number(e.target.value)); }}/></label></div>
      : <div className="temporal-controls"><label>왼쪽 연도<select value={frame} onChange={e => setFrame(Number(e.target.value))}>{years.map((row, i) => <option key={row.year} value={i}>{row.year}</option>)}</select></label><label>오른쪽 연도<select value={Math.min(rightIndex, years.length - 1)} disabled={years.length < 2} onChange={e => setRightIndex(Number(e.target.value))}>{years.map((row, i) => <option key={row.year} value={i}>{row.year}</option>)}</select></label><label>좌우 경계 {position}%<input aria-label="Swipe 비교 경계" type="range" min={0} max={100} value={position} onChange={e => setPosition(Number(e.target.value))}/></label></div>}
      <AnnualMaps key={series.id} left={left} right={right} swipe={mode === 'swipe' && years.length >= 2} position={position}/>
      <p className="help temporal-source">왼쪽 {left.year}: {left.reference_kind || series.kind} · {sourceText(left.source)}{mode === 'swipe' && right && <><br/>오른쪽 {right.year}: {right.reference_kind || series.kind} · {sourceText(right.source)}</>}</p>
      <div className="temporal-legend" aria-label="분류 범례">{palette.length ? palette.map(entry => <span key={entry.value}><i style={{background: entry.color}}/>{entry.value} · {entry.label || series.class_names?.[entry.value] || `클래스 ${entry.value}`}</span>) : <p className="help">서버가 색상 범례를 제공하지 않았습니다. 색상·클래스 의미를 임의로 추정하지 않습니다.</p>}</div></>}
    </>}{data?.limitations?.map((value, i) => <p className="help" key={i}>{value}</p>)}
  </section>;
}
