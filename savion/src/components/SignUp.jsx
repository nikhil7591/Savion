import React, { useState } from 'react';
import { FaEye, FaEyeSlash, FaUser } from 'react-icons/fa';

const SignUp = ({ onViewChange, onLogin }) => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [agreePolicy, setAgreePolicy] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleEmailSignUp = async (e) => {
    e.preventDefault();
    if (!agreePolicy) {
      alert('You must agree to the privacy policy.');
      return;
    }
    setLoading(true);
    try {
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, email, password }),
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
        alert(data.detail || data.message || 'Sign up failed');
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
        <h2 className="auth-title">Sign Up</h2>
        <p className="auth-subtitle">
          Please register to continue using our app.
        </p>

        <p className="divider-text">Sign up with your email</p>

        <form onSubmit={handleEmailSignUp} className="auth-form">
          <div className="form-group">
            <div className="input-with-icon">
              <input
                type="text"
                placeholder="Username"
                className="form-input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
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
              I agree with the privacy policy
            </label>
          </div>

          <button 
            type="submit" 
            className="primary-btn"
            disabled={loading || !agreePolicy}
          >
            {loading ? 'Signing up...' : 'Sign up'}
          </button>
        </form>

        <p className="switch-text">
          Already have an account?{' '}
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