import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { RegisterData } from '../types/user';

interface RegisterFormProps {
  onSuccess?: () => void;
  onSwitchToLogin?: () => void;
}

const RegisterForm: React.FC<RegisterFormProps> = ({ onSuccess, onSwitchToLogin }) => {
  const { register, loading, error, clearError } = useAuth();
  const [formData, setFormData] = useState<RegisterData>({
    username: '',
    email: '',
    password: '',
    password_confirm: '',
    first_name: '',
    last_name: '',
  });
  const [formErrors, setFormErrors] = useState<Partial<RegisterData>>({});

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));

    // Clear field-specific error when user starts typing
    if (formErrors[name as keyof RegisterData]) {
      setFormErrors(prev => ({ ...prev, [name]: undefined }));
    }

    // Clear global error when user starts typing
    if (error) {
      clearError();
    }
  };

  const validateForm = (): boolean => {
    const errors: Partial<RegisterData> = {};

    if (!formData.username.trim()) {
      errors.username = 'Username is required';
    } else if (formData.username.length < 3) {
      errors.username = 'Username must be at least 3 characters long';
    }

    if (!formData.email.trim()) {
      errors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      errors.email = 'Please enter a valid email address';
    }

    if (!formData.password) {
      errors.password = 'Password is required';
    } else if (formData.password.length < 8) {
      errors.password = 'Password must be at least 8 characters long';
    }

    if (!formData.password_confirm) {
      errors.password_confirm = 'Please confirm your password';
    } else if (formData.password !== formData.password_confirm) {
      errors.password_confirm = 'Passwords do not match';
    }

    if (!formData.first_name.trim()) {
      errors.first_name = 'First name is required';
    }

    if (!formData.last_name.trim()) {
      errors.last_name = 'Last name is required';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    try {
      await register(formData);
      onSuccess?.();
    } catch (error) {
      // Error is handled by AuthContext
    }
  };

  return (
    <div className="auth-form-container">
      <div className="auth-form-header">
        <h2>Register</h2>
      </div>

      <form onSubmit={handleSubmit} className="auth-form">
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
          <label htmlFor="username">Username</label>
          <input
            type="text"
            id="username"
            name="username"
            value={formData.username}
            onChange={handleChange}
            className={formErrors.username ? 'error' : ''}
            disabled={loading}
            placeholder="Choose a username"
          />
          {formErrors.username && (
            <div className="field-error">{formErrors.username}</div>
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
          <label htmlFor="password">Password</label>
          <input
            type="password"
            id="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            className={formErrors.password ? 'error' : ''}
            disabled={loading}
            placeholder="Choose a password (minimum 8 characters)"
          />
          {formErrors.password && (
            <div className="field-error">{formErrors.password}</div>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="password_confirm">Confirm Password</label>
          <input
            type="password"
            id="password_confirm"
            name="password_confirm"
            value={formData.password_confirm}
            onChange={handleChange}
            className={formErrors.password_confirm ? 'error' : ''}
            disabled={loading}
            placeholder="Confirm your password"
          />
          {formErrors.password_confirm && (
            <div className="field-error">{formErrors.password_confirm}</div>
          )}
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          disabled={loading}
        >
          {loading ? 'Creating Account...' : 'Register'}
        </button>
      </form>

      <div className="auth-form-footer">
        <p>
          Already have an account?{' '}
          <button
            type="button"
            className="link-button"
            onClick={onSwitchToLogin}
            disabled={loading}
          >
            Login here
          </button>
        </p>
      </div>
    </div>
  );
};

export default RegisterForm;
