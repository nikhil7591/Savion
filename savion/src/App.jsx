import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Welcome from './components/Welcome';
import SignUp from './components/SignUp';
import SignIn from './components/SignIn';
import ExpenseDashboard from './components/ExpenseDashboard';
import EditProfile from './components/EditProfile';
import './App.css';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [currentView, setCurrentView] = useState('welcome');

  useEffect(() => {
    const token = localStorage.getItem('token');
    const storedUser = localStorage.getItem('user');
    if (token && storedUser) {
      setIsAuthenticated(true);
      try {
        setUser(JSON.parse(storedUser));
      } catch {
        localStorage.removeItem('user');
      }
    }
    setLoading(false);
  }, []);

  const handleLogin = (authUser) => {
    setIsAuthenticated(true);
    setUser(authUser || null);
    if (authUser) {
      localStorage.setItem('user', JSON.stringify(authUser));
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setIsAuthenticated(false);
    setUser(null);
    setCurrentView('welcome');
  };

  const handleViewChange = (view) => setCurrentView(view);

  if (loading) {
    return (
      <div className="app-container">
        <div className="loading">Loading...</div>
      </div>
    );
  }

  if (isAuthenticated && user) {
    return (
      <Router>
        <Routes>
          <Route path="/" element={<ExpenseDashboard user={user} logout={handleLogout} />} />
          <Route path="/edit-profile" element={<EditProfile goBack={() => window.history.back()} />} />
        </Routes>
      </Router>
    );
  }

  return (
    <div className="app-container">
      {currentView === 'welcome' && <Welcome onViewChange={handleViewChange} />}
      {currentView === 'signup' && <SignUp onViewChange={handleViewChange} onLogin={handleLogin} />}
      {currentView === 'signin' && <SignIn onViewChange={handleViewChange} onLogin={handleLogin} />}
    </div>
  );
}

export default App;
