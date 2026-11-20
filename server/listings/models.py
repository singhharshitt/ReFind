from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Avg, Q


class User(AbstractUser):
    """Custom user model for ReFind.  One row per campus student or admin."""

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=160, blank=True)
    campus_verified = models.BooleanField(default=False)
    phone = models.CharField(max_length=30, blank=True)
    hostel = models.CharField(max_length=100, blank=True)
    role = models.CharField(
        max_length=20,
        choices=(('student', 'Student'), ('admin', 'Administrator')),
        default='student',
    )
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    avatar_initials = models.CharField(max_length=4, blank=True)

    # saved_listings is on Listing.saved_by (ManyToMany) → access via user.saved_listings

    def save(self, *args, **kwargs):
        # Keep full_name in sync with first_name + last_name from AbstractUser
        if self.first_name or self.last_name:
            computed = f'{self.first_name} {self.last_name}'.strip()
            if computed:
                self.full_name = computed
        if not self.avatar_initials:
            name = self.full_name or self.get_full_name() or self.username
            parts = name.split()
            self.avatar_initials = ''.join(p[0] for p in parts[:2]).upper() if parts else 'U'
        super().save(*args, **kwargs)

    def get_display_name(self):
        return self.full_name or self.get_full_name() or self.username

    def get_avg_rating(self):
        """Average rating received as a seller across all completed requests."""
        value = Request.objects.filter(
            listing__owner=self,
            status=Request.Status.COMPLETED,
            rating__isnull=False,
        ).aggregate(avg=Avg('rating'))['avg']
        return round(value, 1) if value is not None else None


class Listing(models.Model):
    """A product offered for sale, exchange, or donation."""

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

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='listings'
    )
    title = models.CharField(max_length=160)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=Category.choices)
    condition = models.CharField(max_length=20, choices=Condition.choices)
    listing_type = models.CharField(max_length=20, choices=ListingType.choices)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    wanted_item_text = models.CharField(max_length=200, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.AVAILABLE
    )
    # Images stored as uploaded files (Pillow required); first image required.
    image = models.ImageField(upload_to='listings/', null=True, blank=True)
    image2 = models.ImageField(upload_to='listings/', null=True, blank=True)
    image3 = models.ImageField(upload_to='listings/', null=True, blank=True)
    saved_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name='saved_listings', blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=('status', 'category', 'created_at')),
            models.Index(fields=('price',)),
            models.Index(fields=('listing_type',)),
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
            raise ValidationError(
                {'wanted_item_text': 'Exchange listings must say what you want in return.'}
            )
        if self.listing_type != self.ListingType.EXCHANGE:
            self.wanted_item_text = ''

    # ── Convenience properties ───────────────────────────────────────────────

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
        if self.price is not None:
            return f'₹{self.price:,.0f}'
        return '–'

    @property
    def seller(self):
        return self.owner.get_display_name()

    @property
    def seller_initial(self):
        return self.owner.avatar_initials or self.seller[:2].upper()

    @property
    def rating(self):
        value = self.owner.get_avg_rating()
        return f'{value}' if value is not None else 'New'

    def get_primary_image_url(self):
        """Return the URL of the first available image, with a fallback."""
        for field in (self.image, self.image2, self.image3):
            if field:
                return field.url
        return 'https://images.unsplash.com/photo-1495446815901-a7297e633e8d?auto=format&fit=crop&w=900&q=80'

    # Legacy alias used by existing listing_card.html template
    @property
    def image_url(self):
        return self.get_primary_image_url()

    def is_available(self):
        return self.status == self.Status.AVAILABLE


class Request(models.Model):
    """A buy / exchange / donation request sent by a student to a listing owner."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        REJECTED = 'rejected', 'Rejected'
        CANCELLED = 'cancelled', 'Cancelled'
        COMPLETED = 'completed', 'Completed'

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='requests')
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='requests'
    )
    offered_listing = models.ForeignKey(
        Listing,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exchange_requests',
    )
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
    """A single message in a listing-based conversation thread."""

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages'
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_messages'
    )
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ('sent_at',)
        indexes = [
            models.Index(fields=('listing', 'sender', 'recipient', 'sent_at')),
        ]


class Report(models.Model):
    """A user's report of an inappropriate or fraudulent listing."""

    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        RESOLVED = 'resolved', 'Resolved'
        DISMISSED = 'dismissed', 'Dismissed'

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='reports')
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
