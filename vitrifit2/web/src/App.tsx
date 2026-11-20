import { useEffect, useMemo, useState } from "react";
import Plot from "react-plotly.js";

type Item = { id: string; name: string };
type Experiment = { id: string; original_filename: string };
type CurveSummary = { id: string; temperature_c: number; source_curve_id: string };
type Curve = { curve_id: string; source_curve_id: string; temperature_c: number; time_s: number[];
  modulus_mpa: number[]; mask: boolean[]; active_revision_id: string; can_undo: boolean; can_redo: boolean };
type Run = { id: string; project_name: string; sample_name: string; sample_id: string;
  temperature_c: number; model: string; tau_definition: string; is_current: boolean;
  results: { tau_s?: number; r2?: number; beta?: number; flags?: string[] } };
type Preset = { id: string; name: string; settings: Record<string, unknown> };
type Tab = "Library" | "Preparation" | "Analysis" | "Comparison" | "Figure Studio";
const tabs: Tab[] = ["Library", "Preparation", "Analysis", "Comparison", "Figure Studio"];
const initialStyle: Record<string, unknown> = {
  pub_preset: "ACS/RSC Single-Column (85 x 75 mm)", pub_w: 8.5, pub_h: 7.5,
  pub_relfont_family: "Arial", pub_rel_lbl_sz: 12, pub_rel_num_sz: 10,
  pub_rel_lw: 1.5, pub_rel_ms: 4, pub_xscale: "Log", pub_yscale: "Linear",
  pub_colorspace: "RGB", pub_relleg: true
};
async function api<T>(url: string, method = "GET", body?: unknown): Promise<T> {
  const options: RequestInit = { method };
  if (body instanceof FormData) options.body = body;
  else if (body !== undefined) {
    options.body = JSON.stringify(body);
    options.headers = { "Content-Type": "application/json" };
  }
  const response = await fetch("/api" + url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail));
  return data as T;
}
const errorMessage = (e: unknown) => e instanceof Error ? e.message : String(e);

