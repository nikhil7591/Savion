import React, { useState } from 'react';
import { FaEye, FaEyeSlash, FaUser } from 'react-icons/fa';
import { auth } from "../api/auth.js";

const SignUp = ({ onViewChange }) => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [agreePolicy, setAgreePolicy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleEmailSignUp = async (e) => {
    e.preventDefault();
    setError('');

    if (!agreePolicy) {
      setError('Please agree to the privacy policy');
      return;
    }

    if (!username.trim()) {
      setError('Please enter a username');
      return;
    }

    if (username.length < 3) {
      setError('Username must be at least 3 characters long');
      return;
    }

    setLoading(true);
    try {
      const { data, error: signUpError } = await auth.signup(email, password, username);
      if (signUpError) {
        setError(signUpError.message || 'Signup failed');
      } else {
        // Signup successful, component will re-render via auth state change
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
        <h2 className="auth-title">Sign Up</h2>
        <p className="auth-subtitle">
          Please register with email and create an account to continue using our app.
        </p>

        {error && <div className="error-message">{error}</div>}

        <form onSubmit={handleEmailSignUp} className="auth-form">
          <div className="form-group">
            <div className="input-with-icon">
              <input
                type="text"
                placeholder="Username"
                className="form-input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                minLength={3}
              />
              <FaUser className="input-icon" />
            </div>
          </div>

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
              minLength={6}
            />
            <button
              type="button"
              className="password-toggle"
              onClick={() => setShowPassword(!showPassword)}
            >
              {showPassword ? <FaEyeSlash /> : <FaEye />}
            </button>
          </div>

          <div className="checkbox-group">
            <input
              type="checkbox"
              id="privacy-policy"
              checked={agreePolicy}
              onChange={(e) => setAgreePolicy(e.target.checked)}
            />
            <label htmlFor="privacy-policy">
              I agree with privacy policy
            </label>
          </div>

          <button 
            type="submit" 
            className="primary-btn"
            disabled={loading}
          >
            {loading ? 'Signing up...' : 'Sign up'}
          </button>
        </form>

        <p className="switch-text">
          You already have an account?{' '}
          <button 
            className="link-btn"
            onClick={() => onViewChange('signin')}
          >
            Login
          </button>
        </p>
      </div>
    </div>
  );
};

export default SignUp;