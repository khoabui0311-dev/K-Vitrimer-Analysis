import { useEffect, useState } from "react";
import Plot from "react-plotly.js";
import { api, errorMessage } from "./api";

type Measurement = {measurement_id:string;specimen_id:string;technique:string;method:string;
  conditions:Record<string,unknown>;files:{file_id:string;filename:string;sha256:string}[]};
type Specimen = {specimen_id:string;label:string;metadata:Record<string,unknown>;measurements:Measurement[]};
type Profile = {sample_id:string;name:string;specimens:Specimen[];
  techniques:Record<string,Measurement[]>};
type Analysis = {analysis_id:string;measurement_id:string;file_id:string;method:string;
  source_sha256:string;algorithm_version:string;config:Record<string,any>;
  results:Record<string,any>};

const request = <T,>(url: string, method = "GET", body?: unknown) =>
  api<T>("/v2"+url,method,body);

const columnFields: Record<string, {key:string; label:string; example:string}[]> = {
  temperature_ramp: [
    {key:"temperature_c",label:"Temperature (°C)",example:"T"},
    {key:"storage_modulus",label:"Storage modulus E′",example:"Ep"},
    {key:"loss_modulus",label:"Loss modulus E″",example:"Epp"},
  ],
  calorimetry: [
    {key:"temperature_c",label:"Temperature (°C)",example:"T"},
    {key:"heat_flow",label:"Heat flow",example:"heat"},
  ],
  tensile_test: [
    {key:"displacement_mm",label:"Displacement (mm)",example:"extension"},
    {key:"force_n",label:"Force (N)",example:"load"},
  ],
  amplitude_sweep: [
    {key:"strain_percent",label:"Strain (%)",example:"strain"},
    {key:"storage_modulus",label:"Storage modulus G′",example:"Gp"},
  ],
  frequency_sweep: [
    {key:"frequency",label:"Frequency",example:"freq"},
    {key:"storage_modulus",label:"Storage modulus G′",example:"Gp"},
    {key:"loss_modulus",label:"Loss modulus G″",example:"Gpp"},
  ],
};

