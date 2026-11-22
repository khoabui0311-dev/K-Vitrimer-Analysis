import { useEffect, useMemo, useState } from "react";
import Plot from "react-plotly.js";
import type { Data, Layout, PlotRelayoutEvent, Shape } from "plotly.js";
import SampleProfile from "./SampleProfile";
import RelaxationImport from "./RelaxationImport";
import SampleNotes from "./SampleNotes";
import { api, apiBlob, errorMessage } from "./api";

type Item = { id: string; name: string };
type Experiment = { id: string; original_filename: string; metadata?: {
  curve_quality?: {source_curve_id: string;temperature_c:number;warnings:string[]}[];
  import_warnings?: string[]; import_requires_review?: boolean; }; };
type CurveSummary = { id: string; temperature_c: number; source_curve_id: string };
type Curve = { curve_id: string; source_curve_id: string; temperature_c: number; time_s: number[];
  modulus_mpa: number[]; mask: boolean[]; active_revision_id: string; can_undo: boolean; can_redo: boolean };
type Run = { id: string; curve_id: string; project_name: string; sample_name: string; sample_id: string;
  temperature_c: number; original_filename: string; source_curve_id: string; model: string; tau_definition: string; is_current: boolean;
  results: { tau_s?: number; r2?: number; beta?: number; flags?: string[] } };
