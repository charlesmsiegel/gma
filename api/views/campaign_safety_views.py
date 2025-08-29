"""
API views for campaign safety management.
"""

import logging
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from campaigns.models import Campaign, CampaignSafetyAgreement
from campaigns.services.safety import CampaignSafetyService
from core.services.safety import SafetyValidationService
from ..serializers import (
    CampaignSafetySerializer,
    CampaignSafetyAgreementSerializer,
    CampaignSafetyOverviewSerializer,
    CampaignSafetyAgreementsStatusSerializer,
    SafetyCompatibilityRequestSerializer,
    SafetyCompatibilityResultSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def campaign_safety_view(request, campaign_id):
    """Get or update campaign safety settings."""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        return Response(
            {"detail": "Campaign not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if user has access to campaign
    user_role = campaign.get_user_role(request.user)
    if user_role is None:
        return Response(
            {"detail": "Campaign not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    service = CampaignSafetyService()
    
    if request.method == "GET":
        # Anyone with campaign access can view safety info
        serializer = CampaignSafetySerializer(campaign)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method == "PUT":
        # Only owners and GMs can update safety settings
        if user_role not in ["OWNER", "GM"]:
            return Response(
                {"detail": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = CampaignSafetySerializer(data=request.data)
        if serializer.is_valid():
            try:
                updated_campaign = service.update_campaign_safety_settings(
                    campaign=campaign,
                    updated_by=request.user,
                    content_warnings=serializer.validated_data.get('content_warnings'),
                    safety_tools_enabled=serializer.validated_data.get('safety_tools_enabled')
                )
                
                response_serializer = CampaignSafetySerializer(updated_campaign)
                logger.info(f"Campaign safety settings updated by {request.user.username} for campaign {campaign.id}")
                return Response(response_serializer.data, status=status.HTTP_200_OK)
                
            except ValidationError as e:
                return Response(
                    {"detail": str(e)},
                    status=status.HTTP_403_FORBIDDEN
                )
            except Exception as e:
                logger.error(f"Error updating campaign safety settings: {e}")
                return Response(
                    {"detail": "Failed to update safety settings"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "POST", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def campaign_safety_agreement_view(request, campaign_id):
    """Manage user's safety agreement for a campaign."""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        return Response(
            {"detail": "Campaign not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if user has access to campaign
    user_role = campaign.get_user_role(request.user)
    if user_role is None:
        return Response(
            {"detail": "Campaign not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    service = CampaignSafetyService()
    
    if request.method == "GET":
        # Get user's safety agreement
        agreement = service.get_user_safety_agreement(campaign, request.user)
        if agreement:
            serializer = CampaignSafetyAgreementSerializer(agreement)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {"detail": "No safety agreement found"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    elif request.method in ["POST", "PUT"]:
        # Create or update safety agreement
        serializer = CampaignSafetyAgreementSerializer(data=request.data)
        if serializer.is_valid():
            try:
                agreement = service.create_safety_agreement(
                    campaign=campaign,
                    user=request.user,
                    acknowledged_warnings=serializer.validated_data['acknowledged_warnings'],
                    agreed_to_terms=serializer.validated_data.get('agreed_to_terms', True)
                )
                
                response_serializer = CampaignSafetyAgreementSerializer(agreement)
                status_code = status.HTTP_201_CREATED if request.method == "POST" else status.HTTP_200_OK
                return Response(response_serializer.data, status=status_code)
                
            except ValidationError as e:
                return Response(
                    {"detail": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                logger.error(f"Error creating/updating safety agreement: {e}")
                return Response(
                    {"detail": "Failed to create/update safety agreement"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == "DELETE":
        # Delete safety agreement
        try:
            deleted = service.delete_safety_agreement(campaign, request.user, request.user)
            if deleted:
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(
                    {"detail": "No safety agreement found"},
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except ValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error deleting safety agreement: {e}")
            return Response(
                {"detail": "Failed to delete safety agreement"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def campaign_safety_agreements_view(request, campaign_id):
    """Get all safety agreements for a campaign (Owner/GM only)."""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        return Response(
            {"detail": "Campaign not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if user has access to campaign
    user_role = campaign.get_user_role(request.user)
    if user_role is None:
        return Response(
            {"detail": "Campaign not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Only owners and GMs can view all agreements
    if user_role not in ["OWNER", "GM"]:
        return Response(
            {"detail": "Permission denied"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    service = CampaignSafetyService()
    
    try:
        agreements_summary = service.get_campaign_agreements_summary(campaign, request.user)
        return Response({"agreements": agreements_summary["participants"]}, status=status.HTTP_200_OK)
        
    except ValidationError as e:
        return Response(
            {"detail": str(e)},
            status=status.HTTP_403_FORBIDDEN
        )
    except Exception as e:
        logger.error(f"Error getting campaign safety agreements: {e}")
        return Response(
            {"detail": "Failed to get safety agreements"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def campaign_safety_overview_view(request, campaign_id):
    """Get safety overview for a campaign."""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        return Response(
            {"detail": "Campaign not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if user has access to campaign
    user_role = campaign.get_user_role(request.user)
    if user_role is None:
        return Response(
            {"detail": "Campaign not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Players get limited access, GMs get full access
    validation_service = SafetyValidationService()
    
    try:
        if user_role in ["OWNER", "GM"]:
            # Full overview for GMs/Owners
            overview = validation_service.get_campaign_safety_overview(campaign, request.user)
            
            # Also get campaign safety service overview
            campaign_service = CampaignSafetyService()
            campaign_overview = campaign_service.get_campaign_safety_overview(campaign, request.user)
            
            # Combine data
            combined_overview = {
                **overview,
                "safety_summary": {
                    "campaign_name": campaign_overview["campaign_name"],
                    "safety_tools_enabled": campaign_overview["safety_tools_enabled"],
                    "content_warnings": campaign_overview["content_warnings"],
                    "user_role": campaign_overview["user_role"],
                }
            }
            
            if campaign_overview.get("gm_info"):
                combined_overview["agreements_status"] = campaign_overview["gm_info"]
            
            return Response(combined_overview, status=status.HTTP_200_OK)
        else:
            # Limited overview for players
            campaign_service = CampaignSafetyService()
            overview = campaign_service.get_campaign_safety_overview(campaign, request.user)
            
            # Remove sensitive information
            limited_overview = {
                "safety_summary": {
                    "campaign_name": overview["campaign_name"],
                    "safety_tools_enabled": overview["safety_tools_enabled"],
                    "content_warnings": overview["content_warnings"],
                    "user_agreement_status": overview.get("user_agreement_status"),
                    "warnings_to_acknowledge": overview.get("warnings_to_acknowledge", []),
                }
            }
            
            return Response(limited_overview, status=status.HTTP_200_OK)
            
    except ValidationError as e:
        return Response(
            {"detail": str(e)},
            status=status.HTTP_403_FORBIDDEN
        )
    except Exception as e:
        logger.error(f"Error getting campaign safety overview: {e}")
        return Response(
            {"detail": "Failed to get safety overview"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def campaign_safety_agreements_status_view(request, campaign_id):
    """Get safety agreement status for all campaign participants."""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        return Response(
            {"detail": "Campaign not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if user has access to campaign and is owner/GM
    user_role = campaign.get_user_role(request.user)
    if user_role is None:
        return Response(
            {"detail": "Campaign not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if user_role not in ["OWNER", "GM"]:
        return Response(
            {"detail": "Permission denied"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    service = CampaignSafetyService()
    
    try:
        agreements_summary = service.get_campaign_agreements_summary(campaign, request.user)
        
        # Transform data for response
        status_data = []
        for participant_data in agreements_summary["participants"]:
            agreement_status = participant_data["agreement_status"]
            status_entry = {
                "user_id": participant_data["user_id"],
                "username": participant_data["username"],
                "role": participant_data["role"],
                "has_agreement": agreement_status["has_agreement"],
                "agreed_to_terms": agreement_status["agreed_to_terms"],
                "last_updated": participant_data["last_updated"],
            }
            status_data.append(status_entry)
        
        return Response({"agreements_status": status_data}, status=status.HTTP_200_OK)
        
    except ValidationError as e:
        return Response(
            {"detail": str(e)},
            status=status.HTTP_403_FORBIDDEN
        )
    except Exception as e:
        logger.error(f"Error getting agreement status: {e}")
        return Response(
            {"detail": "Failed to get agreement status"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def campaign_safety_check_view(request, campaign_id):
    """Check safety compatibility between user and campaign."""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        return Response(
            {"detail": "Campaign not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if user has access to campaign and is owner/GM
    user_role = campaign.get_user_role(request.user)
    if user_role is None:
        return Response(
            {"detail": "Campaign not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if user_role not in ["OWNER", "GM"]:
        return Response(
            {"detail": "Permission denied"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = SafetyCompatibilityRequestSerializer(data=request.data)
    if serializer.is_valid():
        try:
            target_user = User.objects.get(id=serializer.validated_data["user_id"])
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        validation_service = SafetyValidationService()
        
        try:
            compatibility_result = validation_service.check_campaign_compatibility(target_user, campaign)
            response_data = {"compatibility_result": compatibility_result}
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error checking safety compatibility: {e}")
            return Response(
                {"detail": "Failed to check safety compatibility"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)