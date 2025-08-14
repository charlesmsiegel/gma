/**
 * Tests for CharacterList component.
 *
 * Tests character list functionality including:
 * - Rendering character data from API
 * - Search and filtering capabilities
 * - Inline editing functionality
 * - Permission-based action visibility
 * - Loading and error states
 * - API integration
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { rest } from 'msw';
import { setupServer } from 'msw/node';
import { AuthProvider } from '../../contexts/AuthContext';
import CharacterList from '../CharacterList';

// Mock API server
const server = setupServer(
  // Characters list endpoint
  rest.get('/api/characters/', (req, res, ctx) => {
    const campaignId = req.url.searchParams.get('campaign');
    const search = req.url.searchParams.get('search');
    const user = req.url.searchParams.get('user');

    let characters = [
      {
        id: 1,
        name: 'Test Character 1',
        description: 'First test character',
        campaign: { id: 1, name: 'Test Campaign' },
        player_owner: { id: 1, username: 'player1' },
        game_system: 'Mage: The Ascension',
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T00:00:00Z',
        is_deleted: false,
        deleted_at: null,
        deleted_by: null
      },
      {
        id: 2,
        name: 'Test Character 2',
        description: 'Second test character',
        campaign: { id: 1, name: 'Test Campaign' },
        player_owner: { id: 2, username: 'player2' },
        game_system: 'Mage: The Ascension',
        created_at: '2023-01-02T00:00:00Z',
        updated_at: '2023-01-02T00:00:00Z',
        is_deleted: false,
        deleted_at: null,
        deleted_by: null
      },
      {
        id: 3,
        name: 'GM NPC',
        description: 'NPC controlled by GM',
        campaign: { id: 1, name: 'Test Campaign' },
        player_owner: { id: 3, username: 'gm' },
        game_system: 'Mage: The Ascension',
        created_at: '2023-01-03T00:00:00Z',
        updated_at: '2023-01-03T00:00:00Z',
        is_deleted: false,
        deleted_at: null,
        deleted_by: null
      }
    ];

    // Apply filters
    if (campaignId) {
      characters = characters.filter(char => char.campaign.id.toString() === campaignId);
    }
    if (search) {
      characters = characters.filter(char =>
        char.name.toLowerCase().includes(search.toLowerCase())
      );
    }
    if (user) {
      characters = characters.filter(char => char.player_owner.id.toString() === user);
    }

    return res(
      ctx.json({
        count: characters.length,
        next: null,
        previous: null,
        results: characters
      })
    );
  }),

  // Character update endpoint
  rest.patch('/api/characters/:id/', (req, res, ctx) => {
    const { id } = req.params;
    const body = req.body as any;

    return res(
      ctx.json({
        id: parseInt(id as string),
        name: body.name || 'Updated Character',
        description: body.description || 'Updated description',
        campaign: { id: 1, name: 'Test Campaign' },
        player_owner: { id: 1, username: 'player1' },
        game_system: 'Mage: The Ascension',
        created_at: '2023-01-01T00:00:00Z',
        updated_at: new Date().toISOString(),
        is_deleted: false,
        deleted_at: null,
        deleted_by: null
      })
    );
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

// Wrapper component with auth context
const renderWithAuth = (component: React.ReactElement, userRole = 'PLAYER') => {
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
    <AuthProvider value={authContextValue}>
      {component}
    </AuthProvider>
  );
};

describe('CharacterList Component', () => {
  const defaultProps = {
    campaignId: 1,
    userRole: 'PLAYER' as const,
    currentUserId: 1,
    canManageAll: false,
    canCreateCharacter: true
  };

  test('renders character list correctly', async () => {
    renderWithAuth(<CharacterList {...defaultProps} />);

    // Should show loading initially
    expect(screen.getByText('Loading characters...')).toBeInTheDocument();

    // Wait for characters to load
    await waitFor(() => {
      expect(screen.getByText('Test Character 1')).toBeInTheDocument();
    });

    expect(screen.getByText('Test Character 2')).toBeInTheDocument();
    expect(screen.getByText('GM NPC')).toBeInTheDocument();
  });

  test('displays character information correctly', async () => {
    renderWithAuth(<CharacterList {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character 1')).toBeInTheDocument();
    });

    // Check character details are displayed
    expect(screen.getByText('First test character')).toBeInTheDocument();
    expect(screen.getByText('player1')).toBeInTheDocument();
    expect(screen.getByText('Mage: The Ascension')).toBeInTheDocument();
  });

  test('shows create character button when user has permission', async () => {
    renderWithAuth(<CharacterList {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Create Character')).toBeInTheDocument();
    });
  });

  test('hides create character button when user lacks permission', async () => {
    const props = { ...defaultProps, canCreateCharacter: false };
    renderWithAuth(<CharacterList {...props} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character 1')).toBeInTheDocument();
    });

    expect(screen.queryByText('Create Character')).not.toBeInTheDocument();
  });

  test('filters characters by search term', async () => {
    const user = userEvent.setup();
    renderWithAuth(<CharacterList {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character 1')).toBeInTheDocument();
    });

    // Find and use search input
    const searchInput = screen.getByPlaceholderText('Search characters...');
    await user.type(searchInput, 'Character 1');

    await waitFor(() => {
      expect(screen.getByText('Test Character 1')).toBeInTheDocument();
      expect(screen.queryByText('Test Character 2')).not.toBeInTheDocument();
    });
  });

  test('filters characters by player owner', async () => {
    const props = { ...defaultProps, canManageAll: true };
    const user = userEvent.setup();
    renderWithAuth(<CharacterList {...props} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character 1')).toBeInTheDocument();
    });

    // Find and use player filter dropdown
    const playerFilter = screen.getByLabelText('Filter by Player');
    await user.selectOptions(playerFilter, '1');

    await waitFor(() => {
      expect(screen.getByText('Test Character 1')).toBeInTheDocument();
      expect(screen.queryByText('Test Character 2')).not.toBeInTheDocument();
    });
  });

  test('enables inline editing for character owner', async () => {
    const user = userEvent.setup();
    renderWithAuth(<CharacterList {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character 1')).toBeInTheDocument();
    });

    // Find edit button for character owned by current user
    const editButton = screen.getByLabelText('Edit Test Character 1');
    await user.click(editButton);

    // Should show inline edit form
    expect(screen.getByDisplayValue('Test Character 1')).toBeInTheDocument();
    expect(screen.getByDisplayValue('First test character')).toBeInTheDocument();
  });

  test('disables inline editing for characters not owned by user', async () => {
    renderWithAuth(<CharacterList {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character 2')).toBeInTheDocument();
    });

    // Should not show edit button for character not owned by current user
    expect(screen.queryByLabelText('Edit Test Character 2')).not.toBeInTheDocument();
  });

  test('allows GMs to edit all characters when canManageAll is true', async () => {
    const props = { ...defaultProps, canManageAll: true, userRole: 'GM' as const };
    const user = userEvent.setup();
    renderWithAuth(<CharacterList {...props} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character 2')).toBeInTheDocument();
    });

    // GM should be able to edit any character
    const editButton = screen.getByLabelText('Edit Test Character 2');
    await user.click(editButton);

    expect(screen.getByDisplayValue('Test Character 2')).toBeInTheDocument();
  });

  test('saves character changes via API', async () => {
    const user = userEvent.setup();
    renderWithAuth(<CharacterList {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character 1')).toBeInTheDocument();
    });

    // Start editing
    const editButton = screen.getByLabelText('Edit Test Character 1');
    await user.click(editButton);

    // Update name
    const nameInput = screen.getByDisplayValue('Test Character 1');
    await user.clear(nameInput);
    await user.type(nameInput, 'Updated Character Name');

    // Save changes
    const saveButton = screen.getByText('Save');
    await user.click(saveButton);

    // Should show success message
    await waitFor(() => {
      expect(screen.getByText('Character updated successfully')).toBeInTheDocument();
    });
  });

  test('cancels editing without saving changes', async () => {
    const user = userEvent.setup();
    renderWithAuth(<CharacterList {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character 1')).toBeInTheDocument();
    });

    // Start editing
    const editButton = screen.getByLabelText('Edit Test Character 1');
    await user.click(editButton);

    // Make changes
    const nameInput = screen.getByDisplayValue('Test Character 1');
    await user.clear(nameInput);
    await user.type(nameInput, 'Changed Name');

    // Cancel editing
    const cancelButton = screen.getByText('Cancel');
    await user.click(cancelButton);

    // Should revert to original name
    expect(screen.getByText('Test Character 1')).toBeInTheDocument();
    expect(screen.queryByText('Changed Name')).not.toBeInTheDocument();
  });

  test('shows delete confirmation for character owner', async () => {
    const user = userEvent.setup();
    renderWithAuth(<CharacterList {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character 1')).toBeInTheDocument();
    });

    // Find delete button
    const deleteButton = screen.getByLabelText('Delete Test Character 1');
    await user.click(deleteButton);

    // Should show confirmation dialog
    expect(screen.getByText('Confirm Character Deletion')).toBeInTheDocument();
    expect(screen.getByText('Type the character name to confirm:')).toBeInTheDocument();
  });

  test('deletes character with proper confirmation', async () => {
    const user = userEvent.setup();
    renderWithAuth(<CharacterList {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character 1')).toBeInTheDocument();
    });

    // Start deletion
    const deleteButton = screen.getByLabelText('Delete Test Character 1');
    await user.click(deleteButton);

    // Enter confirmation
    const confirmInput = screen.getByPlaceholderText('Enter character name');
    await user.type(confirmInput, 'Test Character 1');

    // Confirm deletion
    const confirmButton = screen.getByText('Delete Character');
    await user.click(confirmButton);

    // Should show success message and remove character
    await waitFor(() => {
      expect(screen.getByText('Character deleted successfully')).toBeInTheDocument();
    });
  });

  test('prevents deletion without proper confirmation', async () => {
    const user = userEvent.setup();
    renderWithAuth(<CharacterList {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character 1')).toBeInTheDocument();
    });

    // Start deletion
    const deleteButton = screen.getByLabelText('Delete Test Character 1');
    await user.click(deleteButton);

    // Enter wrong confirmation
    const confirmInput = screen.getByPlaceholderText('Enter character name');
    await user.type(confirmInput, 'Wrong Name');

    // Try to confirm deletion
    const confirmButton = screen.getByText('Delete Character');
    expect(confirmButton).toBeDisabled();
  });

  test('handles API errors gracefully', async () => {
    // Mock API error
    server.use(
      rest.get('/api/characters/', (req, res, ctx) => {
        return res(ctx.status(500), ctx.json({ error: 'Server error' }));
      })
    );

    renderWithAuth(<CharacterList {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Error loading characters')).toBeInTheDocument();
    });

    // Should show retry button
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  test('retries loading after error', async () => {
    let callCount = 0;
    server.use(
      rest.get('/api/characters/', (req, res, ctx) => {
        callCount++;
        if (callCount === 1) {
          return res(ctx.status(500), ctx.json({ error: 'Server error' }));
        }
        return res(
          ctx.json({
            count: 1,
            next: null,
            previous: null,
            results: [{
              id: 1,
              name: 'Test Character 1',
              description: 'First test character',
              campaign: { id: 1, name: 'Test Campaign' },
              player_owner: { id: 1, username: 'player1' },
              game_system: 'Mage: The Ascension',
              created_at: '2023-01-01T00:00:00Z',
              updated_at: '2023-01-01T00:00:00Z',
              is_deleted: false,
              deleted_at: null,
              deleted_by: null
            }]
          })
        );
      })
    );

    const user = userEvent.setup();
    renderWithAuth(<CharacterList {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Error loading characters')).toBeInTheDocument();
    });

    // Click retry
    const retryButton = screen.getByText('Retry');
    await user.click(retryButton);

    // Should load successfully
    await waitFor(() => {
      expect(screen.getByText('Test Character 1')).toBeInTheDocument();
    });
  });

  test('shows empty state when no characters exist', async () => {
    server.use(
      rest.get('/api/characters/', (req, res, ctx) => {
        return res(
          ctx.json({
            count: 0,
            next: null,
            previous: null,
            results: []
          })
        );
      })
    );

    renderWithAuth(<CharacterList {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('No characters found')).toBeInTheDocument();
    });

    expect(screen.getByText('Create your first character to get started!')).toBeInTheDocument();
  });

  test('displays character counts and limits', async () => {
    const props = { ...defaultProps, canManageAll: true };
    renderWithAuth(<CharacterList {...props} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character 1')).toBeInTheDocument();
    });

    // Should show character count
    expect(screen.getByText('3 characters')).toBeInTheDocument();
  });

  test('handles pagination correctly', async () => {
    // Mock paginated response
    server.use(
      rest.get('/api/characters/', (req, res, ctx) => {
        const page = req.url.searchParams.get('page') || '1';

        if (page === '1') {
          return res(
            ctx.json({
              count: 25,
              next: '/api/characters/?page=2',
              previous: null,
              results: Array.from({ length: 20 }, (_, i) => ({
                id: i + 1,
                name: `Character ${i + 1}`,
                description: `Description ${i + 1}`,
                campaign: { id: 1, name: 'Test Campaign' },
                player_owner: { id: 1, username: 'player1' },
                game_system: 'Mage: The Ascension',
                created_at: '2023-01-01T00:00:00Z',
                updated_at: '2023-01-01T00:00:00Z',
                is_deleted: false,
                deleted_at: null,
                deleted_by: null
              }))
            })
          );
        } else {
          return res(
            ctx.json({
              count: 25,
              next: null,
              previous: '/api/characters/?page=1',
              results: Array.from({ length: 5 }, (_, i) => ({
                id: i + 21,
                name: `Character ${i + 21}`,
                description: `Description ${i + 21}`,
                campaign: { id: 1, name: 'Test Campaign' },
                player_owner: { id: 1, username: 'player1' },
                game_system: 'Mage: The Ascension',
                created_at: '2023-01-01T00:00:00Z',
                updated_at: '2023-01-01T00:00:00Z',
                is_deleted: false,
                deleted_at: null,
                deleted_by: null
              }))
            })
          );
        }
      })
    );

    const user = userEvent.setup();
    renderWithAuth(<CharacterList {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Character 1')).toBeInTheDocument();
    });

    // Should show pagination controls
    expect(screen.getByText('Next')).toBeInTheDocument();
    expect(screen.queryByText('Previous')).not.toBeInTheDocument();

    // Click next page
    const nextButton = screen.getByText('Next');
    await user.click(nextButton);

    await waitFor(() => {
      expect(screen.getByText('Character 21')).toBeInTheDocument();
    });

    // Should show previous button
    expect(screen.getByText('Previous')).toBeInTheDocument();
  });

  test('preserves user input during real-time validation', async () => {
    const user = userEvent.setup();
    renderWithAuth(<CharacterList {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Character 1')).toBeInTheDocument();
    });

    // Start editing
    const editButton = screen.getByLabelText('Edit Test Character 1');
    await user.click(editButton);

    // Type in name field
    const nameInput = screen.getByDisplayValue('Test Character 1');
    await user.clear(nameInput);
    await user.type(nameInput, 'A');

    // Should show validation message for short name
    await waitFor(() => {
      expect(screen.getByText('Name must be at least 2 characters')).toBeInTheDocument();
    });

    // Continue typing
    await user.type(nameInput, 'valid Name');

    // Validation message should disappear
    await waitFor(() => {
      expect(screen.queryByText('Name must be at least 2 characters')).not.toBeInTheDocument();
    });

    // Input should preserve full text
    expect(nameInput).toHaveValue('Avalid Name');
  });
});
