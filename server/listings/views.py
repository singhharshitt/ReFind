"""Views for the ReFind campus marketplace."""

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import urlsafe_base64_decode

from .decorators import campus_verified_required
from .forms import (
    ExchangeRequestForm,
    ListingForm,
    MessageForm,
    ProfileForm,
    ReportForm,
    RequestForm,
)
from .models import Listing, Message, Report, Request, User
from .services import accept_request, cancel_request_restore_listing, complete_request


def _querystring_without_page(request):
    """Build a query string for pagination that omits the current page param."""
    params = request.GET.copy()
    params.pop('page', None)
    return params.urlencode()


def _can_access_thread(user, listing, partner):
    """True when user and partner are the two ends of a listing conversation."""
    if user.id == partner.id:
        return False
    return listing.owner_id in (user.id, partner.id)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _filtered_listings(request):
    """Build a filtered and sorted queryset of available listings from request GET params."""
    queryset = Listing.objects.select_related('owner').filter(status=Listing.Status.AVAILABLE)

    kind_aliases = {
        'sale': Listing.ListingType.SELL,
        'sell': Listing.ListingType.SELL,
        'exchange': Listing.ListingType.EXCHANGE,
        'donation': Listing.ListingType.DONATE,
        'donate': Listing.ListingType.DONATE,
    }
    listing_type = request.GET.get('kind', '').strip().lower()
    if listing_type:
        listing_type = kind_aliases.get(listing_type, listing_type)
        queryset = queryset.filter(listing_type=listing_type)

    category = request.GET.get('category', '').strip().lower()
    if category:
        queryset = queryset.filter(category=category)

    condition = request.GET.get('condition', '').strip().lower()
    if condition:
        queryset = queryset.filter(condition=condition)

    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    if min_price:
        try:
            queryset = queryset.filter(price__gte=float(min_price))
        except ValueError:
            pass
    if max_price:
        try:
            queryset = queryset.filter(price__lte=float(max_price))
        except ValueError:
            pass

    search = request.GET.get('q', '').strip()
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(owner__full_name__icontains=search)
            | Q(owner__first_name__icontains=search)
            | Q(owner__last_name__icontains=search)
            | Q(owner__email__icontains=search)
            | Q(owner__username__icontains=search)
        )

    sort = request.GET.get('sort', 'newest')
    if sort == 'price-low':
        queryset = queryset.order_by('price', '-created_at')
    elif sort == 'price-high':
        queryset = queryset.order_by('-price', '-created_at')
    else:
        queryset = queryset.order_by('-created_at')

    return queryset


# ─────────────────────────────────────────────────────────────────────────────
# Public pages
# ─────────────────────────────────────────────────────────────────────────────

