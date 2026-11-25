import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import Notice from "../components/Notice";
import Pager from "../components/Pager";

const empty = { name: "", age: "", gender: "M", phone: "", address: "", medical_history: "" };

export default function Patients() {
  const [patients, setPatients] = useState([]);
  const [page, setPage] = useState(1);
  const [count, setCount] = useState(0);
  const [form, setForm] = useState(empty);
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState(null);

  const load = async (p = page) => {
    try {
      const data = await api.get(`/patients/?page=${p}`); // GET /patients/ (paginated)
      // If the last row of a page was just removed, step back one page
      if (data.results.length === 0 && p > 1) return changePage(p - 1);
      setPatients(data.results);
      setCount(data.count);
    } catch (e) {
      setNotice({ type: "error", text: e.message });
    } finally {
      setLoading(false);
    }
  };
  const changePage = (p) => {
    setPage(p);
    load(p);
  };
  useEffect(() => {
    load();
  }, []);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setNotice(null);
    const payload = { ...form, age: Number(form.age) };
    try {
      if (editingId) {
        await api.put(`/patients/${editingId}/`, payload); // PUT /patients/<id>/
        setNotice({ type: "success", text: "Patient updated." });
      } else {
        await api.post("/patients/", payload); // POST /patients/
        setNotice({ type: "success", text: "Patient added." });
      }
      setForm(empty);
      setEditingId(null);
      load();
    } catch (err) {
      setNotice({ type: "error", text: err.message });
    }
  };

  const startEdit = async (p) => {
    try {
      const full = await api.get(`/patients/${p.id}/`); // GET /patients/<id>/
      setForm({
        name: full.name, age: full.age, gender: full.gender, phone: full.phone,
        address: full.address, medical_history: full.medical_history,
      });
      setEditingId(full.id);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setNotice({ type: "error", text: err.message });
    }
  };

  const remove = async (p) => {
    if (!window.confirm(`Delete patient "${p.name}"? They will be removed from your lists (the record is kept for audit purposes).`)) return;
    try {
      await api.del(`/patients/${p.id}/`); // DELETE /patients/<id>/
      setNotice({ type: "success", text: "Patient deleted." });
      load();
    } catch (err) {
      setNotice({ type: "error", text: err.message });
    }
  };

  return (
    <>
      <h2>Patients</h2>
      <Notice notice={notice} />

      <form className="card form-grid" onSubmit={submit}>
        <h3>{editingId ? "Edit patient" : "Add patient"}</h3>
        <label>Name<input required value={form.name} onChange={set("name")} /></label>
        <label>Age<input type="number" min="0" max="150" required value={form.age} onChange={set("age")} /></label>
        <label>Gender
          <select value={form.gender} onChange={set("gender")}>
            <option value="M">Male</option>
            <option value="F">Female</option>
            <option value="O">Other</option>
          </select>
        </label>
        <label>Phone<input value={form.phone} onChange={set("phone")} /></label>
        <label className="wide">Address<input value={form.address} onChange={set("address")} /></label>
        <label className="wide">Medical history
          <textarea rows="3" value={form.medical_history} onChange={set("medical_history")} />
        </label>
        <div className="actions wide">
          <button className="btn">{editingId ? "Save changes" : "Add patient"}</button>
          {editingId && (
            <button type="button" className="btn ghost"
              onClick={() => { setEditingId(null); setForm(empty); }}>
              Cancel
            </button>
          )}
        </div>
      </form>

      <div className="card">
        <h3>Your patients</h3>
        {loading ? <p className="muted">Loading...</p> : patients.length === 0 ? (
          <p className="muted">No patients yet. Add one above.</p>
        ) : (
          <table>
            <thead>
              <tr><th>Name</th><th>Age</th><th>Gender</th><th>Phone</th><th></th></tr>
            </thead>
            <tbody>
              {patients.map((p) => (
                <tr key={p.id}>
                  <td><Link to={`/patients/${p.id}`}>{p.name}</Link></td>
                  <td>{p.age}</td>
                  <td>{p.gender}</td>
                  <td>{p.phone || "-"}</td>
                  <td className="row-actions">
                    <Link className="btn small ghost" to={`/patients/${p.id}`}>View</Link>
                    <button className="btn small ghost" onClick={() => startEdit(p)}>Edit</button>
                    <button className="btn small danger" onClick={() => remove(p)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <Pager page={page} count={count} onPage={changePage} />
      </div>
    </>
  );
}