export default function App() {
  const [tab, setTab] = useState<Tab>("Library");
  const [projects, setProjects] = useState<Item[]>([]);
  const [projectId, setProjectId] = useState("");
  const [samples, setSamples] = useState<Item[]>([]);
  const [sampleId, setSampleId] = useState("");
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [experimentId, setExperimentId] = useState("");
  const [curves, setCurves] = useState<CurveSummary[]>([]);
  const [curveId, setCurveId] = useState("");
  const [curve, setCurve] = useState<Curve | null>(null);
  const [upload, setUpload] = useState<File | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [presets, setPresets] = useState<Preset[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [trimMode, setTrimMode] = useState("keep");
  const [start, setStart] = useState(0);
  const [end, setEnd] = useState(100);
  const [clickAnchor, setClickAnchor] = useState<number | null>(null);
  const [normalized, setNormalized] = useState(true);
  const [timeLog, setTimeLog] = useState(true);
  const [model, setModel] = useState("Single_KWW");
  const [component, setComponent] = useState("characteristic");
  const [plateau, setPlateau] = useState("Zero");
  const [fixedPlateau, setFixedPlateau] = useState(0);
  const [fit, setFit] = useState<any>(null);
  const [selectedRuns, setSelectedRuns] = useState<string[]>([]);
  const [compareMode, setCompareMode] = useState("kinetics");
  const [kineticModel, setKineticModel] = useState("Arrhenius");
  const [temperature, setTemperature] = useState(100);
  const [comparison, setComparison] = useState<any>(null);
  const [style, setStyle] = useState<Record<string, unknown>>({ ...initialStyle });

  const refreshProjects = () => api<Item[]>("/projects").then(setProjects);
  const refreshRuns = () => api<Run[]>("/analyses").then(setRuns);
  const refreshPresets = () => api<Preset[]>("/figures/presets").then(setPresets);
  useEffect(() => { Promise.all([refreshProjects(), refreshRuns(), refreshPresets()]).catch(e => setError(errorMessage(e))); }, []);
  useEffect(() => {
    setSamples([]); setSampleId("");
    if (projectId) api<Item[]>("/projects/" + projectId + "/samples").then(setSamples).catch(e => setError(errorMessage(e)));
  }, [projectId]);
  useEffect(() => {
    setExperiments([]); setExperimentId("");
    if (sampleId) api<Experiment[]>("/samples/" + sampleId + "/experiments").then(setExperiments).catch(e => setError(errorMessage(e)));
  }, [sampleId]);
  useEffect(() => {
    setCurves([]); setCurveId("");
    if (experimentId) api<CurveSummary[]>("/experiments/" + experimentId + "/curves").then(setCurves).catch(e => setError(errorMessage(e)));
  }, [experimentId]);
  useEffect(() => {
    setCurve(null); setFit(null); setClickAnchor(null);
    if (curveId) api<Curve>("/curves/" + curveId).then(loadCurve).catch(e => setError(errorMessage(e)));
  }, [curveId]);

  function loadCurve(c: Curve) {
    setCurve(c);
    if (c.time_s.length) { setStart(Math.min(...c.time_s)); setEnd(Math.max(...c.time_s)); }
  }
  async function run(task: () => Promise<void>) {
    setError(""); setBusy(true);
    try { await task(); } catch(e) { setError(errorMessage(e)); }
    finally { setBusy(false); }
  }
  async function addProject() {
    const name = window.prompt("Project name"); if (!name?.trim()) return;
    await run(async () => {
      const added = await api<{id:string}>("/projects", "POST", {name});
      await refreshProjects(); setProjectId(added.id);
    });
  }
  async function addSample() {
    if (!projectId) return;
    const name = window.prompt("Sample name"); if (!name?.trim()) return;
    await run(async () => {
      const added = await api<{id:string}>("/projects/" + projectId + "/samples", "POST", {name});
      setSamples(await api<Item[]>("/projects/" + projectId + "/samples")); setSampleId(added.id);
    });
  }
  async function importData() {
    if (!sampleId || !upload) return;
    await run(async () => {
      const form = new FormData(); form.append("file", upload);
      const result = await api<{experiment_id:string}>("/samples/" + sampleId + "/experiments", "POST", form);
      setExperiments(await api<Experiment[]>("/samples/" + sampleId + "/experiments"));
      setExperimentId(result.experiment_id); setUpload(null); setTab("Preparation");
    });
  }
  function graph(data: any[], xLabel: string, yLabel: string, xScale = "linear", yScale = "linear",
                 onSelect?: (event:any) => void, onClick?: (event:any) => void) {
    return <Plot data={data as any} layout={{
      autosize: true, height: 395, paper_bgcolor: "#fff", plot_bgcolor: "#fff",
      font: {family: "Arial, sans-serif", color: "#1e293b", size: 12},
      xaxis: {title: {text: xLabel}, type: xScale as any, gridcolor: "#e8eef5"},
      yaxis: {title: {text: yLabel}, type: yScale as any, gridcolor: "#e8eef5"},
      margin: {l: 76, r: 24, t: 25, b: 64}, dragmode: "select",
      legend: {orientation:"h", y:1.18, x:0}
    }} config={{responsive:true, displaylogo:false, scrollZoom:true}}
    style={{width:"100%"}} useResizeHandler onSelected={onSelect} onClick={onClick}/>;
  }
  function selectedInterval(event:any) {
    let xs: number[] = event?.range?.x || [];
    if (xs.length < 2 && event?.points?.length) xs = event.points.map((p:any) => Number(p.x));
    if (xs.length >= 2) {setStart(Math.min(...xs)); setEnd(Math.max(...xs)); setClickAnchor(null);}
  }
  function pointClicked(event:any) {
    const x = Number(event?.points?.[0]?.x); if (!Number.isFinite(x)) return;
    if (clickAnchor === null) {setClickAnchor(x); setStart(x); setEnd(x);}
    else {setStart(Math.min(clickAnchor, x)); setEnd(Math.max(clickAnchor, x)); setClickAnchor(null);}
  }
  const displayed = useMemo(() => {
    if (!curve) return [];
    const refIndex = curve.mask.findIndex(Boolean);
    const ref = curve.modulus_mpa[Math.max(0,refIndex)] || 1;
    const data = curve.modulus_mpa.map(v => normalized ? v / ref : v);
    return [
      {x:curve.time_s, y:data, type:"scattergl", mode:"lines", name:"Original", line:{color:"#cbd5e1",width:1}},
      {x:curve.time_s, y:data.map((v,i) => curve.mask[i] ? v : null),
        type:"scattergl", mode:"lines+markers", name:"Included", line:{color:"#2563eb",width:2}, marker:{size:3}},
      {x:curve.time_s.filter((_,i)=>!curve.mask[i]),
        y:data.filter((_,i)=>!curve.mask[i]), type:"scattergl", mode:"markers",
        name:"Excluded", marker:{color:"#da713f",size:6}}
    ];
  }, [curve,normalized]);

  async function editCurve(mode: "region"|"undo"|"redo") {
    if (!curveId) return;
    await run(async () => {
      const data:any = await api("/curves/" + curveId + "/" + mode, "POST",
        mode === "region" ? {mode:trimMode,start_s:start,end_s:end} : undefined);
      loadCurve(mode === "region" ? data.curve : data); await refreshRuns();
    });
  }
  async function fitCurve() {
    if (!curveId) return;
    await run(async () => {
      const result = await api<any>("/curves/" + curveId + "/fit", "POST",
        {model,plateau_mode:plateau,fixed_plateau_mpa:fixedPlateau,component});
      setFit(result); await refreshRuns();
    });
  }
  async function doComparison() {
    if (selectedRuns.length < 2) return;
    await run(async () => setComparison(await api<any>("/compare","POST",
      {run_ids:selectedRuns, mode:compareMode, temperature_c:temperature, kinetic_model:kineticModel})));
  }
  async function saveComparison() {
    if (!comparison) return;
    const name=window.prompt("Name this comparison","Cross-sample comparison"); if(!name?.trim()) return;
    await run(async () => {await api("/comparisons","POST",
      {name,run_ids:selectedRuns,mode:compareMode,settings:{temperature_c:temperature,kinetic_model:kineticModel}});});
  }
  async function savePreset() {
    const name=window.prompt("Name this figure style","ACS/RSC style"); if(!name?.trim()) return;
    await run(async () => {await api("/figures/presets","POST",{name,settings:style}); await refreshPresets();});
  }
  async function saveFigure() {
    if (!selectedRuns.length) return;
    const name=window.prompt("Name this figure project","Publication figure"); if(!name?.trim()) return;
    await run(async () => {await api("/figures","POST",
      {name,run_ids:selectedRuns,composition:{plot_type:compareMode},overrides:style});});
  }
  function comparisonGraph() {
    if (!comparison) return <p className="muted">Select at least two saved analyses to compare.</p>;
    if (comparison.mode === "curves") return graph(comparison.curves.map((r:any)=>({
      x:r.time_s,y:r.normalized_modulus,type:"scatter",mode:"lines",
      name:r.sample + " · " + r.temperature_c + "°C"
    })),"Time (s)","Normalized modulus","log");
    if (comparison.mode === "fixed_temperature") return graph([{
      x:comparison.rows.map((r:any)=>r.sample), y:comparison.rows.map((r:any)=>r.tau_s),
      type:"bar",marker:{color:"#2563eb"}
    }],"Sample","Relaxation time τ (s)","linear","log");
    const traces:any[]=[];
    comparison.samples.forEach((r:any)=>{
      const x=r.observations.map((a:any)=>1000/(a.temperature_c+273.15));
      const y=r.observations.map((a:any)=>Math.log(a.tau_s));
      traces.push({x,y,type:"scatter",mode:"markers",name:r.sample});
      if (r.slope != null && r.intercept != null) {
        const ends=[Math.min(...x),Math.max(...x)];
        traces.push({x:ends,y:ends.map(v=>r.slope*v/1000+r.intercept),
          type:"scatter",mode:"lines",showlegend:false});
      }
    });
    return graph(traces,"1000/T (K⁻¹)","ln(τ / s)");
  }
  function numberStyle(key:string,label:string,step=0.5) {
    return <label className="field">{label}<input type="number" step={step} min="0"
      value={Number(style[key]||0)} onChange={e=>setStyle(s=>({...s,[key]:Number(e.target.value)}))}/></label>;
  }

  return <div className="app">
    <header className="topbar"><div className="brand"><span className="brand-icon">V</span>
      <strong>VitriFit</strong><span className="version">2.0 • Development</span></div>
      <div className="head-note"><span className="dot"/> Local research workspace · <a href="/api/docs" target="_blank" rel="noreferrer">API docs</a></div>
    </header>
    <div className="shell">
      <aside className="sidebar">
        <p className="section-label">WORKSPACES</p>
        {tabs.map(t=><button key={t} className={"nav "+(tab===t?"active":"")}
          onClick={()=>{setTab(t);setError("");}}>{t}</button>)}
        <p className="section-label space-top">RESEARCH LIBRARY</p>
        <label className="field">Project<select value={projectId} onChange={e=>setProjectId(e.target.value)}>
          <option value="">Choose project</option>{projects.map(p=><option value={p.id} key={p.id}>{p.name}</option>)}
        </select></label>
        <button className="subtle" onClick={addProject}>+ Create project</button>
        <label className="field">Sample<select value={sampleId} disabled={!projectId} onChange={e=>setSampleId(e.target.value)}>
          <option value="">Choose sample</option>{samples.map(s=><option value={s.id} key={s.id}>{s.name}</option>)}
        </select></label>
        <button className="subtle" disabled={!projectId} onClick={addSample}>+ Add sample</button>
        <label className="field">Experiment<select value={experimentId} disabled={!sampleId} onChange={e=>setExperimentId(e.target.value)}>
          <option value="">Choose experiment</option>{experiments.map(e=><option value={e.id} key={e.id}>{e.original_filename}</option>)}
        </select></label>
        <label className="field">Curve<select value={curveId} disabled={!experimentId} onChange={e=>setCurveId(e.target.value)}>
          <option value="">Choose curve</option>{curves.map(c=><option value={c.id} key={c.id}>{c.temperature_c}°C · {c.source_curve_id}</option>)}
        </select></label>
        <p className="sidebar-hint">Your original file, processing revisions, fits and figure configurations are saved locally.</p>
      </aside>

      <main className="main">
        <p className="eyebrow">SCIENTIFIC DATA WORKSPACE</p><h1>{tab}</h1>
        <p className="lead">{tab==="Library"?"Manage persistent scientific records":
          tab==="Preparation"?"Edit individual relaxation curves without deleting raw measurements":
          tab==="Analysis"?"Fit selected curves and preserve each analysis revision":
          tab==="Comparison"?"Compare samples at matching temperatures and across kinetic windows":
          "Save publication styles without changing the original v1 rendering standards"}</p>
        {error&&<div className="error"><strong>Action failed:</strong> {error}<button onClick={()=>setError("")}>×</button></div>}
        {busy&&<p className="loading">Processing…</p>}
        {tab==="Library"&&<section className="card"><h2>Import relaxation experiment</h2>
          <p className="muted">Use the validated wide-format CSV/TXT/XLSX parser already in VitriFit v1. Select a project and sample first.</p>
          <div className="row"><input type="file" disabled={!sampleId} accept=".csv,.txt,.xlsx"
            onChange={e=>setUpload(e.target.files?.[0]||null)}/>
            <button className="primary" disabled={!sampleId||!upload||busy} onClick={importData}>Import & save</button></div>
          <div className="stats"><div><strong>{projects.length}</strong><small>Projects</small></div>
            <div><strong>{samples.length}</strong><small>Samples</small></div>
            <div><strong>{experiments.length}</strong><small>Experiments</small></div>
            <div><strong>{runs.length}</strong><small>Saved fits</small></div></div>
        </section>}
        {tab==="Preparation"&&<section className="card"><div className="card-head"><h2>Individual curve editor</h2><span className="tag">Non-destructive</span></div>
          {!curve?<p className="muted">Select a curve from the research library on the left.</p>:<>
            <div className="row compact"><label><input type="checkbox" checked={normalized} onChange={e=>setNormalized(e.target.checked)}/> Normalized modulus</label>
              <label><input type="checkbox" checked={timeLog} onChange={e=>setTimeLog(e.target.checked)}/> Log time</label></div>
            {graph(displayed,"Instrument time (s)",normalized?"G/G(ref)":"Modulus (MPa)",timeLog?"log":"linear","linear",selectedInterval,pointClicked)}
            <p className="hint">Drag a box on the graph or click two points to choose a region. The precise start and end can be edited below.</p>
            <div className="controls"><label className="field">Action<select value={trimMode} onChange={e=>setTrimMode(e.target.value)}>
              <option value="keep">Keep region</option><option value="exclude">Exclude region</option></select></label>
              <label className="field">Start (s)<input type="number" step="any" value={start} onChange={e=>setStart(Number(e.target.value))}/></label>
              <label className="field">End (s)<input type="number" step="any" value={end} onChange={e=>setEnd(Number(e.target.value))}/></label>
              <button className="primary" disabled={busy||end<=start} onClick={()=>editCurve("region")}>Apply</button>
              <button className="subtle" disabled={!curve.can_undo||busy} onClick={()=>editCurve("undo")}>↶ Undo</button>
              <button className="subtle" disabled={!curve.can_redo||busy} onClick={()=>editCurve("redo")}>↷ Redo</button>
            </div>
            <div className="bottom-note"><span>{curve.mask.filter(Boolean).length} / {curve.mask.length} points retained</span>
              <span>Revision {curve.active_revision_id.slice(0,9)}</span></div>
          </>}
        </section>}
        {tab==="Analysis"&&<section className="card"><h2>Relaxation fitting</h2>
          {!curve?<p className="muted">Choose a curve first.</p>:<>
            <div className="controls"><label className="field">Model<select value={model} onChange={e=>{
              setModel(e.target.value);setComponent(["Maxwell","Single_KWW"].includes(e.target.value)?"characteristic":"slow");
            }}>{["Single_KWW","Maxwell","Dual_KWW","Two-Maxwell (Prony)"].map(m=><option key={m}>{m}</option>)}</select></label>
              {["Dual_KWW","Two-Maxwell (Prony)"].includes(model)&&<label className="field">τ component<select value={component} onChange={e=>setComponent(e.target.value)}>
                <option value="fast">Fast</option><option value="slow">Slow</option></select></label>}
              <label className="field">Long-time plateau<select value={plateau} onChange={e=>setPlateau(e.target.value)}>
                <option>Zero</option><option>Fit</option><option>Fixed</option></select></label>
              {plateau==="Fixed"&&<label className="field">G∞ (MPa)<input type="number" step="any" value={fixedPlateau}
                onChange={e=>setFixedPlateau(Number(e.target.value))}/></label>}
              <button className="primary" disabled={busy} onClick={fitCurve}>Run & save</button></div>
            <p className="hint">The manually selected points go directly to the existing fitting engine; the old automatic trimming routine is not run again.</p>
            {fit?.results&&<><div className="stats"><div><strong>{Number(fit.results.tau_s).toPrecision(5)} s</strong><small>τ</small></div>
              <div><strong>{Number(fit.results.r2).toFixed(4)}</strong><small>R²</small></div>
              <div><strong>{fit.results.beta==null?"—":Number(fit.results.beta).toFixed(3)}</strong><small>β</small></div></div>
              {graph([{x:fit.results.fit_time_s,y:fit.results.fit_normalized_observed,mode:"markers",name:"Measured"},
                {x:fit.results.fit_time_s,y:fit.results.fit_normalized_prediction,mode:"lines",name:"Fit"}],
                "Instrument time (s)","G/G(ref)","log")}
              {(fit.results.flags||[]).map((f:string,i:number)=><p className="warning" key={i}>{f}</p>)}
            </>}
          </>}
        </section>}
        {tab==="Comparison"&&<section className="card"><h2>Cross-sample analysis</h2>
          <p className="muted">Select analyses from different experiments. Definitions of τ must agree. Stale fits are blocked.</p>
          <div className="run-list">{runs.map(r=><label key={r.id} className={"run-item "+(r.is_current?"":"stale")}>
            <input type="checkbox" checked={selectedRuns.includes(r.id)} onChange={e=>{
              setComparison(null);setSelectedRuns(a=>e.target.checked?[...a,r.id]:a.filter(x=>x!==r.id));}}/>
            <span><strong>{r.sample_name}</strong><small>{r.project_name} · {r.temperature_c}°C · {r.model}</small></span>
            <span className="run-tau">{r.results.tau_s?.toPrecision(4)} s {r.is_current?"":"⚠ stale"}</span>
          </label>)}{!runs.length&&<p className="muted">No saved analyses yet.</p>}</div>
          <div className="controls"><label className="field">Comparison<select value={compareMode} onChange={e=>{setCompareMode(e.target.value);setComparison(null);}}>
            <option value="kinetics">Kinetics (Arrhenius / VFT)</option><option value="fixed_temperature">τ at measured temperature</option><option value="curves">Relaxation overlay</option>
          </select></label>
            {compareMode==="kinetics"&&<label className="field">Kinetics<select value={kineticModel} onChange={e=>setKineticModel(e.target.value)}>
              <option>Arrhenius</option><option>VFT</option></select></label>}
            {compareMode==="fixed_temperature"&&<label className="field">Temperature (°C)<input type="number" value={temperature}
              onChange={e=>setTemperature(Number(e.target.value))}/></label>}
            <button className="primary" disabled={busy||selectedRuns.length<2} onClick={doComparison}>Compare</button>
            <button className="subtle" disabled={busy||!comparison} onClick={saveComparison}>Save comparison</button>
          </div>
          {comparisonGraph()}
          {comparison?.samples&&<table className="results"><thead><tr><th>Sample</th><th>Points</th><th>Ea (kJ/mol)</th><th>R²</th><th>Notes</th></tr></thead>
            <tbody>{comparison.samples.map((s:any)=><tr key={s.sample_id}>
              <td>{s.sample}</td><td>{s.observations.length}</td>
              <td>{s.Ea_kj_mol==null?"—":Number(s.Ea_kj_mol).toFixed(2)}</td>
              <td>{s.r2==null?"—":Number(s.r2).toFixed(4)}</td><td>{s.warning||"Fit available"}</td></tr>)}</tbody>
          </table>}
        </section>}
        {tab==="Figure Studio"&&<section className="card"><div className="card-head"><h2>Publication settings</h2><span className="tag">v1 standards protected</span></div>
          <p className="muted">This first version saves and restores publication style settings. Full figure rendering remains in the existing Publication tab until feature parity is verified.</p>
          <div className="controls"><label className="field">Saved preset<select defaultValue="" onChange={e=>{
            const preset=presets.find(p=>p.id===e.target.value);
            if(preset)setStyle({...initialStyle,...preset.settings});
          }}><option value="">Choose a saved style</option>{presets.map(p=><option value={p.id} key={p.id}>{p.name}</option>)}</select></label>
            <label className="field">Journal size<select value={String(style.pub_preset)} onChange={e=>{
              const p=e.target.value;setStyle(s=>({...s,pub_preset:p,pub_w:p.includes("Single")?8.5:p.includes("Double")?17:12.7,
                pub_h:p.includes("Single")?7.5:p.includes("Double")?14:10}));
            }}><option>ACS/RSC Single-Column (85 x 75 mm)</option><option>ACS/RSC Double-Column (170 x 140 mm)</option>
              <option>Custom</option></select></label>
            {numberStyle("pub_w","Width (cm)",0.1)}{numberStyle("pub_h","Height (cm)",0.1)}
            <label className="field">Font<select value={String(style.pub_relfont_family)} onChange={e=>setStyle(s=>({...s,pub_relfont_family:e.target.value}))}>
              {["Arial","Times New Roman","Courier New","DejaVu Sans"].map(s=><option key={s}>{s}</option>)}</select></label>
            {numberStyle("pub_rel_lbl_sz","Labels (pt)",1)}{numberStyle("pub_rel_num_sz","Ticks (pt)",1)}
            {numberStyle("pub_rel_lw","Line width (pt)")}
            <label className="field">Color space<select value={String(style.pub_colorspace)} onChange={e=>setStyle(s=>({...s,pub_colorspace:e.target.value}))}>
              <option>RGB</option><option>CMYK (for Print/Publication)</option></select></label>
          </div>
          <div className="row"><button className="primary" disabled={busy} onClick={savePreset}>Save style preset</button>
            <button className="subtle" disabled={!selectedRuns.length||busy} onClick={saveFigure}>Save figure project ({selectedRuns.length} analyses)</button></div>
          <p className="hint">Saving a style does not alter current v1 exports. Figure snapshots and presets are stored separately.</p>
        </section>}
        <footer>VitriFit 2.0 experimental local browser interface · built on the existing validated scientific core</footer>
      </main>
    </div>
  </div>;
}
