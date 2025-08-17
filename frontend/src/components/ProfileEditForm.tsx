import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { ProfileUpdateData, User } from '../types/user';
import { profileAPI } from '../services/api';

interface ProfileEditFormProps {
  user?: User;
  onSuccess?: (updatedUser: User) => void;
  onCancel?: () => void;
}

const ProfileEditForm: React.FC<ProfileEditFormProps> = ({ user: propUser, onSuccess, onCancel }) => {
  const { user: contextUser } = useAuth();
  const user = propUser || contextUser;

  const [formData, setFormData] = useState<ProfileUpdateData>({
    first_name: '',
    last_name: '',
    display_name: '',
    timezone: '',
    email: '',
  });
  const [formErrors, setFormErrors] = useState<Partial<ProfileUpdateData>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Initialize form data when user is available
  useEffect(() => {
    if (user) {
      setFormData({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        display_name: user.display_name || '',
        timezone: user.timezone || '',
        email: user.email || '',
      });
    }
  }, [user]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(function(prev) { return ({ ...prev, [name]: value }) });

    // Clear field-specific error when user starts typing
    if (formErrors[name as keyof ProfileUpdateData]) {
      setFormErrors(prev => ({ ...prev, [name]: undefined }));
    }

    // Clear global error when user starts typing
    if (error) {
      setError(null);
    }
  };

  const validateForm = (): boolean => {
    const errors: Partial<ProfileUpdateData> = {};

    if (!formData.first_name.trim()) {
      errors.first_name = 'First name is required';
    }

    if (!formData.last_name.trim()) {
      errors.last_name = 'Last name is required';
    }

    if (!formData.email.trim()) {
      errors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      errors.email = 'Please enter a valid email address';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await profileAPI.updateProfile(formData);
      onSuccess?.(response.user);
    } catch (error: any) {
      const errorMessage = error.response?.data?.email?.[0] ||
                          error.response?.data?.first_name?.[0] ||
                          error.response?.data?.last_name?.[0] ||
                          error.response?.data?.detail ||
                          'Profile update failed. Please try again.';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const timezoneOptions = [
    { value: '', label: 'Select Timezone' },
    { value: 'UTC', label: 'UTC' },
    { value: 'America/New_York', label: 'Eastern Time' },
    { value: 'America/Chicago', label: 'Central Time' },
    { value: 'America/Denver', label: 'Mountain Time' },
    { value: 'America/Los_Angeles', label: 'Pacific Time' },
    { value: 'Europe/London', label: 'London' },
    { value: 'Europe/Paris', label: 'Paris' },
    { value: 'Europe/Berlin', label: 'Berlin' },
    { value: 'Asia/Tokyo', label: 'Tokyo' },
    { value: 'Asia/Shanghai', label: 'Shanghai' },
    { value: 'Australia/Sydney', label: 'Sydney' },
  ];

  if (!user) {
    return (
      <div className="profile-edit-container">
        <div className="alert alert-error">
          No user information available. Please log in.
        </div>
      </div>
    );
  }

  return (
    <div className="profile-edit-container">
      <div className="profile-edit-header">
        <h2>Edit Profile</h2>
      </div>

      <form onSubmit={handleSubmit} className="profile-edit-form">
        {error && (
          <div className="alert alert-error">
            {error}
          </div>
        )}

        <div className="form-row">
          <div className="form-group">
            <label htmlFor="first_name">First Name</label>
            <input
              type="text"
              id="first_name"
              name="first_name"
              value={formData.first_name}
              onChange={handleChange}
              className={formErrors.first_name ? 'error' : ''}
              disabled={loading}
              placeholder="Enter your first name"
            />
            {formErrors.first_name && (
              <div className="field-error">{formErrors.first_name}</div>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="last_name">Last Name</label>
            <input
              type="text"
              id="last_name"
              name="last_name"
              value={formData.last_name}
              onChange={handleChange}
              className={formErrors.last_name ? 'error' : ''}
              disabled={loading}
              placeholder="Enter your last name"
            />
            {formErrors.last_name && (
              <div className="field-error">{formErrors.last_name}</div>
            )}
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="display_name">Display Name</label>
          <input
            type="text"
            id="display_name"
            name="display_name"
            value={formData.display_name}
            onChange={handleChange}
            className={formErrors.display_name ? 'error' : ''}
            disabled={loading}
            placeholder="Enter display name (optional)"
          />
          {formErrors.display_name && (
            <div className="field-error">{formErrors.display_name}</div>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="email">Email</label>
          <input
            type="email"
            id="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            className={formErrors.email ? 'error' : ''}
            disabled={loading}
            placeholder="Enter your email address"
          />
          {formErrors.email && (
            <div className="field-error">{formErrors.email}</div>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="timezone">Timezone</label>
          <select
            id="timezone"
            name="timezone"
            value={formData.timezone}
            onChange={handleChange}
            className={formErrors.timezone ? 'error' : ''}
            disabled={loading}
          >
            {timezoneOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          {formErrors.timezone && (
            <div className="field-error">{formErrors.timezone}</div>
          )}
        </div>

        <div className="form-actions">
          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
          >
            {loading ? 'Saving...' : 'Save Changes'}
          </button>

          {onCancel && (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onCancel}
              disabled={loading}
            >
              Cancel
            </button>
          )}
        </div>
      </form>
    </div>
  );
};

export default ProfileEditForm;
