/**
 * API service functions for character CRUD operations.
 * 
 * This module provides functions to interact with the Django REST API
 * for character management operations with proper error handling,
 * CSRF token support, and TypeScript type safety.
 */

import api, { ensureCSRFToken } from './api';
import {
  Character,
  CharacterCreateData,
  CharacterUpdateData,
  CharacterListResponse,
  CharacterListParams,
  CharacterAuditEntry,
  CampaignOption,
  APIError
} from '../types/character';

// Helper function to build query parameters
const buildQueryParams = (params: CharacterListParams): URLSearchParams => {
  const searchParams = new URLSearchParams();
  
  if (params.campaign) searchParams.append('campaign', params.campaign.toString());
  if (params.search) searchParams.append('search', params.search);
  if (params.user) searchParams.append('user', params.user.toString());
  if (params.page) searchParams.append('page', params.page.toString());
  if (params.page_size) searchParams.append('page_size', params.page_size.toString());
  if (params.ordering) searchParams.append('ordering', params.ordering);
  
  return searchParams;
};

// Character API endpoints
export const characterAPI = {
  /**
   * Get list of characters with filtering and pagination
   */
  getCharacters: async (params: CharacterListParams = {}): Promise<CharacterListResponse> => {
    try {
      const queryParams = buildQueryParams(params);
      const url = `characters/${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
      
      const response = await api.get<CharacterListResponse>(url);
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 401) {
        throw new Error('Authentication required');
      }
      if (error.response?.status === 403) {
        throw new Error('Permission denied');
      }
      if (error.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
      throw new Error('Failed to load characters');
    }
  },

  /**
   * Get a single character by ID
   */
  getCharacter: async (id: number): Promise<Character> => {
    try {
      const response = await api.get<Character>(`characters/${id}/`);
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        throw new Error('Character not found');
      }
      if (error.response?.status === 401) {
        throw new Error('Authentication required');
      }
      if (error.response?.status === 403) {
        throw new Error('Permission denied');
      }
      if (error.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
      throw new Error('Failed to load character');
    }
  },

  /**
   * Create a new character
   */
  createCharacter: async (data: CharacterCreateData): Promise<Character> => {
    try {
      await ensureCSRFToken();
      const response = await api.post<Character>('characters/', data);
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 400) {
        // Return validation errors for form handling
        const apiError = error.response.data as APIError;
        const errorMessage = apiError.detail || 'Validation failed';
        const validationError = new Error(errorMessage) as any;
        validationError.validationErrors = apiError;
        throw validationError;
      }
      if (error.response?.status === 401) {
        throw new Error('Authentication required');
      }
      if (error.response?.status === 403) {
        throw new Error('Permission denied');
      }
      if (error.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
      throw new Error('Failed to create character');
    }
  },

  /**
   * Update an existing character
   */
  updateCharacter: async (id: number, data: CharacterUpdateData): Promise<Character> => {
    try {
      await ensureCSRFToken();
      const response = await api.patch<Character>(`characters/${id}/`, data);
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 400) {
        // Return validation errors for form handling
        const apiError = error.response.data as APIError;
        const errorMessage = apiError.detail || 'Validation failed';
        const validationError = new Error(errorMessage) as any;
        validationError.validationErrors = apiError;
        throw validationError;
      }
      if (error.response?.status === 404) {
        throw new Error('Character not found');
      }
      if (error.response?.status === 401) {
        throw new Error('Authentication required');
      }
      if (error.response?.status === 403) {
        throw new Error('Permission denied');
      }
      if (error.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
      throw new Error('Failed to update character');
    }
  },

  /**
   * Delete a character (soft delete)
   */
  deleteCharacter: async (id: number, confirmationName?: string): Promise<void> => {
    try {
      await ensureCSRFToken();
      const requestData = confirmationName ? { confirmation_name: confirmationName } : {};
      await api.delete(`characters/${id}/`, { data: requestData });
    } catch (error: any) {
      if (error.response?.status === 400) {
        const apiError = error.response.data as APIError;
        throw new Error(apiError.detail || 'Validation failed');
      }
      if (error.response?.status === 404) {
        throw new Error('Character not found');
      }
      if (error.response?.status === 401) {
        throw new Error('Authentication required');
      }
      if (error.response?.status === 403) {
        throw new Error('Permission denied');
      }
      if (error.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
      throw new Error('Failed to delete character');
    }
  },

  /**
   * Restore a soft-deleted character
   */
  restoreCharacter: async (id: number): Promise<Character> => {
    try {
      await ensureCSRFToken();
      const response = await api.post<Character>(`characters/${id}/restore/`);
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        throw new Error('Character not found');
      }
      if (error.response?.status === 401) {
        throw new Error('Authentication required');
      }
      if (error.response?.status === 403) {
        throw new Error('Permission denied');
      }
      if (error.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
      throw new Error('Failed to restore character');
    }
  },

  /**
   * Get character audit trail
   */
  getCharacterAuditTrail: async (id: number): Promise<CharacterAuditEntry[]> => {
    try {
      const response = await api.get<CharacterAuditEntry[]>(`characters/${id}/audit-trail/`);
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        throw new Error('Character not found');
      }
      if (error.response?.status === 401) {
        throw new Error('Authentication required');
      }
      if (error.response?.status === 403) {
        throw new Error('Permission denied');
      }
      if (error.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
      throw new Error('Failed to load audit trail');
    }
  },

  /**
   * Get available campaigns for character creation
   */
  getAvailableCampaigns: async (): Promise<CampaignOption[]> => {
    try {
      const response = await api.get<{ results: CampaignOption[] }>('campaigns/');
      return response.data.results;
    } catch (error: any) {
      if (error.response?.status === 401) {
        throw new Error('Authentication required');
      }
      if (error.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
      throw new Error('Failed to load campaigns');
    }
  }
};

// Helper functions for permission checking
export const characterPermissions = {
  /**
   * Check if user can edit a character
   */
  canEdit: (character: Character, currentUserId: number, userRole: string): boolean => {
    // Character owners can always edit
    if (character.player_owner.id === currentUserId) {
      return true;
    }
    
    // Campaign owners and GMs can edit all characters
    return userRole === 'OWNER' || userRole === 'GM';
  },

  /**
   * Check if user can delete a character
   */
  canDelete: (character: Character, currentUserId: number, userRole: string): boolean => {
    // Character owners can always delete their own characters
    if (character.player_owner.id === currentUserId) {
      return true;
    }
    
    // Campaign owners can delete characters (subject to campaign settings)
    if (userRole === 'OWNER') {
      return true;
    }
    
    // GMs may be able to delete characters (subject to campaign settings)
    // This would need to be checked against campaign.allow_gm_character_deletion
    // For now, we'll allow it and let the API enforce the actual permission
    return userRole === 'GM';
  },

  /**
   * Check if user can view a character
   */
  canView: (character: Character, currentUserId: number, userRole: string): boolean => {
    // All campaign members can view characters
    return userRole !== null && userRole !== undefined;
  }
};

export default characterAPI;