type Preset = { id: string; name: string; settings: Record<string, unknown> };
type Tab = "Library" | "Sample Profile" | "Notes" | "Preparation" | "Analysis" | "Comparison" | "Figure Studio";
const tabs: Tab[] = ["Library", "Sample Profile", "Preparation", "Analysis", "Comparison", "Figure Studio", "Notes"];
const initialStyle: Record<string, unknown> = {
  pub_preset: "ACS/RSC Single-Column (85 x 75 mm)", pub_w: 8.5, pub_h: 7.5,
  pub_relfont_family: "Arial", pub_rel_lbl_sz: 12, pub_rel_num_sz: 10,
  pub_rel_lw: 1.5, pub_rel_ms: 4, pub_xscale: "Log", pub_yscale: "Linear",
  pub_colorspace: "RGB", pub_relleg: true,
  // These are the exact persisted widget keys of v1 Publication Figures 3/4.
  eyr_lw: 1.5, eyr_ms: 6, eyr_ff: "Arial", eyr_lsz: 12,
  eyr_lwt: "normal", eyr_lst: "normal", eyr_nf: "Same as Label",
  eyr_nsz: 10, eyr_nwt: "normal", eyr_nst: "normal", eyr_mir: false,
  eyr_clim: false, eyr_leg: true, eyr_legpos: "Best (Auto)",
  eyr_legfont: 8, eyr_legncol: 1, eyr_legbox: false,
  vh_lw: 1.5, vh_ms: 6, vh_ff: "Arial", vh_lsz: 12,
  vh_lwt: "normal", vh_lst: "normal", vh_nf: "Same as Label",
  vh_nsz: 10, vh_nwt: "normal", vh_nst: "normal", vh_mir: false,
  vh_clim: false, vh_leg: true, vh_legpos: "Best (Auto)",
  vh_legfont: 8, vh_legncol: 1, vh_legbox: false, vh_yscale: "Linear",
  pl_3: "c", plx_3: -0.12, ply_3: 1.02,
  pl_4: "d", plx_4: -0.12, ply_4: 1.02
};
export default function App() {
  const [tab, setTab] = useState<Tab>("Library");
  const [projects, setProjects] = useState<Item[]>([]);
  const [projectId, setProjectId] = useState("");
  const [samples, setSamples] = useState<Item[]>([]);
  const [sampleId, setSampleId] = useState("");
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [experimentRefresh, setExperimentRefresh] = useState(0);
  const [experimentId, setExperimentId] = useState("");
  const [curves, setCurves] = useState<CurveSummary[]>([]);
  const [curveId, setCurveId] = useState("");
  const [curve, setCurve] = useState<Curve | null>(null);
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
  const [batchFits, setBatchFits] = useState<{curve: CurveSummary; id?: string; error?: string}[]>([]);
  const [selectedRuns, setSelectedRuns] = useState<string[]>([]);
  const [compareMode, setCompareMode] = useState("kinetics");
  const [figureKind, setFigureKind] = useState("curves");
  const [kineticModel, setKineticModel] = useState("Arrhenius");
  const [fitWindows, setFitWindows] = useState<Record<string, [number, number]>>({});
  const [savedComparisons, setSavedComparisons] = useState<Item[]>([]);
  const [activeComparisonId, setActiveComparisonId] = useState("");
  const [savedFigures, setSavedFigures] = useState<Item[]>([]);
  const [temperature, setTemperature] = useState(100);
  const [showExcluded, setShowExcluded] = useState(false);
  const [comparison, setComparison] = useState<any>(null);
  const [style, setStyle] = useState<Record<string, unknown>>({ ...initialStyle });
  const [activeFigureId, setActiveFigureId] = useState("");
  const [draftFigure, setDraftFigure] = useState<{url:string; key:string} | null>(null);
  const [exportFormat, setExportFormat] = useState("tiff");
  const [exportDpi, setExportDpi] = useState(1200);

  useEffect(()=>()=>{
    if (draftFigure) URL.revokeObjectURL(draftFigure.url);
  },[draftFigure]);

  const refreshProjects = () => api<Item[]>("/projects").then(setProjects);
  const refreshRuns = () => api<Run[]>("/analyses").then(setRuns);
  const refreshPresets = () => api<Preset[]>("/figures/presets").then(setPresets);
  const refreshComparisons = () => api<Item[]>("/comparisons").then(setSavedComparisons);
  const refreshFigures = () => api<Item[]>("/figures").then(setSavedFigures);
  useEffect(() => { Promise.all([refreshProjects(), refreshRuns(), refreshPresets(), refreshComparisons(), refreshFigures()]).catch(e => setError(errorMessage(e))); }, []);
  useEffect(() => {
    setSamples([]); setSampleId("");
    if (projectId) api<Item[]>("/projects/" + projectId + "/samples").then(setSamples).catch(e => setError(errorMessage(e)));
  }, [projectId]);
  useEffect(() => {
    setExperiments([]); setExperimentId("");
  }, [sampleId]);
  useEffect(() => {
    if (!sampleId) return;
    let current = true;
    api<Experiment[]>("/samples/" + sampleId + "/experiments").then(items=>{
      if (current) setExperiments(items);
    }).catch(e=>{ if (current) setError(errorMessage(e)); });
    return ()=>{ current = false; };
  }, [sampleId, experimentRefresh]);
  useEffect(() => {
    setCurves([]); setCurveId(""); setBatchFits([]);
    if (!experimentId) return;
    let current = true;
    api<CurveSummary[]>("/experiments/" + experimentId + "/curves").then(items=>{
      if (current) setCurves(items);
    }).catch(e=>{ if (current) setError(errorMessage(e)); });
    return ()=>{ current = false; };
  }, [experimentId]);
  useEffect(() => {
    setCurve(null); setFit(null); setClickAnchor(null);
    if (!curveId) return;
    let current = true;
    api<Curve>("/curves/" + curveId).then(data=>{
      if (current) { loadCurve(data); setTimeLog(!data.time_s.includes(0)); }
    }).catch(e=>{ if (current) setError(errorMessage(e)); });
    return ()=>{ current = false; };
  }, [curveId]);

  function loadCurve(c: Curve) {
    setCurve(c);
    const [low, high] = c.time_s.reduce(
      ([min, max], time)=>[Math.min(min,time),Math.max(max,time)], [Infinity,-Infinity]);
    setStart(low);
    setEnd(high);
    setClickAnchor(null);
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
  function graph(data: any[], xLabel: string, yLabel: string, xScale = "linear", yScale = "linear",
                 onSelect?: (event:any) => void, onClick?: (event:any) => void,
                 shapes?: Layout["shapes"], onRelayout?: (event:PlotRelayoutEvent)=>void) {
    return <Plot key={onSelect ? curveId+":"+xScale : undefined} data={data as any} layout={{
      autosize: true, height: 395, paper_bgcolor: "#fff", plot_bgcolor: "#fff",
      font: {family: "Arial, sans-serif", color: "#1e293b", size: 12},
      xaxis: {title: {text: xLabel}, type: xScale as any, gridcolor: "#e8eef5"},
      yaxis: {title: {text: yLabel}, type: yScale as any, gridcolor: "#e8eef5"},
      margin: {l: 76, r: 24, t: 25, b: 64}, dragmode: onSelect?"select":"zoom",
      selectdirection: "h", shapes, uirevision:onSelect?curveId+":"+xScale:undefined,
      legend: {orientation:"h", y:1.18, x:0}
    }} config={{responsive:true, displaylogo:false, scrollZoom:true}}
    style={{width:"100%"}} useResizeHandler onSelected={onSelect} onClick={onClick} onRelayout={onRelayout}/>;
  }
  const trimShapes: (Partial<Shape> & {editable: boolean})[] = [];
  const trimHandles: ("start"|"end"|null)[] = [];
  const showBoundary = (time: number)=>Number.isFinite(time)&&(!timeLog||time>0);
  if (start<end && showBoundary(start) && showBoundary(end)) {
    trimShapes.push({type:"rect",xref:"x",yref:"paper",x0:start,x1:end,y0:0,y1:1,
      fillcolor:trimMode==="keep"?"rgba(37,99,235,.09)":"rgba(218,113,63,.13)",
      line:{width:0},layer:"below",editable:false});
    trimHandles.push(null);
  }
  for (const [boundary, time] of [["start",start],["end",end]] as const) {
    if (showBoundary(time)) {
      trimShapes.push({type:"line",xref:"x",yref:"paper",x0:time,x1:time,y0:0,y1:1,
        line:{color:boundary==="start"?"#2563eb":"#b45309",width:3,dash:"dash"},editable:true});
      trimHandles.push(boundary);
    }
  }
  function moveTrimHandle(event: PlotRelayoutEvent) {
    const changes = event as Record<string, unknown>;
    trimHandles.forEach((boundary,index)=>{
      if (!boundary) return;
      const time = changes[`shapes[${index}].x0`] ?? changes[`shapes[${index}].x1`];
      if (typeof time !== "number" || !Number.isFinite(time)) return;
      setClickAnchor(null);
      if (boundary==="start") setStart(Math.min(end,Math.max(0,time)));
      else setEnd(Math.max(start,time));
    });
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
      loadCurve(mode === "region" ? data.curve : data);
      setBatchFits([]);
      setFit(null);
      setComparison(null);
      await refreshRuns();
    });
  }
  async function suggestTrim() {
    if (!curveId) return;
    await run(async () => {
      const proposal = await api<{start_s:number,end_s:number}>("/curves/" + curveId + "/suggest-trim");
      setStart(proposal.start_s); setEnd(proposal.end_s); setTrimMode("keep");
    });
  }
  const fitSettings = {model,plateau_mode:plateau,fixed_plateau_mpa:fixedPlateau,component};
  const comparisonKey = JSON.stringify([selectedRuns,compareMode,temperature,kineticModel,fitWindows]);
  const [shownComparisonKey, setShownComparisonKey] = useState("");
  const comparisonIsCurrent = Boolean(comparison && shownComparisonKey===comparisonKey);

  async function fitExperiment() {
    setBatchFits([]);
    await run(async ()=>{
      for (const item of curves) {
        try {
          const result = await api<{run_id:string}>("/curves/"+item.id+"/fit","POST",fitSettings);
          setBatchFits(previous=>[...previous,{curve:item,id:result.run_id}]);
        } catch (error) {
          setBatchFits(previous=>[...previous,{curve:item,error:errorMessage(error)}]);
        }
      }
      await refreshRuns();
    });
  }
  async function fitCurve() {
    if (!curveId) return;
    await run(async () => {
      const result = await api<any>("/curves/" + curveId + "/fit", "POST",
        fitSettings);
      setFit(result); await refreshRuns();
    });
  }
  async function doComparison() {
    if (selectedRuns.length < 2) return;
    await run(async () => {
      setComparison(await api("/compare","POST",
        {run_ids:selectedRuns, mode:compareMode, temperature_c:temperature, kinetic_model:kineticModel, windows:fitWindows}));
      setShownComparisonKey(comparisonKey);
    });
  }
  async function saveComparison() {
    if (!comparisonIsCurrent) return;
    const name=window.prompt("Name this comparison","Cross-sample comparison"); if(!name?.trim()) return;
    await run(async () => {const saved = await api<{id:string}>("/comparisons","POST",
      {name,run_ids:selectedRuns,mode:compareMode,settings:{temperature_c:temperature,kinetic_model:kineticModel,windows:fitWindows}});
      setActiveComparisonId(saved.id);
      await refreshComparisons();});
  }
  async function savePreset() {
    const name=window.prompt("Name this figure style","ACS/RSC style"); if(!name?.trim()) return;
    await run(async () => {await api("/figures/presets","POST",{name,settings:style}); await refreshPresets();});
  }
  const figureSettings = {
    run_ids:selectedRuns,
    composition:{plot_type:figureKind,kinetic_model:kineticModel,
      temperature_c:temperature,windows:fitWindows},
    overrides:style,
  };
  const figureKey = JSON.stringify(figureSettings);

  async function previewFigure() {
    await run(async()=>{
      const blob = await apiBlob("/figures/preview","POST",figureSettings);
      setDraftFigure({url:URL.createObjectURL(blob),key:figureKey});
    });
  }

  async function saveFigure() {
    if (!selectedRuns.length) return;
    const name = window.prompt("Name this figure project","Publication figure");
    if (!name?.trim()) return;
    await run(async()=>{
      const created = await api<{id:string}>("/figures","POST",{name,...figureSettings});
      setDraftFigure(null);
      setActiveFigureId(created.id);
      await refreshFigures();
    });
  }
  async function reopenComparison(id:string) {
    if (!id) return;
    await run(async () => {
      const saved:any = await api("/comparisons/" + id);
      setActiveComparisonId(id);
      setSelectedRuns(saved.run_ids); setCompareMode(saved.mode);
      setTemperature(Number(saved.settings.temperature_c ?? 100));
      setKineticModel(saved.settings.kinetic_model || "Arrhenius");
      setFitWindows(saved.settings.windows || {});
      setComparison(null);
      setShownComparisonKey(JSON.stringify([
        saved.run_ids,saved.mode,Number(saved.settings.temperature_c ?? 100),
        saved.settings.kinetic_model || "Arrhenius",saved.settings.windows || {},
      ]));
      setComparison(await api("/compare","POST",{
        run_ids:saved.run_ids,mode:saved.mode,temperature_c:saved.settings.temperature_c,
        kinetic_model:saved.settings.kinetic_model || "Arrhenius",
        windows:saved.settings.windows || {}
      }));
    });
  }
  async function reopenFigure(id:string) {
    if (!id) return;
    await run(async () => {
      const saved:any = await api("/figures/" + id);
      setSelectedRuns(saved.run_ids);
      setStyle({...initialStyle,...saved.overrides});
      setFigureKind(saved.composition.plot_type || "curves");
      setTemperature(Number(saved.composition.temperature_c ?? 100));
      setKineticModel(saved.composition.kinetic_model || "Arrhenius");
      setFitWindows(saved.composition.windows || {});
      setDraftFigure(null);
      setActiveFigureId(id);
    });
  }
  async function exportFigure() {
    if (!activeFigureId) return;
    await run(async () => {
      const query = new URLSearchParams({fmt:exportFormat,dpi:String(exportDpi)});
      const response = await fetch("/api/figures/"+activeFigureId+"/export?"+query);
      if(!response.ok) {
        const detail = await response.json();
        throw new Error(detail.detail || "Publication export failed");
      }
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = "VitriFit_Figure_"+activeFigureId.slice(0,8)+
                      "."+(exportFormat==="jpeg"?"jpg":exportFormat);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(()=>URL.revokeObjectURL(objectUrl),1000);
    });
  }
  function comparisonGraph() {
    if (!comparisonIsCurrent) return <p className="muted">Select at least two saved analyses and run the comparison.</p>;
    if (comparison.mode==="curves") {
      const colors = ["#2563eb","#b45309","#0f766e","#7c3aed","#be185d","#475569"];
      const traces = comparison.curves.flatMap((row:any,index:number)=>{
        const name = `${row.sample} · ${row.original_filename} · ${row.source_curve_id} · ${row.temperature_c} °C`;
        const color = colors[index % colors.length];
        const shared = {type:"scattergl" as const,legendgroup:row.run_id};
        const series: Data[] = [{...shared,name:name+" · Retained",x:row.time_s,y:row.normalized_modulus,
          mode:"markers",marker:{color,size:5}}];
        if (row.fit_time_s?.length) series.push({
          ...shared,name:name+" · Fit",x:row.fit_time_s,y:row.fit_normalized_prediction,
          mode:"lines",line:{color,width:2},showlegend:false,
        });
        if (showExcluded&&row.excluded_time_s.length) series.push({
          ...shared,name:name+" · Excluded",x:row.excluded_time_s,y:row.excluded_normalized_modulus,
          mode:"markers",marker:{color,size:6,symbol:"x",opacity:.55},showlegend:false,
        });
        return series;
      });
      const hasZero = comparison.curves.some((row:any)=>row.time_s.includes(0)||
        (showExcluded&&row.excluded_time_s.includes(0)));
      return graph(traces,"Instrument time (s)","G/G(ref)",hasZero?"linear":"log");
    }
    if (comparison.mode === "fixed_temperature") return graph([{
      x:comparison.rows.map((r:any)=>r.sample), y:comparison.rows.map((r:any)=>r.tau_s),
      type:"bar",marker:{color:"#2563eb"}
    }],"Sample","Relaxation time τ (s)","linear","log");
    const traces:any[]=[];
    comparison.samples.forEach((r:any)=>{
      const x=r.observations.map((a:any)=>1000/(a.temperature_c+273.15));
      const y=r.observations.map((a:any)=>Math.log(a.tau_s));
      traces.push({x,y,type:"scatter",mode:"markers",name:r.sample});
      if (r.fitted_curve?.x_1000_per_k?.length && r.fitted_curve?.ln_tau?.length) {
        traces.push({x:r.fitted_curve.x_1000_per_k,y:r.fitted_curve.ln_tau,
          type:"scatter",mode:"lines",showlegend:false,name:r.sample+" fit"});
      }
    });
    return graph(traces,"1000/T (K⁻¹)","ln(τ / s)");
  }
  function advancedStyleNumber(key:string,label:string,defaultValue:number,step=0.5) {
    return <label className="field">{label}
      <input type="number" step={step} value={Number(style[key] ?? defaultValue)}
        onChange={e=>setStyle(s=>({...s,[key]:Number(e.target.value)}))}/>
    </label>;
  }
  function advancedStyleSelect(key:string,label:string,values:string[],defaultValue:string) {
    return <label className="field">{label}
      <select aria-label={label} value={String(style[key] ?? defaultValue)}
        onChange={e=>setStyle(s=>({...s,[key]:e.target.value}))}>
        {values.map(v=><option value={v} key={v}>{v}</option>)}
      </select>
    </label>;
  }
  function advancedStyleToggle(key:string,label:string,defaultValue=false) {
    return <label className="figure-check"><input type="checkbox"
      checked={Boolean(style[key] ?? defaultValue)}
      onChange={e=>setStyle(s=>({...s,[key]:e.target.checked}))}/>
      {label}</label>;
  }
  function kineticWindowEditor() {
    return <div className="window-editor">
      <p className="small-heading">Independent temperature windows (°C)</p>
      {Array.from(new Map<string,Run>(runs.filter(r=>selectedRuns.includes(r.id))
          .map(r=>[r.sample_id,r] as [string,Run])).values()).map(r=>{
        const grouped=runs.filter(x=>x.sample_id===r.sample_id&&selectedRuns.includes(x.id));
        const low=Math.min(...grouped.map(x=>x.temperature_c));
        const high=Math.max(...grouped.map(x=>x.temperature_c));
        const bounds=fitWindows[r.sample_id]||[low,high];
        return <div className="window-row" key={r.sample_id}>
          <span>{r.sample_name}</span>
          <input type="number" value={bounds[0]} aria-label={r.sample_name+" minimum"}
            onChange={e=>setFitWindows(s=>({...s,[r.sample_id]:[Number(e.target.value),bounds[1]]}))}/>
          <span>to</span>
          <input type="number" value={bounds[1]} aria-label={r.sample_name+" maximum"}
            onChange={e=>setFitWindows(s=>({...s,[r.sample_id]:[bounds[0],Number(e.target.value)]}))}/>
          <button className="subtle" onClick={()=>setFitWindows(s=>{
            const next={...s};delete next[r.sample_id];return next;
          })}>Reset</button>
        </div>;
      })}
    </div>;
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
        <label className="field">Project<select aria-label="Project" value={projectId} disabled={busy} onChange={e=>setProjectId(e.target.value)}>
          <option value="">Choose project</option>{projects.map(p=><option value={p.id} key={p.id}>{p.name}</option>)}
        </select></label>
        <button className="subtle" disabled={busy} onClick={addProject}>+ Create project</button>
        <label className="field">Sample<select aria-label="Sample" value={sampleId} disabled={busy||!projectId} onChange={e=>setSampleId(e.target.value)}>
          <option value="">Choose sample</option>{samples.map(s=><option value={s.id} key={s.id}>{s.name}</option>)}
        </select></label>
        <button className="subtle" disabled={busy||!projectId} onClick={addSample}>+ Add sample</button>
        <label className="field">Experiment<select aria-label="Experiment" value={experimentId} disabled={busy||!sampleId} onChange={e=>setExperimentId(e.target.value)}>
          <option value="">Choose experiment</option>{experiments.map(e=><option value={e.id} key={e.id}>{e.original_filename}</option>)}
        </select></label>
        <label className="field">Curve<select aria-label="Curve" value={curveId} disabled={busy||!experimentId} onChange={e=>setCurveId(e.target.value)}>
          <option value="">Choose curve</option>{curves.map(c=><option value={c.id} key={c.id}>{c.temperature_c}°C · {c.source_curve_id}</option>)}
        </select></label>
        <p className="sidebar-hint">Your original file, processing revisions, fits and figure configurations are saved locally.</p>
      </aside>

      <main className="main">
        <p className="eyebrow">SCIENTIFIC DATA WORKSPACE</p><h1>{tab}</h1>
        <p className="lead">{tab==="Library"?"Manage persistent scientific records":
          tab==="Sample Profile"?"Specimen-centred DMA, DSC, rheology and tensile records with traceable raw data":
          tab==="Notes"?"Record specimen history and analysis decisions":
          tab==="Preparation"?"Edit individual relaxation curves without deleting raw measurements":
          tab==="Analysis"?"Fit individual curves or entire experiments and preserve each analysis revision":
          tab==="Comparison"?"Compare samples at matching temperatures and across kinetic windows":
          "Save publication styles without changing the original v1 rendering standards"}</p>
        {error&&<div className="error"><strong>Action failed:</strong> {error}<button onClick={()=>setError("")}>×</button></div>}
        {busy&&<p className="loading">Processing…</p>}
        {tab==="Sample Profile"&&<SampleProfile key={sampleId} sampleId={sampleId}/>}
        <div hidden={tab!=="Notes"}><SampleNotes sampleId={sampleId}/></div>
        <section hidden={tab!=="Library"} className="card"><h2>Import relaxation experiments</h2>
          <RelaxationImport key={projectId} samples={samples} defaultSampleId={sampleId}
            onSaved={()=>setExperimentRefresh(count=>count+1)}/>
          <p className="hint"><a href="/api/backup" download>Download complete local-library backup (SQLite + original uploads)</a></p>
          <div className="stats"><div><strong>{projects.length}</strong><small>Projects</small></div>
            <div><strong>{samples.length}</strong><small>Samples</small></div>
            <div><strong>{experiments.length}</strong><small>Experiments</small></div>
            <div><strong>{runs.length}</strong><small>Saved fits</small></div></div>
        </section>
        {tab==="Preparation"&&<section className="card"><div className="card-head"><h2>Individual curve editor</h2><span className="tag">Non-destructive</span></div>
          {!curve?<p className="muted">Select a curve from the research library on the left.</p>:<>
            {(()=>{
              const imported=experiments.find(e=>e.id===experimentId);
              const quality=imported?.metadata?.curve_quality?.find(q=>q.source_curve_id===curve.source_curve_id);
              return quality?.warnings?.length?<div className="import-warnings">
                <strong>Original-file data-quality warnings for this curve</strong>
                <ul>{quality.warnings.map((w,i)=><li key={i}>{w}</li>)}</ul>
                <p className="hint">These are historical import observations. Trimming or excluding points does not overwrite the original instrument record.</p>
              </div>:null;
            })()}
            <div className="row compact"><label><input type="checkbox" checked={normalized} onChange={e=>setNormalized(e.target.checked)}/> Normalized modulus</label>
              <label><input type="checkbox" checked={timeLog} onChange={e=>setTimeLog(e.target.checked)}/> Log time</label></div>
            {graph(displayed,"Instrument time (s)",normalized?"G/G(ref)":"Modulus (MPa)",timeLog?"log":"linear","linear",selectedInterval,pointClicked,trimShapes,moveTrimHandle)}
            <p className="hint">Brush across the graph or click two points to select a time interval. Click a dashed boundary to activate it, then drag it to refine the interval before applying.</p>
            <div className="controls"><label className="field">Action<select value={trimMode} onChange={e=>setTrimMode(e.target.value)}>
              <option value="keep">Keep region</option><option value="exclude">Exclude region</option></select></label>
              <label className="field">Start (s)<input type="number" step="any" value={start} onChange={e=>setStart(Number(e.target.value))}/></label>
              <label className="field">End (s)<input type="number" step="any" value={end} onChange={e=>setEnd(Number(e.target.value))}/></label>
              <button className="subtle" disabled={busy} onClick={suggestTrim}>Suggest auto trim</button>
              <button className="primary" disabled={busy||end<start||clickAnchor!==null} onClick={()=>editCurve("region")}>Apply</button>
              <button className="subtle" disabled={!curve.can_undo||busy} onClick={()=>editCurve("undo")}>↶ Undo</button>
              <button className="subtle" disabled={!curve.can_redo||busy} onClick={()=>editCurve("redo")}>↷ Redo</button>
            </div>
            <div className="bottom-note"><span>{curve.mask.filter(Boolean).length} / {curve.mask.length} points retained</span>
              <span>Proposed edit retains {curve.time_s.filter((time,index)=>{
                const inside = time>=start&&time<=end;
                return curve.mask[index]&&(trimMode==="keep"?inside:!inside);
              }).length} points</span>
              <span>Revision {curve.active_revision_id.slice(0,9)}</span></div>
          </>}
        </section>}
        {tab==="Analysis"&&<section className="card"><h2>Relaxation fitting</h2>
          {!experimentId?<p className="muted">Choose an experiment first.</p>:<>
            <div className="controls"><label className="field">Model<select value={model} onChange={e=>{
              setModel(e.target.value);setComponent(["Maxwell","Single_KWW"].includes(e.target.value)?"characteristic":"slow");
            }}>{["Single_KWW","Maxwell","Dual_KWW","Two-Maxwell (Prony)"].map(m=><option key={m}>{m}</option>)}</select></label>
              {["Dual_KWW","Two-Maxwell (Prony)"].includes(model)&&<label className="field">τ component<select value={component} onChange={e=>setComponent(e.target.value)}>
                <option value="fast">Fast</option><option value="slow">Slow</option></select></label>}
              <label className="field">Long-time plateau<select value={plateau} onChange={e=>setPlateau(e.target.value)}>
                <option>Zero</option><option>Fit</option><option>Fixed</option></select></label>
              {plateau==="Fixed"&&<label className="field">G∞ (MPa)<input type="number" step="any" value={fixedPlateau}
                onChange={e=>setFixedPlateau(Number(e.target.value))}/></label>}
              <button className="primary" disabled={busy||!curve} onClick={fitCurve}>Fit this curve</button>
              <button className="subtle" disabled={busy||curves.length<2} onClick={fitExperiment}>Fit all {curves.length} curves in experiment</button>
            </div>
            {batchFits.length>0&&<div>
              <p role="status">{batchFits.filter(item=>!item.error).length} fits saved · {batchFits.filter(item=>item.error).length} failed</p>
              {batchFits.filter(item=>item.error).map(item=><p className="warning" key={item.curve.id}>
                {item.curve.temperature_c} °C · {item.curve.source_curve_id} — {item.error}
              </p>)}
              <button className="subtle" disabled={busy||batchFits.every(item=>!item.id)} onClick={()=>{
                setSelectedRuns(batchFits.flatMap(item=>item.id?[item.id]:[]));
                setComparison(null);
                setActiveComparisonId("");
                setTab("Comparison");
              }}>Select these fits in Comparison</button>
            </div>}
            {curve&&<label className="field" style={{maxWidth:380}}>Reopen saved analysis for this curve
              <select key={curve.active_revision_id} defaultValue="" onChange={e=>{
                const existing=runs.find(r=>r.id===e.target.value);
                setFit(existing ?? null);
              }}><option value="">Select saved fit</option>
                {runs.filter(r=>r.curve_id===curveId).map(r=>
                  <option key={r.id} value={r.id}>{r.model} · τ {r.results.tau_s?.toPrecision(4)} s {r.is_current?"":"(stale)"}</option>)}
              </select>
            </label>}
            <p className="hint">The manually selected points go directly to the existing fitting engine; the old automatic trimming routine is not run again.</p>
            {fit?.results&&<>{fit.is_current===false&&<p className="warning">Historical fit from an earlier trim revision.</p>}
              <div className="stats"><div><strong>{Number(fit.results.tau_s).toPrecision(5)} s</strong><small>τ</small></div>
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
          <label className="field" style={{maxWidth:360}}>Reopen saved comparison
            <select value={activeComparisonId} onChange={e=>reopenComparison(e.target.value)}>
              <option value="">Choose comparison</option>
              {savedComparisons.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </label>
          {activeComparisonId && <p><a href={"/api/comparisons/" + encodeURIComponent(activeComparisonId) + "/export.csv"} download="vitrifit-comparison.csv">Download saved comparison CSV (includes revision provenance)</a></p>}
          <div className="run-list">{runs.map(r=><label key={r.id} className={"run-item "+(r.is_current?"":"stale")}>
            <input type="checkbox" checked={selectedRuns.includes(r.id)} onChange={e=>{
              setComparison(null);setSelectedRuns(a=>e.target.checked?[...a,r.id]:a.filter(x=>x!==r.id));}}/>
            <span><strong>{r.sample_name}</strong><small>{r.project_name} · {r.original_filename} · {r.source_curve_id} · {r.temperature_c}°C · {r.model}</small></span>
            <span className="run-tau">{r.results.tau_s?.toPrecision(4)} s {r.is_current?"":"⚠ stale"}</span>
          </label>)}{!runs.length&&<p className="muted">No saved analyses yet.</p>}</div>
          <div className="controls"><label className="field">Comparison<select aria-label="Comparison" value={compareMode} onChange={e=>{setCompareMode(e.target.value);setComparison(null);}}>
            <option value="kinetics">Kinetics (Arrhenius / VFT)</option><option value="fixed_temperature">τ at measured temperature</option><option value="curves">Relaxation overlay</option>
          </select></label>
            {compareMode==="kinetics"&&<label className="field">Kinetics<select value={kineticModel} onChange={e=>setKineticModel(e.target.value)}>
              <option>Arrhenius</option><option>VFT</option></select></label>}
            {compareMode==="fixed_temperature"&&<label className="field">Temperature (°C)<input type="number" value={temperature}
              onChange={e=>setTemperature(Number(e.target.value))}/></label>}
            <button className="primary" disabled={busy||selectedRuns.length<2} onClick={doComparison}>Compare</button>
            <button className="subtle" disabled={busy||!comparisonIsCurrent} onClick={saveComparison}>Save comparison</button>
          </div>
          {compareMode==="kinetics"&&selectedRuns.length>0&&kineticWindowEditor()}
          {comparisonIsCurrent&&comparison?.mode==="curves"&&<label>
            <input type="checkbox" checked={showExcluded} onChange={e=>setShowExcluded(e.target.checked)}/>
            Show excluded observations
          </label>}
          {comparisonGraph()}
          {comparisonIsCurrent&&comparison?.samples&&<table className="results"><thead>
            <tr><th>Sample</th><th>Temperatures</th><th>Points</th>
              {kineticModel==="VFT"?<><th>A</th><th>B (K)</th><th>T₀ (K)</th></>:
                <><th>Ea (kJ/mol)</th><th>Ea 95% CI (kJ/mol)</th></>}
              <th>R²</th><th>Notes</th></tr></thead>
            <tbody>{comparison.samples.map((s:any)=><tr key={s.sample_id}>
              <td>{s.sample}</td><td>{s.n_distinct_temperatures}</td><td>{s.observations.length}</td>
              {kineticModel==="VFT"?["A","B","T0"].map(parameter=>
                <td key={parameter}>{s.parameters?.[parameter]?.toPrecision(4)??"—"}</td>):
                <><td>{s.Ea_kj_mol?.toFixed(2)??"—"}</td>
                  <td>{s.Ea_ci95_kj_mol?.map((value:number)=>value.toFixed(2)).join(" to ")??"—"}</td></>}
              <td>{s.r2?.toFixed(4)??"—"}</td><td>{s.warning||"Fit available"}</td></tr>)}</tbody>
          </table>}
        </section>}
        {tab==="Figure Studio"&&<section className="card"><div className="card-head"><h2>Publication settings</h2><span className="tag">v1 standards protected</span></div>
          <p className="muted">Select saved analyses, preview your settings, and save a figure to export with its source revisions.</p>
          <label className="field" style={{maxWidth:360}}>Reopen figure project
            <select aria-label="Reopen figure project" value={activeFigureId} onChange={e=>{
              if (e.target.value) void reopenFigure(e.target.value);
              else setActiveFigureId("");
            }}><option value="">Choose saved figure</option>
              {savedFigures.map(f=><option key={f.id} value={f.id}>{f.name}</option>)}
            </select>
          </label>
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
          <div className="controls"><label className="field">Figure content
            <select aria-label="Figure content" value={figureKind} onChange={e=>setFigureKind(e.target.value)}>
              <option value="curves">Relaxation curves</option>
              <option value="kinetics">Arrhenius / VFT kinetics</option>
              <option value="eyring">Eyring activation kinetics (Fig. 3)</option>
              <option value="van_t_hoff">Observed G₀ — empirical Van 't Hoff (Fig. 4)</option>
              <option value="fixed_temperature">τ at measured temperature</option>
            </select></label>
            {figureKind==="kinetics"&&<label className="field">Kinetic model
              <select value={kineticModel} onChange={e=>setKineticModel(e.target.value)}>
                <option>Arrhenius</option><option>VFT</option>
              </select></label>}
            {figureKind==="fixed_temperature"&&<label className="field">Measured temperature (°C)
              <input type="number" value={temperature} onChange={e=>setTemperature(Number(e.target.value))}/>
              </label>}
          </div>

          {figureKind==="curves"&&<div className="controls">
            {advancedStyleSelect("pub_xscale","Time axis",["Linear","Log"],"Log")}
            {advancedStyleSelect("pub_yscale","Modulus axis",["Linear","Log"],"Linear")}
            {advancedStyleToggle("pub_relleg","Show legend",true)}
          </div>}
          {(figureKind==="kinetics"||figureKind==="eyring"||figureKind==="van_t_hoff")&&selectedRuns.length>0&&
            kineticWindowEditor()}
          {(figureKind==="eyring"||figureKind==="van_t_hoff")&&(()=>{
            const p=figureKind==="eyring"?"eyr":"vh";
            const panel=figureKind==="eyring"?3:4;
            return <div className="advanced-figure-controls">
              <h3>{figureKind==="eyring"?"Eyring (Figure 3)":"Empirical Van 't Hoff (Figure 4)"} — v1 publication formatting</h3>
              <p className="hint">{figureKind==="eyring"?
                "ln(τ·T) versus 1000/T. Apparent activation parameters assume that τ is proportional to an inverse rate.":
                "Observed reference modulus G₀ versus 1000/T. This is an empirical trend, not independent evidence of equilibrium network dissociation."}</p>
              <div className="controls">
                {advancedStyleNumber(p+"_lw","Fit line width (pt)",1.5)}
                {advancedStyleNumber(p+"_ms","Marker size (pt)",6,1)}
                {advancedStyleSelect(p+"_ff","Font family",
                  ["Arial","Times New Roman","Courier New","DejaVu Sans"],"Arial")}
                {advancedStyleNumber(p+"_lsz","Label size (pt)",12,1)}
                {advancedStyleSelect(p+"_lwt","Label weight",["normal","bold"],"normal")}
                {advancedStyleSelect(p+"_lst","Label style",["normal","italic"],"normal")}
                {advancedStyleSelect(p+"_nf","Tick font",
                  ["Same as Label","Arial","Times New Roman"],"Same as Label")}
                {advancedStyleNumber(p+"_nsz","Tick size (pt)",10,1)}
                {advancedStyleSelect(p+"_nwt","Tick weight",["normal","bold"],"normal")}
                {advancedStyleSelect(p+"_nst","Tick style",["normal","italic"],"normal")}
                {advancedStyleToggle(p+"_mir","Mirror ticks")}
                {figureKind==="van_t_hoff"&&advancedStyleSelect("vh_yscale","Modulus scale",
                  ["Linear","Log"],"Linear")}
              </div>
              <div className="controls">
                {advancedStyleToggle(p+"_leg","Show legend",true)}
                {Boolean(style[p+"_leg"]??true)&&<>
                  {advancedStyleSelect(p+"_legpos","Legend position",
                    ["Best (Auto)","Upper Right","Upper Left","Lower Left",
                     "Lower Right","Right (Outside)"],"Best (Auto)")}
                  {advancedStyleNumber(p+"_legfont","Legend font (pt)",8,1)}
                  {advancedStyleNumber(p+"_legncol","Legend columns",1,1)}
                  {advancedStyleToggle(p+"_legbox","Legend box")}
                </>}
                {advancedStyleToggle(p+"_clim","Manual axis limits")}
                {Boolean(style[p+"_clim"])&&<>
                  {advancedStyleNumber(p+"_xmin","X min",0,.1)}
                  {advancedStyleNumber(p+"_xmax","X max",5,.1)}
                  {advancedStyleNumber(p+"_ymin","Y min",0,.1)}
                  {advancedStyleNumber(p+"_ymax","Y max",1,.1)}
                </>}
              </div>
              <div className="controls">
                <label className="field">Panel letter<input type="text" maxLength={3}
                  value={String(style["pl_"+panel]??(panel===3?"c":"d"))}
                  onChange={e=>setStyle(s=>({...s,["pl_"+panel]:e.target.value}))}/></label>
                {advancedStyleNumber("plx_"+panel,"Panel letter X",-0.12,.01)}
                {advancedStyleNumber("ply_"+panel,"Panel letter Y",1.02,.01)}
              </div>
            </div>;
          })()}
          <div className="row">
            <button className="primary" disabled={!selectedRuns.length||busy} onClick={previewFigure}>Preview current settings</button>
            <button className="subtle" disabled={busy} onClick={savePreset}>Save style preset</button>
            <button className="subtle" disabled={!selectedRuns.length||busy} onClick={saveFigure}>Save figure project ({selectedRuns.length} analyses)</button>
          </div>
          {draftFigure&&<div className="saved-figure-preview">
            <h3>Draft figure preview</h3>
            {draftFigure.key===figureKey?<img alt="Draft publication figure" src={draftFigure.url}/>:
              <p className="hint">Settings changed. Preview again to see the updated figure.</p>}
            {String(style.pub_colorspace).startsWith("CMYK")&&<p className="hint">
              The browser preview uses RGB. TIFF, JPEG, and PDF exports use the saved CMYK setting.
            </p>}
          </div>}
          {activeFigureId&&<div className="saved-figure-preview">
            <h3>Saved-figure preview</h3>
            <p className="hint">This preview comes from the saved source-analysis revisions and stored figure settings. To use new controls, save a new figure project.</p>
            <img alt="Saved publication figure" loading="lazy"
              src={"/api/figures/"+activeFigureId+"/export?fmt=svg&dpi=300&inline=true"}/>
          </div>}
          <div className="export-panel">
            <h3>Export saved figure</h3>
            <p className="hint">Saved figures use the exact processing revision of each analysis, even if you later trim the source data. Journal dimensions, typefaces and export conversion follow the existing Publication implementation.</p>
            <div className="controls">
              <label className="field">Format<select aria-label="Format" value={exportFormat} onChange={e=>{setExportFormat(e.target.value);setExportDpi(e.target.value==="tiff"?1200:e.target.value==="jpeg"?600:300);}}>
                <option value="tiff">TIFF (publication)</option>
                <option value="jpeg">JPEG</option>
                <option value="pdf">PDF</option>
                <option value="svg">SVG</option>
                <option value="png">PNG</option>
              </select></label>
              <label className="field">Resolution<select value={exportDpi} onChange={e=>setExportDpi(Number(e.target.value))}>
                <option value={300}>300 DPI</option>
                <option value={600}>600 DPI</option>
                <option value={1200}>1200 DPI</option>
              </select></label>
              <button className="primary" disabled={!activeFigureId||busy} onClick={exportFigure}>
                Download figure
              </button>
            </div>
            {!activeFigureId&&<p className="muted">Save or reopen a figure project to enable export.</p>}
            <p className="hint">Default TIFF resolution is 1200 DPI and JPEG is 600 DPI, matching v1. The existing 40-megapixel limit still applies. CMYK is supported for TIFF/JPEG/PDF, RGB for PNG/SVG. Eyring and Van 't Hoff now export from saved analyses; visual parity and advanced controls still require further qualification.</p>
          </div>
          <p className="hint">Saving a style does not alter current v1 exports. Figure snapshots and presets are stored separately.</p>
        </section>}
        <footer>VitriFit 2.0 experimental local browser interface · built on the existing validated scientific core</footer>
      </main>
    </div>
  </div>;
}
