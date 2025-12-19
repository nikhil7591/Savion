import React from "react";
import "./UserDashboard.css";

const UserProfile = ({ userEmail, onEdit, onClose }) => {
  return (
    <div className="user-dashboard">
      <h2>User Profile</h2>
      <p><strong>Email:</strong> {userEmail}</p>

      <div className="user-actions">
        <button onClick={onEdit} className="edit-btn">
          Edit Profile
        </button>
        <button onClick={onClose} className="close-btn">
          Back to Dashboard
        </button>
      </div>
    </div>
  );
};

export default UserProfile;
