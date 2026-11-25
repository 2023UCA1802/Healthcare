import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import Notice from "../components/Notice";

export default function PatientDetail() {
  const { id } = useParams();
  const [patient, setPatient] = useState(null);
  const [assigned, setAssigned] = useState([]);
  const [doctors, setDoctors] = useState([]);
  const [doctorId, setDoctorId] = useState("");
  const [notice, setNotice] = useState(null);

  const load = async () => {
    try {
      const [p, m, d] = await Promise.all([
        api.get(`/patients/${id}/`),  // GET /patients/<id>/
        api.get(`/mappings/${id}/`),  // GET /mappings/<patient_id>/
        api.getAll("/doctors/"),      // GET /doctors/ (all pages, for the dropdown)
      ]);
      setPatient(p);
      setAssigned(m);
      setDoctors(d);
    } catch (e) {
      setNotice({ type: "error", text: e.message });
    }
  };
  useEffect(() => {
    load();
  }, [id]);

  const assign = async (e) => {
    e.preventDefault();
    setNotice(null);
    try {
      await api.post("/mappings/", { patient: Number(id), doctor: Number(doctorId) }); // POST /mappings/
      setDoctorId("");
      setNotice({ type: "success", text: "Doctor assigned." });
      load();
    } catch (err) {
      setNotice({ type: "error", text: err.message });
    }
  };

  const unassign = async (mappingId) => {
    try {
      await api.del(`/mappings/${mappingId}/`); // DELETE /mappings/<id>/
      setNotice({ type: "success", text: "Doctor removed from patient." });
      load();
    } catch (err) {
      setNotice({ type: "error", text: err.message });
    }
  };

  if (!patient) {
    return (
      <>
        <Link to="/patients">&larr; Back</Link>
        <Notice notice={notice} />
      </>
    );
  }

  const assignedIds = new Set(assigned.map((m) => m.doctor.id));
  const available = doctors.filter((d) => !assignedIds.has(d.id));

  return (
    <>
      <Link to="/patients">&larr; Back to patients</Link>
      <h2>{patient.name}</h2>
      <Notice notice={notice} />

      <div className="card">
        <h3>Details</h3>
        <dl className="details">
          <dt>Age</dt><dd>{patient.age}</dd>
          <dt>Gender</dt><dd>{patient.gender}</dd>
          <dt>Phone</dt><dd>{patient.phone || "-"}</dd>
          <dt>Address</dt><dd>{patient.address || "-"}</dd>
          <dt>Medical history</dt><dd>{patient.medical_history || "-"}</dd>
        </dl>
      </div>

      <div className="card">
        <h3>Assigned doctors</h3>
        {assigned.length === 0 ? <p className="muted">No doctors assigned yet.</p> : (
          <table>
            <thead><tr><th>Doctor</th><th>Specialization</th><th>Email</th><th></th></tr></thead>
            <tbody>
              {assigned.map((m) => (
                <tr key={m.id}>
                  <td>{m.doctor.name}</td>
                  <td>{m.doctor.specialization}</td>
                  <td>{m.doctor.email}</td>
                  <td className="row-actions">
                    <button className="btn small danger" onClick={() => unassign(m.id)}>Remove</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <form className="inline-form" onSubmit={assign}>
          <select required value={doctorId} onChange={(e) => setDoctorId(e.target.value)}>
            <option value="">Select a doctor to assign...</option>
            {available.map((d) => (
              <option key={d.id} value={d.id}>{d.name} ({d.specialization})</option>
            ))}
          </select>
          <button className="btn" disabled={!doctorId}>Assign</button>
        </form>
      </div>
    </>
  );
}
