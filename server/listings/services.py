"""Business-logic services for the ReFind marketplace.

All operations that touch multiple rows in one logical unit live here,
keeping views thin and making the logic easy to test.
"""

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Listing, Request


@transaction.atomic
def accept_request(marketplace_request, owner):
    """Accept a pending request; reserve the listing; auto-reject all other pending requests.

    Uses select_for_update() so a concurrent acceptance on the same listing must
    wait — this prevents two students from securing the same item.
    """
    listing = Listing.objects.select_for_update().get(pk=marketplace_request.listing_id)

    if listing.owner_id != owner.id:
        raise ValidationError('Only the listing owner can accept requests.')
    if listing.status != Listing.Status.AVAILABLE:
        raise ValidationError('This listing is no longer available.')
    if marketplace_request.status != Request.Status.PENDING:
        raise ValidationError('Only pending requests can be accepted.')

    marketplace_request.status = Request.Status.ACCEPTED
    marketplace_request.save(update_fields=('status', 'updated_at'))

    # Auto-reject all other pending requests for the same listing
    Request.objects.filter(
        listing=listing,
        status=Request.Status.PENDING,
    ).exclude(pk=marketplace_request.pk).update(status=Request.Status.REJECTED)

    listing.status = Listing.Status.RESERVED
    listing.save(update_fields=('status', 'updated_at'))

    return marketplace_request


@transaction.atomic
def complete_request(marketplace_request, user):
    """Mark a request as completed and update the listing status accordingly.

    Either the listing owner or the requester can mark it completed (they agreed
    in person).
    """
    if user.id not in (marketplace_request.listing.owner_id, marketplace_request.requester_id):
        raise ValidationError('Only the participants can complete a request.')
    if marketplace_request.status != Request.Status.ACCEPTED:
        raise ValidationError('Only accepted requests can be marked completed.')

    marketplace_request.status = Request.Status.COMPLETED
    marketplace_request.save(update_fields=('status', 'updated_at'))

    final_status = {
        Listing.ListingType.SELL: Listing.Status.SOLD,
        Listing.ListingType.EXCHANGE: Listing.Status.EXCHANGED,
        Listing.ListingType.DONATE: Listing.Status.DONATED,
    }.get(marketplace_request.listing.listing_type, Listing.Status.SOLD)

    Listing.objects.filter(pk=marketplace_request.listing_id).update(status=final_status)

    return marketplace_request


@transaction.atomic
def cancel_request_restore_listing(marketplace_request):
    """Cancel a request; if it was Accepted, restore the listing to Available."""
    if marketplace_request.status not in (
        Request.Status.PENDING, Request.Status.ACCEPTED
    ):
        raise ValidationError('This request cannot be cancelled.')

    was_accepted = marketplace_request.status == Request.Status.ACCEPTED
    marketplace_request.status = Request.Status.CANCELLED
    marketplace_request.save(update_fields=('status', 'updated_at'))

    if was_accepted:
        listing = Listing.objects.select_for_update().get(pk=marketplace_request.listing_id)
        if listing.status == Listing.Status.RESERVED:
            listing.status = Listing.Status.AVAILABLE
            listing.save(update_fields=('status', 'updated_at'))

    return marketplace_request
