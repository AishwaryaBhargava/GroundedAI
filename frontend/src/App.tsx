import { Routes, Route } from "react-router-dom";

import Header from "./components/Header";
import Footer from "./components/Footer";
import LandingPage from "./pages/LandingPage";
import Dashboard from "./pages/Dashboard";
import RequireGuest from "./components/RequireGuest";

import "./App.css";

function App() {
  return (
    <div className="app">
      <Header />

      <main className="app-content">
        <Routes>
          <Route path="/" element={<LandingPage />} />

          <Route
            path="/dashboard"
            element={
              <RequireGuest>
                <Dashboard />
              </RequireGuest>
            }
          />
        </Routes>
      </main>

      <Footer />
    </div>
  );
}

export default App;
