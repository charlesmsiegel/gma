/**
 * CharacterEditForm component for creating and editing characters.
 *
 * Features:
 * - Form for creating new characters and editing existing ones
 * - Campaign selection with character limits
 * - Real-time validation with error handling
 * - Loading states and error messages
 * - Responsive layout matching Django templates
 * - Support for both standalone and inline editing modes
 */

import React, { useState, useEffect } from 'react';
import { characterAPI } from '../services/characterAPI';
import {
  Character,
  CharacterEditFormProps,
  CharacterCreateData,
  CharacterUpdateData,
  CharacterFormErrors,
  CampaignOption
} from '../types/character';

const CharacterEditForm: React.FC<CharacterEditFormProps> = ({
  character,
  campaignId,
  onSave,
  onCancel,
  isInline = false
}) => {
  // Form state
  const [formData, setFormData] = useState<CharacterCreateData | CharacterUpdateData>({
    name: character?.name || '',
    description: character?.description || '',
    ...(character ? {} : { campaign: campaignId || 0 })
  });

  // Validation and UI state
  const [errors, setErrors] = useState<CharacterFormErrors>({});
  const [loading, setLoading] = useState(false);
  const [campaigns, setCampaigns] = useState<CampaignOption[]>([]);
  const [campaignsLoading, setCampaignsLoading] = useState(!character); // Don't load campaigns for editing

  // Load campaigns for creation mode
  useEffect(() => {
    if (!character) {
      const loadCampaigns = async () => {
        try {
          setCampaignsLoading(true);
          const campaignData = await characterAPI.getAvailableCampaigns();
          setCampaigns(campaignData);
        } catch (err: any) {
          setErrors({ campaign: [err.message || 'Failed to load campaigns'] });
        } finally {
          setCampaignsLoading(false);
        }
      };

      loadCampaigns();
    }
  }, [character]);

  // Handle form field changes
  const handleFieldChange = (field: string, value: string | number) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));

    // Clear field-specific errors when user types
    if (errors[field as keyof CharacterFormErrors]) {
      setErrors(prev => ({
        ...prev,
        [field]: undefined
      }));
    }
  };

  // Validate form data
  const validateForm = (): boolean => {
    const newErrors: CharacterFormErrors = {};

    // Name validation
    if (!formData.name || formData.name.trim().length === 0) {
      newErrors.name = ['Character name is required'];
    } else if (formData.name.trim().length < 2) {
      newErrors.name = ['Character name must be at least 2 characters'];
    } else if (formData.name.length > 100) {
      newErrors.name = ['Character name cannot exceed 100 characters'];
    }

    // Campaign validation (only for creation)
    if (!character) {
      const createData = formData as CharacterCreateData;
      if (!createData.campaign || createData.campaign === 0) {
        newErrors.campaign = ['Please select a campaign'];
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    try {
      setLoading(true);
      setErrors({});

      let savedCharacter: Character;

      if (character) {
        // Update existing character
        savedCharacter = await characterAPI.updateCharacter(
          character.id,
          formData as CharacterUpdateData
        );
      } else {
        // Create new character
        savedCharacter = await characterAPI.createCharacter(
          formData as CharacterCreateData
        );
      }

      onSave(savedCharacter);
    } catch (err: any) {
      if (err.validationErrors) {
        setErrors(err.validationErrors);
      } else {
        setErrors({
          non_field_errors: [err.message || 'Failed to save character']
        });
      }
    } finally {
      setLoading(false);
    }
  };

  // Handle cancel
  const handleCancel = () => {
    onCancel();
  };

  // Get selected campaign info
  const selectedCampaign = campaigns.find(c => c.id === (formData as CharacterCreateData).campaign);

  // Check if user is at character limit
  const isAtCharacterLimit = selectedCampaign &&
    selectedCampaign.max_characters_per_player > 0 &&
    selectedCampaign.user_character_count >= selectedCampaign.max_characters_per_player;

  const formTitle = character ? 'Edit Character' : 'Create Character';
  const submitButtonText = loading ? 'Saving...' : (character ? 'Save Changes' : 'Create Character');

  // Inline mode rendering (simplified)
  if (isInline) {
    return (
      <form onSubmit={handleSubmit} className="character-edit-form-inline">
        {errors.non_field_errors && (
          <div className="alert alert-danger" role="alert">
            {errors.non_field_errors.map((error, index) => (
              <div key={index}>{error}</div>
            ))}
          </div>
        )}

        <div className="mb-3">
          <label className="form-label">Character Name</label>
          <input
            type="text"
            className={`form-control ${errors.name ? 'is-invalid' : ''}`}
            value={formData.name}
            onChange={(e) => handleFieldChange('name', e.target.value)}
            disabled={loading}
            maxLength={100}
          />
          {errors.name && (
            <div className="invalid-feedback">
              {errors.name.join(', ')}
            </div>
          )}
        </div>

        <div className="mb-3">
          <label className="form-label">Description</label>
          <textarea
            className={`form-control ${errors.description ? 'is-invalid' : ''}`}
            rows={3}
            value={formData.description || ''}
            onChange={(e) => handleFieldChange('description', e.target.value)}
            disabled={loading}
          />
          {errors.description && (
            <div className="invalid-feedback">
              {errors.description.join(', ')}
            </div>
          )}
        </div>

        <div className="d-flex gap-2">
          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading || !formData.name || formData.name.trim().length < 2}
          >
            {submitButtonText}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleCancel}
            disabled={loading}
          >
            Cancel
          </button>
        </div>
      </form>
    );
  }

  // Full form rendering (standalone)
  return (
    <div className="container-fluid">
      <div className="row justify-content-center">
        <div className="col-12 col-lg-8">
          {/* Breadcrumb Navigation */}
          {character && (
            <nav aria-label="breadcrumb" className="mb-4">
              <ol className="breadcrumb">
                <li className="breadcrumb-item">
                  <button
                    type="button"
                    className="btn btn-link p-0 text-decoration-none"
                    onClick={() => {
                      window.location.href = `/campaigns/${character.campaign.slug || character.campaign.id}/`;
                    }}
                  >
                    <i className="bi bi-flag me-1"></i>{character.campaign.name}
                  </button>
                </li>
                <li className="breadcrumb-item">
                  <button
                    type="button"
                    className="btn btn-link p-0 text-decoration-none"
                    onClick={() => {
                      window.location.href = `/characters/${character.id}/`;
                    }}
                  >
                    <i className="bi bi-person me-1"></i>{character.name}
                  </button>
                </li>
                <li className="breadcrumb-item active" aria-current="page">Edit</li>
              </ol>
            </nav>
          )}

          <div className="card">
            <div className="card-header">
              <div className="d-flex justify-content-between align-items-center">
                <h1 className="card-title h3 mb-0">{formTitle}</h1>
                {character && (
                  <div className="d-flex align-items-center text-muted">
                    <i className="bi bi-dice-3 me-2"></i>{character.game_system}
                  </div>
                )}
              </div>
            </div>
            <div className="card-body">
              <form onSubmit={handleSubmit} noValidate>
                {errors.non_field_errors && (
                  <div className="alert alert-danger" role="alert">
                    <h6 className="alert-heading">Form Errors:</h6>
                    {errors.non_field_errors.map((error, index) => (
                      <p key={index} className="mb-0">{error}</p>
                    ))}
                  </div>
                )}

                <div className="row">
                  {/* Character Name */}
                  <div className={character ? "col-md-6" : "col-md-8"}>
                    <div className="mb-3">
                      <label htmlFor="character-name" className="form-label">
                        Character Name <span className="text-danger">*</span>
                      </label>
                      <input
                        type="text"
                        className={`form-control ${errors.name ? 'is-invalid' : ''}`}
                        id="character-name"
                        value={formData.name}
                        onChange={(e) => handleFieldChange('name', e.target.value)}
                        disabled={loading}
                        maxLength={100}
                        required
                      />
                      {errors.name && (
                        <div className="invalid-feedback">
                          {errors.name.join(', ')}
                        </div>
                      )}
                      <div className="form-text">
                        Must be unique within the campaign
                      </div>
                    </div>
                  </div>

                  {/* Campaign Selection (creation only) */}
                  {!character && (
                    <div className="col-md-4">
                      <div className="mb-3">
                        <label htmlFor="campaign-select" className="form-label">
                          Campaign <span className="text-danger">*</span>
                        </label>
                        <select
                          className={`form-select ${errors.campaign ? 'is-invalid' : ''}`}
                          id="campaign-select"
                          value={(formData as CharacterCreateData).campaign || ''}
                          onChange={(e) => handleFieldChange('campaign', parseInt(e.target.value))}
                          disabled={loading || campaignsLoading}
                          required
                        >
                          <option value="">Select a campaign</option>
                          {campaigns.map(campaign => (
                            <option
                              key={campaign.id}
                              value={campaign.id}
                              disabled={
                                campaign.max_characters_per_player > 0 &&
                                campaign.user_character_count >= campaign.max_characters_per_player
                              }
                            >
                              {campaign.name} ({campaign.game_system})
                              {campaign.max_characters_per_player > 0 && (
                                ` - ${campaign.user_character_count}/${campaign.max_characters_per_player} chars`
                              )}
                            </option>
                          ))}
                        </select>
                        {errors.campaign && (
                          <div className="invalid-feedback">
                            {errors.campaign.join(', ')}
                          </div>
                        )}
                        {isAtCharacterLimit && (
                          <div className="text-warning small">
                            You are at the character limit for this campaign
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Campaign Info (editing only) */}
                  {character && (
                    <div className="col-md-6">
                      <div className="mb-3">
                        <label className="form-label">Campaign</label>
                        <div className="form-control-plaintext bg-light p-2 rounded">
                          <i className="bi bi-flag me-2"></i>{character.campaign.name}
                          <small className="text-muted d-block">{character.game_system}</small>
                        </div>
                        <div className="form-text">Campaign cannot be changed after character creation.</div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Character Description */}
                <div className="mb-3">
                  <label htmlFor="character-description" className="form-label">
                    Description
                  </label>
                  <textarea
                    className={`form-control ${errors.description ? 'is-invalid' : ''}`}
                    id="character-description"
                    rows={5}
                    value={formData.description || ''}
                    onChange={(e) => handleFieldChange('description', e.target.value)}
                    disabled={loading}
                    placeholder="Describe your character's background, personality, and appearance..."
                  />
                  {errors.description && (
                    <div className="invalid-feedback">
                      {errors.description.join(', ')}
                    </div>
                  )}
                  <div className="form-text">
                    Optional character background and description
                  </div>
                </div>

                {/* Character Information Card (editing only) */}
                {character && (
                  <div className="card bg-light mb-4">
                    <div className="card-header">
                      <h6 className="card-title mb-0">
                        <i className="bi bi-info-circle me-2"></i>Character Information
                      </h6>
                    </div>
                    <div className="card-body">
                      <div className="row">
                        <div className="col-md-6">
                          <dl className="row mb-0">
                            <dt className="col-sm-6">Owner:</dt>
                            <dd className="col-sm-6">{character.player_owner.username}</dd>

                            <dt className="col-sm-6">Created:</dt>
                            <dd className="col-sm-6">
                              {new Date(character.created_at).toLocaleDateString()}
                            </dd>
                          </dl>
                        </div>
                        <div className="col-md-6">
                          <dl className="row mb-0">
                            <dt className="col-sm-6">Campaign:</dt>
                            <dd className="col-sm-6">{character.campaign.name}</dd>

                            <dt className="col-sm-6">Game System:</dt>
                            <dd className="col-sm-6">{character.game_system}</dd>
                          </dl>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Form Actions */}
                <div className="d-flex justify-content-between">
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={handleCancel}
                    disabled={loading}
                  >
                    <i className="bi bi-arrow-left me-1"></i>Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={
                      loading ||
                      !formData.name ||
                      formData.name.trim().length < 2 ||
                      (!character && !((formData as CharacterCreateData).campaign)) ||
                      isAtCharacterLimit
                    }
                  >
                    <i className="bi bi-check-lg me-1"></i>{submitButtonText}
                  </button>
                </div>
              </form>
            </div>
          </div>

          {/* Additional Information */}
          <div className="card mt-4">
            <div className="card-body">
              <div className="row">
                <div className="col-md-8">
                  <h6 className="text-muted mb-2">
                    <i className="bi bi-lightbulb me-1"></i>
                    {character ? 'Editing Guidelines' : 'Character Creation Guidelines'}
                  </h6>
                  <ul className="small text-muted mb-0">
                    <li>Character names must be unique within each campaign</li>
                    {!character && <li>You can only create characters in campaigns where you're a member</li>}
                    {character && <li>Changes are tracked for campaign staff review</li>}
                    {character && <li>Campaign and game system cannot be changed after creation</li>}
                    <li>Character sheets and stats will be available in future updates</li>
                  </ul>
                </div>
                <div className="col-md-4">
                  <h6 className="text-muted mb-2">
                    <i className="bi bi-shield-check me-1"></i>Required Information
                  </h6>
                  <div className="small text-muted">
                    <div className="d-flex align-items-center mb-1">
                      <i className="bi bi-check-circle text-success me-2"></i>
                      Character name (2-100 characters)
                    </div>
                    {!character && (
                      <div className="d-flex align-items-center mb-1">
                        <i className="bi bi-check-circle text-success me-2"></i>
                        Campaign selection
                      </div>
                    )}
                    <div className="d-flex align-items-center">
                      <i className="bi bi-dash-circle text-muted me-2"></i>
                      Description (optional)
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CharacterEditForm;
