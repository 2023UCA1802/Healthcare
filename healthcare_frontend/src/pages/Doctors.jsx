import { useEffect, useState } from "react";
import { api } from "../api";
import Notice from "../components/Notice";
import Pager from "../components/Pager";

const empty = { name: "", email: "", phone: "", specialization: "", experience_years: 0 };

export default function Doctors() {
  const [doctors, setDoctors] = useState([]);
  const [page, setPage] = useState(1);
  const [count, setCount] = useState(0);
  const [form, setForm] = useState(empty);
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState(null);

  const load = async (p = page) => {
    try {
      const data = await api.get(`/doctors/?page=${p}`); // GET /doctors/ (your doctors, paginated)
      if (data.results.length === 0 && p > 1) return changePage(p - 1);
      setDoctors(data.results);
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
    const payload = { ...form, experience_years: Number(form.experience_years) };
    try {
      if (editingId) {
        await api.put(`/doctors/${editingId}/`, payload); // PUT /doctors/<id>/
        setNotice({ type: "success", text: "Doctor updated." });
      } else {
        await api.post("/doctors/", payload); // POST /doctors/
        setNotice({ type: "success", text: "Doctor added." });
      }
      setForm(empty);
      setEditingId(null);
      load();
    } catch (err) {
      setNotice({ type: "error", text: err.message });
    }
  };

  const startEdit = async (d) => {
    try {
      const full = await api.get(`/doctors/${d.id}/`); // GET /doctors/<id>/
      setForm({
        name: full.name, email: full.email, phone: full.phone,
        specialization: full.specialization, experience_years: full.experience_years,
      });
      setEditingId(full.id);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setNotice({ type: "error", text: err.message });
    }
  };

  const remove = async (d) => {
    if (!window.confirm(`Delete Dr. ${d.name}? (Not possible while they are still assigned to a patient.)`)) return;
    try {
      await api.del(`/doctors/${d.id}/`); // DELETE /doctors/<id>/
      setNotice({ type: "success", text: "Doctor deleted." });
      load();
    } catch (err) {
      setNotice({ type: "error", text: err.message });
    }
  };

  return (
    <>
      <h2>Doctors</h2>
      <Notice notice={notice} />

      <form className="card form-grid" onSubmit={submit}>
        <h3>{editingId ? "Edit doctor" : "Add doctor"}</h3>
        <label>Name<input required value={form.name} onChange={set("name")} /></label>
        <label>Email<input type="email" required value={form.email} onChange={set("email")} /></label>
        <label>Specialization<input required value={form.specialization} onChange={set("specialization")} /></label>
        <label>Experience (years)
          <input type="number" min="0" max="80" value={form.experience_years} onChange={set("experience_years")} />
        </label>
        <label>Phone<input value={form.phone} onChange={set("phone")} /></label>
        <div className="actions wide">
          <button className="btn">{editingId ? "Save changes" : "Add doctor"}</button>
          {editingId && (
            <button type="button" className="btn ghost"
              onClick={() => { setEditingId(null); setForm(empty); }}>
              Cancel
            </button>
          )}
        </div>
      </form>

      <div className="card">
        <h3>Your doctors</h3>
        {loading ? <p className="muted">Loading...</p> : doctors.length === 0 ? (
          <p className="muted">No doctors yet. Add one above.</p>
        ) : (
          <table>
            <thead>
              <tr><th>Name</th><th>Specialization</th><th>Experience</th><th>Email</th><th></th></tr>
            </thead>
            <tbody>
              {doctors.map((d) => (
                <tr key={d.id}>
                  <td>{d.name}</td>
                  <td>{d.specialization}</td>
                  <td>{d.experience_years} yrs</td>
                  <td>{d.email}</td>
                  <td className="row-actions">
                    <button className="btn small ghost" onClick={() => startEdit(d)}>Edit</button>
                    <button className="btn small danger" onClick={() => remove(d)}>Delete</button>
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
