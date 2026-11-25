export default function Pager({ page, count, pageSize = 20, onPage }) {
  const pages = Math.max(1, Math.ceil(count / pageSize));
  if (pages <= 1) return null;
  return (
    <div className="actions" style={{ justifyContent: "flex-end", alignItems: "center", marginTop: "0.75rem" }}>
      <button className="btn small ghost" disabled={page <= 1} onClick={() => onPage(page - 1)}>
        &larr; Prev
      </button>
      <span className="muted">Page {page} of {pages} ({count} total)</span>
      <button className="btn small ghost" disabled={page >= pages} onClick={() => onPage(page + 1)}>
        Next &rarr;
      </button>
    </div>
  );
}
