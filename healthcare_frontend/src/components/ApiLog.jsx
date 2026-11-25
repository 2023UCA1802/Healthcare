import { useEffect, useState } from "react";
import { onLog } from "../api";

// Shows the most recent API calls so you can see each endpoint being hit.
export default function ApiLog() {
  const [entries, setEntries] = useState([]);

  useEffect(
    () =>
      onLog((e) =>
        setEntries((prev) => [{ ...e, id: crypto.randomUUID() }, ...prev].slice(0, 8))
      ),
    []
  );

  return (
    <aside className="apilog">
      <h4>Live API calls</h4>
      {entries.length === 0 && <p className="muted">Nothing yet. Use the app.</p>}
      {entries.map((e) => (
        <div key={e.id} className="logrow">
          <span className={`method ${e.method}`}>{e.method}</span>
          <code>/api{e.path}</code>
          <span className={e.status >= 200 && e.status < 300 ? "ok" : "bad"}>
            {e.status || "ERR"}
          </span>
        </div>
      ))}
    </aside>
  );
}
