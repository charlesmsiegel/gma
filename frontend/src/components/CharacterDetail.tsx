/**
 * CharacterDetail component for displaying character information.
 *
 * Features:
 * - Display character information with inline editing
 * - Role-based action button visibility
 * - Breadcrumb navigation
 * - Audit trail display (optional)
 * - Recent scenes display
 * - Responsive layout matching Django templates
 */

import React, { useState, useEffect } from 'react';
import { characterAPI, characterPermissions } from '../services/characterAPI';
import {
  Character,
  CharacterDetailProps,
  CharacterUpdateData,
  CharacterFormErrors,
  CharacterAuditEntry
} from '../types/character';

const CharacterDetail: React.FC<CharacterDetailProps> = ({
  characterId,
  userRole,
  currentUserId,
  onEdit,
  onDelete,
  showAuditTrail = false
}) => {
  // State management
  const [character, setCharacter] = useState<Character | null>(null);
  const [auditTrail, setAuditTrail] = useState<CharacterAuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Editing state
  const [isEditing, setIsEditing] = useState(false);
  const [editFormData, setEditFormData] = useState<CharacterUpdateData>({});
  const [editErrors, setEditErrors] = useState<CharacterFormErrors>({});
  const [editLoading, setEditLoading] = useState(false);

  // Success/error messages
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Load character data
  useEffect(() => {
    const loadCharacter = async () => {
      try {
        setLoading(true);
        setError(null);

        const characterData = await characterAPI.getCharacter(characterId);
        setCharacter(characterData);

        // Load audit trail if requested and user has permission
        if (showAuditTrail) {
          try {
            const auditData = await characterAPI.getCharacterAuditTrail(characterId);
            setAuditTrail(auditData);
          } catch (auditError: any) {
            // Ignore audit trail errors - user might not have permission
            console.warn('Could not load audit trail:', auditError.message);
          }
        }
      } catch (err: unknown) {
        setError((err as Error).message || 'Failed to load character');
      } finally {
        setLoading(false);
      }
    };

    loadCharacter();
  }, [characterId, showAuditTrail]);

  // Clear success messages after a delay
  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(function() { return setSuccessMessage(null) }, 5000);
      return function() { return clearTimeout(timer) };
    }
  }, [successMessage]);

  // Start editing mode
  const startEditing = () => {
    if (!character) return;

    setIsEditing(true);
    setEditFormData({
      name: character.name,
      description: character.description
    });
    setEditErrors({});
    onEdit?.();
  };

  // Cancel editing mode
  const cancelEditing = () => {
    setIsEditing(false);
    setEditFormData({});
    setEditErrors({});
  };

  // Save character changes
  const saveCharacter = async () => {
    if (!character) return;

    try {
      setEditLoading(true);
      setEditErrors({});

      const updatedCharacter = await characterAPI.updateCharacter(character.id, editFormData);
      setCharacter(updatedCharacter);
      setIsEditing(false);
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

  // Handle delete button click
  const handleDelete = () => {
    onDelete?.();
  };

  // Format date for display
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  // Format relative time for audit trail
  const formatRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));

    if (diffInHours < 24) {
      return `${diffInHours} hour${diffInHours !== 1 ? 's' : ''} ago`;
    } else {
      const diffInDays = Math.floor(diffInHours / 24);
      return `${diffInDays} day${diffInDays !== 1 ? 's' : ''} ago`;
    }
  };

  // Render loading state
  if (loading) {
    return (
      <div className="d-flex justify-content-center p-4">
        <div className="text-muted">Loading character...</div>
      </div>
    );
  }

  // Render error state
  if (error) {
    return (
      <div className="container-fluid">
        <div className="card">
          <div className="card-body text-center">
            <h5 className="card-title text-danger">Error loading character</h5>
            <p className="card-text">{error}</p>
            <button
              className="btn btn-primary"
              onClick={() => window.location.reload()}
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!character) {
    return (
      <div className="container-fluid">
        <div className="card">
          <div className="card-body text-center">
            <h5 className="card-title">Character not found</h5>
            <p className="card-text">The requested character could not be found.</p>
          </div>
        </div>
      </div>
    );
  }

  const canEdit = characterPermissions.canEdit(character, currentUserId, userRole);
  const canDelete = characterPermissions.canDelete(character, currentUserId, userRole);

  return (
    <div className="container-fluid">
      <div className="row">
        <div className="col-12">
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

          {/* Character Header */}
          <div className="card mb-4">
            <div className="card-header">
              <div className="d-flex justify-content-between align-items-center">
                <div>
                  <h1 className="card-title h3 mb-1">{character.name}</h1>
                  <p className="card-subtitle text-muted mb-0">
                    <i className="fas fa-dice-d20 me-1"></i>{character.game_system}
                    <span className="mx-2">•</span>
                    <button
                      className="btn btn-link p-0 text-decoration-none"
                      onClick={() => {
                        // Navigate to campaign detail
                        window.location.href = `/campaigns/${character.campaign.slug || character.campaign.id}/`;
                      }}
                    >
                      <i className="fas fa-flag me-1"></i>{character.campaign.name}
                    </button>
                  </p>
                </div>
                <div className="btn-group" role="group">
                  {canEdit && !isEditing && (
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={startEditing}
                    >
                      <i className="fas fa-edit me-1"></i>Edit Character
                    </button>
                  )}
                  {canDelete && !isEditing && (
                    <button
                      className="btn btn-outline-danger btn-sm"
                      onClick={handleDelete}
                    >
                      <i className="fas fa-trash me-1"></i>Delete
                    </button>
                  )}
                </div>
              </div>
            </div>
            <div className="card-body">
              <div className="row">
                <div className="col-md-8">
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
                      </div>

                      <div className="mb-3">
                        <label className="form-label">Character Background</label>
                        <textarea
                          className={`form-control ${editErrors.description ? 'is-invalid' : ''}`}
                          rows={5}
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
                          className="btn btn-primary"
                          onClick={saveCharacter}
                          disabled={editLoading || !editFormData.name}
                        >
                          {editLoading ? 'Saving...' : 'Save Changes'}
                        </button>
                        <button
                          className="btn btn-secondary"
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
                      {character.description ? (
                        <>
                          <h5>Character Background</h5>
                          <p className="lead">{character.description}</p>
                        </>
                      ) : (
                        <p className="text-muted fst-italic">No character description provided.</p>
                      )}
                    </>
                  )}
                </div>
                <div className="col-md-4">
                  <div className="card bg-light">
                    <div className="card-header">
                      <h6 className="card-title mb-0">Character Information</h6>
                    </div>
                    <div className="card-body">
                      <dl className="row mb-0">
                        <dt className="col-6">Owner:</dt>
                        <dd className="col-6">{character.player_owner.username}</dd>

                        <dt className="col-6">Created:</dt>
                        <dd className="col-6">{formatDate(character.created_at)}</dd>

                        <dt className="col-6">Updated:</dt>
                        <dd className="col-6">{formatDate(character.updated_at)}</dd>

                        <dt className="col-6">Campaign:</dt>
                        <dd className="col-6">
                          <button
                            className="btn btn-link p-0 text-decoration-none"
                            onClick={() => {
                              window.location.href = `/campaigns/${character.campaign.slug || character.campaign.id}/`;
                            }}
                          >
                            {character.campaign.name}
                          </button>
                        </dd>
                      </dl>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Character Sheets Section (Future Implementation) */}
          <div className="card mb-4">
            <div className="card-header">
              <h5 className="card-title mb-0">
                <i className="fas fa-clipboard-list me-2"></i>Character Sheet
              </h5>
            </div>
            <div className="card-body">
              <div className="alert alert-info" role="alert">
                <h6 className="alert-heading">Character Sheet Coming Soon!</h6>
                <p className="mb-0">
                  Detailed character sheets with stats, abilities, and traits will be available in a future update.
                  For now, you can edit the basic information above.
                </p>
              </div>
            </div>
          </div>

          {/* Recent Scenes Section */}
          <div className="card mb-4">
            <div className="card-header">
              <h5 className="card-title mb-0">
                <i className="fas fa-theater-masks me-2"></i>Recent Scenes
              </h5>
            </div>
            <div className="card-body">
              <p className="text-muted mb-0">This character hasn't participated in any scenes yet.</p>
            </div>
          </div>

          {/* Audit Trail Section */}
          {showAuditTrail && auditTrail.length > 0 && (
            <div className="card mb-4">
              <div className="card-header">
                <h5 className="card-title mb-0">
                  <i className="fas fa-history me-2"></i>Character History
                </h5>
              </div>
              <div className="card-body">
                <div className="list-group">
                  {auditTrail.map(entry => (
                    <div key={entry.id} className="list-group-item">
                      <div className="d-flex w-100 justify-content-between">
                        <h6 className="mb-1">
                          {entry.action === 'CREATE' && 'Character Created'}
                          {entry.action === 'UPDATE' && 'Character Updated'}
                          {entry.action === 'DELETE' && 'Character Deleted'}
                          {entry.action === 'RESTORE' && 'Character Restored'}
                        </h6>
                        <small>{formatRelativeTime(entry.timestamp)}</small>
                      </div>
                      <p className="mb-1">
                        by {entry.user?.username || 'System'}
                      </p>
                      {Object.keys(entry.changes).length > 0 && (
                        <small>
                          Changed: {Object.keys(entry.changes).join(', ')}
                        </small>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Navigation */}
          <div className="d-flex justify-content-between mt-4">
            <button
              className="btn btn-secondary"
              onClick={() => {
                window.location.href = `/campaigns/${character.campaign.slug || character.campaign.id}/`;
              }}
            >
              <i className="fas fa-arrow-left me-1"></i>Back to Campaign
            </button>
            {canEdit && !isEditing && (
              <button
                className="btn btn-primary"
                onClick={startEditing}
              >
                <i className="fas fa-edit me-1"></i>Edit Character
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CharacterDetail;
