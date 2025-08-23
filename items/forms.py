"""
Forms for item management.

Provides form classes for creating and editing items with proper validation,
campaign context, and character ownership filtering.
"""

from django import forms
from django.core.validators import MinValueValidator

from characters.models import Character
from items.models import Item


class ItemForm(forms.ModelForm):
    """
    Form for creating and editing items.
    
    Handles validation, character filtering by campaign context,
    and proper ownership management.
    """
    
    class Meta:
        model = Item
        fields = ['name', 'description', 'quantity', 'owner']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter item name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter item description (optional)'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': '1'
            }),
            'owner': forms.Select(attrs={
                'class': 'form-select'
            }),
        }

    def __init__(self, *args, campaign=None, **kwargs):
        """
        Initialize form with campaign context.
        
        Args:
            campaign: Campaign instance to filter characters for ownership
        """
        self.campaign = campaign
        super().__init__(*args, **kwargs)
        
        # Filter owner choices to only characters in this campaign
        if campaign:
            self.fields['owner'].queryset = Character.objects.filter(
                campaign=campaign
            ).select_related('player_owner')
            
            # Add empty choice for no owner
            self.fields['owner'].empty_label = "No owner (unassigned)"
        else:
            # No campaign context, show empty queryset
            self.fields['owner'].queryset = Character.objects.none()
            
        # Set field requirements and help text
        self.fields['name'].help_text = "Enter a unique name for this item"
        self.fields['description'].required = False
        self.fields['description'].help_text = "Optional description for this item"
        self.fields['quantity'].help_text = "Number of items (minimum 1)"
        self.fields['owner'].help_text = "Character who owns this item (optional)"
        
    def clean_quantity(self):
        """Validate quantity is at least 1."""
        quantity = self.cleaned_data.get('quantity')
        if quantity is not None and quantity < 1:
            raise forms.ValidationError("Quantity must be at least 1.")
        return quantity
        
    def clean_name(self):
        """Validate name is provided and not just whitespace."""
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
            if not name:
                raise forms.ValidationError("Name cannot be empty or just whitespace.")
        return name
        
    def save(self, created_by=None, modified_by=None, commit=True):
        """
        Save the item with proper audit tracking and campaign context.
        
        Args:
            created_by: User creating the item (for new items)
            modified_by: User modifying the item (for existing items) 
            commit: Whether to save to database immediately
            
        Returns:
            Item instance
        """
        item = super().save(commit=False)
        
        # Set campaign context if creating new item
        if not item.pk and self.campaign:
            item.campaign = self.campaign
            
        # Set audit fields
        if not item.pk and created_by:
            item.created_by = created_by
        elif modified_by:
            item.modified_by = modified_by
            
        # Handle ownership transfer
        if commit and item.pk:
            # Check if owner changed
            original_item = Item.objects.get(pk=item.pk)
            if original_item.owner != item.owner:
                # Trigger transfer method to update timestamp
                if commit:
                    item.save()
                    item.transfer_to(item.owner)
                    return item
                    
        if commit:
            item.save()
            
        return item