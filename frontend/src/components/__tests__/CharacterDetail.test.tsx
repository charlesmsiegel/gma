/**
 * Tests for CharacterDetail component.
 *
 * Tests character detail functionality including:
 * - Displaying character information
 * - Role-based information visibility
 * - Edit and delete action availability
 * - Navigation and breadcrumbs
 * - Loading and error states
 * - Character history/audit trail display
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { rest } from 'msw';
import { setupServer } from 'msw/node';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../../contexts/AuthContext';
import CharacterDetail from '../CharacterDetail';

// Mock character data
const mockCharacter = {
  id: 1,
  name: 'Test Character',
  description: 'A detailed test character with a rich background story.',
  campaign: {
    id: 1,
    name: 'Test Campaign',
    slug: 'test-campaign'
  },
  player_owner: {
    id: 1,
    username: 'player1',
    first_name: 'John',
    last_name: 'Player'
  },
  game_system: 'Mage: The Ascension',
  created_at: '2023-01-01T00:00:00Z',
  updated_at: '2023-01-15T12:30:00Z',
  is_deleted: false,
  deleted_at: null,
  deleted_by: null,
  // Character stats (for polymorphic characters)
  character_type: 'MageCharacter',
  arete: 3,
  quintessence: 12,
  paradox: 2
};

const mockAuditTrail = [
  {
    id: 1,
    action: 'CREATE',
    user: { id: 1, username: 'player1' },
    timestamp: '2023-01-01T00:00:00Z',
    changes: {
      name: { new: 'Test Character' },
      description: { new: 'A detailed test character...' }
    }
  },
  {
    id: 2,
    action: 'UPDATE',
    user: { id: 2, username: 'gm' },
    timestamp: '2023-01-15T12:30:00Z',
    changes: {
      description: {
        old: 'Original description',
        new: 'A detailed test character with a rich background story.'
      }
    }
  }
];

// Mock API server
const server = setupServer(
  // Character detail endpoint
  rest.get('/api/characters/:id/', (req, res, ctx) => {
    const { id } = req.params;

    if (id === '1') {
      return res(ctx.json(mockCharacter));
    } else if (id === '404') {
      return res(ctx.status(404), ctx.json({ detail: 'Character not found' }));
    } else if (id === '403') {
      return res(ctx.status(403), ctx.json({ detail: 'Permission denied' }));
    }

    return res(ctx.status(500));
  }),

  // Character audit trail endpoint
  rest.get('/api/characters/:id/audit-trail/', (req, res, ctx) => {
    const { id } = req.params;

    if (id === '1') {
      return res(ctx.json(mockAuditTrail));
    }

    return res(ctx.json([]));
  }),

  // Character delete endpoint
  rest.delete('/api/characters/:id/', (req, res, ctx) => {
    return res(ctx.status(204));
  })
);

// Setup and teardown
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// Mock user for auth context
const mockUser = {
  id: 1,
  username: 'testuser',
  email: 'test@example.com',
  first_name: 'Test',
  last_name: 'User',
  is_staff: false,
  is_superuser: false
};

// Wrapper component with auth context and router
const renderWithProviders = (
  component: React.ReactElement,
  initialRoute = '/characters/1'
) => {
  const authContextValue = {
    user: mockUser,
    login: jest.fn(),
    logout: jest.fn(),
    register: jest.fn(),
    updateProfile: jest.fn(),
    isLoading: false,
    error: null
  };

  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <AuthProvider value={authContextValue}>
        {component}
      </AuthProvider>
    </MemoryRouter>
  );
};

describe('CharacterDetail Component', () => {
  const defaultProps = {
    characterId: 1,
    userRole: 'PLAYER' as const,
    currentUserId: 1,
    canEdit: true,
    canDelete: true
  };

  test('renders character information correctly', async () => {
    renderWithProviders(<CharacterDetail {...defaultProps} />);

    // Should show loading initially
    expect(screen.getByText('Loading character...')).toBeInTheDocument();

    // Wait for character to load
    await waitFor(() => {
      expect(screen.getByText('Test Character')).toBeInTheDocument();
    });

    // Check all character information is displayed
    expect(screen.getByText('A detailed test character with a rich background story.')).toBeInTheDocument();
    expect(screen.getByText('Test Campaign')).toBeInTheDocument();
    expect(screen.getByText('John Player (player1)')).toBeInTheDocument();
    expect(screen.getByText('Mage: The Ascension')).toBeInTheDocument();
  });

  test('displays polymorphic character stats when available', async () => {
    renderWithProviders(<CharacterDetail {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character')).toBeInTheDocument();
    });

    // Should show Mage-specific stats
    expect(screen.getByText('Arete: 3')).toBeInTheDocument();
    expect(screen.getByText('Quintessence: 12')).toBeInTheDocument();
    expect(screen.getByText('Paradox: 2')).toBeInTheDocument();
  });

  test('shows edit button when user has edit permission', async () => {
    renderWithProviders(<CharacterDetail {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character')).toBeInTheDocument();
    });

    expect(screen.getByText('Edit Character')).toBeInTheDocument();
  });

  test('hides edit button when user lacks edit permission', async () => {
    const props = { ...defaultProps, canEdit: false };
    renderWithProviders(<CharacterDetail {...props} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character')).toBeInTheDocument();
    });

    expect(screen.queryByText('Edit Character')).not.toBeInTheDocument();
  });

  test('shows delete button when user has delete permission', async () => {
    renderWithProviders(<CharacterDetail {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character')).toBeInTheDocument();
    });

    expect(screen.getByText('Delete Character')).toBeInTheDocument();
  });

  test('hides delete button when user lacks delete permission', async () => {
    const props = { ...defaultProps, canDelete: false };
    renderWithProviders(<CharacterDetail {...props} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character')).toBeInTheDocument();
    });

    expect(screen.queryByText('Delete Character')).not.toBeInTheDocument();
  });

  test('navigates to edit page when edit button is clicked', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CharacterDetail {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character')).toBeInTheDocument();
    });

    const editButton = screen.getByText('Edit Character');
    await user.click(editButton);

    // Should navigate to edit route (mocked navigation)
    expect(window.location.pathname).toBe('/characters/1/edit');
  });

  test('shows delete confirmation when delete button is clicked', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CharacterDetail {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character')).toBeInTheDocument();
    });

    const deleteButton = screen.getByText('Delete Character');
    await user.click(deleteButton);

    // Should show confirmation modal
    expect(screen.getByText('Confirm Character Deletion')).toBeInTheDocument();
    expect(screen.getByText('Type "Test Character" to confirm deletion:')).toBeInTheDocument();
  });

  test('deletes character with proper confirmation', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CharacterDetail {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character')).toBeInTheDocument();
    });

    // Open delete confirmation
    const deleteButton = screen.getByText('Delete Character');
    await user.click(deleteButton);

    // Enter confirmation text
    const confirmInput = screen.getByPlaceholderText('Enter character name');
    await user.type(confirmInput, 'Test Character');

    // Confirm deletion
    const confirmButton = screen.getByText('Delete Character', { selector: 'button' });
    await user.click(confirmButton);

    // Should show success message and navigate away
    await waitFor(() => {
      expect(screen.getByText('Character deleted successfully')).toBeInTheDocument();
    });
  });

  test('prevents deletion without proper confirmation', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CharacterDetail {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character')).toBeInTheDocument();
    });

    // Open delete confirmation
    const deleteButton = screen.getByText('Delete Character');
    await user.click(deleteButton);

    // Enter wrong confirmation text
    const confirmInput = screen.getByPlaceholderText('Enter character name');
    await user.type(confirmInput, 'Wrong Name');

    // Confirm button should be disabled
    const confirmButton = screen.getByText('Delete Character', { selector: 'button' });
    expect(confirmButton).toBeDisabled();
  });

  test('displays breadcrumb navigation', async () => {
    renderWithProviders(<CharacterDetail {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character')).toBeInTheDocument();
    });

    // Should show breadcrumb navigation
    expect(screen.getByText('Test Campaign')).toBeInTheDocument();
    expect(screen.getByText('Characters')).toBeInTheDocument();
    expect(screen.getByText('Test Character')).toBeInTheDocument();
  });

  test('shows character metadata', async () => {
    renderWithProviders(<CharacterDetail {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character')).toBeInTheDocument();
    });

    // Should show creation and update dates
    expect(screen.getByText('Created: January 1, 2023')).toBeInTheDocument();
    expect(screen.getByText('Last Updated: January 15, 2023')).toBeInTheDocument();
  });

  test('displays audit trail when available', async () => {
    renderWithProviders(<CharacterDetail {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character')).toBeInTheDocument();
    });

    // Should show audit trail section
    expect(screen.getByText('Character History')).toBeInTheDocument();
    expect(screen.getByText('Created by player1')).toBeInTheDocument();
    expect(screen.getByText('Updated by gm')).toBeInTheDocument();
  });

  test('shows limited audit trail for regular players', async () => {
    const props = { ...defaultProps, userRole: 'PLAYER' as const, currentUserId: 2 };
    renderWithProviders(<CharacterDetail {...props} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character')).toBeInTheDocument();
    });

    // Regular players should see limited history
    expect(screen.getByText('Character History')).toBeInTheDocument();
    // Should not show detailed change information
    expect(screen.queryByText('Description changed')).not.toBeInTheDocument();
  });

  test('shows full audit trail for GMs and owners', async () => {
    const props = { ...defaultProps, userRole: 'GM' as const };
    renderWithProviders(<CharacterDetail {...props} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character')).toBeInTheDocument();
    });

    // GMs should see full history
    expect(screen.getByText('Character History')).toBeInTheDocument();
    expect(screen.getByText('Description changed')).toBeInTheDocument();
  });

  test('handles character not found error', async () => {
    const props = { ...defaultProps, characterId: 404 };
    renderWithProviders(<CharacterDetail {...props} />);

    await waitFor(() => {
      expect(screen.getByText('Character not found')).toBeInTheDocument();
    });

    expect(screen.getByText('Back to Character List')).toBeInTheDocument();
  });

  test('handles permission denied error', async () => {
    const props = { ...defaultProps, characterId: 403 };
    renderWithProviders(<CharacterDetail {...props} />);

    await waitFor(() => {
      expect(screen.getByText('Access denied')).toBeInTheDocument();
    });

    expect(screen.getByText('You do not have permission to view this character.')).toBeInTheDocument();
  });

  test('handles server error gracefully', async () => {
    server.use(
      rest.get('/api/characters/:id/', (req, res, ctx) => {
        return res(ctx.status(500), ctx.json({ error: 'Server error' }));
      })
    );

    renderWithProviders(<CharacterDetail {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Error loading character')).toBeInTheDocument();
    });

    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  test('retries loading after error', async () => {
    let callCount = 0;
    server.use(
      rest.get('/api/characters/:id/', (req, res, ctx) => {
        callCount++;
        if (callCount === 1) {
          return res(ctx.status(500), ctx.json({ error: 'Server error' }));
        }
        return res(ctx.json(mockCharacter));
      })
    );

    const user = userEvent.setup();
    renderWithProviders(<CharacterDetail {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Error loading character')).toBeInTheDocument();
    });

    // Click retry
    const retryButton = screen.getByText('Retry');
    await user.click(retryButton);

    // Should load successfully
    await waitFor(() => {
      expect(screen.getByText('Test Character')).toBeInTheDocument();
    });
  });

  test('displays soft-deleted character with warning', async () => {
    server.use(
      rest.get('/api/characters/:id/', (req, res, ctx) => {
        return res(ctx.json({
          ...mockCharacter,
          is_deleted: true,
          deleted_at: '2023-02-01T10:00:00Z',
          deleted_by: { id: 1, username: 'player1' }
        }));
      })
    );

    renderWithProviders(<CharacterDetail {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character')).toBeInTheDocument();
    });

    // Should show deletion warning
    expect(screen.getByText('This character has been deleted')).toBeInTheDocument();
    expect(screen.getByText('Deleted by player1 on February 1, 2023')).toBeInTheDocument();
  });

  test('shows restore option for deleted character when user has permission', async () => {
    server.use(
      rest.get('/api/characters/:id/', (req, res, ctx) => {
        return res(ctx.json({
          ...mockCharacter,
          is_deleted: true,
          deleted_at: '2023-02-01T10:00:00Z',
          deleted_by: { id: 1, username: 'player1' }
        }));
      }),
      rest.post('/api/characters/:id/restore/', (req, res, ctx) => {
        return res(ctx.json({ ...mockCharacter, is_deleted: false }));
      })
    );

    const props = { ...defaultProps, userRole: 'GM' as const };
    const user = userEvent.setup();
    renderWithProviders(<CharacterDetail {...props} />);

    await waitFor(() => {
      expect(screen.getByText('This character has been deleted')).toBeInTheDocument();
    });

    // Should show restore button for GM
    const restoreButton = screen.getByText('Restore Character');
    await user.click(restoreButton);

    // Should restore character
    await waitFor(() => {
      expect(screen.queryByText('This character has been deleted')).not.toBeInTheDocument();
    });
  });

  test('navigates back to character list', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CharacterDetail {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character')).toBeInTheDocument();
    });

    const backButton = screen.getByText('← Back to Characters');
    await user.click(backButton);

    // Should navigate back to character list
    expect(window.location.pathname).toBe('/campaigns/test-campaign/characters');
  });

  test('displays recent scenes when available', async () => {
    server.use(
      rest.get('/api/characters/:id/recent-scenes/', (req, res, ctx) => {
        return res(ctx.json([
          {
            id: 1,
            name: 'Chapter 1: The Beginning',
            campaign: { id: 1, name: 'Test Campaign' },
            updated_at: '2023-01-10T15:30:00Z'
          },
          {
            id: 2,
            name: 'Chapter 2: The Mystery Deepens',
            campaign: { id: 1, name: 'Test Campaign' },
            updated_at: '2023-01-12T20:15:00Z'
          }
        ]));
      })
    );

    renderWithProviders(<CharacterDetail {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character')).toBeInTheDocument();
    });

    // Should show recent scenes section
    expect(screen.getByText('Recent Scenes')).toBeInTheDocument();
    expect(screen.getByText('Chapter 1: The Beginning')).toBeInTheDocument();
    expect(screen.getByText('Chapter 2: The Mystery Deepens')).toBeInTheDocument();
  });

  test('shows empty state when character has no recent scenes', async () => {
    server.use(
      rest.get('/api/characters/:id/recent-scenes/', (req, res, ctx) => {
        return res(ctx.json([]));
      })
    );

    renderWithProviders(<CharacterDetail {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character')).toBeInTheDocument();
    });

    // Should show empty state for scenes
    expect(screen.getByText('Recent Scenes')).toBeInTheDocument();
    expect(screen.getByText('No recent scenes')).toBeInTheDocument();
  });

  test('renders character sheet link for supported game systems', async () => {
    renderWithProviders(<CharacterDetail {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character')).toBeInTheDocument();
    });

    // Should show character sheet link for Mage characters
    expect(screen.getByText('View Character Sheet')).toBeInTheDocument();
  });

  test('updates browser title with character name', async () => {
    renderWithProviders(<CharacterDetail {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character')).toBeInTheDocument();
    });

    // Should update document title
    expect(document.title).toBe('Test Character - GMA');
  });
});
