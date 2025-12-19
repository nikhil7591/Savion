  import React, { useState } from 'react';
  import { FaEye, FaEyeSlash } from 'react-icons/fa';
  import { auth } from "../api/auth.js";

  const SignIn = ({ onViewChange }) => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleEmailSignIn = async (e) => {
      e.preventDefault();
      setLoading(true);
      setError('');
      
      try {
        const { data, error: signInError } = await auth.signin(email, password);
        if (signInError) {
          setError(signInError.message || 'Login failed');
        } else {
          // Login successful, component will re-render via auth state change
          window.location.reload();
        }
      } catch (error) {
        setError('Error: ' + error.message);
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

          {error && <div className="error-message">{error}</div>}

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