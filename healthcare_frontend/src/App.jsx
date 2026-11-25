import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Patients from "./pages/Patients";
import PatientDetail from "./pages/PatientDetail";
import Doctors from "./pages/Doctors";
import Mappings from "./pages/Mappings";

function Protected({ children }) {
  const { user, booting } = useAuth();
  if (booting) return <p className="muted" style={{ padding: "2rem" }}>Loading...</p>;
  return user ? children : <Navigate to="/login" replace />;
}

function PublicOnly({ children }) {
  const { user, booting } = useAuth();
  if (booting) return <p className="muted" style={{ padding: "2rem" }}>Loading...</p>;
  return user ? <Navigate to="/patients" replace /> : children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
      <Route path="/register" element={<PublicOnly><Register /></PublicOnly>} />
      <Route element={<Protected><Layout /></Protected>}>
        <Route path="/patients" element={<Patients />} />
        <Route path="/patients/:id" element={<PatientDetail />} />
        <Route path="/doctors" element={<Doctors />} />
        <Route path="/mappings" element={<Mappings />} />
      </Route>
      <Route path="*" element={<Navigate to="/patients" replace />} />
    </Routes>
  );
}
