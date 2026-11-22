import { useEffect, useState } from "react";
import { api, errorMessage } from "./api";

type Notes = { text: string; revision: number; updated_at: string | null };

export default function SampleNotes({sampleId}: {sampleId: string}) {
  const [visited, setVisited] = useState<string[]>([]);
  useEffect(()=>{
    if (sampleId) setVisited(previous=>previous.includes(sampleId)?previous:[...previous,sampleId]);
  },[sampleId]);
  return <section className="card">
    <h2>Sample notes</h2>
    {!sampleId&&<p className="muted">Choose a sample in the research library.</p>}
    {visited.map(id=><div key={id} hidden={id!==sampleId}><NotesEditor sampleId={id}/></div>)}
  </section>;
}

function NotesEditor({sampleId}: {sampleId: string}) {
  const [saved, setSaved] = useState<Notes | null>(null);
  const [latest, setLatest] = useState<Notes | null>(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const url = "/samples/"+sampleId+"/notes";
  const dirty = Boolean(saved && saved.text!==draft);

  useEffect(()=>{
    let active = true;
    api<Notes>(url).then(record=>{
      if (active) { setSaved(record); setDraft(record.text); }
    }).catch(error=>{ if (active) setError(errorMessage(error)); });
    return ()=>{ active = false; };
  },[url]);

  useEffect(()=>{
    if (!dirty) return;
    function preventUnload(event: BeforeUnloadEvent) {
      event.preventDefault();
      event.returnValue = "";
    }
    window.addEventListener("beforeunload",preventUnload);
    return ()=>window.removeEventListener("beforeunload",preventUnload);
  },[dirty]);

  async function save() {
    if (!saved) return;
    setBusy(true);
    setError("");
    try {
      setSaved(await api<Notes>(url,"PUT",{text:draft,revision:saved.revision}));
    } catch (error) {
      setError(errorMessage(error));
      try {
        const current = await api<Notes>(url);
        if (current.revision!==saved.revision) setLatest(current);
      } catch {
        // Keep the draft and original error available for a retry.
      }
    } finally {
      setBusy(false);
    }
  }

  return <>
    {error&&<p role="alert">{error}</p>}
    {saved&&<>
      <label className="field">Notes
        <textarea rows={14} value={draft} maxLength={100000}
          placeholder="Record specimen preparation, instrument settings, or analysis decisions."
          onChange={event=>setDraft(event.target.value)}/>
      </label>
      {latest&&<div>
        <label className="field">Latest saved version<textarea readOnly rows={6} value={latest.text}/></label>
        <button className="subtle" onClick={()=>{
          setDraft(latest.text); setSaved(latest); setLatest(null); setError("");
        }}>Use saved version</button>
        <button className="subtle" onClick={()=>{
          setSaved(latest); setLatest(null); setError("");
        }}>Keep editing my draft</button>
      </div>}
      <button className="primary" disabled={busy||!dirty||Boolean(latest)} onClick={save}>Save notes</button>
      <p className="hint" role="status">{dirty?"Unsaved changes":saved.updated_at?
        "Saved "+new Date(saved.updated_at).toLocaleString():"No notes saved yet"}</p>
    </>}
  </>;
}
