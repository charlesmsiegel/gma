/**
 * Tests for CharacterForm component.
 *
 * Tests character form functionality including:
 * - Creating new characters
 * - Editing existing characters
 * - Polymorphic character type handling
 * - Form validation and error handling
 * - Campaign filtering and selection
 * - Character limit validation
 * - Real-time validation feedback
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { rest } from 'msw';
import { setupServer } from 'msw/node';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../../contexts/AuthContext';
import CharacterForm from '../CharacterForm';

// Mock campaigns data
const mockCampaigns = [
  {
    id: 1,
    name: 'Test Campaign 1',
    slug: 'test-campaign-1',
    game_system: 'Mage: The Ascension',
    max_characters_per_player: 2,
    user_character_count: 1
  },
  {
    id: 2,
    name: 'Test Campaign 2',
    slug: 'test-campaign-2',
    game_system: 'D&D 5e',
    max_characters_per_player: 0, // Unlimited
    user_character_count: 3
  },
  {
    id: 3,
    name: 'Full Campaign',
    slug: 'full-campaign',
    game_system: 'Call of Cthulhu',
    max_characters_per_player: 1,
    user_character_count: 1 // At limit
  }
];

// Mock existing character data
const mockExistingCharacter = {
  id: 1,
  name: 'Existing Character',
  description: 'An existing character for editing tests',
  campaign: { id: 1, name: 'Test Campaign 1' },
  player_owner: { id: 1, username: 'player1' },
  game_system: 'Mage: The Ascension',
  character_type: 'MageCharacter',
  arete: 3,
  quintessence: 12,
  paradox: 1,
  created_at: '2023-01-01T00:00:00Z',
  updated_at: '2023-01-15T12:30:00Z',
  is_deleted: false
};

// Mock API server
const server = setupServer(
  // Campaigns endpoint
  rest.get('/api/campaigns/', (req, res, ctx) => {
    return res(ctx.json({
      count: mockCampaigns.length,
      results: mockCampaigns
    }));
  }),

  // Character creation endpoint
  rest.post('/api/characters/', (req, res, ctx) => {
    const body = req.body as any;

    // Simulate validation errors
    if (body.name === 'Duplicate Name') {
      return res(
        ctx.status(400),
        ctx.json({
          name: ['A character with this name already exists in this campaign.']
        })
      );
    }

    if (body.campaign === 3) { // Full campaign
      return res(
        ctx.status(400),
        ctx.json({
          campaign: ['You cannot have more than 1 character in this campaign.']
        })
      );
    }

    return res(
      ctx.status(201),
      ctx.json({
        id: 42,
        name: body.name,
        description: body.description || '',
        campaign: mockCampaigns.find(c => c.id === body.campaign),
        player_owner: { id: 1, username: 'player1' },
        game_system: mockCampaigns.find(c => c.id === body.campaign)?.game_system,
        character_type: body.character_type || 'Character',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        is_deleted: false,
        ...body // Include any additional character-specific fields
      })
    );
  }),

  // Character update endpoint
  rest.patch('/api/characters/:id/', (req, res, ctx) => {
    const { id } = req.params;
    const body = req.body as any;

    return res(
      ctx.json({
        ...mockExistingCharacter,
        ...body,
        updated_at: new Date().toISOString()
      })
    );
  }),

  // Character detail endpoint (for editing)
  rest.get('/api/characters/:id/', (req, res, ctx) => {
    const { id } = req.params;

    if (id === '1') {
      return res(ctx.json(mockExistingCharacter));
    }

    return res(ctx.status(404));
  }),

  // Game systems endpoint
  rest.get('/api/game-systems/', (req, res, ctx) => {
    return res(ctx.json([
      {
        id: 'mage',
        name: 'Mage: The Ascension',
        character_types: [
          { id: 'Character', name: 'Basic Character' },
          { id: 'MageCharacter', name: 'Mage Character' }
        ]
      },
      {
        id: 'dnd5e',
        name: 'D&D 5e',
        character_types: [
          { id: 'Character', name: 'Basic Character' },
          { id: 'DnDCharacter', name: 'D&D Character' }
        ]
      }
    ]));
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
  initialRoute = '/characters/create'
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

describe('CharacterForm Component - Create Mode', () => {
  const defaultCreateProps = {
    mode: 'create' as const,
    onSuccess: jest.fn(),
    onCancel: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders create form correctly', async () => {
    renderWithProviders(<CharacterForm {...defaultCreateProps} />);

    expect(screen.getByText('Create Character')).toBeInTheDocument();
    expect(screen.getByLabelText('Character Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Description')).toBeInTheDocument();
    expect(screen.getByLabelText('Campaign')).toBeInTheDocument();
    expect(screen.getByText('Create Character', { selector: 'button' })).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  test('loads and displays available campaigns', async () => {
    renderWithProviders(<CharacterForm {...defaultCreateProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Campaign 1')).toBeInTheDocument();
    });

    expect(screen.getByText('Test Campaign 2')).toBeInTheDocument();
    expect(screen.getByText('Full Campaign')).toBeInTheDocument();
  });

  test('shows character limits for campaigns', async () => {
    renderWithProviders(<CharacterForm {...defaultCreateProps} />);

    await waitFor(() => {
      expect(screen.getByText('1/2 characters')).toBeInTheDocument();
    });

    expect(screen.getByText('3/∞ characters')).toBeInTheDocument();
    expect(screen.getByText('1/1 characters (Full)')).toBeInTheDocument();
  });

  test('disables campaigns at character limit', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CharacterForm {...defaultCreateProps} />);

    await waitFor(() => {
      expect(screen.getByText('Full Campaign')).toBeInTheDocument();
    });

    // Campaign at limit should be disabled
    const fullCampaignOption = screen.getByRole('option', { name: /Full Campaign.*Full/ });
    expect(fullCampaignOption).toBeDisabled();
  });

  test('shows character type selection based on campaign game system', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CharacterForm {...defaultCreateProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Campaign 1')).toBeInTheDocument();
    });

    // Select Mage campaign
    const campaignSelect = screen.getByLabelText('Campaign');
    await user.selectOptions(campaignSelect, '1');

    // Should show character type options for Mage
    await waitFor(() => {
      expect(screen.getByLabelText('Character Type')).toBeInTheDocument();
    });

    expect(screen.getByText('Basic Character')).toBeInTheDocument();
    expect(screen.getByText('Mage Character')).toBeInTheDocument();
  });

  test('shows polymorphic fields when specific character type is selected', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CharacterForm {...defaultCreateProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Campaign 1')).toBeInTheDocument();
    });

    // Select Mage campaign
    const campaignSelect = screen.getByLabelText('Campaign');
    await user.selectOptions(campaignSelect, '1');

    // Select Mage character type
    await waitFor(() => {
      expect(screen.getByLabelText('Character Type')).toBeInTheDocument();
    });

    const characterTypeSelect = screen.getByLabelText('Character Type');
    await user.selectOptions(characterTypeSelect, 'MageCharacter');

    // Should show Mage-specific fields
    await waitFor(() => {
      expect(screen.getByLabelText('Arete')).toBeInTheDocument();
    });

    expect(screen.getByLabelText('Quintessence')).toBeInTheDocument();
    expect(screen.getByLabelText('Paradox')).toBeInTheDocument();
  });

  test('validates required fields', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CharacterForm {...defaultCreateProps} />);

    // Try to submit without filling required fields
    const submitButton = screen.getByText('Create Character', { selector: 'button' });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Name is required')).toBeInTheDocument();
    });

    expect(screen.getByText('Campaign is required')).toBeInTheDocument();
  });

  test('validates character name length', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CharacterForm {...defaultCreateProps} />);

    const nameInput = screen.getByLabelText('Character Name');

    // Test name too short
    await user.type(nameInput, 'A');
    await user.tab(); // Trigger blur validation

    await waitFor(() => {
      expect(screen.getByText('Name must be at least 2 characters')).toBeInTheDocument();
    });

    // Test name too long
    await user.clear(nameInput);
    await user.type(nameInput, 'A'.repeat(101));
    await user.tab();

    await waitFor(() => {
      expect(screen.getByText('Name cannot exceed 100 characters')).toBeInTheDocument();
    });
  });

  test('creates character successfully', async () => {
    const user = userEvent.setup();
    const mockOnSuccess = jest.fn();

    renderWithProviders(
      <CharacterForm {...defaultCreateProps} onSuccess={mockOnSuccess} />
    );

    await waitFor(() => {
      expect(screen.getByText('Test Campaign 1')).toBeInTheDocument();
    });

    // Fill form
    const nameInput = screen.getByLabelText('Character Name');
    await user.type(nameInput, 'New Test Character');

    const descriptionInput = screen.getByLabelText('Description');
    await user.type(descriptionInput, 'A brand new character for testing');

    const campaignSelect = screen.getByLabelText('Campaign');
    await user.selectOptions(campaignSelect, '1');

    // Submit form
    const submitButton = screen.getByText('Create Character', { selector: 'button' });
    await user.click(submitButton);

    // Should show success and call onSuccess
    await waitFor(() => {
      expect(mockOnSuccess).toHaveBeenCalledWith(expect.objectContaining({
        id: 42,
        name: 'New Test Character'
      }));
    });
  });

  test('creates polymorphic character with specific fields', async () => {
    const user = userEvent.setup();
    const mockOnSuccess = jest.fn();

    renderWithProviders(
      <CharacterForm {...defaultCreateProps} onSuccess={mockOnSuccess} />
    );

    await waitFor(() => {
      expect(screen.getByText('Test Campaign 1')).toBeInTheDocument();
    });

    // Fill basic form
    await user.type(screen.getByLabelText('Character Name'), 'New Mage Character');
    await user.selectOptions(screen.getByLabelText('Campaign'), '1');

    // Select Mage character type
    await waitFor(() => {
      expect(screen.getByLabelText('Character Type')).toBeInTheDocument();
    });
    await user.selectOptions(screen.getByLabelText('Character Type'), 'MageCharacter');

    // Fill Mage-specific fields
    await waitFor(() => {
      expect(screen.getByLabelText('Arete')).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText('Arete'), '2');
    await user.type(screen.getByLabelText('Quintessence'), '15');
    await user.type(screen.getByLabelText('Paradox'), '0');

    // Submit form
    await user.click(screen.getByText('Create Character', { selector: 'button' }));

    await waitFor(() => {
      expect(mockOnSuccess).toHaveBeenCalledWith(expect.objectContaining({
        character_type: 'MageCharacter',
        arete: 2,
        quintessence: 15,
        paradox: 0
      }));
    });
  });

  test('handles server validation errors', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CharacterForm {...defaultCreateProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Campaign 1')).toBeInTheDocument();
    });

    // Fill form with duplicate name
    await user.type(screen.getByLabelText('Character Name'), 'Duplicate Name');
    await user.selectOptions(screen.getByLabelText('Campaign'), '1');

    // Submit form
    await user.click(screen.getByText('Create Character', { selector: 'button' }));

    // Should show server error
    await waitFor(() => {
      expect(screen.getByText('A character with this name already exists in this campaign.')).toBeInTheDocument();
    });
  });

  test('handles character limit validation error', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CharacterForm {...defaultCreateProps} />);

    await waitFor(() => {
      expect(screen.getByText('Full Campaign')).toBeInTheDocument();
    });

    // Fill form for full campaign
    await user.type(screen.getByLabelText('Character Name'), 'Limit Test Character');
    await user.selectOptions(screen.getByLabelText('Campaign'), '3');

    // Submit form
    await user.click(screen.getByText('Create Character', { selector: 'button' }));

    // Should show character limit error
    await waitFor(() => {
      expect(screen.getByText('You cannot have more than 1 character in this campaign.')).toBeInTheDocument();
    });
  });

  test('cancels form and calls onCancel', async () => {
    const user = userEvent.setup();
    const mockOnCancel = jest.fn();

    renderWithProviders(
      <CharacterForm {...defaultCreateProps} onCancel={mockOnCancel} />
    );

    const cancelButton = screen.getByText('Cancel');
    await user.click(cancelButton);

    expect(mockOnCancel).toHaveBeenCalled();
  });

  test('shows loading state during submission', async () => {
    // Mock slow API response
    server.use(
      rest.post('/api/characters/', (req, res, ctx) => {
        return res(ctx.delay(1000), ctx.json({ id: 42 }));
      })
    );

    const user = userEvent.setup();
    renderWithProviders(<CharacterForm {...defaultCreateProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Campaign 1')).toBeInTheDocument();
    });

    // Fill minimal form
    await user.type(screen.getByLabelText('Character Name'), 'Loading Test');
    await user.selectOptions(screen.getByLabelText('Campaign'), '1');

    // Submit form
    await user.click(screen.getByText('Create Character', { selector: 'button' }));

    // Should show loading state
    expect(screen.getByText('Creating...')).toBeInTheDocument();
    expect(screen.getByText('Creating...', { selector: 'button' })).toBeDisabled();
  });
});

describe('CharacterForm Component - Edit Mode', () => {
  const defaultEditProps = {
    mode: 'edit' as const,
    characterId: 1,
    onSuccess: jest.fn(),
    onCancel: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders edit form correctly', async () => {
    renderWithProviders(<CharacterForm {...defaultEditProps} />);

    expect(screen.getByText('Loading character...')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Edit Character')).toBeInTheDocument();
    });

    expect(screen.getByDisplayValue('Existing Character')).toBeInTheDocument();
    expect(screen.getByDisplayValue('An existing character for editing tests')).toBeInTheDocument();
    expect(screen.getByText('Update Character', { selector: 'button' })).toBeInTheDocument();
  });

  test('loads existing character data', async () => {
    renderWithProviders(<CharacterForm {...defaultEditProps} />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('Existing Character')).toBeInTheDocument();
    });

    expect(screen.getByDisplayValue('An existing character for editing tests')).toBeInTheDocument();
    // Campaign should be selected and disabled
    expect(screen.getByDisplayValue('Test Campaign 1')).toBeInTheDocument();
    expect(screen.getByLabelText('Campaign')).toBeDisabled();
  });

  test('loads polymorphic character fields', async () => {
    renderWithProviders(<CharacterForm {...defaultEditProps} />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('Existing Character')).toBeInTheDocument();
    });

    // Should show Mage-specific fields with values
    expect(screen.getByDisplayValue('3')).toBeInTheDocument(); // Arete
    expect(screen.getByDisplayValue('12')).toBeInTheDocument(); // Quintessence
    expect(screen.getByDisplayValue('1')).toBeInTheDocument(); // Paradox
  });

  test('prevents editing campaign in edit mode', async () => {
    renderWithProviders(<CharacterForm {...defaultEditProps} />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('Existing Character')).toBeInTheDocument();
    });

    const campaignSelect = screen.getByLabelText('Campaign');
    expect(campaignSelect).toBeDisabled();
  });

  test('prevents editing character type in edit mode', async () => {
    renderWithProviders(<CharacterForm {...defaultEditProps} />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('Existing Character')).toBeInTheDocument();
    });

    const characterTypeSelect = screen.getByLabelText('Character Type');
    expect(characterTypeSelect).toBeDisabled();
  });

  test('updates character successfully', async () => {
    const user = userEvent.setup();
    const mockOnSuccess = jest.fn();

    renderWithProviders(
      <CharacterForm {...defaultEditProps} onSuccess={mockOnSuccess} />
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue('Existing Character')).toBeInTheDocument();
    });

    // Update name and description
    const nameInput = screen.getByDisplayValue('Existing Character');
    await user.clear(nameInput);
    await user.type(nameInput, 'Updated Character Name');

    const descriptionInput = screen.getByDisplayValue('An existing character for editing tests');
    await user.clear(descriptionInput);
    await user.type(descriptionInput, 'Updated character description');

    // Update Mage-specific field
    const areteInput = screen.getByDisplayValue('3');
    await user.clear(areteInput);
    await user.type(areteInput, '4');

    // Submit form
    await user.click(screen.getByText('Update Character', { selector: 'button' }));

    await waitFor(() => {
      expect(mockOnSuccess).toHaveBeenCalledWith(expect.objectContaining({
        name: 'Updated Character Name',
        description: 'Updated character description',
        arete: 4
      }));
    });
  });

  test('handles character not found error', async () => {
    const props = { ...defaultEditProps, characterId: 999 };
    renderWithProviders(<CharacterForm {...props} />);

    await waitFor(() => {
      expect(screen.getByText('Character not found')).toBeInTheDocument();
    });

    expect(screen.getByText('The character you are trying to edit does not exist.')).toBeInTheDocument();
  });

  test('shows loading state during update', async () => {
    // Mock slow API response
    server.use(
      rest.patch('/api/characters/:id/', (req, res, ctx) => {
        return res(ctx.delay(1000), ctx.json(mockExistingCharacter));
      })
    );

    const user = userEvent.setup();
    renderWithProviders(<CharacterForm {...defaultEditProps} />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('Existing Character')).toBeInTheDocument();
    });

    // Make a change and submit
    await user.type(screen.getByDisplayValue('Existing Character'), ' Updated');
    await user.click(screen.getByText('Update Character', { selector: 'button' }));

    // Should show loading state
    expect(screen.getByText('Updating...')).toBeInTheDocument();
    expect(screen.getByText('Updating...', { selector: 'button' })).toBeDisabled();
  });
});

describe('CharacterForm Component - General Functionality', () => {
  test('preserves user input during validation', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CharacterForm mode="create" onSuccess={jest.fn()} onCancel={jest.fn()} />);

    const nameInput = screen.getByLabelText('Character Name');

    // Type progressively to test real-time validation
    await user.type(nameInput, 'A');

    // Should show validation error but preserve input
    await waitFor(() => {
      expect(screen.getByText('Name must be at least 2 characters')).toBeInTheDocument();
    });
    expect(nameInput).toHaveValue('A');

    // Continue typing
    await user.type(nameInput, 'valid Name');

    // Error should disappear, input should be preserved
    await waitFor(() => {
      expect(screen.queryByText('Name must be at least 2 characters')).not.toBeInTheDocument();
    });
    expect(nameInput).toHaveValue('Avalid Name');
  });

  test('clears form when switching between campaigns with different game systems', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CharacterForm mode="create" onSuccess={jest.fn()} onCancel={jest.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Test Campaign 1')).toBeInTheDocument();
    });

    // Select Mage campaign and character type
    await user.selectOptions(screen.getByLabelText('Campaign'), '1');

    await waitFor(() => {
      expect(screen.getByLabelText('Character Type')).toBeInTheDocument();
    });
    await user.selectOptions(screen.getByLabelText('Character Type'), 'MageCharacter');

    // Fill Mage-specific fields
    await waitFor(() => {
      expect(screen.getByLabelText('Arete')).toBeInTheDocument();
    });
    await user.type(screen.getByLabelText('Arete'), '3');

    // Switch to D&D campaign
    await user.selectOptions(screen.getByLabelText('Campaign'), '2');

    // Character type should reset and Mage fields should be gone
    await waitFor(() => {
      expect(screen.queryByLabelText('Arete')).not.toBeInTheDocument();
    });
  });

  test('provides helpful tooltips for complex fields', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CharacterForm mode="create" onSuccess={jest.fn()} onCancel={jest.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Test Campaign 1')).toBeInTheDocument();
    });

    // Select Mage campaign and character type
    await user.selectOptions(screen.getByLabelText('Campaign'), '1');
    await waitFor(() => {
      expect(screen.getByLabelText('Character Type')).toBeInTheDocument();
    });
    await user.selectOptions(screen.getByLabelText('Character Type'), 'MageCharacter');

    await waitFor(() => {
      expect(screen.getByLabelText('Arete')).toBeInTheDocument();
    });

    // Hover over Arete field to show tooltip
    const areteLabel = screen.getByLabelText('Arete');
    await user.hover(areteLabel);

    await waitFor(() => {
      expect(screen.getByText('Measures a mage\'s enlightenment and magical power (1-10)')).toBeInTheDocument();
    });
  });
});
