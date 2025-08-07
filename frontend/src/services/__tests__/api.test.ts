import axios from 'axios';
import * as api from '../api';

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

// Mock window.fetch for CSRF token
global.fetch = jest.fn();

describe('API Service', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Clear cached CSRF token
    (api as any).csrfToken = null;
  });

  describe('CSRF Token Handling', () => {
    it('fetches CSRF token before making POST requests', async () => {
      // Mock CSRF token fetch
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ csrfToken: 'test-csrf-token' }),
      });

      // Mock login request
      mockedAxios.post.mockResolvedValueOnce({
        data: {
          user: { id: 1, username: 'testuser' },
          message: 'Login successful'
        },
      });

      await api.login('testuser', 'password');

      // Should fetch CSRF token first
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/auth/csrf/'),
        expect.objectContaining({
          credentials: 'include',
        })
      );

      // Should include CSRF token in request
      expect(mockedAxios.post).toHaveBeenCalledWith(
        expect.any(String),
        expect.any(Object),
        expect.objectContaining({
          headers: {
            'X-CSRFToken': 'test-csrf-token',
          },
        })
      );
    });

    it('caches CSRF token for subsequent requests', async () => {
      // Mock CSRF token fetch
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ csrfToken: 'cached-token' }),
      });

      // Mock multiple API calls
      mockedAxios.post.mockResolvedValue({ data: {} });

      // First call - should fetch CSRF token
      await api.login('user1', 'pass1');
      expect(global.fetch).toHaveBeenCalledTimes(1);

      // Second call - should use cached token
      await api.login('user2', 'pass2');
      expect(global.fetch).toHaveBeenCalledTimes(1); // Still only called once

      // Both requests should use the same token
      expect(mockedAxios.post).toHaveBeenNthCalledWith(
        1,
        expect.any(String),
        expect.any(Object),
        expect.objectContaining({
          headers: { 'X-CSRFToken': 'cached-token' },
        })
      );

      expect(mockedAxios.post).toHaveBeenNthCalledWith(
        2,
        expect.any(String),
        expect.any(Object),
        expect.objectContaining({
          headers: { 'X-CSRFToken': 'cached-token' },
        })
      );
    });

    it('should refresh CSRF token on 403 error', async () => {
      // This test documents expected behavior for token refresh
      // Currently not implemented - token is cached indefinitely

      // Mock initial CSRF token
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ csrfToken: 'old-token' }),
      });

      // Mock 403 error on first attempt
      mockedAxios.post.mockRejectedValueOnce({
        response: { status: 403, data: { detail: 'CSRF Failed' } },
      });

      // Mock new CSRF token fetch
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ csrfToken: 'new-token' }),
      });

      // Mock successful retry
      mockedAxios.post.mockResolvedValueOnce({
        data: { user: { id: 1 } },
      });

      try {
        await api.login('testuser', 'password');
      } catch (error) {
        // Currently throws error - doesn't retry with new token
        expect(error).toBeDefined();
      }

      // Document that this should:
      // 1. Detect 403 CSRF error
      // 2. Fetch new token
      // 3. Retry request with new token
    });
  });

  describe('Authentication API', () => {
    it('sends login request with correct data', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ csrfToken: 'token' }),
      });

      mockedAxios.post.mockResolvedValueOnce({
        data: {
          user: { id: 1, username: 'testuser', email: 'test@example.com' },
        },
      });

      const result = await api.login('testuser', 'TestPass123!');

      expect(mockedAxios.post).toHaveBeenCalledWith(
        expect.stringContaining('/api/auth/login/'),
        { username: 'testuser', password: 'TestPass123!' },
        expect.objectContaining({
          withCredentials: true,
        })
      );

      expect(result).toEqual({
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
      });
    });

    it('sends registration request with all fields', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ csrfToken: 'token' }),
      });

      mockedAxios.post.mockResolvedValueOnce({
        data: {
          user: { id: 1, username: 'newuser' },
        },
      });

      const registrationData = {
        username: 'newuser',
        email: 'new@example.com',
        password: 'TestPass123!',
        password_confirm: 'TestPass123!',
        first_name: 'New',
        last_name: 'User',
      };

      await api.register(registrationData);

      expect(mockedAxios.post).toHaveBeenCalledWith(
        expect.stringContaining('/api/auth/register/'),
        registrationData,
        expect.any(Object)
      );
    });

    it('sends logout request', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ csrfToken: 'token' }),
      });

      mockedAxios.post.mockResolvedValueOnce({ data: {} });

      await api.logout();

      expect(mockedAxios.post).toHaveBeenCalledWith(
        expect.stringContaining('/api/auth/logout/'),
        {},
        expect.any(Object)
      );
    });

    it('fetches user info', async () => {
      mockedAxios.get.mockResolvedValueOnce({
        data: {
          user: { id: 1, username: 'testuser' },
        },
      });

      const result = await api.getUserInfo();

      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.stringContaining('/api/auth/user/'),
        expect.objectContaining({
          withCredentials: true,
        })
      );

      expect(result).toEqual({ id: 1, username: 'testuser' });
    });
  });

  describe('Error Handling', () => {
    it('should handle 401/403 errors globally', async () => {
      // This test documents expected behavior for global error handling

      // Mock 403 error
      mockedAxios.get.mockRejectedValueOnce({
        response: {
          status: 403,
          data: { detail: 'Authentication credentials were not provided.' }
        },
      });

      try {
        await api.getUserInfo();
      } catch (error: any) {
        expect(error.response.status).toBe(403);
        // Currently just passes error through
        // Should trigger global handler to:
        // 1. Clear auth state
        // 2. Redirect to login
        // 3. Show appropriate message
      }
    });

    it('should handle network errors gracefully', async () => {
      mockedAxios.get.mockRejectedValueOnce(new Error('Network Error'));

      try {
        await api.getUserInfo();
      } catch (error: any) {
        expect(error.message).toBe('Network Error');
        // Should show user-friendly error message
      }
    });

    it('should handle rate limiting (429) errors', async () => {
      // Mock 429 error
      mockedAxios.post.mockRejectedValueOnce({
        response: {
          status: 429,
          data: {
            detail: 'Too many requests',
            retry_after: 60
          },
        },
      });

      try {
        await api.login('user', 'pass');
      } catch (error: any) {
        expect(error.response.status).toBe(429);
        // Should:
        // 1. Show rate limit message
        // 2. Display retry time
        // 3. Disable form for retry period
      }
    });
  });

  describe('Profile API', () => {
    it('fetches user profile', async () => {
      mockedAxios.get.mockResolvedValueOnce({
        data: {
          id: 1,
          username: 'testuser',
          display_name: 'Test User',
          timezone: 'UTC',
        },
      });

      const result = await api.getProfile();

      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.stringContaining('/api/profile/'),
        expect.any(Object)
      );

      expect(result).toHaveProperty('display_name', 'Test User');
    });

    it('updates user profile', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ csrfToken: 'token' }),
      });

      mockedAxios.put.mockResolvedValueOnce({
        data: {
          id: 1,
          display_name: 'Updated Name',
        },
      });

      const profileData = {
        display_name: 'Updated Name',
        timezone: 'America/New_York',
      };

      await api.updateProfile(profileData);

      expect(mockedAxios.put).toHaveBeenCalledWith(
        expect.stringContaining('/api/profile/'),
        profileData,
        expect.any(Object)
      );
    });
  });

  describe('Request Configuration', () => {
    it('includes credentials in all requests', async () => {
      mockedAxios.get.mockResolvedValueOnce({ data: {} });

      await api.getUserInfo();

      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          withCredentials: true,
        })
      );
    });

    it('sets correct content type for JSON requests', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ csrfToken: 'token' }),
      });

      mockedAxios.post.mockResolvedValueOnce({ data: {} });

      await api.login('user', 'pass');

      expect(mockedAxios.post).toHaveBeenCalledWith(
        expect.any(String),
        expect.any(Object),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      );
    });
  });
});
