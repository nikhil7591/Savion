  import React, { useState } from 'react';
import { FaEye, FaEyeSlash } from 'react-icons/fa';

const SignIn = ({ onViewChange, onLogin }) => {

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleEmailSignIn = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData,
      });
      const data = await response.json();
      if (response.ok) {
        localStorage.setItem('token', data.access_token);
        if (data.user) {
          localStorage.setItem('user', JSON.stringify(data.user));
          onLogin(data.user);
        } else {
          onLogin(null);
        }
      } else {
        alert(data.detail || data.message || 'Login failed');
      }
    } catch (error) {
      alert('Error: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-card">
      <div className="auth-content">
        <h2 className="auth-title">Login Now</h2>
        <p className="auth-subtitle">
          Please login to continue using our app.
        </p>

        <p className="divider-text">Login with your email</p>

        <form onSubmit={handleEmailSignIn} className="auth-form">
          <div className="form-group">
            <input
              type="email"
              placeholder="jhon.doe@gmail.com"
              className="form-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="form-group password-group">
            <input
              type={showPassword ? 'text' : 'password'}
              placeholder="••••••••"
              className="form-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <button
              type="button"
              className="password-toggle"
              onClick={() => setShowPassword(!showPassword)}
            >
              {showPassword ? <FaEyeSlash /> : <FaEye />}
            </button>
          </div>

          <button 
            type="submit" 
            className="primary-btn"
            disabled={loading}
          >
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>

        <p className="switch-text">
          Don't have an account?{' '}
          <button 
            className="link-btn"
            onClick={() => onViewChange('signup')}
          >
            Sign up
          </button>
        </p>
      </div>
    </div>
  );
};

export default SignIn;