import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import Notice from "../components/Notice";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setNotice(null);
    try {
      await register(form.name, form.email, form.password);
      // Same message whether or not the email was already taken (no account discovery).
      navigate("/login", {
        state: { notice: "If that email can be registered, your account is ready. Please log in." },
      });
    } catch (err) {
      setNotice({ type: "error", text: err.message });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-page">
      <form className="card auth-card" onSubmit={submit}>
        <h2>Create account</h2>
        <Notice notice={notice} />
        <label>Name
          <input required value={form.name} onChange={set("name")} />
        </label>
        <label>Email
          <input type="email" required value={form.email} onChange={set("email")} />
        </label>
        <label>Password
          <input type="password" required minLength={8} value={form.password} onChange={set("password")} />
        </label>
        <button className="btn" disabled={busy}>{busy ? "Creating..." : "Register"}</button>
        <p className="muted">Already registered? <Link to="/login">Log in</Link></p>
      </form>
    </div>
  );
}