def home(request):
    """Homepage: hero + marketplace with search, filters, and sorting."""
    queryset = _filtered_listings(request)
    paginator = Paginator(queryset, 24)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Counts for filter sidebar
    type_counts = {
        'sell': Listing.objects.filter(status=Listing.Status.AVAILABLE, listing_type=Listing.ListingType.SELL).count(),
        'exchange': Listing.objects.filter(status=Listing.Status.AVAILABLE, listing_type=Listing.ListingType.EXCHANGE).count(),
        'donate': Listing.objects.filter(status=Listing.Status.AVAILABLE, listing_type=Listing.ListingType.DONATE).count(),
    }

    # Pass set of saved listing IDs to avoid N+1 in template
    saved_ids = set()
    if request.user.is_authenticated:
        saved_ids = set(request.user.saved_listings.values_list('id', flat=True))

    is_htmx = bool(request.headers.get('HX-Request'))
    context = {
        'listings': page_obj,
        'page_obj': page_obj,
        'listing_count': paginator.count,
        'type_counts': type_counts,
        'saved_ids': saved_ids,
        'page_query': _querystring_without_page(request),
        'is_htmx': is_htmx,
    }
    if is_htmx:
        return render(request, 'listings/partials/listing_grid.html', context)
    return render(request, 'listings/home.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# Authentication
# ─────────────────────────────────────────────────────────────────────────────

def auth(request):
    """Combined register / login view."""
    if request.user.is_authenticated:
        return redirect('home')

    screen = request.GET.get('screen', 'register')
    if screen not in {'register', 'login'}:
        screen = 'register'

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'register':
            email = request.POST.get('email', '').strip().lower()
            name = request.POST.get('name', '').strip()
            password = request.POST.get('password', '')
            confirm = request.POST.get('confirm_password', '')

            if User.objects.filter(email=email).exists():
                messages.error(request, 'An account with that email already exists.')
                screen = 'register'
            elif '@' not in email or '.' not in email.split('@')[-1]:
                messages.error(request, 'Please enter a valid email address.')
                screen = 'register'
            elif len(password) < 8:
                messages.error(request, 'Password must be at least 8 characters.')
                screen = 'register'
            elif password != confirm:
                messages.error(request, 'Passwords do not match.')
                screen = 'register'
            else:
                parts = name.split(maxsplit=1)
                first = parts[0] if parts else ''
                last = parts[1] if len(parts) > 1 else ''
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=first,
                    last_name=last,
                    full_name=name,
                    campus_verified=True,
                )
                user.save(update_fields=('avatar_initials', 'full_name', 'campus_verified'))
                login(request, user)
                messages.success(request, 'Welcome to ReFind! Your account is ready.')
                return redirect('home')

        elif action == 'login':
            email = request.POST.get('email', '').strip().lower()
            password = request.POST.get('password', '')
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                next_url = request.GET.get('next', reverse('home'))
                return redirect(next_url)
            messages.error(request, 'Those login details were not recognised. Check your email and password.')
            screen = 'login'

    return render(request, 'listings/auth.html', {'screen': screen})


def logout_view(request):
    logout(request)
    return redirect('home')


def verify_email(request, uid, token):
    """Legacy verification links redirect home; verification is no longer required."""
    try:
        user_pk = urlsafe_base64_decode(uid).decode()
        user = User.objects.get(pk=user_pk)
        if default_token_generator.check_token(user, token):
            if not user.campus_verified:
                user.campus_verified = True
                user.save(update_fields=('campus_verified',))
            login(request, user)
            messages.success(request, 'Welcome to ReFind!')
            return redirect('home')
    except (User.DoesNotExist, ValueError, UnicodeDecodeError):
        pass
    messages.info(request, 'You can sign in with your email. Verification is no longer required.')
    return redirect(f"{reverse('auth')}?screen=login")

# ─────────────────────────────────────────────────────────────────────────────
# Listing CRUD
# ─────────────────────────────────────────────────────────────────────────────

def listing_detail(request, pk):
    """Public product detail page."""
    listing = get_object_or_404(Listing.objects.select_related('owner'), pk=pk)
    is_owner = request.user.is_authenticated and listing.owner_id == request.user.id
    already_requested = False
    existing_request = None

    if request.user.is_authenticated and not is_owner:
        existing_request = Request.objects.filter(
            listing=listing, requester=request.user
        ).exclude(status=Request.Status.REJECTED).exclude(status=Request.Status.CANCELLED).first()
        already_requested = existing_request is not None

    seller_reviews = Request.objects.filter(
        listing__owner=listing.owner,
        status=Request.Status.COMPLETED,
        rating__isnull=False,
    ).select_related('requester').order_by('-updated_at')[:5]

    seller_avg = listing.owner.get_avg_rating()

    request_form = RequestForm()
    exchange_form = ExchangeRequestForm(requester=request.user if request.user.is_authenticated else None)

    # Collect all listing images
    images = [i for i in (listing.image, listing.image2, listing.image3) if i]

    is_saved = request.user.is_authenticated and listing.saved_by.filter(pk=request.user.pk).exists()

    return render(request, 'listings/detail.html', {
        'listing': listing,
        'is_owner': is_owner,
        'already_requested': already_requested,
        'existing_request': existing_request,
        'request_form': request_form,
        'exchange_form': exchange_form,
        'seller_reviews': seller_reviews,
        'seller_avg': seller_avg,
        'images': images,
        'is_saved': is_saved,
    })


