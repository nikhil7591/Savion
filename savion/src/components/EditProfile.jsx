import React from 'react';
import './UserDashboard.css';

const EditProfile = ({ goBack }) => {
  return (
    <div>
      <nav className="navbar">
        <h2>Edit Profile</h2>
        <div className="nav-links">
          <span onClick={goBack}>← Back to Dashboard</span>
        </div>
      </nav>
      <div className="dashboard-container">
        <div className="profile-card">
          <p>Profile editing is not yet implemented in this version.</p>
        </div>
      </div>
    </div>
  );
};

export default EditProfile;
