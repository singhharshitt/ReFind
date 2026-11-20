from django import forms

from .models import Listing, Message, Report, Request, User


class ListingForm(forms.ModelForm):
    """Form for creating or editing a listing."""

    class Meta:
        model = Listing
        fields = (
            'title',
            'description',
            'category',
            'condition',
            'listing_type',
            'price',
            'wanted_item_text',
            'image',
            'image2',
            'image3',
        )
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describe your item: condition details, included accessories, reason for selling...'}),
            'price': forms.NumberInput(attrs={'min': '0', 'step': '1', 'placeholder': '₹ 0'}),
            'wanted_item_text': forms.TextInput(attrs={'placeholder': 'e.g. Programming textbook, DSA book...'}),
            'title': forms.TextInput(attrs={'placeholder': 'e.g. MacBook Air M1 2020'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Main image required on create; optional on edit when one already exists.
        has_existing_image = bool(self.instance and self.instance.pk and self.instance.image)
        self.fields['image'].required = not has_existing_image
        self.fields['image2'].required = False
        self.fields['image3'].required = False
        self.fields['price'].required = False
        self.fields['wanted_item_text'].required = False
        self.fields['image'].label = 'Main Image (required)'
        self.fields['image2'].label = 'Second Image (optional)'
        self.fields['image3'].label = 'Third Image (optional)'
        for name in self.fields:
            css = self.fields[name].widget.attrs.get('class', '')
            self.fields[name].widget.attrs['class'] = f'{css} rf-input'.strip()

    def clean(self):
        cleaned_data = super().clean()
        listing_type = cleaned_data.get('listing_type')
        price = cleaned_data.get('price')
        wanted = cleaned_data.get('wanted_item_text', '').strip()
        image = cleaned_data.get('image')

        if listing_type == Listing.ListingType.SELL and price is None:
            self.add_error('price', 'Sale listings need a price.')
        if listing_type == Listing.ListingType.EXCHANGE and not wanted:
            self.add_error('wanted_item_text', 'Tell people what you want in return for the exchange.')
        if listing_type != Listing.ListingType.EXCHANGE:
            cleaned_data['wanted_item_text'] = ''
        if listing_type != Listing.ListingType.SELL:
            cleaned_data['price'] = None
        if not image and not (self.instance and self.instance.pk and self.instance.image):
            self.add_error('image', 'Please upload at least one photo of your item.')
        return cleaned_data


class ExchangeRequestForm(forms.ModelForm):
    """Form for submitting an exchange request, with optional offered_listing selection."""

    class Meta:
        model = Request
        fields = ('offered_listing', 'message')
        widgets = {
            'message': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Tell the owner what you are offering and why...'}),
        }

    def __init__(self, *args, requester=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['offered_listing'].required = False
        self.fields['offered_listing'].label = 'Your listing to offer (optional)'
        if requester is not None:
            # Any available listing owned by the requester can be offered in an exchange.
            self.fields['offered_listing'].queryset = Listing.objects.filter(
                owner=requester,
                status=Listing.Status.AVAILABLE,
            ).order_by('-created_at')
        else:
            self.fields['offered_listing'].queryset = Listing.objects.none()
        self.fields['offered_listing'].empty_label = 'Select one of your listings (optional)'


class RequestForm(forms.ModelForm):
    """Simple request form (buy / donate) with just a message note."""

    class Meta:
        model = Request
        fields = ('message',)
        widgets = {
            'message': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Add a note to the seller (optional)...'}),
        }


class ProfileForm(forms.ModelForm):
    """Form for editing user profile details."""

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'phone', 'hostel', 'bio', 'avatar')
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Tell other students a little about yourself...'}),
            'phone': forms.TextInput(attrs={'placeholder': '+91 98765 43210'}),
            'hostel': forms.TextInput(attrs={'placeholder': 'e.g. Block A, Room 204'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        # Keep full_name and avatar_initials in sync
        full = f'{user.first_name} {user.last_name}'.strip()
        if full:
            user.full_name = full
        parts = (user.full_name or user.username).split()
        user.avatar_initials = ''.join(p[0] for p in parts[:2]).upper() if parts else 'U'
        if commit:
            user.save()
        return user


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ('body',)
        widgets = {
            'body': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Write a message...',
                'class': 'message-input',
            }),
        }


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ('reason',)
        widgets = {
            'reason': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Tell us what is wrong with this listing...',
            }),
        }
