from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Listing, Request


@transaction.atomic
def accept_request(marketplace_request, owner):
    listing = Listing.objects.select_for_update().get(pk=marketplace_request.listing_id)
    if listing.owner_id != owner.id:
        raise ValidationError('Only the listing owner can accept requests.')
    if listing.status != Listing.Status.AVAILABLE or marketplace_request.status != Request.Status.PENDING:
        raise ValidationError('This listing is no longer available for that request.')
    marketplace_request.status = Request.Status.ACCEPTED
    marketplace_request.save(update_fields=('status', 'updated_at'))
    Request.objects.filter(
        listing=listing, status=Request.Status.PENDING
    ).exclude(pk=marketplace_request.pk).update(status=Request.Status.REJECTED)
    listing.status = Listing.Status.RESERVED
    listing.save(update_fields=('status', 'updated_at'))
    return marketplace_request


@transaction.atomic
def complete_request(marketplace_request, user):
    if user.id not in (marketplace_request.listing.owner_id, marketplace_request.requester_id):
        raise ValidationError('Only participants can complete a request.')
    if marketplace_request.status != Request.Status.ACCEPTED:
        raise ValidationError('Only accepted requests can be completed.')
    marketplace_request.status = Request.Status.COMPLETED
    marketplace_request.save(update_fields=('status', 'updated_at'))
    listing_status = {
        Listing.ListingType.SELL: Listing.Status.SOLD,
        Listing.ListingType.EXCHANGE: Listing.Status.EXCHANGED,
        Listing.ListingType.DONATE: Listing.Status.DONATED,
    }[marketplace_request.listing.listing_type]
    Listing.objects.filter(pk=marketplace_request.listing_id).update(
        status=listing_status
    )
    return marketplace_request
