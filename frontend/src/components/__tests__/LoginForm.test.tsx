import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LoginForm } from '../LoginForm';
import { AuthProvider } from '../../contexts/AuthContext';
import * as api from '../../services/api';

// Mock the API module
jest.mock('../../services/api');
const mockedApi = api as jest.Mocked<typeof api>;

// Mock useNavigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

describe('LoginForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset navigate mock
    mockNavigate.mockReset();
  });

  const renderLoginForm = (redirectUrl?: string) => {
    return render(
      <AuthProvider>
        <LoginForm redirectUrl={redirectUrl} />
      </AuthProvider>
    );
  };

  describe('Form Rendering', () => {
    it('renders login form with all required fields', () => {
      renderLoginForm();

      expect(screen.getByLabelText(/username or email/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
    });

    it('shows forgot password and register links', () => {
      renderLoginForm();

      expect(screen.getByText(/forgot password/i)).toBeInTheDocument();
      expect(screen.getByText(/don't have an account/i)).toBeInTheDocument();
    });
  });

  describe('Form Validation', () => {
    it('shows validation errors for empty fields', async () => {
      renderLoginForm();
      const submitButton = screen.getByRole('button', { name: /login/i });

      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/username or email is required/i)).toBeInTheDocument();
        expect(screen.getByText(/password is required/i)).toBeInTheDocument();
      });
    });

    it('clears field-specific errors when user types', async () => {
      renderLoginForm();
      const user = userEvent.setup();
      const submitButton = screen.getByRole('button', { name: /login/i });

      // Submit empty form to trigger errors
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/username or email is required/i)).toBeInTheDocument();
      });

      // Type in username field
      const usernameInput = screen.getByLabelText(/username or email/i);
      await user.type(usernameInput, 'testuser');

      // Username error should be cleared
      expect(screen.queryByText(/username or email is required/i)).not.toBeInTheDocument();
      // Password error should still be present
      expect(screen.getByText(/password is required/i)).toBeInTheDocument();
    });
  });

  describe('Form Submission', () => {
    it('successfully logs in with username', async () => {
      mockedApi.login.mockResolvedValueOnce({
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        first_name: 'Test',
        last_name: 'User',
      });

      renderLoginForm('/dashboard');
      const user = userEvent.setup();

      await user.type(screen.getByLabelText(/username or email/i), 'testuser');
      await user.type(screen.getByLabelText(/password/i), 'TestPass123!');
      await user.click(screen.getByRole('button', { name: /login/i }));

      await waitFor(() => {
        expect(mockedApi.login).toHaveBeenCalledWith('testuser', 'TestPass123!');
        expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
      });
    });

    it('successfully logs in with email', async () => {
      mockedApi.login.mockResolvedValueOnce({
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        first_name: 'Test',
        last_name: 'User',
      });

      renderLoginForm();
      const user = userEvent.setup();

      await user.type(screen.getByLabelText(/username or email/i), 'test@example.com');
      await user.type(screen.getByLabelText(/password/i), 'TestPass123!');
      await user.click(screen.getByRole('button', { name: /login/i }));

      await waitFor(() => {
        expect(mockedApi.login).toHaveBeenCalledWith('test@example.com', 'TestPass123!');
        expect(mockNavigate).toHaveBeenCalledWith('/');
      });
    });

    it('displays error message on login failure', async () => {
      mockedApi.login.mockRejectedValueOnce({
        response: {
          data: {
            non_field_errors: ['Invalid credentials.'],
          },
        },
      });

      renderLoginForm();
      const user = userEvent.setup();

      await user.type(screen.getByLabelText(/username or email/i), 'wronguser');
      await user.type(screen.getByLabelText(/password/i), 'WrongPass');
      await user.click(screen.getByRole('button', { name: /login/i }));

      await waitFor(() => {
        expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument();
      });
    });

    it('disables form during submission', async () => {
      // Mock a slow API call
      mockedApi.login.mockImplementation(
        () => new Promise(resolve => setTimeout(resolve, 1000))
      );

      renderLoginForm();
      const user = userEvent.setup();

      await user.type(screen.getByLabelText(/username or email/i), 'testuser');
      await user.type(screen.getByLabelText(/password/i), 'TestPass123!');

      const submitButton = screen.getByRole('button', { name: /login/i });
      await user.click(submitButton);

      // Check that inputs and button are disabled during submission
      expect(screen.getByLabelText(/username or email/i)).toBeDisabled();
      expect(screen.getByLabelText(/password/i)).toBeDisabled();
      expect(submitButton).toBeDisabled();
    });
  });

  describe('Security', () => {
    it('does not reveal whether username exists on failed login', async () => {
      // Test with non-existent user
      mockedApi.login.mockRejectedValueOnce({
        response: {
          data: {
            non_field_errors: ['Invalid credentials.'],
          },
        },
      });

      renderLoginForm();
      const user = userEvent.setup();

      await user.type(screen.getByLabelText(/username or email/i), 'nonexistent');
      await user.type(screen.getByLabelText(/password/i), 'SomePass123!');
      await user.click(screen.getByRole('button', { name: /login/i }));

      const errorMessage1 = await screen.findByText(/invalid credentials/i);

      // Clear and test with existing user but wrong password
      mockedApi.login.mockRejectedValueOnce({
        response: {
          data: {
            non_field_errors: ['Invalid credentials.'],
          },
        },
      });

      await user.clear(screen.getByLabelText(/username or email/i));
      await user.clear(screen.getByLabelText(/password/i));
      await user.type(screen.getByLabelText(/username or email/i), 'existing');
      await user.type(screen.getByLabelText(/password/i), 'WrongPass123!');
      await user.click(screen.getByRole('button', { name: /login/i }));

      const errorMessage2 = await screen.findByText(/invalid credentials/i);

      // Both error messages should be identical
      expect(errorMessage1.textContent).toBe(errorMessage2.textContent);
    });

    it('masks password input', () => {
      renderLoginForm();
      const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement;

      expect(passwordInput.type).toBe('password');
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels', () => {
      renderLoginForm();

      expect(screen.getByLabelText(/username or email/i)).toHaveAttribute('id');
      expect(screen.getByLabelText(/password/i)).toHaveAttribute('id');
    });

    it('supports keyboard navigation', async () => {
      renderLoginForm();
      const user = userEvent.setup();

      // Tab through form elements
      await user.tab();
      expect(screen.getByLabelText(/username or email/i)).toHaveFocus();

      await user.tab();
      expect(screen.getByLabelText(/password/i)).toHaveFocus();

      await user.tab();
      expect(screen.getByRole('button', { name: /login/i })).toHaveFocus();
    });

    it('submits form with Enter key', async () => {
      mockedApi.login.mockResolvedValueOnce({
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        first_name: 'Test',
        last_name: 'User',
      });

      renderLoginForm();
      const user = userEvent.setup();

      await user.type(screen.getByLabelText(/username or email/i), 'testuser');
      await user.type(screen.getByLabelText(/password/i), 'TestPass123!');

      // Press Enter in password field
      await user.type(screen.getByLabelText(/password/i), '{Enter}');

      await waitFor(() => {
        expect(mockedApi.login).toHaveBeenCalled();
      });
    });
  });
});