export default function SampleProfile({sampleId}:{sampleId:string}){
  const [profile,setProfile]=useState<Profile|null>(null);
  const [specimenId,setSpecimenId]=useState("");
  const [measurementId,setMeasurementId]=useState("");
  const [technique,setTechnique]=useState("Rheology");
  const [method,setMethod]=useState("amplitude_sweep");
  const [conditions,setConditions]=useState('{"temperature_c":40,"frequency_hz":1,"geometry_id":"plate-8mm","material_state_id":"annealed"}');
  const [file,setFile]=useState<File|null>(null);
  const [columns,setColumns]=useState<Record<string,string>>({});
  const [frequencyUnit,setFrequencyUnit]=useState("Hz");
  const [modulusUnit,setModulusUnit]=useState("Pa");
  const [heatFlowUnit,setHeatFlowUnit]=useState("mW");
  const [heatingRate,setHeatingRate]=useState(5);
  const [gaugeLength,setGaugeLength]=useState(10);
  const [width,setWidth]=useState(2);
  const [thickness,setThickness]=useState(1);
  const [analyses,setAnalyses]=useState<Analysis[]>([]);
  const [active,setActive]=useState<Analysis|null>(null);
  const [departure,setDeparture]=useState(.05);
  const [comparisonIds,setComparisonIds]=useState<string[]>([]);
  const [comparisonKeys,setComparisonKeys]=useState("temperature_c,geometry_id,material_state_id");
  const [comparison,setComparison]=useState<Record<string,any>|null>(null);
  const [busy,setBusy]=useState(false);
  const [backupFile,setBackupFile]=useState<File|null>(null);
  const [backupReport,setBackupReport]=useState<Record<string,unknown>|null>(null);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");

  async function refresh(){
    const p=await request<Profile>("/samples/"+sampleId+"/profile");
    setProfile(p);
    return p;
  }
  useEffect(()=>{
    setProfile(null);setSpecimenId("");setMeasurementId("");setAnalyses([]);setActive(null);
    if(sampleId) refresh().catch(e=>setError(errorMessage(e)));
  },[sampleId]);
  useEffect(()=>{
    setAnalyses([]);setActive(null);setComparisonIds([]);setComparison(null);setFile(null);setColumns({});
    let current = true;
    if(measurementId){
      const technique=profile?.specimens.flatMap(s=>s.measurements).find(m=>m.measurement_id===measurementId)?.technique;
      const adapter=technique==="Tensile"?"tensile":technique==="DMA"||technique==="DSC"?"thermal":"rheology";
      request<Analysis[]>("/measurements/"+measurementId+"/"+adapter+"/analyses")
        .then(items=>{ if (current) setAnalyses(items); })
        .catch(e=>{ if (current) setError(errorMessage(e)); });
    }
    return ()=>{ current = false; };
  },[measurementId]);
  async function execute(task:()=>Promise<void>){
    setBusy(true);setError("");setNotice("");
    try{await task();}catch(e){setError(errorMessage(e));}finally{setBusy(false);}
  }
  async function verifyBackup(){
    if(!backupFile)return;
    await execute(async()=>{
      const body=new FormData();
      body.append("file",backupFile);
      setBackupReport(await request<Record<string,unknown>>("/backup/verify","POST",body));
      setNotice("Archive integrity verified. No data were restored or modified.");
    });
  }
  async function addSpecimen(){
    const label=window.prompt("Specimen label (unique physical piece)","specimen-1");
    if(!label?.trim())return;
    await execute(async()=>{
      const created=await request<{id:string}>("/samples/"+sampleId+"/specimens","POST",{label});
      await refresh();setSpecimenId(created.id);setNotice("Specimen created.");
    });
  }
  async function addMeasurement(){
    if(!specimenId)return;
    await execute(async()=>{
      const parsed=JSON.parse(conditions);
      if(!parsed||typeof parsed!=="object"||Array.isArray(parsed))throw Error("Conditions must be an object");
      const created=await request<{id:string}>("/specimens/"+specimenId+"/measurements","POST",
        {technique,method,conditions:parsed});
      await refresh();setMeasurementId(created.id);setNotice("Measurement created.");
    });
  }
  async function importCsv(){
    if(!measurementId||!file)return;
    await execute(async()=>{
      const mapping = Object.fromEntries(fields.map(field=>[
        field.key,(columns[field.key]??field.example).trim(),
      ]));
      const headers = Object.values(mapping);
      if (headers.some(header=>!header) || new Set(headers).size!==headers.length) {
        throw new Error("Enter a different CSV column header for each measurement quantity.");
      }
      const form=new FormData();
      form.append("file",file);form.append("method",selected?.method||method);
      form.append("columns_json",JSON.stringify(mapping));
      form.append("frequency_unit",frequencyUnit);form.append("modulus_unit",modulusUnit);
      form.append("departure_fraction",String(departure));
      if(selected?.method==="calorimetry"){
        form.append("heat_flow_unit",heatFlowUnit);
        form.append("heating_rate_c_min",String(heatingRate));
      }
      if(selected?.method==="tensile_test"){
        form.append("gauge_length_mm",String(gaugeLength));
        form.append("width_mm",String(width));
        form.append("thickness_mm",String(thickness));
      }
      const adapter=selected?.technique==="Tensile"?"tensile":
        selected?.technique==="DMA"||selected?.technique==="DSC"?"thermal":"rheology";
      const result=await request<Analysis>("/measurements/"+measurementId+"/"+adapter+"/import","POST",form);
      setAnalyses(await request<Analysis[]>("/measurements/"+measurementId+"/"+adapter+"/analyses"));
      setActive(result);await refresh();setNotice("Raw CSV and analysis saved with provenance.");
    });
  }
  async function reanalyze(){
    if(!active)return;
    await execute(async()=>{
      const result=await request<Analysis>("/rheology/analyses/"+active.analysis_id+"/reanalyze",
        "POST",{departure_fraction:departure});
      setAnalyses(await request<Analysis[]>("/measurements/"+measurementId+"/rheology/analyses"));
      setActive(result);setNotice("New immutable analysis revision created.");
    });
  }
  async function manifest(){
    if(!active)return;
    await execute(async()=>{
      const response=await fetch("/api/v2/analyses/manifest",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({analysis_ids:[active.analysis_id]})});
      if(!response.ok)throw Error("Manifest export failed");
      const url=URL.createObjectURL(await response.blob());
      const link=document.createElement("a");link.href=url;link.download="vitrifit-sample-analysis-manifest.json";
      link.click();URL.revokeObjectURL(url);
    });
  }
  async function compareSelected(){
    if(comparisonIds.length<2)return;
    await execute(async()=>{
      const result=await request<Record<string,any>>("/rheology/compare","POST",{
        analysis_ids:comparisonIds,
        required_condition_keys:comparisonKeys.split(",").map(s=>s.trim()).filter(Boolean)
      });
      setComparison(result);
    });
  }
  const selected=profile?.specimens.flatMap(s=>s.measurements).find(m=>m.measurement_id===measurementId);
  const fields = columnFields[selected?.method??""]??[];
  const traces=active?.method==="frequency_sweep" ? [
    {x:active.results.angular_frequency_rad_s,y:active.results.storage_modulus_pa,
      name:"G′",type:"scatter" as const,mode:"lines+markers" as const},
    {x:active.results.angular_frequency_rad_s,y:active.results.loss_modulus_pa,
      name:"G″",type:"scatter" as const,mode:"lines+markers" as const},
  ]:[];

  if(!sampleId)return <section className="card"><p className="muted">Choose a sample in the sidebar to open its profile.</p></section>;
  return <div className="profile-stack">
    {error&&<div className="error">{error}</div>}
    {notice&&<p className="ok-text" role="status">{notice}</p>}
    <section className="card">
      <h2>Verify backup integrity</h2>
      <p className="muted">Checks a VitriFit ZIP without restoring files or changing the current workspace.</p>
      <div className="controls">
        <label className="field">Backup ZIP<input type="file" accept=".zip,application/zip"
          onChange={e=>{setBackupFile(e.target.files?.[0]||null);setBackupReport(null);}}/></label>
        <button className="subtle" disabled={!backupFile||busy} onClick={verifyBackup}>Verify ZIP</button>
      </div>
      {backupReport&&<p className="ok-text" role="status">Verified: {String(backupReport.raw_blob_count)} raw blobs,
        {" "}{String(backupReport.database_integrity)} SQLite integrity.
        No restore performed.</p>}
    </section>
    <section className="card">
      <div className="card-head"><h2>{profile?.name||"Loading sample..."}</h2>
        <button className="subtle" disabled={busy} onClick={addSpecimen}>+ New specimen</button></div>
      <p className="muted">Sample → physical specimen → measurement → immutable raw file → analysis.</p>
      <div className="profile-techniques">{["DMA","DSC","Rheology","Tensile"].map(t=>
        <div key={t}><strong>{t}</strong><small>{profile?.techniques[t]?.length||0} measurements</small></div>)}</div>
      <label className="field">Specimen<select aria-label="Specimen" value={specimenId} disabled={busy} onChange={e=>{setSpecimenId(e.target.value);setMeasurementId("");}}>
        <option value="">Choose specimen</option>{profile?.specimens.map(s=>
          <option key={s.specimen_id} value={s.specimen_id}>{s.label}</option>)}</select></label>
    </section>
    {specimenId&&<section className="card">
      <h2>Create measurement</h2><div className="controls">
        <label className="field">Technique<select aria-label="Technique" value={technique} disabled={busy} onChange={e=>{setTechnique(e.target.value);
          setMethod(e.target.value==="Rheology"?"amplitude_sweep":e.target.value==="DMA"?"temperature_ramp":e.target.value==="DSC"?"calorimetry":"tensile_test");}}>
          {["Rheology","DMA","DSC","Tensile"].map(t=><option key={t}>{t}</option>)}</select></label>
        <label className="field">Method<select value={method} onChange={e=>setMethod(e.target.value)}>
          {(technique==="Rheology"?["amplitude_sweep","frequency_sweep","stress_relaxation"]:
            technique==="DMA"?["temperature_ramp"]:
            technique==="DSC"?["calorimetry"]:["tensile_test"]).map(m=><option key={m}>{m}</option>)}</select></label>
      </div>
      <label className="field">Measurement conditions (JSON)
        <textarea rows={3} value={conditions} onChange={e=>setConditions(e.target.value)}/></label>
      <button className="primary" disabled={busy} onClick={addMeasurement}>Create measurement</button>
      <h2 style={{marginTop:20}}>Saved measurements</h2>
      <div className="run-list">{profile?.specimens.find(s=>s.specimen_id===specimenId)?.measurements.map(m=>
        <button className={"profile-measurement "+(measurementId===m.measurement_id?"selected":"")}
          key={m.measurement_id} disabled={busy} onClick={()=>setMeasurementId(m.measurement_id)}>
          <strong>{m.technique} · {m.method}</strong>
          <small>{m.conditions.temperature_c==null?"Temperature not supplied":String(m.conditions.temperature_c)+" °C"} · {m.files.length} raw files</small>
        </button>)}</div>
    </section>}
    {selected&&<section className="card">
      <h2>{selected.method} · Import and analyses</h2>
      {!((selected.technique==="Rheology"&&["amplitude_sweep","frequency_sweep"].includes(selected.method))||
         (selected.technique==="Tensile"&&selected.method==="tensile_test")||
         (selected.technique==="DMA"&&selected.method==="temperature_ramp")||
         (selected.technique==="DSC"&&selected.method==="calorimetry"))
        ?<p className="warning">Metadata only. This method has no CSV analysis adapter yet.</p>
        :<>
        <p className="muted">CSV with header row, numeric values and explicit mapping. No automatic instrument parsing or hidden unit assumptions.</p>
        {selected.method==="calorimetry"&&<div className="controls">
          <label className="field">Heat-flow unit<select value={heatFlowUnit} onChange={e=>setHeatFlowUnit(e.target.value)}>
            {["mW","W","W/g","mW/mg"].map(u=><option key={u}>{u}</option>)}</select></label>
          <label className="field">Heating rate (°C/min)<input type="number" min=".001" step=".5"
            value={heatingRate} onChange={e=>setHeatingRate(Number(e.target.value))}/></label>
        </div>}
        {selected.method==="tensile_test"&&<div className="controls">
          <label className="field">Gauge length (mm)<input type="number" min=".001" step=".1" value={gaugeLength} onChange={e=>setGaugeLength(Number(e.target.value))}/></label>
          <label className="field">Width (mm)<input type="number" min=".001" step=".1" value={width} onChange={e=>setWidth(Number(e.target.value))}/></label>
          <label className="field">Thickness (mm)<input type="number" min=".001" step=".1" value={thickness} onChange={e=>setThickness(Number(e.target.value))}/></label>
        </div>}
        <div className="controls">
          <label className="field">CSV file<input key={measurementId} type="file" accept=".csv,text/csv"
            onChange={e=>setFile(e.target.files?.[0]||null)}/></label>
          {selected.method!=="tensile_test"&&selected.method!=="calorimetry"&&<label className="field">Modulus unit<select value={modulusUnit} onChange={e=>setModulusUnit(e.target.value)}>
            {(selected.method==="temperature_ramp"?["Pa","kPa","MPa","GPa"]:["Pa","kPa","MPa"]).map(u=><option key={u}>{u}</option>)}</select></label>}
          {selected.method==="frequency_sweep"&&<label className="field">Frequency unit
            <select value={frequencyUnit} onChange={e=>setFrequencyUnit(e.target.value)}>
              {["Hz","rad/s"].map(u=><option key={u}>{u}</option>)}</select></label>}
        </div>
        <fieldset className="profile-columns" key={measurementId}>
          <legend>CSV column headers</legend>
          <div className="controls">{fields.map(field=><label className="field" key={field.key}>{field.label}
            <input type="text" value={columns[field.key]??field.example}
              onChange={event=>setColumns(previous=>({...previous,[field.key]:event.target.value}))}/>
          </label>)}</div>
        </fieldset>
        <button className="primary" disabled={!file||busy} onClick={importCsv}>Import, analyze and save</button>
        </>}
      <h2 style={{marginTop:22}}>Original measurement files ({selected.files.length})</h2>
      {selected.files.length===0&&<p className="muted">No original files attached yet.</p>}
      {selected.files.map(original=><div className="profile-raw-file" key={original.file_id}>
        <span><strong>{original.filename}</strong><small>SHA-256: {original.sha256}</small></span>
        <a href={"/api/v2/files/"+encodeURIComponent(original.file_id)+"/raw"}
          download="vitrifit-original.bin">Download original bytes</a>
      </div>)}
      <h2 style={{marginTop:22}}>Analysis history ({analyses.length})</h2>
      {analyses.length===0&&<p className="muted">No saved analyses for this measurement.</p>}
      <div className="run-list">{analyses.map(a=><div key={a.analysis_id} className="profile-analysis-row">
        {selected.technique==="Rheology"&&<input type="checkbox" aria-label={"Select analysis "+a.analysis_id+" for comparison"}
          checked={comparisonIds.includes(a.analysis_id)}
          onChange={e=>setComparisonIds(ids=>e.target.checked?[...ids,a.analysis_id]:ids.filter(id=>id!==a.analysis_id))}/>}
        <button
        className={"profile-measurement "+(active?.analysis_id===a.analysis_id?"selected":"")}
        onClick={()=>{setActive(a);setDeparture(Number(a.config.departure_fraction??.05));}}>
        <strong>{a.method} · {a.analysis_id.slice(0,8)}</strong>
        <small>Source SHA256 {a.source_sha256.slice(0,16)}… · {a.algorithm_version}</small>
      </button></div>)}</div>
      {selected.technique==="Rheology"&&<div className="controls">
        <label className="field">Required matching conditions (comma-separated)
          <input value={comparisonKeys} onChange={e=>setComparisonKeys(e.target.value)}/></label>
        <button className="subtle" disabled={busy||comparisonIds.length<2} onClick={compareSelected}>
          Compare selected analyses</button>
      </div>}
      {comparison&&<div className={comparison.status==="conditions_matched"?"muted":"warning"}>
        <strong>{comparison.status}</strong> · mismatched or missing keys:{" "}
        {(comparison.mismatched_or_missing_keys||[]).join(", ")||"none"}.
        <details><summary>Comparison provenance</summary><pre className="profile-json">{JSON.stringify(comparison,null,2)}</pre></details>
      </div>}
      {active&&<div className="profile-analysis">
        <div className="controls"><button className="subtle" disabled={busy} onClick={manifest}>
          Export provenance JSON</button>
          {active.method==="amplitude_sweep"&&<>
            <label className="field">LVR departure fraction<input type="number" min=".001" max=".99"
              step=".01" value={departure} onChange={e=>setDeparture(Number(e.target.value))}/></label>
            <button className="primary" disabled={busy} onClick={reanalyze}>Reanalyze (new revision)</button>
          </>}</div>
        {active.method==="temperature_ramp"&&<>
          <p className="muted">Observed tan δ peak: {active.results.tan_delta_peak_temperature_c??"not captured"} °C (not DSC Tg onset).</p>
          <Plot data={[{x:active.results.temperature_c,y:active.results.storage_modulus_pa,name:"E′",type:"scatter",mode:"lines"},
            {x:active.results.temperature_c,y:active.results.loss_modulus_pa,name:"E″",type:"scatter",mode:"lines"}] as any}
            layout={{autosize:true,margin:{l:75,r:20,t:20,b:65},
              xaxis:{title:{text:"Temperature (°C)"}},yaxis:{title:{text:"Modulus (Pa)"},type:"log"}}}
            useResizeHandler style={{width:"100%",height:360}} config={{responsive:true,displaylogo:false}}/>
          <p className="warning">{String(active.results.warning)}</p>
        </>}
        {active.method==="calorimetry"&&<>
          <Plot data={[{x:active.results.temperature_c,y:active.results.heat_flow,
            name:"Heat flow",type:"scatter",mode:"lines"}] as any}
            layout={{autosize:true,margin:{l:75,r:20,t:20,b:65},
              xaxis:{title:{text:"Temperature (°C)"}},
              yaxis:{title:{text:"Heat flow ("+active.results.heat_flow_unit+")"}}}}
            useResizeHandler style={{width:"100%",height:360}} config={{responsive:true,displaylogo:false}}/>
          <p className="warning">{String(active.results.warning)}</p>
        </>}
        {active.method==="tensile_test"&&<>
          <p className="muted">Young’s modulus: {active.results.youngs_modulus_mpa===null?"not determined":
            Number(active.results.youngs_modulus_mpa).toFixed(2)+" MPa"} · Max engineering stress:{" "}
            {Number(active.results.max_engineering_stress_mpa).toFixed(2)} MPa</p>
          <Plot data={[{x:active.results.engineering_strain,y:active.results.engineering_stress_mpa,
            name:"Engineering",type:"scatter",mode:"lines"},
            ...(active.results.true_strain_estimate?[{x:active.results.true_strain_estimate,
              y:active.results.true_stress_mpa_estimate,name:"True (estimated)",type:"scatter",mode:"lines"}]:[])] as any}
            layout={{autosize:true,margin:{l:75,r:20,t:20,b:65},
              xaxis:{title:{text:"Strain (dimensionless)"}},
              yaxis:{title:{text:"Stress (MPa)"}}}}
            useResizeHandler style={{width:"100%",height:380}}
            config={{responsive:true,displaylogo:false}}/>
          <p className="warning">{String(active.results.warning)}</p>
        </>}
        {active.method==="frequency_sweep"&&<Plot data={traces as any}
          layout={{autosize:true,margin:{l:75,r:20,t:20,b:65},
            xaxis:{title:{text:"Angular frequency (rad/s)"},type:"log"},
            yaxis:{title:{text:"Modulus (Pa)"},type:"log"},showlegend:true}}
          useResizeHandler style={{width:"100%",height:380}}
          config={{responsive:true,displaylogo:false}}/>}
        {active.method==="amplitude_sweep"&&active.results.observations&&<Plot
          data={[{x:active.results.observations.strain_percent,
            y:active.results.observations.storage_modulus_pa,
            type:"scatter",mode:"lines+markers",name:"Measured G′"}] as any}
          layout={{autosize:true,margin:{l:75,r:20,t:20,b:65},
            xaxis:{title:{text:"Oscillatory strain amplitude (%)"},type:"log"},
            yaxis:{title:{text:"Storage modulus G′ (Pa)"},type:"log"}}}
          useResizeHandler style={{width:"100%",height:360}}
          config={{responsive:true,displaylogo:false}}/>}
        {active.method==="amplitude_sweep"&&<p className="warning">
          LVR: {String(active.results.status)} · last measured in-range amplitude:
          {" "}{String(active.results.highest_measured_in_range_strain_percent??"not established")}%.
          This does not verify step-strain relaxation.</p>}
        <details><summary>Full analysis and provenance</summary>
          <pre className="profile-json">{JSON.stringify(active,null,2)}</pre></details>
      </div>}
    </section>}
  </div>;
}
