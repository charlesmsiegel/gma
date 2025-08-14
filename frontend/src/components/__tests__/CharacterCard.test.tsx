/**
 * Tests for CharacterCard component.
 *
 * Tests character card functionality including:
 * - Displaying character summary information
 * - Role-based action visibility
 * - Quick actions (edit, delete)
 * - Character status indicators
 * - Click-through navigation
 * - Responsive layout
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../../contexts/AuthContext';
import CharacterCard from '../CharacterCard';

// Mock character data
const mockCharacter = {
  id: 1,
  name: 'Test Character',
  description: 'A test character with a longer description that should be truncated properly when displayed in the card format.',
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
  character_type: 'MageCharacter',
  // Polymorphic fields
  arete: 3,
  quintessence: 12,
  paradox: 1
};

const mockDeletedCharacter = {
  ...mockCharacter,
  id: 2,
  name: 'Deleted Character',
  is_deleted: true,
  deleted_at: '2023-02-01T10:00:00Z',
  deleted_by: { id: 2, username: 'gm' }
};

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
const renderWithProviders = (component: React.ReactElement) => {
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
    <MemoryRouter>
      <AuthProvider value={authContextValue}>
        {component}
      </AuthProvider>
    </MemoryRouter>
  );
};

describe('CharacterCard Component', () => {
  const defaultProps = {
    character: mockCharacter,
    currentUserId: 1,
    userRole: 'PLAYER' as const,
    canEdit: true,
    canDelete: true,
    onClick: jest.fn(),
    onEdit: jest.fn(),
    onDelete: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders character information correctly', () => {
    renderWithProviders(<CharacterCard {...defaultProps} />);

    expect(screen.getByText('Test Character')).toBeInTheDocument();
    expect(screen.getByText('Mage: The Ascension')).toBeInTheDocument();
    expect(screen.getByText('John Player')).toBeInTheDocument();
    expect(screen.getByText('Test Campaign')).toBeInTheDocument();
  });

  test('truncates long descriptions with ellipsis', () => {
    renderWithProviders(<CharacterCard {...defaultProps} />);

    const description = screen.getByText(/A test character with a longer description/);
    expect(description).toBeInTheDocument();
    // Should be truncated (exact text depends on implementation)
    expect(description.textContent).toMatch(/\.\.\.$/);
  });

  test('shows full description on hover/expansion', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CharacterCard {...defaultProps} />);

    const descriptionElement = screen.getByText(/A test character with a longer description/);

    // Hover to show full description
    await user.hover(descriptionElement);

    await waitFor(() => {
      expect(screen.getByText(/properly when displayed in the card format/)).toBeInTheDocument();
    });
  });

  test('displays character creation date', () => {
    renderWithProviders(<CharacterCard {...defaultProps} />);

    expect(screen.getByText('Created: Jan 1, 2023')).toBeInTheDocument();
  });

  test('displays last updated date when different from creation', () => {
    renderWithProviders(<CharacterCard {...defaultProps} />);

    expect(screen.getByText('Updated: Jan 15, 2023')).toBeInTheDocument();
  });

  test('displays polymorphic character stats', () => {
    renderWithProviders(<CharacterCard {...defaultProps} />);

    // Should show key Mage stats
    expect(screen.getByText('Arete: 3')).toBeInTheDocument();
    expect(screen.getByText('Quintessence: 12')).toBeInTheDocument();
    expect(screen.getByText('Paradox: 1')).toBeInTheDocument();
  });

  test('shows edit button when user has edit permission', () => {
    renderWithProviders(<CharacterCard {...defaultProps} />);

    const editButton = screen.getByLabelText('Edit Test Character');
    expect(editButton).toBeInTheDocument();
  });

  test('hides edit button when user lacks edit permission', () => {
    const props = { ...defaultProps, canEdit: false };
    renderWithProviders(<CharacterCard {...props} />);

    expect(screen.queryByLabelText('Edit Test Character')).not.toBeInTheDocument();
  });

  test('shows delete button when user has delete permission', () => {
    renderWithProviders(<CharacterCard {...defaultProps} />);

    const deleteButton = screen.getByLabelText('Delete Test Character');
    expect(deleteButton).toBeInTheDocument();
  });

  test('hides delete button when user lacks delete permission', () => {
    const props = { ...defaultProps, canDelete: false };
    renderWithProviders(<CharacterCard {...props} />);

    expect(screen.queryByLabelText('Delete Test Character')).not.toBeInTheDocument();
  });

  test('calls onClick when card is clicked', async () => {
    const user = userEvent.setup();
    const mockOnClick = jest.fn();

    renderWithProviders(
      <CharacterCard {...defaultProps} onClick={mockOnClick} />
    );

    const cardElement = screen.getByRole('article'); // Assuming card uses article role
    await user.click(cardElement);

    expect(mockOnClick).toHaveBeenCalledWith(mockCharacter);
  });

  test('calls onEdit when edit button is clicked', async () => {
    const user = userEvent.setup();
    const mockOnEdit = jest.fn();

    renderWithProviders(
      <CharacterCard {...defaultProps} onEdit={mockOnEdit} />
    );

    const editButton = screen.getByLabelText('Edit Test Character');
    await user.click(editButton);

    expect(mockOnEdit).toHaveBeenCalledWith(mockCharacter);
  });

  test('calls onDelete when delete button is clicked', async () => {
    const user = userEvent.setup();
    const mockOnDelete = jest.fn();

    renderWithProviders(
      <CharacterCard {...defaultProps} onDelete={mockOnDelete} />
    );

    const deleteButton = screen.getByLabelText('Delete Test Character');
    await user.click(deleteButton);

    expect(mockOnDelete).toHaveBeenCalledWith(mockCharacter);
  });

  test('prevents card click when action buttons are clicked', async () => {
    const user = userEvent.setup();
    const mockOnClick = jest.fn();
    const mockOnEdit = jest.fn();

    renderWithProviders(
      <CharacterCard {...defaultProps} onClick={mockOnClick} onEdit={mockOnEdit} />
    );

    const editButton = screen.getByLabelText('Edit Test Character');
    await user.click(editButton);

    // Should call onEdit but not onClick
    expect(mockOnEdit).toHaveBeenCalled();
    expect(mockOnClick).not.toHaveBeenCalled();
  });

  test('displays deleted character with proper styling and warning', () => {
    const props = { ...defaultProps, character: mockDeletedCharacter };
    renderWithProviders(<CharacterCard {...props} />);

    expect(screen.getByText('Deleted Character')).toBeInTheDocument();
    expect(screen.getByText('Deleted')).toBeInTheDocument();
    expect(screen.getByText('Feb 1, 2023 by gm')).toBeInTheDocument();

    // Card should have deleted styling (test implementation specific class)
    const cardElement = screen.getByRole('article');
    expect(cardElement).toHaveClass('character-card--deleted');
  });

  test('shows restore option for deleted character when user has permission', () => {
    const props = {
      ...defaultProps,
      character: mockDeletedCharacter,
      userRole: 'GM' as const,
      canRestore: true
    };
    renderWithProviders(<CharacterCard {...props} />);

    expect(screen.getByLabelText('Restore Deleted Character')).toBeInTheDocument();
  });

  test('hides restore option for deleted character when user lacks permission', () => {
    const props = {
      ...defaultProps,
      character: mockDeletedCharacter,
      userRole: 'PLAYER' as const,
      canRestore: false
    };
    renderWithProviders(<CharacterCard {...props} />);

    expect(screen.queryByLabelText('Restore Deleted Character')).not.toBeInTheDocument();
  });

  test('displays character avatar when available', () => {
    const characterWithAvatar = {
      ...mockCharacter,
      avatar_url: '/media/avatars/character1.jpg'
    };
    const props = { ...defaultProps, character: characterWithAvatar };

    renderWithProviders(<CharacterCard {...props} />);

    const avatar = screen.getByAltText('Test Character avatar');
    expect(avatar).toBeInTheDocument();
    expect(avatar).toHaveAttribute('src', '/media/avatars/character1.jpg');
  });

  test('displays default avatar when character has no custom avatar', () => {
    renderWithProviders(<CharacterCard {...defaultProps} />);

    const defaultAvatar = screen.getByLabelText('Default character avatar');
    expect(defaultAvatar).toBeInTheDocument();
  });

  test('shows character type badge', () => {
    renderWithProviders(<CharacterCard {...defaultProps} />);

    expect(screen.getByText('Mage')).toBeInTheDocument();
  });

  test('displays campaign link', () => {
    renderWithProviders(<CharacterCard {...defaultProps} />);

    const campaignLink = screen.getByRole('link', { name: 'Test Campaign' });
    expect(campaignLink).toBeInTheDocument();
    expect(campaignLink).toHaveAttribute('href', '/campaigns/test-campaign');
  });

  test('shows character status indicators', () => {
    const activeCharacter = {
      ...mockCharacter,
      last_active: '2023-01-20T15:30:00Z',
      is_online: true
    };
    const props = { ...defaultProps, character: activeCharacter };

    renderWithProviders(<CharacterCard {...props} />);

    expect(screen.getByLabelText('Character recently active')).toBeInTheDocument();
    expect(screen.getByText('Last active: 4 days ago')).toBeInTheDocument();
  });

  test('handles missing optional character data gracefully', () => {
    const minimalCharacter = {
      id: 1,
      name: 'Minimal Character',
      description: '',
      campaign: { id: 1, name: 'Test Campaign', slug: 'test-campaign' },
      player_owner: { id: 1, username: 'player1' },
      game_system: 'Generic',
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z',
      is_deleted: false,
      deleted_at: null,
      deleted_by: null
    };
    const props = { ...defaultProps, character: minimalCharacter };

    renderWithProviders(<CharacterCard {...props} />);

    expect(screen.getByText('Minimal Character')).toBeInTheDocument();
    expect(screen.getByText('Generic')).toBeInTheDocument();
    // Should not show description section when empty
    expect(screen.queryByText('No description provided')).not.toBeInTheDocument();
  });

  test('supports keyboard navigation', async () => {
    const user = userEvent.setup();
    const mockOnClick = jest.fn();

    renderWithProviders(
      <CharacterCard {...defaultProps} onClick={mockOnClick} />
    );

    const cardElement = screen.getByRole('article');

    // Tab to focus the card
    await user.tab();
    expect(cardElement).toHaveFocus();

    // Press Enter to activate
    await user.keyboard('{Enter}');
    expect(mockOnClick).toHaveBeenCalledWith(mockCharacter);
  });

  test('shows loading state when character data is being updated', () => {
    const props = { ...defaultProps, isUpdating: true };
    renderWithProviders(<CharacterCard {...props} />);

    expect(screen.getByLabelText('Character updating')).toBeInTheDocument();

    // Action buttons should be disabled during update
    const editButton = screen.getByLabelText('Edit Test Character');
    expect(editButton).toBeDisabled();
  });

  test('displays error state when character has validation issues', () => {
    const characterWithErrors = {
      ...mockCharacter,
      has_errors: true,
      error_message: 'Character sheet validation failed'
    };
    const props = { ...defaultProps, character: characterWithErrors };

    renderWithProviders(<CharacterCard {...props} />);

    expect(screen.getByLabelText('Character has validation errors')).toBeInTheDocument();
    expect(screen.getByText('Validation errors')).toBeInTheDocument();
  });

  test('handles very long character names gracefully', () => {
    const longNameCharacter = {
      ...mockCharacter,
      name: 'This is a very long character name that should be handled gracefully by the card component'
    };
    const props = { ...defaultProps, character: longNameCharacter };

    renderWithProviders(<CharacterCard {...props} />);

    const nameElement = screen.getByText(/This is a very long character name/);
    expect(nameElement).toBeInTheDocument();
    // Should apply text truncation CSS
    expect(nameElement).toHaveClass('character-card__name--long');
  });

  test('shows favorite indicator when character is favorited', () => {
    const favoritedCharacter = {
      ...mockCharacter,
      is_favorited: true
    };
    const props = { ...defaultProps, character: favoritedCharacter };

    renderWithProviders(<CharacterCard {...props} />);

    expect(screen.getByLabelText('Favorited character')).toBeInTheDocument();
  });

  test('displays recent activity summary', () => {
    const activeCharacter = {
      ...mockCharacter,
      recent_scenes: 3,
      last_scene_date: '2023-01-18T20:00:00Z'
    };
    const props = { ...defaultProps, character: activeCharacter };

    renderWithProviders(<CharacterCard {...props} />);

    expect(screen.getByText('3 recent scenes')).toBeInTheDocument();
    expect(screen.getByText('Last scene: 2 days ago')).toBeInTheDocument();
  });

  test('supports compact layout mode', () => {
    const props = { ...defaultProps, layout: 'compact' };
    renderWithProviders(<CharacterCard {...props} />);

    const cardElement = screen.getByRole('article');
    expect(cardElement).toHaveClass('character-card--compact');

    // In compact mode, some details should be hidden
    expect(screen.queryByText(/A test character with a longer description/)).not.toBeInTheDocument();
  });

  test('supports detailed layout mode', () => {
    const props = { ...defaultProps, layout: 'detailed' };
    renderWithProviders(<CharacterCard {...props} />);

    const cardElement = screen.getByRole('article');
    expect(cardElement).toHaveClass('character-card--detailed');

    // In detailed mode, more information should be visible
    expect(screen.getByText('Character Details')).toBeInTheDocument();
  });
});
