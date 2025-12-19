import React, { useEffect, useState } from "react";
import { auth } from "./api/auth.js";
import Welcome from "./components/Welcome";
import SignUp from "./components/SignUp";
import SignIn from "./components/SignIn";
import ExpenseDashboard from "./components/ExpenseDashboard";
import EditProfile from "./components/EditProfile";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import "./App.css";

function App() {
  const [user, setUser] = useState(null);
  const [currentView, setCurrentView] = useState("welcome");
  const [loading, setLoading] = useState(true);
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem("theme") || "light";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  useEffect(() => {
    if (auth.isAuthenticated()) {
      setUser(auth.getUser());
      setLoading(false);
    } else {
      setLoading(false);
    }

    const subscription = auth.onAuthStateChange((_event, user) => {
      setUser(user);
      setLoading(false);
    });

    return () => {
      if (subscription?.unsubscribe) {
        subscription.unsubscribe();
      }
    };
  }, []);

  const handleViewChange = (view) => setCurrentView(view);

  const handleLogout = async () => {
    auth.logout();
    setUser(null);
    setCurrentView("welcome");
  };

  const toggleTheme = () => {
    setTheme(theme === "light" ? "dark" : "light");
  };

  if (loading) {
    return (
      <div className="app-container">
        <div className="loading">Loading...</div>
      </div>
    );
  }

  if (user) {
    return (
      <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          {/* Dashboard */}
          <Route
            path="/"
            element={<ExpenseDashboard user={user} logout={handleLogout} theme={theme} toggleTheme={toggleTheme} />}
          />

          {/* Edit Profile with goBack */}
          <Route
            path="/edit-profile"
            element={
              <EditProfile
                user={user}
                goBack={(updatedUser) => {
                  if (updatedUser) setUser(updatedUser);
                  window.history.back();
                }}
                theme={theme}
              />
            }
          />
        </Routes>
      </Router>
    );
  }

  return (
    <div className="app-container">
      {currentView === "welcome" && <Welcome onViewChange={handleViewChange} />}
      {currentView === "signup" && <SignUp onViewChange={handleViewChange} />}
      {currentView === "signin" && <SignIn onViewChange={handleViewChange} />}
    </div>
  );
}

export default App;
