import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import Notice from "../components/Notice";
import Pager from "../components/Pager";

export default function Mappings() {
  const [mappings, setMappings] = useState([]);
  const [page, setPage] = useState(1);
  const [count, setCount] = useState(0);
  const [patients, setPatients] = useState([]);
  const [doctors, setDoctors] = useState([]);
  const [form, setForm] = useState({ patient: "", doctor: "" });
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState(null);

  const load = async (pg = page) => {
    try {
      const [m, p, d] = await Promise.all([
        api.get(`/mappings/?page=${pg}`), // GET /mappings/ (paginated)
        api.getAll("/patients/"),         // dropdowns need every row
        api.getAll("/doctors/"),
      ]);
      if (m.results.length === 0 && pg > 1) return changePage(pg - 1);
      setMappings(m.results);
      setCount(m.count);
      setPatients(p);
      setDoctors(d);
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

  const assign = async (e) => {
    e.preventDefault();
    setNotice(null);
    try {
      await api.post("/mappings/", { patient: Number(form.patient), doctor: Number(form.doctor) }); // POST /mappings/
      setForm({ patient: "", doctor: "" });
      setNotice({ type: "success", text: "Doctor assigned to patient." });
      load();
    } catch (err) {
      setNotice({ type: "error", text: err.message });
    }
  };

  const remove = async (id) => {
    try {
      await api.del(`/mappings/${id}/`); // DELETE /mappings/<id>/
      setNotice({ type: "success", text: "Mapping removed." });
      load();
    } catch (err) {
      setNotice({ type: "error", text: err.message });
    }
  };

  return (
    <>
      <h2>Patient-Doctor Mappings</h2>
      <Notice notice={notice} />

      <form className="card inline-form" onSubmit={assign}>
        <select required value={form.patient} onChange={(e) => setForm({ ...form, patient: e.target.value })}>
          <option value="">Select patient...</option>
          {patients.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <select required value={form.doctor} onChange={(e) => setForm({ ...form, doctor: e.target.value })}>
          <option value="">Select doctor...</option>
          {doctors.map((d) => <option key={d.id} value={d.id}>{d.name} ({d.specialization})</option>)}
        </select>
        <button className="btn">Assign</button>
      </form>

      <div className="card">
        <h3>All mappings</h3>
        {loading ? <p className="muted">Loading...</p> : mappings.length === 0 ? (
          <p className="muted">No mappings yet.</p>
        ) : (
          <table>
            <thead><tr><th>Patient</th><th>Doctor</th><th>Assigned</th><th></th></tr></thead>
            <tbody>
              {mappings.map((m) => (
                <tr key={m.id}>
                  <td><Link to={`/patients/${m.patient}`}>{m.patient_name}</Link></td>
                  <td>{m.doctor_name}</td>
                  <td>{new Date(m.assigned_at).toLocaleString()}</td>
                  <td className="row-actions">
                    <button className="btn small danger" onClick={() => remove(m.id)}>Remove</button>
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
