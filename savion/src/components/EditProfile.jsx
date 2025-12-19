import React, { useState } from "react";
import { auth } from "../api/auth.js";
import "./UserDashboard.css"; 

const EditProfile = ({ user, goBack }) => {
  const [username, setUsername] = useState(user?.name || "");
  const [email, setEmail] = useState(user?.email || "");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSave = async () => {
    setError("");
    setSuccess("");

    if (!username) {
      setError("Username cannot be empty");
      return;
    }

    setLoading(true);
    try {
      // For now, we just update locally since the backend API would need an update endpoint
      // In a real app, you'd call an API endpoint to update the profile
      const updatedUser = {
        ...user,
        name: username,
        email: email
      };
      
      // Store updated user in auth client
      auth.setToken(auth.getToken(), updatedUser);
      
      setSuccess("Profile updated successfully!");
      setTimeout(() => {
        goBack(updatedUser);
      }, 1000);
    } catch (err) {
      console.error(err);
      setError("Failed to update profile: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {/* Navbar */}
      <nav className="navbar">
        <h2>Edit Profile</h2>
        <div className="nav-links">
          <span onClick={() => goBack(null)}>← Back to Dashboard</span>
        </div>
      </nav>

      {/* Edit Card */}
      <div className="dashboard-container">
        <div className="profile-card">
          {error && <div className="error-message">{error}</div>}
          {success && <div className="success-message">{success}</div>}
          
          <label>
            Username:
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
            />
          </label>
          
          <label>
            Email:
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              disabled
            />
          </label>
          
          <button 
            className="save-btn" 
            onClick={handleSave}
            disabled={loading}
          >
            {loading ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default EditProfile;
