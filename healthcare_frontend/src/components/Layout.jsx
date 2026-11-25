import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import ApiLog from "./ApiLog";

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="shell">
      <header className="topbar">
        <strong className="brand">Healthcare Portal</strong>
        <nav>
          <NavLink to="/patients">Patients</NavLink>
          <NavLink to="/doctors">Doctors</NavLink>
          <NavLink to="/mappings">Mappings</NavLink>
        </nav>
        <div className="who">
          <span>{user?.name}</span>
          <button
            className="btn ghost"
            onClick={async () => {
              await logout();
              navigate("/login");
            }}
          >
            Log out
          </button>
        </div>
      </header>
      <main className="content">
        <div className="main-col">
          <Outlet />
        </div>
        <ApiLog />
      </main>
    </div>
  );
}
