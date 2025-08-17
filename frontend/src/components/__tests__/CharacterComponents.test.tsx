/**
 * Basic smoke tests for Character components to ensure they import and render.
 *
 * These tests verify that the components can be imported and don't crash on render,
 * matching the functionality described in the Django templates.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import CharacterList from '../CharacterList';
import CharacterDetail from '../CharacterDetail';
import CharacterEditForm from '../CharacterEditForm';

// Mock the characterAPI module
jest.mock('../../services/characterAPI', () => ({
  characterAPI: {
    getCharacters: jest.fn(() => Promise.resolve({
      count: 0,
      next: null,
      previous: null,
      results: []
    })),
    getCharacter: jest.fn(() => Promise.resolve({
      id: 1,
      name: 'Test Character',
      description: 'Test description',
      campaign: { id: 1, name: 'Test Campaign', game_system: 'Test System' },
      player_owner: { id: 1, username: 'testuser', email: 'test@example.com' },
      game_system: 'Test System',
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z',
      is_deleted: false,
      deleted_at: null,
      deleted_by: null,
      character_type: 'Character'
    })),
    getAvailableCampaigns: jest.fn(() => Promise.resolve([])),
    updateCharacter: jest.fn(() => Promise.resolve({} as unknown)),
    createCharacter: jest.fn(() => Promise.resolve({} as any)),
    deleteCharacter: jest.fn(function() { return Promise.resolve() }),
  },
  characterPermissions: {
    canEdit: jest.fn(() => true),
    canDelete: jest.fn(function() { return true }),
    canView: jest.fn(() => true),
  }
}));

// Mock the AuthContext
const mockAuthContext = {
  user: {
    id: 1,
    username: 'testuser',
    email: 'test@example.com',
    first_name: 'Test',
    last_name: 'User',
    is_staff: false,
    is_superuser: false
  },
  login: jest.fn(),
  logout: jest.fn(),
  register: jest.fn(),
  updateProfile: jest.fn(),
  isLoading: false,
  error: null
};

jest.mock('../../contexts/AuthContext', () => ({
  AuthProvider: function({ children }: { children: React.ReactNode }) { return children },
  useAuth: () => mockAuthContext
}));

describe('Character Components Smoke Tests', () => {
  test('CharacterList renders without crashing', () => {
    const defaultProps = {
      userRole: 'PLAYER' as const,
      currentUserId: 1,
      canManageAll: false,
      canCreateCharacter: true
    };

    render(<CharacterList {...defaultProps} />);
    // If we get here without throwing, the component rendered successfully
  });

  test('CharacterDetail renders without crashing', () => {
    const defaultProps = {
      characterId: 1,
      userRole: 'PLAYER' as const,
      currentUserId: 1
    };

    render(<CharacterDetail {...defaultProps} />);
    // If we get here without throwing, the component rendered successfully
  });

  test('CharacterEditForm renders without crashing', () => {
    const defaultProps = {
      onSave: jest.fn(),
      onCancel: jest.fn()
    };

    render(<CharacterEditForm {...defaultProps} />);
    // If we get here without throwing, the component rendered successfully
  });

  test('CharacterEditForm renders in inline mode without crashing', () => {
    const defaultProps = {
      onSave: jest.fn(),
      onCancel: jest.fn(),
      isInline: true
    };

    render(<CharacterEditForm {...defaultProps} />);
    // If we get here without throwing, the component rendered successfully
  });

  test('CharacterEditForm renders with existing character without crashing', () => {
    const character = {
      id: 1,
      name: 'Test Character',
      description: 'Test description',
      campaign: {
        id: 1,
        name: 'Test Campaign',
        slug: 'test-campaign',
        game_system: 'Test System'
      },
      player_owner: {
        id: 1,
        username: 'testuser',
        email: 'test@example.com'
      },
      game_system: 'Test System',
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z',
      is_deleted: false,
      deleted_at: null,
      deleted_by: null,
      character_type: 'Character'
    };

    const defaultProps = {
      character,
      onSave: jest.fn(),
      onCancel: jest.fn()
    };

    render(<CharacterEditForm {...defaultProps} />);
    // If we get here without throwing, the component rendered successfully
  });

  test('Components include expected UI elements matching Django templates', () => {
    // Test CharacterList includes expected elements
    const listProps = {
      userRole: 'PLAYER' as const,
      currentUserId: 1,
      canManageAll: false,
      canCreateCharacter: true
    };

    const { unmount } = render(<CharacterList {...listProps} />);

    // Should render loading or error state initially
    expect(screen.getByText(/Loading characters|Error loading characters/)).toBeInTheDocument();

    unmount();

    // Test CharacterEditForm includes expected form elements
    const formProps = {
      onSave: jest.fn(),
      onCancel: jest.fn()
    };

    render(<CharacterEditForm {...formProps} />);

    // Should have required form inputs by ID/role
    expect(screen.getByRole('textbox', { name: /character name/i })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: /campaign/i })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: /description/i })).toBeInTheDocument();

    // Should have form actions
    expect(screen.getByRole('button', { name: /create character/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
  });
});
