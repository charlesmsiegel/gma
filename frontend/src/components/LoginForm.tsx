import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { LoginData } from '../types/user';

interface LoginFormProps {
  onSuccess?: () => void;
  onSwitchToRegister?: () => void;
}

const LoginForm: React.FC<LoginFormProps> = ({ onSuccess, onSwitchToRegister }) => {
  const { login, loading, error, clearError } = useAuth();
  const [formData, setFormData] = useState<LoginData>({
    username: '',
    password: '',
  });
  const [formErrors, setFormErrors] = useState<Partial<LoginData>>({});

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));

    // Clear field-specific error when user starts typing
    if (formErrors[name as keyof LoginData]) {
      setFormErrors(prev => ({ ...prev, [name]: undefined }));
    }

    // Clear global error when user starts typing
    if (error) {
      clearError();
    }
  };

  const validateForm = (): boolean => {
    const errors: Partial<LoginData> = {};

    if (!formData.username.trim()) {
      errors.username = 'Username or email is required';
    }

    if (!formData.password) {
      errors.password = 'Password is required';
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
      await login(formData);
      onSuccess?.();
    } catch (error) {
      // Error is handled by AuthContext
    }
  };

  return (
    <div className="auth-form-container">
      <div className="auth-form-header">
        <h2>Login</h2>
      </div>

      <form onSubmit={handleSubmit} className="auth-form">
        {error && (
          <div className="alert alert-error">
            {error}
          </div>
        )}

        <div className="form-group">
          <label htmlFor="username">Username or Email</label>
          <input
            type="text"
            id="username"
            name="username"
            value={formData.username}
            onChange={handleChange}
            className={formErrors.username ? 'error' : ''}
            disabled={loading}
            placeholder="Enter your username or email"
          />
          {formErrors.username && (
            <div className="field-error">{formErrors.username}</div>
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
            placeholder="Enter your password"
          />
          {formErrors.password && (
            <div className="field-error">{formErrors.password}</div>
          )}
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          disabled={loading}
        >
          {loading ? 'Logging in...' : 'Login'}
        </button>
      </form>

      <div className="auth-form-footer">
        <p>
          Don't have an account?{' '}
          <button
            type="button"
            className="link-button"
            onClick={onSwitchToRegister}
            disabled={loading}
          >
            Register here
          </button>
        </p>
      </div>
    </div>
  );
};

export default LoginForm;
