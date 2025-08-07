import React from 'react';
import { User } from '../types/user';
import { useAuth } from '../contexts/AuthContext';

interface ProfileViewProps {
  user?: User;
  onEdit?: () => void;
}

const ProfileView: React.FC<ProfileViewProps> = ({ user: propUser, onEdit }) => {
  const { user: contextUser } = useAuth();

  // Use prop user if provided, otherwise use context user
  const user = propUser || contextUser;

  if (!user) {
    return (
      <div className="profile-container">
        <div className="alert alert-info">
          No user information available. Please log in.
        </div>
      </div>
    );
  }

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  return (
    <div className="profile-container">
      <div className="profile-header">
        <h2>User Profile</h2>
        {onEdit && (
          <button className="btn btn-secondary" onClick={onEdit}>
            Edit Profile
          </button>
        )}
      </div>

      <div className="profile-content">
        <div className="profile-section">
          <h3>Personal Information</h3>
          <div className="profile-field">
            <label>Display Name:</label>
            <span>{user.display_name || `${user.first_name} ${user.last_name}`}</span>
          </div>
          <div className="profile-field">
            <label>First Name:</label>
            <span>{user.first_name || 'Not provided'}</span>
          </div>
          <div className="profile-field">
            <label>Last Name:</label>
            <span>{user.last_name || 'Not provided'}</span>
          </div>
          <div className="profile-field">
            <label>Username:</label>
            <span>{user.username}</span>
          </div>
        </div>

        <div className="profile-section">
          <h3>Account Information</h3>
          <div className="profile-field">
            <label>Email:</label>
            <span>{user.email}</span>
          </div>
          <div className="profile-field">
            <label>Timezone:</label>
            <span>{user.timezone || 'Not set'}</span>
          </div>
          <div className="profile-field">
            <label>Member Since:</label>
            <span>{formatDate(user.date_joined)}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfileView;
