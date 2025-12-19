import React from "react";
import { FaSignOutAlt } from "react-icons/fa";
import "./UserDashboard.css";

const UserDashboard = ({ session, goToDashboard, goToEdit, handleSignOut }) => {
  const user = session.user;

  return (
    <div>
      {/* Navbar */}
      <nav className="navbar">
        <h2>ExpenseTracker</h2>
        <div className="nav-links">
          <span onClick={goToDashboard}>← Dashboard</span>
          <button onClick={handleSignOut}><FaSignOutAlt /> Sign Out</button>
        </div>
      </nav>

      {/* Profile Card */}
      <div className="dashboard-container">
        <div className="profile-card">
          <p><b>Name:</b> {user.user_metadata?.username || user.email.split("@")[0]}</p>
          <p><b>Email:</b> {user.email}</p>
          <p><b>Created:</b> {new Date(user.created_at).toLocaleDateString()}</p>
          <p><b>Last Sign In:</b> {new Date(user.last_sign_in_at).toLocaleDateString()}</p>
          
          {/* Edit Profile Button */}
          <button className="edit-btn" onClick={goToEdit}>Edit Profile</button>
        </div>
      </div>
    </div>
  );
};

export default UserDashboard;