@campus_verified_required
def listing_create(request):
    if request.method == 'POST':
        form = ListingForm(request.POST, request.FILES)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.owner = request.user
            listing.save()
            messages.success(request, 'Your listing is live on ReFind!')
            return redirect('listing-detail', pk=listing.pk)
    else:
        form = ListingForm()
    return render(request, 'listings/listing_form.html', {'form': form, 'editing': False})


@campus_verified_required
def listing_edit(request, pk):
    listing = get_object_or_404(Listing, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = ListingForm(request.POST, request.FILES, instance=listing)
        if form.is_valid():
            form.save()
            messages.success(request, 'Listing updated.')
            return redirect('listing-detail', pk=listing.pk)
    else:
        form = ListingForm(instance=listing)
    return render(request, 'listings/listing_form.html', {
        'form': form,
        'editing': True,
        'listing': listing,
    })


@campus_verified_required
def listing_delete(request, pk):
    listing = get_object_or_404(Listing, pk=pk, owner=request.user)
    if request.method == 'POST':
        listing.delete()
        messages.success(request, 'Listing deleted.')
        return redirect('my-listings')
    return render(request, 'listings/confirm_delete.html', {'listing': listing})


@campus_verified_required
def listing_mark_unavailable(request, pk):
    """Owner can manually mark a listing as unavailable."""
    listing = get_object_or_404(Listing, pk=pk, owner=request.user)
    if request.method == 'POST':
        listing.status = Listing.Status.UNAVAILABLE
        listing.save(update_fields=('status', 'updated_at'))
        messages.success(request, 'Listing marked as unavailable.')
    return redirect('my-listings')


# ─────────────────────────────────────────────────────────────────────────────
# Wishlist
# ─────────────────────────────────────────────────────────────────────────────

@campus_verified_required
def toggle_wishlist(request, pk):
    """Toggle save/unsave. Returns HTMX partial or full redirect."""
    listing = get_object_or_404(Listing, pk=pk)
    if request.user in listing.saved_by.all():
        listing.saved_by.remove(request.user)
        saved = False
    else:
        listing.saved_by.add(request.user)
        saved = True

    if request.headers.get('HX-Request'):
        return render(
            request,
            'listings/partials/wishlist_button.html',
            {'listing': listing, 'saved': saved},
        )
    return redirect(request.META.get('HTTP_REFERER') or reverse('home'))


@campus_verified_required
def wishlist(request):
    """The user's saved listings page."""
    queryset = request.user.saved_listings.select_related('owner').all()

    search = request.GET.get('q', '').strip()
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(owner__full_name__icontains=search)
            | Q(owner__first_name__icontains=search)
            | Q(owner__last_name__icontains=search)
        )

    category = request.GET.get('category', '').strip()
    if category:
        queryset = queryset.filter(category=category)

    kind = request.GET.get('kind', '').strip().lower()
    kind_aliases = {
        'sale': Listing.ListingType.SELL,
        'sell': Listing.ListingType.SELL,
        'exchange': Listing.ListingType.EXCHANGE,
        'donation': Listing.ListingType.DONATE,
        'donate': Listing.ListingType.DONATE,
    }
    if kind:
        queryset = queryset.filter(listing_type=kind_aliases.get(kind, kind))

    sort = request.GET.get('sort', 'recent')
    if sort == 'price-low':
        queryset = queryset.order_by('price')
    elif sort == 'price-high':
        queryset = queryset.order_by('-price')
    else:
        queryset = queryset.order_by('-created_at')

    saved_ids = set(queryset.values_list('id', flat=True))
    return render(request, 'listings/wishlist.html', {
        'listings': queryset,
        'listing_count': queryset.count(),
        'saved_ids': saved_ids,
    })


