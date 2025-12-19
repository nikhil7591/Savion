import React from 'react';
import { FaGithub, FaGoogle } from 'react-icons/fa';

const Welcome = ({ onViewChange }) => {
  
  return (
    <div className="auth-card">
      <div className="auth-content">
        <h2 className="auth-title">Welcome</h2>
        <p className="auth-subtitle">
          Please login or sign up to continue using our app.
        </p>
        
        <div className="welcome-illustration">
          <div className="illustration-container">
            <div className="server-icon">
              <div className="server-body"></div>
              <div className="server-lights">
                <div className="light"></div>
                <div className="light"></div>
                <div className="light"></div>
              </div>
            </div>
            <div className="user-icon">
              <div className="user-head"></div>
              <div className="user-body"></div>
            </div>
            <div className="security-elements">
              <div className="lock-icon"></div>
              <div className="shield-icon"></div>
            </div>
          </div>
        </div>

        <p className="divider-text">or login with email</p>

        <button 
          className="primary-btn"
          onClick={() => onViewChange('signup')}
        >
          Sign up
        </button>

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

export default Welcome;