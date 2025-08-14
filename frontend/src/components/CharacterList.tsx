/**
 * CharacterList component for displaying and managing characters.
 * 
 * Features:
 * - List characters with search and filtering
 * - Inline editing for character owners/GMs
 * - Role-based action visibility
 * - Pagination support
 * - Delete confirmation with name verification
 * - Responsive card layout matching Django templates
 */

import React, { useState, useEffect, useCallback } from 'react';
import { characterAPI, characterPermissions } from '../services/characterAPI';
import {
  Character,
  CharacterListProps,
  CharacterListParams,
  CharacterUpdateData,
  CharacterFormErrors
} from '../types/character';

const CharacterList: React.FC<CharacterListProps> = ({
  campaignId,
  userRole,
  currentUserId,
  canManageAll,
  canCreateCharacter,
  onCharacterSelect,
  showCampaignFilter = false,
  showUserFilter = false
}) => {
  // State management
  const [characters, setCharacters] = useState<Character[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedUserId, setSelectedUserId] = useState<number | undefined>();
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  
  // Editing state
  const [editingCharacterId, setEditingCharacterId] = useState<number | null>(null);
  const [editFormData, setEditFormData] = useState<CharacterUpdateData>({});
  const [editErrors, setEditErrors] = useState<CharacterFormErrors>({});
  const [editLoading, setEditLoading] = useState(false);
  
  // Delete confirmation state
  const [deletingCharacterId, setDeletingCharacterId] = useState<number | null>(null);
  const [deleteConfirmationName, setDeleteConfirmationName] = useState('');
  const [deleteLoading, setDeleteLoading] = useState(false);
  
  // Success/error messages
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Load characters function
  const loadCharacters = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params: CharacterListParams = {
        campaign: campaignId,
        search: searchTerm || undefined,
        user: selectedUserId,
        page: currentPage,
        page_size: 20,
        ordering: 'name'
      };
      
      const response = await characterAPI.getCharacters(params);
      
      setCharacters(response.results);
      setTotalCount(response.count);
      setTotalPages(Math.ceil(response.count / 20));
    } catch (err: any) {
      setError(err.message || 'Failed to load characters');
    } finally {
      setLoading(false);
    }
  }, [campaignId, searchTerm, selectedUserId, currentPage]);

  // Load characters on mount and when dependencies change
  useEffect(() => {
    loadCharacters();
  }, [loadCharacters]);

  // Clear success messages after a delay
  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => setSuccessMessage(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [successMessage]);

  // Handle search input change
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
    setCurrentPage(1); // Reset to first page when searching
  };

  // Handle user filter change
  const handleUserFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const userId = e.target.value ? parseInt(e.target.value) : undefined;
    setSelectedUserId(userId);
    setCurrentPage(1); // Reset to first page when filtering
  };

  // Handle pagination
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  // Start editing a character
  const startEditing = (character: Character) => {
    setEditingCharacterId(character.id);
    setEditFormData({
      name: character.name,
      description: character.description
    });
    setEditErrors({});
  };

  // Cancel editing
  const cancelEditing = () => {
    setEditingCharacterId(null);
    setEditFormData({});
    setEditErrors({});
  };

  // Save character changes
  const saveCharacter = async (characterId: number) => {
    try {
      setEditLoading(true);
      setEditErrors({});
      
      const updatedCharacter = await characterAPI.updateCharacter(characterId, editFormData);
      
      // Update character in list
      setCharacters(prev => 
        prev.map(char => char.id === characterId ? updatedCharacter : char)
      );
      
      setEditingCharacterId(null);
      setEditFormData({});
      setSuccessMessage('Character updated successfully');
    } catch (err: any) {
      if (err.validationErrors) {
        setEditErrors(err.validationErrors);
      } else {
        setError(err.message || 'Failed to update character');
      }
    } finally {
      setEditLoading(false);
    }
  };

  // Start character deletion
  const startDeleting = (characterId: number) => {
    setDeletingCharacterId(characterId);
    setDeleteConfirmationName('');
  };

  // Cancel character deletion
  const cancelDeleting = () => {
    setDeletingCharacterId(null);
    setDeleteConfirmationName('');
  };

  // Confirm character deletion
  const confirmDelete = async () => {
    if (!deletingCharacterId) return;
    
    const character = characters.find(c => c.id === deletingCharacterId);
    if (!character) return;
    
    if (deleteConfirmationName !== character.name) {
      return; // Button should be disabled, but just in case
    }
    
    try {
      setDeleteLoading(true);
      await characterAPI.deleteCharacter(deletingCharacterId, deleteConfirmationName);
      
      // Remove character from list
      setCharacters(prev => prev.filter(c => c.id !== deletingCharacterId));
      setTotalCount(prev => prev - 1);
      
      setDeletingCharacterId(null);
      setDeleteConfirmationName('');
      setSuccessMessage('Character deleted successfully');
    } catch (err: any) {
      setError(err.message || 'Failed to delete character');
    } finally {
      setDeleteLoading(false);
    }
  };

  // Get unique users for filter dropdown
  const availableUsers = Array.from(
    new Set(characters.map(c => c.player_owner.id))
  ).map(id => {
    const user = characters.find(c => c.player_owner.id === id)?.player_owner;
    return user;
  }).filter(Boolean);

  // Retry loading on error
  const retryLoading = () => {
    loadCharacters();
  };

  // Render loading state
  if (loading && characters.length === 0) {
    return (
      <div className="d-flex justify-content-center p-4">
        <div className="text-muted">Loading characters...</div>
      </div>
    );
  }

  // Render error state
  if (error && characters.length === 0) {
    return (
      <div className="card">
        <div className="card-body text-center">
          <h5 className="card-title text-danger">Error loading characters</h5>
          <p className="card-text">{error}</p>
          <button className="btn btn-primary" onClick={retryLoading}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="container-fluid">
      {/* Page Header */}
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h1 className="h2 mb-1">
            {campaignId ? 'Campaign Characters' : 'My Characters'}
          </h1>
          <p className="text-muted mb-0">
            {totalCount} character{totalCount !== 1 ? 's' : ''} found
          </p>
        </div>
        {canCreateCharacter && (
          <button className="btn btn-primary">
            <i className="bi bi-plus-circle"></i> Create Character
          </button>
        )}
      </div>

      {/* Success Message */}
      {successMessage && (
        <div className="alert alert-success alert-dismissible fade show" role="alert">
          {successMessage}
          <button
            type="button"
            className="btn-close"
            onClick={() => setSuccessMessage(null)}
            aria-label="Close"
          ></button>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="alert alert-danger alert-dismissible fade show" role="alert">
          {error}
          <button
            type="button"
            className="btn-close"
            onClick={() => setError(null)}
            aria-label="Close"
          ></button>
        </div>
      )}

      {/* Search and Filter Form */}
      {(characters.length > 0 || searchTerm || selectedUserId) && (
        <div className="card mb-4">
          <div className="card-body">
            <div className="row g-3 align-items-end">
              <div className={showUserFilter ? "col-md-6" : "col-md-8"}>
                <label htmlFor="search" className="form-label">Search Characters</label>
                <input
                  type="text"
                  className="form-control"
                  id="search"
                  value={searchTerm}
                  onChange={handleSearchChange}
                  placeholder="Search characters..."
                />
              </div>
              
              {showUserFilter && canManageAll && (
                <div className="col-md-4">
                  <label htmlFor="user-filter" className="form-label">Filter by Player</label>
                  <select
                    className="form-select"
                    id="user-filter"
                    aria-label="Filter by Player"
                    value={selectedUserId || ''}
                    onChange={handleUserFilterChange}
                  >
                    <option value="">All Players</option>
                    {availableUsers.map(user => user && (
                      <option key={user.id} value={user.id}>
                        {user.username}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              
              <div className="col-md-2">
                <div className="d-flex gap-2">
                  <button 
                    type="button" 
                    className="btn btn-primary"
                    onClick={loadCharacters}
                    disabled={loading}
                  >
                    <i className="bi bi-search"></i> Search
                  </button>
                  {(searchTerm || selectedUserId) && (
                    <button
                      type="button"
                      className="btn btn-outline-secondary"
                      onClick={() => {
                        setSearchTerm('');
                        setSelectedUserId(undefined);
                        setCurrentPage(1);
                      }}
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Characters List */}
      {characters.length > 0 ? (
        <>
          <div className="row">
            {characters.map(character => {
              const canEdit = characterPermissions.canEdit(character, currentUserId, userRole);
              const canDelete = characterPermissions.canDelete(character, currentUserId, userRole);
              const isEditing = editingCharacterId === character.id;
              const isDeleting = deletingCharacterId === character.id;

              return (
                <div key={character.id} className="col-lg-6 col-xl-4 mb-4">
                  <div className="card h-100">
                    <div className="card-body">
                      {isEditing ? (
                        // Inline editing form
                        <div>
                          <div className="mb-3">
                            <label className="form-label">Character Name</label>
                            <input
                              type="text"
                              className={`form-control ${editErrors.name ? 'is-invalid' : ''}`}
                              value={editFormData.name || ''}
                              onChange={(e) => setEditFormData(prev => ({
                                ...prev,
                                name: e.target.value
                              }))}
                              disabled={editLoading}
                            />
                            {editErrors.name && (
                              <div className="invalid-feedback">
                                {editErrors.name.join(', ')}
                              </div>
                            )}
                            {editFormData.name && editFormData.name.length < 2 && (
                              <div className="text-warning small">
                                Name must be at least 2 characters
                              </div>
                            )}
                          </div>
                          
                          <div className="mb-3">
                            <label className="form-label">Description</label>
                            <textarea
                              className={`form-control ${editErrors.description ? 'is-invalid' : ''}`}
                              rows={3}
                              value={editFormData.description || ''}
                              onChange={(e) => setEditFormData(prev => ({
                                ...prev,
                                description: e.target.value
                              }))}
                              disabled={editLoading}
                            />
                            {editErrors.description && (
                              <div className="invalid-feedback">
                                {editErrors.description.join(', ')}
                              </div>
                            )}
                          </div>
                          
                          <div className="d-flex gap-2">
                            <button
                              className="btn btn-primary btn-sm"
                              onClick={() => saveCharacter(character.id)}
                              disabled={editLoading || !editFormData.name || editFormData.name.length < 2}
                            >
                              {editLoading ? 'Saving...' : 'Save'}
                            </button>
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={cancelEditing}
                              disabled={editLoading}
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        // Normal character display
                        <>
                          <div className="d-flex justify-content-between align-items-start mb-2">
                            <h5 className="card-title mb-0">
                              <button
                                className="btn btn-link p-0 text-decoration-none"
                                onClick={() => onCharacterSelect?.(character)}
                              >
                                {character.name}
                              </button>
                            </h5>
                            <span className="badge bg-secondary">{character.game_system}</span>
                          </div>

                          <h6 className="card-subtitle mb-2 text-muted">
                            {character.campaign.name}
                          </h6>

                          {character.description && (
                            <p className="card-text">
                              {character.description.length > 100
                                ? `${character.description.substring(0, 100)}...`
                                : character.description
                              }
                            </p>
                          )}

                          <div className="text-muted small mb-2">
                            Player: {character.player_owner.username}
                          </div>

                          <div className="text-muted small">
                            Created {new Date(character.created_at).toLocaleDateString()}
                            {character.updated_at !== character.created_at && (
                              <>
                                {' • Updated '}
                                {new Date(character.updated_at).toLocaleDateString()}
                              </>
                            )}
                          </div>
                        </>
                      )}
                    </div>

                    {!isEditing && (
                      <div className="card-footer bg-transparent">
                        <div className="d-flex justify-content-between">
                          <button
                            className="btn btn-sm btn-outline-primary"
                            onClick={() => onCharacterSelect?.(character)}
                          >
                            <i className="bi bi-eye"></i> View
                          </button>
                          
                          <div className="d-flex gap-1">
                            {canEdit && (
                              <button
                                className="btn btn-sm btn-outline-secondary"
                                onClick={() => startEditing(character)}
                                aria-label={`Edit ${character.name}`}
                              >
                                <i className="bi bi-pencil"></i> Edit
                              </button>
                            )}
                            
                            {canDelete && (
                              <button
                                className="btn btn-sm btn-outline-danger"
                                onClick={() => startDeleting(character.id)}
                                aria-label={`Delete ${character.name}`}
                              >
                                <i className="bi bi-trash"></i> Delete
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <nav aria-label="Characters pagination">
              <ul className="pagination justify-content-center">
                {currentPage > 1 && (
                  <>
                    <li className="page-item">
                      <button
                        className="page-link"
                        onClick={() => handlePageChange(1)}
                        disabled={loading}
                      >
                        First
                      </button>
                    </li>
                    <li className="page-item">
                      <button
                        className="page-link"
                        onClick={() => handlePageChange(currentPage - 1)}
                        disabled={loading}
                      >
                        Previous
                      </button>
                    </li>
                  </>
                )}

                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  const page = Math.max(1, Math.min(currentPage - 2 + i, totalPages - 4 + i));
                  return (
                    <li key={page} className={`page-item ${currentPage === page ? 'active' : ''}`}>
                      <button
                        className="page-link"
                        onClick={() => handlePageChange(page)}
                        disabled={loading}
                      >
                        {page}
                      </button>
                    </li>
                  );
                })}

                {currentPage < totalPages && (
                  <>
                    <li className="page-item">
                      <button
                        className="page-link"
                        onClick={() => handlePageChange(currentPage + 1)}
                        disabled={loading}
                      >
                        Next
                      </button>
                    </li>
                    <li className="page-item">
                      <button
                        className="page-link"
                        onClick={() => handlePageChange(totalPages)}
                        disabled={loading}
                      >
                        Last
                      </button>
                    </li>
                  </>
                )}
              </ul>
            </nav>
          )}
        </>
      ) : (
        // Empty state
        <div className="row justify-content-center">
          <div className="col-lg-8">
            <div className="card text-center">
              <div className="card-body p-5">
                <div className="mb-4">
                  {searchTerm || selectedUserId ? (
                    <>
                      <h3 className="h4 text-muted">No characters found</h3>
                      <p className="text-muted">
                        No characters match your search criteria.
                      </p>
                      <button
                        className="btn btn-outline-secondary"
                        onClick={() => {
                          setSearchTerm('');
                          setSelectedUserId(undefined);
                          setCurrentPage(1);
                        }}
                      >
                        Clear Filters
                      </button>
                    </>
                  ) : (
                    <>
                      <h3 className="h4 text-muted">No characters yet</h3>
                      <p className="text-muted">
                        Create your first character to get started!
                      </p>
                      {canCreateCharacter && (
                        <button className="btn btn-primary">
                          <i className="bi bi-plus-circle"></i> Create your first character
                        </button>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deletingCharacterId && (
        <div className="modal show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Confirm Character Deletion</h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={cancelDeleting}
                  disabled={deleteLoading}
                ></button>
              </div>
              <div className="modal-body">
                <p>
                  Are you sure you want to delete this character? This action cannot be undone.
                </p>
                <p className="text-muted">
                  Type the character name to confirm:
                </p>
                <input
                  type="text"
                  className="form-control"
                  value={deleteConfirmationName}
                  onChange={(e) => setDeleteConfirmationName(e.target.value)}
                  placeholder="Enter character name"
                  disabled={deleteLoading}
                />
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={cancelDeleting}
                  disabled={deleteLoading}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-danger"
                  onClick={confirmDelete}
                  disabled={
                    deleteLoading ||
                    deleteConfirmationName !== characters.find(c => c.id === deletingCharacterId)?.name
                  }
                >
                  {deleteLoading ? 'Deleting...' : 'Delete Character'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CharacterList;