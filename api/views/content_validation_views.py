"""
API views for content validation against safety preferences.
"""

import logging
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from campaigns.models import Campaign
from core.services.safety import SafetyValidationService
from ..serializers import (
    ContentValidationRequestSerializer,
    ContentValidationResponseSerializer,
    CampaignContentValidationRequestSerializer,
    CampaignContentValidationResponseSerializer,
    PreSceneCheckRequestSerializer,
    PreSceneCheckResponseSerializer,
    BatchContentValidationRequestSerializer,
    BatchContentValidationResponseSerializer,
    UserValidationResultSerializer,
    ContentItemResultSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def validate_content_view(request):
    """Validate content against general safety guidelines."""
    # This is a generic endpoint that could be used for general content checking
    # without specific user context
    validation_service = SafetyValidationService()
    
    content = request.data.get("content", "")
    if not content:
        return Response({
            "is_safe": True,
            "lines_violated": [],
            "veils_triggered": [],
            "privacy_restricted": False,
            "consent_required": False,
            "safety_tools_disabled": False,
        }, status=status.HTTP_200_OK)
    
    # Generate generic content warnings
    warnings = validation_service.generate_content_warnings(content)
    
    return Response({
        "is_safe": len(warnings) == 0,
        "generated_warnings": warnings,
        "lines_violated": [],
        "veils_triggered": [],
        "privacy_restricted": False,
        "consent_required": False,
        "safety_tools_disabled": False,
    }, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def validate_content_for_user_view(request):
    """Validate content against a specific user's safety preferences."""
    serializer = ContentValidationRequestSerializer(data=request.data)
    if serializer.is_valid():
        try:
            campaign = Campaign.objects.get(id=serializer.validated_data["campaign_id"])
            target_user = User.objects.get(id=serializer.validated_data["user_id"])
        except Campaign.DoesNotExist:
            return Response(
                {"detail": "Campaign not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if requesting user has access to campaign
        requesting_user_role = campaign.get_user_role(request.user)
        if requesting_user_role is None:
            return Response(
                {"detail": "Campaign not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if target user is in campaign
        target_user_role = campaign.get_user_role(target_user)
        if target_user_role is None:
            return Response(
                {"detail": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        validation_service = SafetyValidationService()
        
        try:
            result = validation_service.validate_content(
                content=serializer.validated_data["content"],
                user=target_user,
                campaign=campaign,
                requesting_user=request.user
            )
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error validating content for user: {e}")
            return Response(
                {"detail": "Failed to validate content"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def validate_content_for_campaign_view(request):
    """Validate content against all campaign participants' preferences."""
    serializer = CampaignContentValidationRequestSerializer(data=request.data)
    if serializer.is_valid():
        try:
            campaign = Campaign.objects.get(id=serializer.validated_data["campaign_id"])
        except Campaign.DoesNotExist:
            return Response(
                {"detail": "Campaign not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if requesting user has access to campaign
        user_role = campaign.get_user_role(request.user)
        if user_role is None:
            return Response(
                {"detail": "Campaign not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        validation_service = SafetyValidationService()
        
        try:
            result = validation_service.validate_content_for_campaign(
                content=serializer.validated_data["content"],
                campaign=campaign
            )
            
            # Transform user_results dict to list format for serializer
            user_results_list = []
            for username, user_result in result["user_results"].items():
                user_results_list.append({
                    "user_id": None,  # We'd need to get this from the campaign
                    "username": username,
                    "is_safe": user_result["is_safe"],
                    "lines_violated": user_result["lines_violated"],
                    "veils_triggered": user_result["veils_triggered"],
                    "consent_required": user_result.get("consent_required", False),
                })
            
            # Get user IDs for the results
            from campaigns.services.campaign_services import MembershipService
            membership_service = MembershipService(campaign)
            
            # Create mapping of username to user ID
            username_to_id = {campaign.owner.username: campaign.owner.id}
            for membership in membership_service.get_campaign_members():
                username_to_id[membership.user.username] = membership.user.id
            
            # Update user results with IDs
            for user_result in user_results_list:
                user_result["user_id"] = username_to_id.get(user_result["username"])
            
            response_data = {
                "is_safe": result["is_safe"],
                "user_results": user_results_list,
                "overall_violations": result["overall_violations"]
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error validating content for campaign: {e}")
            return Response(
                {"detail": "Failed to validate content"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def pre_scene_safety_check_view(request):
    """Perform pre-scene safety check."""
    serializer = PreSceneCheckRequestSerializer(data=request.data)
    if serializer.is_valid():
        try:
            campaign = Campaign.objects.get(id=serializer.validated_data["campaign_id"])
        except Campaign.DoesNotExist:
            return Response(
                {"detail": "Campaign not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if requesting user has access to campaign
        user_role = campaign.get_user_role(request.user)
        if user_role is None:
            return Response(
                {"detail": "Campaign not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Only GMs and owners can perform pre-scene checks
        if user_role not in ["OWNER", "GM"]:
            return Response(
                {"detail": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        validation_service = SafetyValidationService()
        
        try:
            result = validation_service.pre_scene_safety_check(
                campaign=campaign,
                planned_content_summary=serializer.validated_data.get("planned_content_summary")
            )
            
            return Response({
                "check_results": result,
                "recommendations": result.get("required_actions", []),
                "safety_warnings": result.get("warnings", [])
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error performing pre-scene safety check: {e}")
            return Response(
                {"detail": "Failed to perform safety check"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def validate_content_batch_view(request):
    """Validate multiple content items at once."""
    serializer = BatchContentValidationRequestSerializer(data=request.data)
    if serializer.is_valid():
        try:
            campaign = Campaign.objects.get(id=serializer.validated_data["campaign_id"])
        except Campaign.DoesNotExist:
            return Response(
                {"detail": "Campaign not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if requesting user has access to campaign
        user_role = campaign.get_user_role(request.user)
        if user_role is None:
            return Response(
                {"detail": "Campaign not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        validation_service = SafetyValidationService()
        results = []
        
        try:
            for content_item in serializer.validated_data["content_items"]:
                # Validate each content item against campaign participants
                validation_result = validation_service.validate_content_for_campaign(
                    content=content_item["content"],
                    campaign=campaign
                )
                
                # Transform user results to list format
                user_results_list = []
                for username, user_result in validation_result["user_results"].items():
                    user_results_list.append({
                        "user_id": None,  # We'd need user lookup for this
                        "username": username,
                        "is_safe": user_result["is_safe"],
                        "lines_violated": user_result["lines_violated"],
                        "veils_triggered": user_result["veils_triggered"],
                        "consent_required": user_result.get("consent_required", False),
                    })
                
                # Get user IDs for the results
                from campaigns.services.campaign_services import MembershipService
                membership_service = MembershipService(campaign)
                
                # Create mapping of username to user ID
                username_to_id = {campaign.owner.username: campaign.owner.id}
                for membership in membership_service.get_campaign_members():
                    username_to_id[membership.user.username] = membership.user.id
                
                # Update user results with IDs
                for user_result in user_results_list:
                    user_result["user_id"] = username_to_id.get(user_result["username"])
                
                item_result = {
                    "id": content_item["id"],
                    "is_safe": validation_result["is_safe"],
                    "lines_violated": validation_result["overall_violations"].get("lines", []),
                    "veils_triggered": validation_result["overall_violations"].get("veils", []),
                    "user_results": user_results_list
                }
                
                results.append(item_result)
            
            return Response({"results": results}, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error performing batch content validation: {e}")
            return Response(
                {"detail": "Failed to validate content batch"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)