@campus_verified_required
def my_listings(request):
    """The user's own listings management page."""
    status_filter = request.GET.get('status', '')
    queryset = request.user.listings.all()
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    return render(request, 'listings/my_listings.html', {
        'listings': queryset,
        'status_filter': status_filter,
        'statuses': Listing.Status.choices,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Requests / Transactions
# ─────────────────────────────────────────────────────────────────────────────

@campus_verified_required
def create_request(request, pk):
    """Submit a buy, exchange, or donation request on a listing."""
    listing = get_object_or_404(Listing, pk=pk, status=Listing.Status.AVAILABLE)

    if request.method != 'POST':
        return redirect('listing-detail', pk=pk)

    if listing.owner_id == request.user.id:
        messages.error(request, 'You cannot request your own listing.')
        return redirect('listing-detail', pk=pk)

    # Prevent duplicate pending requests
    if Request.objects.filter(
        listing=listing, requester=request.user, status=Request.Status.PENDING
    ).exists():
        messages.warning(request, 'You already have a pending request for this listing.')
        return redirect('listing-detail', pk=pk)

    if listing.listing_type == Listing.ListingType.EXCHANGE:
        form = ExchangeRequestForm(request.POST, requester=request.user)
    else:
        form = RequestForm(request.POST)

    if form.is_valid():
        mrequest = form.save(commit=False)
        mrequest.listing = listing
        mrequest.requester = request.user
        try:
            mrequest.full_clean()
            mrequest.save()
            messages.success(request, 'Request sent to the seller!')
        except ValidationError as err:
            if hasattr(err, 'message_dict'):
                for field_errors in err.message_dict.values():
                    for error in field_errors:
                        messages.error(request, error)
            else:
                for error in err.messages:
                    messages.error(request, error)
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)

    return redirect('listing-detail', pk=pk)


@campus_verified_required
def requests_dashboard(request):
    """Overview of all requests sent by and received by the current user."""
    submitted = (
        Request.objects.filter(requester=request.user)
        .select_related('listing', 'listing__owner', 'offered_listing')
        .order_by('-created_at')
    )
    received = (
        Request.objects.filter(listing__owner=request.user)
        .select_related('listing', 'requester', 'offered_listing')
        .order_by('-created_at')
    )
    # Tab filter
    tab = request.GET.get('tab', 'sent')
    return render(request, 'listings/requests.html', {
        'submitted': submitted,
        'received': received,
        'tab': tab,
    })


@campus_verified_required
def request_action(request, pk, action):
    """Accept / reject / cancel / complete a request."""
    mrequest = get_object_or_404(
        Request.objects.select_related('listing', 'requester', 'listing__owner'),
        pk=pk,
    )
    if request.method != 'POST':
        return redirect('requests-dashboard')

    try:
        if action == 'accept':
            accept_request(mrequest, request.user)
            messages.success(
                request,
                f'Request accepted. Listing is now reserved for '
                f'{mrequest.requester.get_display_name()}.',
            )
        elif action == 'reject':
            if mrequest.listing.owner_id != request.user.id:
                raise ValidationError('Only the listing owner can reject requests.')
            if mrequest.status != Request.Status.PENDING:
                raise ValidationError('Only pending requests can be rejected.')
            mrequest.status = Request.Status.REJECTED
            mrequest.save(update_fields=('status', 'updated_at'))
            messages.success(request, 'Request rejected.')
        elif action == 'cancel':
            if mrequest.requester_id != request.user.id:
                raise ValidationError('Only the requester can cancel their own request.')
            if mrequest.status not in (Request.Status.PENDING, Request.Status.ACCEPTED):
                raise ValidationError('This request cannot be cancelled.')
            cancel_request_restore_listing(mrequest)
            messages.success(request, 'Request cancelled.')
        elif action == 'complete':
            complete_request(mrequest, request.user)
            messages.success(
                request,
                'Transaction marked as completed. You can now rate the seller.',
            )
        else:
            raise ValidationError('Unknown action.')
    except ValidationError as err:
        messages.error(request, err.messages[0] if hasattr(err, 'messages') else str(err))

    tab = 'received' if action in ('accept', 'reject') else 'sent'
    return redirect(f"{reverse('requests-dashboard')}?tab={tab}")


@campus_verified_required
def review_request(request, pk):
    """Submit a 1–5 star rating and optional review after a completed request."""
    mrequest = get_object_or_404(
        Request, pk=pk, requester=request.user, status=Request.Status.COMPLETED
    )
    if request.method == 'POST' and mrequest.rating is None:
        try:
            rating = int(request.POST.get('rating', 0))
        except (ValueError, TypeError):
            rating = 0
        if 1 <= rating <= 5:
            mrequest.rating = rating
            mrequest.review_text = request.POST.get('review_text', '').strip()
            mrequest.save(update_fields=('rating', 'review_text', 'updated_at'))
            messages.success(request, 'Thanks for reviewing the seller!')
        else:
            messages.error(request, 'Please choose a rating between 1 and 5.')
    return redirect(f"{reverse('requests-dashboard')}?tab=sent")


# ─────────────────────────────────────────────────────────────────────────────
# Messaging
# ─────────────────────────────────────────────────────────────────────────────

@campus_verified_required
def inbox(request, listing_id=None, partner_id=None):
    """Inbox: list of conversations + optional open thread."""
    user = request.user

    # Build a deduplicated list of (listing, other_user, last_message) conversations
    all_messages = Message.objects.filter(
        Q(sender=user) | Q(recipient=user)
    ).select_related('listing', 'sender', 'recipient').order_by('-sent_at')

    seen = {}
    conversation_list = []
    for msg in all_messages:
        other = msg.recipient if msg.sender_id == user.id else msg.sender
        key = (msg.listing_id, min(user.id, other.id), max(user.id, other.id))
        if key not in seen:
            seen[key] = True
            unread_count = Message.objects.filter(
                listing_id=msg.listing_id,
                sender=other,
                recipient=user,
                is_read=False,
            ).count()
            conversation_list.append({
                'listing': msg.listing,
                'partner': other,
                'last_message': msg,
                'unread': unread_count,
            })

    thread = []
    listing = None
    partner = None
    message_form = MessageForm()

    if listing_id and partner_id:
        listing = get_object_or_404(Listing.objects.select_related('owner'), pk=listing_id)
        partner = get_object_or_404(User, pk=partner_id)

        if not _can_access_thread(user, listing, partner):
            messages.error(request, 'You are not a participant in that conversation.')
            return redirect('inbox')

        Message.objects.filter(
            listing=listing, sender=partner, recipient=user, is_read=False
        ).update(is_read=True)

        thread = Message.objects.filter(
            Q(sender=user, recipient=partner) | Q(sender=partner, recipient=user),
            listing=listing,
        ).select_related('sender', 'recipient')

    return render(request, 'listings/inbox.html', {
        'conversations': conversation_list,
        'thread': thread,
        'listing': listing,
        'partner': partner,
        'message_form': message_form,
    })


@campus_verified_required
def send_message(request, listing_id, partner_id):
    """POST: send a message in a listing-based thread."""
    listing = get_object_or_404(Listing, pk=listing_id)
    partner = get_object_or_404(User, pk=partner_id)
    user = request.user

    if not _can_access_thread(user, listing, partner):
        messages.error(request, 'You are not a participant in that conversation.')
        return redirect('inbox')
    if request.method != 'POST':
        return redirect('message-thread', listing_id=listing_id, partner_id=partner_id)

    form = MessageForm(request.POST)
    if form.is_valid():
        msg = form.save(commit=False)
        msg.listing = listing
        msg.sender = user
        msg.recipient = partner
        msg.save()
    else:
        messages.error(request, 'Message could not be sent. Please try again.')

    return redirect('message-thread', listing_id=listing_id, partner_id=partner_id)


@campus_verified_required
def start_conversation(request, pk):
    """Redirect to the conversation thread with a listing's owner."""
    listing = get_object_or_404(Listing, pk=pk)
    if listing.owner_id == request.user.id:
        messages.error(request, "You can't message yourself.")
        return redirect('listing-detail', pk=pk)
    return redirect('message-thread', listing_id=pk, partner_id=listing.owner_id)


# ─────────────────────────────────────────────────────────────────────────────
# Reports
# ─────────────────────────────────────────────────────────────────────────────

@campus_verified_required
def report_listing(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    if listing.owner_id == request.user.id:
        messages.error(request, "You cannot report your own listing.")
        return redirect('listing-detail', pk=pk)

    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.listing = listing
            report.reporter = request.user
            report.save()
            messages.success(request, 'Thanks for the report. Our team will review this listing.')
            return redirect('listing-detail', pk=pk)
    else:
        form = ReportForm()
    return render(request, 'listings/report.html', {'listing': listing, 'form': form})


# ─────────────────────────────────────────────────────────────────────────────
# Profile
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)

    # User's own stats
    listings_count = request.user.listings.count()
    completed_count = Request.objects.filter(
        Q(requester=request.user) | Q(listing__owner=request.user),
        status=Request.Status.COMPLETED,
    ).count()
    avg_rating = request.user.get_avg_rating()

    return render(request, 'listings/profile.html', {
        'form': form,
        'listings_count': listings_count,
        'completed_count': completed_count,
        'avg_rating': avg_rating,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Admin dashboard
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def admin_dashboard(request):
    if not (request.user.is_staff or request.user.role == 'admin'):
        messages.error(request, 'You do not have access to the admin dashboard.')
        return redirect('home')

    # Moderation actions
    if request.method == 'POST':
        action = request.POST.get('action')
        target_id = request.POST.get('target_id')

        if action == 'remove_listing' and target_id:
            listing = get_object_or_404(Listing, pk=target_id)
            listing.status = Listing.Status.UNAVAILABLE
            listing.save(update_fields=('status', 'updated_at'))
            messages.success(request, f'Listing "{listing.title}" marked unavailable.')

        elif action == 'suspend_user' and target_id:
            u = get_object_or_404(User, pk=target_id)
            if not u.is_staff:
                u.is_active = False
                u.save(update_fields=('is_active',))
                messages.success(request, f'User {u.email} suspended.')
            else:
                messages.error(request, 'Cannot suspend a staff account.')

        elif action == 'activate_user' and target_id:
            u = get_object_or_404(User, pk=target_id)
            u.is_active = True
            u.save(update_fields=('is_active',))
            messages.success(request, f'User {u.email} reactivated.')

        elif action == 'resolve_report' and target_id:
            report = get_object_or_404(Report, pk=target_id)
            report.status = Report.Status.RESOLVED
            report.save(update_fields=('status',))
            messages.success(request, 'Report marked resolved.')

        elif action == 'dismiss_report' and target_id:
            report = get_object_or_404(Report, pk=target_id)
            report.status = Report.Status.DISMISSED
            report.save(update_fields=('status',))
            messages.success(request, 'Report dismissed.')

        return redirect('admin-dashboard')

    type_counts = list(
        Listing.objects.values('listing_type').annotate(total=Count('id')).order_by('-total')
    )
    # Enrich with display label
    lt_map = dict(Listing.ListingType.choices)
    for tc in type_counts:
        tc['label'] = lt_map.get(tc['listing_type'], tc['listing_type'])

    context = {
        'users_count': User.objects.count(),
        'active_users_count': User.objects.filter(is_active=True).count(),
        'listings_count': Listing.objects.count(),
        'available_count': Listing.objects.filter(status=Listing.Status.AVAILABLE).count(),
        'requests_count': Request.objects.count(),
        'completed_count': Request.objects.filter(status=Request.Status.COMPLETED).count(),
        'reports_count': Report.objects.filter(status=Report.Status.OPEN).count(),
        'recent_reports': Report.objects.select_related('listing', 'reporter').filter(
            status=Report.Status.OPEN
        ).order_by('-created_at')[:8],
        'recent_listings': Listing.objects.select_related('owner').order_by('-created_at')[:8],
        'recent_users': User.objects.order_by('-date_joined')[:8],
        'type_counts': type_counts,
    }
    return render(request, 'listings/admin_dashboard.html', context)
