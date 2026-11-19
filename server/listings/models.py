from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class User(AbstractUser):
    email = models.EmailField(unique=True)
    campus_verified = models.BooleanField(default=False)
    phone = models.CharField(max_length=30, blank=True)
    hostel = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=20, choices=(('student', 'Student'), ('admin', 'Administrator')), default='student')
    bio = models.TextField(blank=True)
    avatar_initials = models.CharField(max_length=4, blank=True)

    def save(self, *args, **kwargs):
        if not self.avatar_initials:
            self.avatar_initials = ''.join(part[0] for part in self.get_full_name().split()[:2]).upper()
        super().save(*args, **kwargs)


class Listing(models.Model):
    class Category(models.TextChoices):
        BOOKS = 'books', 'Books'
        ELECTRONICS = 'electronics', 'Electronics'
        FURNITURE = 'furniture', 'Furniture'
        CYCLES = 'cycles', 'Cycles'
        SPORTS = 'sports', 'Sports'
        ESSENTIALS = 'essentials', 'Hostel Essentials'
        OTHER = 'other', 'Other'

    class Condition(models.TextChoices):
        NEW = 'new', 'New'
        LIKE_NEW = 'like-new', 'Like New'
        GOOD = 'good', 'Good'
        FAIR = 'fair', 'Fair'
        USED = 'used', 'Used'

    class ListingType(models.TextChoices):
        SELL = 'sell', 'For Sale'
        EXCHANGE = 'exchange', 'For Exchange'
        DONATE = 'donate', 'For Donation'

    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        RESERVED = 'reserved', 'Reserved'
        SOLD = 'sold', 'Sold'
        EXCHANGED = 'exchanged', 'Exchanged'
        DONATED = 'donated', 'Donated'
        UNAVAILABLE = 'unavailable', 'Unavailable'

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='listings')
    title = models.CharField(max_length=160)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=Category.choices)
    condition = models.CharField(max_length=20, choices=Condition.choices)
    listing_type = models.CharField(max_length=20, choices=ListingType.choices)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    wanted_item_text = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    image = models.URLField(blank=True)
    image2 = models.URLField(blank=True)
    image3 = models.URLField(blank=True)
    saved_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='saved_listings', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=('status', 'category', 'created_at')),
            models.Index(fields=('price',)),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(listing_type='sell', price__isnull=False) | ~Q(listing_type='sell'),
                name='sell_listings_require_price',
            ),
        ]

    def clean(self):
        if self.listing_type == self.ListingType.SELL and self.price is None:
            raise ValidationError({'price': 'A sale listing must include a price.'})
        if self.listing_type == self.ListingType.EXCHANGE and not self.wanted_item_text:
            raise ValidationError({'wanted_item_text': 'Exchange listings must say what you want in return.'})
        if self.listing_type != self.ListingType.EXCHANGE:
            self.wanted_item_text = ''

    @property
    def kind(self):
        return self.listing_type

    @property
    def kind_label(self):
        return self.get_listing_type_display()

    @property
    def price_label(self):
        if self.listing_type == self.ListingType.DONATE:
            return 'Free'
        if self.listing_type == self.ListingType.EXCHANGE:
            return self.wanted_item_text or 'Open to exchange'
        return f'₹{self.price:,.0f}'

    @property
    def seller(self):
        return self.owner.get_full_name() or self.owner.username

    @property
    def seller_initial(self):
        return self.owner.avatar_initials or self.seller[:2].upper()

    @property
    def rating(self):
        value = Request.objects.filter(
            listing__owner=self.owner, status=Request.Status.COMPLETED, rating__isnull=False
        ).aggregate(
            average=models.Avg('rating')
        )['average']
        return f'{value:.1f}' if value is not None else 'New'

    @property
    def image_url(self):
        return self.image or 'https://images.unsplash.com/photo-1495446815901-a7297e633e8d?auto=format&fit=crop&w=900&q=80'


class Request(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        REJECTED = 'rejected', 'Rejected'
        CANCELLED = 'cancelled', 'Cancelled'
        COMPLETED = 'completed', 'Completed'

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='requests')
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='requests')
    offered_listing = models.ForeignKey(Listing, on_delete=models.SET_NULL, null=True, blank=True, related_name='exchange_requests')
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    review_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('listing', 'requester'),
                condition=Q(status='pending'),
                name='one_pending_request_per_user',
            ),
            models.CheckConstraint(
                condition=Q(rating__isnull=True) | Q(rating__gte=1, rating__lte=5),
                name='request_rating_between_one_and_five',
            ),
        ]

    def clean(self):
        if self.requester_id == self.listing.owner_id:
            raise ValidationError('You cannot request your own listing.')
        if self.offered_listing and self.offered_listing.owner_id != self.requester_id:
            raise ValidationError('An exchange offer must belong to the requester.')


class Message(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_messages')
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)


class Report(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        RESOLVED = 'resolved', 'Resolved'
        DISMISSED = 'dismissed', 'Dismissed'

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='reports')
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
