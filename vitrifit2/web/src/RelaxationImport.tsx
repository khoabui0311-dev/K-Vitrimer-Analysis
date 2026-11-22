import { useRef, useState } from "react";
import Plot from "react-plotly.js";
import { api, errorMessage } from "./api";

type PreviewCurve = { source_curve_id: string; temperature_c: number; points: number;
  first_time_s: number; last_time_s: number; time_min_s: number; time_max_s: number;
  nonpositive_modulus_points: number; duplicate_time_steps: number;
  decreasing_time_steps: number; warnings: string[];
  preview_time_s: number[]; preview_modulus_mpa: number[]; };
type ImportPreview = { filename: string; file_sha256: string; file_bytes: number;
  curve_count: number; curves: PreviewCurve[]; temperatures_c: number[];
  replicates_per_temperature: Record<string, number>;
  canonical_units: Record<string, string>; warnings: string[];
  needs_review: boolean; saved: boolean; };

type Sample = { id: string; name: string };
type Entry = {
  id: string;
  file: File;
  sampleId: string;
  preview?: ImportPreview;
  acknowledged?: boolean;
  error?: string;
  saved?: boolean;
  attempted?: boolean;
};

export default function RelaxationImport({samples, defaultSampleId, onSaved}: {
  samples: Sample[];
  defaultSampleId: string;
  onSaved: () => void;
}) {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [activeId, setActiveId] = useState("");
  const [previewCurveIndex, setPreviewCurveIndex] = useState(0);
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const active = entries.find(entry=>entry.id===activeId);
  const importPreview = active?.preview;
  const importAcknowledged = active?.acknowledged ?? false;

  function update(id: string, changes: Partial<Entry>) {
    setEntries(previous=>previous.map(entry=>entry.id===id?{...entry,...changes}:entry));
  }

  function ready(entry: Entry) {
    return !entry.saved && Boolean(entry.sampleId && entry.preview &&
      (!entry.preview.needs_review || entry.acknowledged));
  }

  async function inspectFiles() {
    setBusy(true);
    try {
      for (const entry of entries.filter(item=>!item.preview && !item.saved)) {
        try {
          const form = new FormData();
          form.append("file", entry.file);
          const preview = await api<ImportPreview>("/import-preview", "POST", form);
          if (preview.filename!==entry.file.name || preview.file_bytes!==entry.file.size) {
            throw new Error("Preview source does not match the selected file");
          }
          update(entry.id,{preview,error:undefined});
        } catch (error) {
          update(entry.id,{error:errorMessage(error)});
        }
      }
    } finally {
      setBusy(false);
    }
  }

  async function saveFiles() {
    let savedAny = false;
    setBusy(true);
    try {
      for (const entry of entries.filter(ready)) {
        update(entry.id,{attempted:true,error:undefined});
        try {
          const form = new FormData();
          form.append("file",entry.file);
          form.append("request_id",entry.id);
          form.append("metadata",JSON.stringify({
            preview_sha256:entry.preview!.file_sha256,
            preview_curve_count:entry.preview!.curve_count,
            review_warnings_acknowledged:Boolean(entry.acknowledged),
          }));
          await api("/samples/"+entry.sampleId+"/experiments","POST",form);
          update(entry.id,{saved:true});
          savedAny = true;
        } catch (error) {
          update(entry.id,{error:errorMessage(error)});
        }
      }
      if (savedAny) onSaved();
    } finally {
      setBusy(false);
    }
  }

  const readyCount = entries.filter(ready).length;
  return <>
    <p className="muted">Choose CSV, TXT, XLS, or XLSX files. Assign each file to a sample in this project, inspect the curves, and review any warnings before saving.</p>
    <div className="row">
      <label className="field">Relaxation files<input ref={input} type="file" multiple
        disabled={!samples.length||busy} accept=".csv,.txt,.xls,.xlsx" onChange={event=>{
          const added = Array.from(event.target.files??[], file=>({
            file, id:crypto.randomUUID(), sampleId:defaultSampleId,
          }));
          if (!added.length) return;
          setEntries(previous=>[...previous,...added]);
          setActiveId(added[0].id);
          setPreviewCurveIndex(0);
          if (input.current) input.current.value="";
        }}/></label>
      <button className="subtle" disabled={busy||!entries.some(entry=>!entry.preview)}
        onClick={inspectFiles}>Inspect files</button>
      <button className="primary" disabled={busy||!readyCount}
        onClick={saveFiles}>Save ready files{readyCount ? " ("+readyCount+")" : ""}</button>
    </div>
    {entries.length>0&&<table className="results">
      <thead><tr><th>File</th><th>Destination sample</th><th>Status</th><th>Queue</th></tr></thead>
      <tbody>{entries.map(entry=><tr key={entry.id} className={entry.id===activeId?"selected-row":""}>
        <td><button className="subtle" aria-pressed={entry.id===activeId} onClick={()=>{
          setActiveId(entry.id); setPreviewCurveIndex(0);
        }}>{entry.file.name}</button></td>
        <td><select aria-label={"Sample for "+entry.file.name} value={entry.sampleId}
          disabled={busy||entry.attempted}
          onChange={event=>update(entry.id,{sampleId:event.target.value})}>
          <option value="">Choose sample</option>
          {samples.map(sample=><option key={sample.id} value={sample.id}>{sample.name}</option>)}
        </select></td>
        <td>{entry.error?<span role="alert">{entry.error}</span>:entry.saved?"Saved":
          ready(entry)?"Ready":entry.preview?.needs_review&&!entry.acknowledged?"Review warnings":
          entry.preview?"Choose sample":"Awaiting inspection"}</td>
        <td><button className="subtle" disabled={busy} aria-label={"Remove "+entry.file.name}
          onClick={()=>setEntries(previous=>previous.filter(item=>item.id!==entry.id))}>Remove</button></td>
      </tr>)}</tbody>
    </table>}
    {importPreview&&active&&
          <div className="import-preview">
            <div className="card-head"><h3>Import review — {importPreview.filename}</h3>
              <span className="tag">{importPreview.curve_count} curves detected</span></div>
            <p className="hint">Canonical units: seconds (s), MPa, °C. Original uploaded bytes are retained unchanged; the preview does not save anything.</p>
            <div className="preview-meta">
              <span><strong>Temperatures:</strong> {importPreview.temperatures_c.map(t=>t+" °C").join(", ")}</span>
              <span><strong>Replicates:</strong> {Object.keys(importPreview.replicates_per_temperature).length?
                Object.entries(importPreview.replicates_per_temperature).map(([t,n])=>t+" °C × "+n).join("; "):"None detected"}</span>
            </div>
            <div className="preview-table"><table className="results">
              <thead><tr><th>Curve</th><th>Temperature</th><th>Points</th><th>Time (s)</th><th>Quality</th></tr></thead>
              <tbody>{importPreview.curves.map((c,i)=><tr key={i}
                className={previewCurveIndex===i?"selected-row":""}>
                <td><button className="subtle" aria-pressed={previewCurveIndex===i}
                  onClick={()=>setPreviewCurveIndex(i)}>{c.source_curve_id}</button></td><td>{c.temperature_c} °C</td>
                <td>{c.points}</td><td>{c.time_min_s.toPrecision(4)} – {c.time_max_s.toPrecision(4)}</td>
                <td>{c.warnings.length?<span className="warn-text">{c.warnings.length} warnings</span>:
                  <span className="ok-text">No detected issues</span>}</td>
              </tr>)}</tbody></table></div>
            {importPreview.curves[previewCurveIndex]&&<div className="preview-curve">
              <h3>Curve preview: {importPreview.curves[previewCurveIndex].temperature_c} °C</h3>
              <Plot data={[{
                x:importPreview.curves[previewCurveIndex].preview_time_s,
                y:importPreview.curves[previewCurveIndex].preview_modulus_mpa,
                type:"scatter", mode:"lines+markers", name:"Original observations",
                line:{color:"#2563eb",width:2},marker:{size:4},
              }]} layout={{height:320, autosize:true,
                xaxis:{title:{text:"Instrument time (s)"}}, yaxis:{title:{text:"Modulus (MPa)"}}}}
                config={{responsive:true,displaylogo:false}} style={{width:"100%"}} useResizeHandler/>
              <p className="hint">The chart is decimated for inspection (up to 120 points). Import preserves every original parsed point.</p>
            </div>}
            {importPreview.warnings.length>0&&<div className="import-warnings">
              <strong>Scientific review required</strong>
              <ul>{importPreview.warnings.map((w,i)=><li key={i}>{w}</li>)}</ul>
              <label><input type="checkbox" checked={importAcknowledged}
                disabled={busy||active.saved} onChange={e=>update(active.id,{acknowledged:e.target.checked})}/>
                I have reviewed these warnings. Keep the original points and correct them in Data Preparation.
              </label>
            </div>}
          </div>}
  </>;
}
