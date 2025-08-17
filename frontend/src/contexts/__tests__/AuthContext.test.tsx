import React from 'react';
import { render, screen, waitFor , renderHook, act } from '@testing-library/react';
import { AuthProvider, useAuth } from '../AuthContext';
import * as api from '../../services/api';

// Mock the API module
jest.mock('../../services/api');
const mockedApi = api as jest.Mocked<typeof api>;

describe('AuthContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <AuthProvider>{children}</AuthProvider>
  );

  describe('Initial State', () => {
    it('starts with no user and not loading', () => {
      const { result } = renderHook(function() { return useAuth() }, { wrapper });

      expect(result.current.user).toBeNull();
      expect(result.current.isLoading).toBe(false);
      expect(result.current.isAuthenticated).toBe(false);
    });

    it('checks for existing session on mount', async () => {
      mockedApi.getUserInfo.mockResolvedValueOnce({
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
      });

      const { result } = renderHook(() => useAuth(), { wrapper });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
        expect(result.current.user).toEqual({
          id: 1,
          username: 'testuser',
          email: 'test@example.com',
        });
        expect(result.current.isAuthenticated).toBe(true);
      });
    });

    it('handles failed session check gracefully', async () => {
      mockedApi.getUserInfo.mockRejectedValueOnce(new Error('Not authenticated'));

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
        expect(result.current.user).toBeNull();
        expect(result.current.isAuthenticated).toBe(false);
      });
    });
  });

  describe('Login', () => {
    it('successfully logs in user', async () => {
      mockedApi.login.mockResolvedValueOnce({
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
      });

      const { result } = renderHook(() => useAuth(), { wrapper });

      await act(async () => {
        await result.current.login('testuser', 'password');
      });

      expect(result.current.user).toEqual({
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
      });
      expect(result.current.isAuthenticated).toBe(true);
    });

    it('handles login failure', async () => {
      mockedApi.login.mockRejectedValueOnce({
        response: {
          data: {
            non_field_errors: ['Invalid credentials.'],
          },
        },
      });

      const { result } = renderHook(() => useAuth(), { wrapper });

      await expect(
        act(async () => {
          await result.current.login('testuser', 'wrongpassword');
        })
      ).rejects.toThrow();

      expect(result.current.user).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
    });

    it('clears previous errors on new login attempt', async () => {
      mockedApi.login
        .mockRejectedValueOnce(new Error('First failure'))
        .mockResolvedValueOnce({
          id: 1,
          username: 'testuser',
          email: 'test@example.com',
        });

      const { result } = renderHook(() => useAuth(), { wrapper });

      // First login fails
      try {
        await act(async () => {
          await result.current.login('user', 'wrong');
        });
      } catch (e) {
        // Expected to fail
      }

      // Second login succeeds
      await act(async () => {
        await result.current.login('user', 'correct');
      });

      expect(result.current.user).not.toBeNull();
    });
  });

  describe('Registration', () => {
    it('successfully registers new user', async () => {
      mockedApi.register.mockResolvedValueOnce({
        id: 1,
        username: 'newuser',
        email: 'new@example.com',
      });

      const { result } = renderHook(() => useAuth(), { wrapper });

      await act(async () => {
        await result.current.register({
          username: 'newuser',
          email: 'new@example.com',
          password: 'TestPass123!',
          password_confirm: 'TestPass123!',
        });
      });

      expect(mockedApi.register).toHaveBeenCalled();
      // Note: Registration doesn't automatically log in
      expect(result.current.user).toBeNull();
    });

    it('handles registration errors', async () => {
      mockedApi.register.mockRejectedValueOnce({
        response: {
          data: {
            username: ['This username is already taken.'],
            email: ['This email is already registered.'],
          },
        },
      });

      const { result } = renderHook(() => useAuth(), { wrapper });

      await expect(
        act(async () => {
          await result.current.register({
            username: 'existing',
            email: 'existing@example.com',
            password: 'TestPass123!',
            password_confirm: 'TestPass123!',
          });
        })
      ).rejects.toThrow();
    });
  });

  describe('Logout', () => {
    it('successfully logs out user', async () => {
      // Setup: User is logged in
      mockedApi.getUserInfo.mockResolvedValueOnce({
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
      });
      mockedApi.logout.mockResolvedValueOnce(undefined);

      const { result } = renderHook(() => useAuth(), { wrapper });

      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isAuthenticated).toBe(true);
      });

      // Logout
      await act(async () => {
        await result.current.logout();
      });

      expect(result.current.user).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
      expect(mockedApi.logout).toHaveBeenCalled();
    });

    it('clears user state even if logout API fails', async () => {
      // Setup: User is logged in
      mockedApi.getUserInfo.mockResolvedValueOnce({
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
      });
      mockedApi.logout.mockRejectedValueOnce(new Error('Network error'));

      const { result } = renderHook(() => useAuth(), { wrapper });

      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isAuthenticated).toBe(true);
      });

      // Logout with API failure
      await act(async () => {
        try {
          await result.current.logout();
        } catch (e) {
          // Expected to fail
        }
      });

      // User should still be logged out locally
      expect(result.current.user).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
    });
  });

  describe('Profile Update', () => {
    it('updates user profile', async () => {
      // Setup: User is logged in
      mockedApi.getUserInfo.mockResolvedValueOnce({
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        display_name: 'Test User',
      });

      mockedApi.updateProfile.mockResolvedValueOnce({
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        display_name: 'Updated Name',
      });

      const { result } = renderHook(() => useAuth(), { wrapper });

      // Wait for initial load
      await waitFor(() => {
        expect(result.current.user).not.toBeNull();
      });

      // Update profile
      await act(async () => {
        await result.current.updateProfile({ display_name: 'Updated Name' });
      });

      expect(result.current.user?.display_name).toBe('Updated Name');
    });
  });

  describe('Session Management', () => {
    it('refreshes user data', async () => {
      mockedApi.getUserInfo
        .mockResolvedValueOnce({
          id: 1,
          username: 'testuser',
          email: 'test@example.com',
          first_name: 'Test',
        })
        .mockResolvedValueOnce({
          id: 1,
          username: 'testuser',
          email: 'test@example.com',
          first_name: 'Updated',
        });

      const { result } = renderHook(() => useAuth(), { wrapper });

      // Initial load
      await waitFor(() => {
        expect(result.current.user?.first_name).toBe('Test');
      });

      // Refresh
      await act(async () => {
        await result.current.checkAuth();
      });

      expect(result.current.user?.first_name).toBe('Updated');
    });

    it('handles session expiration', async () => {
      // User is initially logged in
      mockedApi.getUserInfo.mockResolvedValueOnce({
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
      });

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isAuthenticated).toBe(true);
      });

      // Session expires on next check
      mockedApi.getUserInfo.mockRejectedValueOnce({
        response: { status: 403 },
      });

      await act(async () => {
        await result.current.checkAuth();
      });

      expect(result.current.user).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
    });
  });

  describe('Error Handling', () => {
    it('provides error information from failed operations', async () => {
      const errorMessage = 'Invalid credentials.';
      mockedApi.login.mockRejectedValueOnce({
        response: {
          data: {
            non_field_errors: [errorMessage],
          },
        },
      });

      const { result } = renderHook(() => useAuth(), { wrapper });

      try {
        await act(async () => {
          await result.current.login('user', 'wrong');
        });
      } catch (error: any) {
        expect(error.response.data.non_field_errors).toContain(errorMessage);
      }
    });

    it('handles network errors gracefully', async () => {
      mockedApi.login.mockRejectedValueOnce(new Error('Network Error'));

      const { result } = renderHook(() => useAuth(), { wrapper });

      try {
        await act(async () => {
          await result.current.login('user', 'pass');
        });
      } catch (error: any) {
        expect(error.message).toBe('Network Error');
      }
    });
  });

  describe('Component Integration', () => {
    it('provides auth context to children', () => {
      const TestComponent = () => {
        const { isAuthenticated } = useAuth();
        return <div>{isAuthenticated ? 'Logged In' : 'Not Logged In'}</div>;
      };

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      expect(screen.getByText('Not Logged In')).toBeInTheDocument();
    });

    it('throws error when useAuth is used outside provider', () => {
      const TestComponent = () => {
        useAuth();
        return null;
      };

      // Suppress console.error for this test
      const originalError = console.error;
      console.error = jest.fn();

      expect(() => render(<TestComponent />)).toThrow(
        'useAuth must be used within an AuthProvider'
      );

      console.error = originalError;
    });
  });
});
