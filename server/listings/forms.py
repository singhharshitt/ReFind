from django import forms

from .models import Listing, Message, Report, Request, User


class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = (
            'title', 'description', 'category', 'condition', 'listing_type',
            'price', 'wanted_item_text', 'image', 'image2', 'image3',
        )
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'price': forms.NumberInput(attrs={'min': '0', 'step': '1'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('listing_type') == Listing.ListingType.SELL and cleaned_data.get('price') is None:
            self.add_error('price', 'Sale listings need a price.')
        if cleaned_data.get('listing_type') == Listing.ListingType.EXCHANGE and not cleaned_data.get('wanted_item_text'):
            self.add_error('wanted_item_text', 'Exchange listings need a wanted item.')
        if cleaned_data.get('listing_type') != Listing.ListingType.EXCHANGE:
            cleaned_data['wanted_item_text'] = ''
        return cleaned_data


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'phone', 'hostel', 'bio')


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ('body',)
        widgets = {'body': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Write a message...'})}


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ('reason',)
        widgets = {'reason': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Tell us what is wrong with this listing...'})}


class RequestForm(forms.ModelForm):
    class Meta:
        model = Request
        fields = ('message',)
        widgets = {'message': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Add a note to the seller...'})}
