/**
 * TypeScript interfaces for Character-related data structures.
 *
 * These interfaces match the Django API serializers and models
 * to ensure type safety in React components.
 */

// Base user information as returned by character APIs
export interface CharacterUser {
  id: number;
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
}

// Campaign information as returned by character APIs
export interface CharacterCampaign {
  id: number;
  name: string;
  slug?: string;
  game_system: string;
}

// Base Character interface matching Django serializer
export interface Character {
  id: number;
  name: string;
  description: string;
  game_system: string;
  created_at: string;
  updated_at: string;
  campaign: CharacterCampaign;
  player_owner: CharacterUser;
  is_deleted: boolean;
  deleted_at: string | null;
  deleted_by: CharacterUser | null;
  character_type: string;
}

// Character creation/update data
export interface CharacterCreateData {
  name: string;
  description?: string;
  campaign: number;
}

export interface CharacterUpdateData {
  name?: string;
  description?: string;
}

// Character list response from API
export interface CharacterListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Character[];
}

// Character audit trail entry
export interface CharacterAuditEntry {
  id: number;
  action: 'CREATE' | 'UPDATE' | 'DELETE' | 'RESTORE';
  user: CharacterUser | null;
  timestamp: string;
  changes: Record<string, { old?: any; new?: any }>;
}

// Character list filters and search parameters
export interface CharacterListParams {
  campaign?: number;
  search?: string;
  user?: number;
  page?: number;
  page_size?: number;
  ordering?: string;
}

// Character permissions and role information
export interface CharacterPermissions {
  can_edit: boolean;
  can_delete: boolean;
  can_view: boolean;
  permission_level: 'owner' | 'campaign_owner' | 'gm' | 'read' | 'none';
}

// Form validation errors
export interface CharacterFormErrors {
  name?: string[];
  description?: string[];
  campaign?: string[];
  non_field_errors?: string[];
}

// API error response format
export interface APIError {
  detail?: string;
  [field: string]: string[] | string | undefined;
}

// Campaign information for character creation forms
export interface CampaignOption {
  id: number;
  name: string;
  slug: string;
  game_system: string;
  max_characters_per_player: number;
  user_character_count: number;
}

// Component props interfaces

export interface CharacterListProps {
  campaignId?: number;
  userRole: 'OWNER' | 'GM' | 'PLAYER' | 'OBSERVER';
  currentUserId: number;
  canManageAll: boolean;
  canCreateCharacter: boolean;
  onCharacterSelect?: (character: Character) => void;
  showCampaignFilter?: boolean;
  showUserFilter?: boolean;
}

export interface CharacterDetailProps {
  characterId: number;
  userRole: 'OWNER' | 'GM' | 'PLAYER' | 'OBSERVER';
  currentUserId: number;
  onEdit?: () => void;
  onDelete?: () => void;
  showAuditTrail?: boolean;
}

export interface CharacterEditFormProps {
  character?: Character;
  campaignId?: number;
  onSave: (character: Character) => void;
  onCancel: () => void;
  isInline?: boolean;
}

export interface CharacterCardProps {
  character: Character;
  userRole: 'OWNER' | 'GM' | 'PLAYER' | 'OBSERVER';
  currentUserId: number;
  canEdit: boolean;
  canDelete: boolean;
  onEdit?: () => void;
  onDelete?: () => void;
  isEditing?: boolean;
  onStartEdit?: () => void;
  onCancelEdit?: () => void;
  onSaveEdit?: (data: CharacterUpdateData) => void;
}

// State management interfaces
export interface CharacterListState {
  characters: Character[];
  loading: boolean;
  error: string | null;
  pagination: {
    count: number;
    next: string | null;
    previous: string | null;
    currentPage: number;
  };
  filters: CharacterListParams;
}

export interface CharacterDetailState {
  character: Character | null;
  auditTrail: CharacterAuditEntry[];
  loading: boolean;
  error: string | null;
  isEditing: boolean;
}
