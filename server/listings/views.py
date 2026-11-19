from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.conf import settings

from .forms import ListingForm, MessageForm, ProfileForm, ReportForm, RequestForm
from .models import Listing, Message, Report, Request, User
from .services import accept_request, complete_request


LISTINGS = [
    {
        'title': 'MacBook Air M1 (2020)',
        'kind': 'sale',
        'kind_label': 'For Sale',
        'price': '₹49,000',
        'old_price': '₹55,000',
        'condition': 'Like New',
        'distance': '2 km away',
        'seller': 'Aman Verma',
        'seller_initial': 'AV',
        'rating': '3.9',
        'image': 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&w=900&q=80',
    },
    {
        'title': 'CS Core Books (Set of 3)',
        'kind': 'exchange',
        'kind_label': 'For Exchange',
        'price': 'Exchange for DSA / CN / OS',
        'old_price': '',
        'condition': 'Good',
        'distance': '1.5 km away',
        'seller': 'Riya Sharma',
        'seller_initial': 'RS',
        'rating': '4.8',
        'image': 'https://images.unsplash.com/photo-1516979187457-637abb4f9353?auto=format&fit=crop&w=900&q=80',
    },
    {
        'title': 'Canon EOS 300D II',
        'kind': 'sale',
        'kind_label': 'For Sale',
        'price': '₹32,000',
        'old_price': '₹35,000',
        'condition': 'Good',
        'distance': '2.8 km away',
        'seller': 'Kunal Das',
        'seller_initial': 'KD',
        'rating': '4.7',
        'image': 'https://images.unsplash.com/photo-1502920917128-1aa500764cbd?auto=format&fit=crop&w=900&q=80',
    },
    {
        'title': 'Study Chair',
        'kind': 'donation',
        'kind_label': 'For Donation',
        'price': 'Free',
        'old_price': '',
        'condition': 'Used',
        'distance': '3.1 km away',
        'seller': 'Meenal Gupta',
        'seller_initial': 'MG',
        'rating': '5.0',
        'image': 'https://images.unsplash.com/photo-1580480055273-228ff5388ef8?auto=format&fit=crop&w=900&q=80',
    },
    {
        'title': 'Road Bicycle',
        'kind': 'sale',
        'kind_label': 'For Sale',
        'price': '₹18,500',
        'old_price': '₹22,000',
        'condition': 'Good',
        'distance': '4.2 km away',
        'seller': 'Arjun Mehta',
        'seller_initial': 'AM',
        'rating': '4.6',
        'image': 'https://images.unsplash.com/photo-1485965120184-e220f721d03e?auto=format&fit=crop&w=900&q=80',
    },
    {
        'title': 'Scientific Calculator',
        'kind': 'exchange',
        'kind_label': 'For Exchange',
        'price': 'Exchange for Textbooks',
        'old_price': '',
        'condition': 'Like New',
        'distance': '1.2 km away',
        'seller': 'Nisha Jain',
        'seller_initial': 'NJ',
        'rating': '4.9',
        'image': 'https://images.unsplash.com/photo-1574607383476-f517f220d9a4?auto=format&fit=crop&w=900&q=80',
    },
    {
        'title': 'Sony Headphones',
        'kind': 'sale',
        'kind_label': 'For Sale',
        'price': '₹6,500',
        'old_price': '₹8,000',
        'condition': 'Good',
        'distance': '900 m away',
        'seller': 'Vikas Rao',
        'seller_initial': 'VR',
        'rating': '4.8',
        'image': 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=900&q=80',
    },
    {
        'title': 'Winter Essentials Set',
        'kind': 'donation',
        'kind_label': 'For Donation',
        'price': 'Free',
        'old_price': '',
        'distance': '3.5 km away',
        'condition': 'Used',
        'seller': 'Sara Khan',
        'seller_initial': 'SK',
        'rating': '5.0',
        'image': 'https://images.unsplash.com/photo-1548883354-7622d03aca27?auto=format&fit=crop&w=900&q=80',
    },
]


def _filtered_listings(request):
    queryset = Listing.objects.select_related('owner').filter(status=Listing.Status.AVAILABLE)
    listing_type = request.GET.get('kind')
    category = request.GET.get('category')
    search = request.GET.get('q', '').strip().lower()

    if listing_type:
        queryset = queryset.filter(listing_type=listing_type)
    if category:
        queryset = queryset.filter(category=category)
    condition = request.GET.get('condition')
    if condition:
        queryset = queryset.filter(condition=condition)
    minimum_price = request.GET.get('min_price')
    maximum_price = request.GET.get('max_price')
    if minimum_price:
        queryset = queryset.filter(price__gte=minimum_price)
    if maximum_price:
        queryset = queryset.filter(price__lte=maximum_price)
    if search:
        queryset = queryset.filter(title__icontains=search) | queryset.filter(owner__first_name__icontains=search)

    sort = request.GET.get('sort', 'newest')
    if sort == 'price-low':
        queryset = queryset.order_by('price', '-created_at')
    if Listing.objects.exists():
        return queryset

    listings = LISTINGS.copy()
    if listing_type:
        listings = [listing for listing in listings if listing['kind'] == listing_type]
    if search:
        listings = [listing for listing in listings if search in listing['title'].lower() or search in listing['seller'].lower()]
    if sort == 'price-low':
        listings.sort(key=lambda listing: int(''.join(c for c in listing['price'] if c.isdigit()) or 0))
    return listings


def home(request):
    listings = _filtered_listings(request)
    context = {
        'listings': listings,
        'listing_count': listings.count() if hasattr(listings, 'count') and not isinstance(listings, list) else len(listings),
    }
    if request.headers.get('HX-Request'):
        return render(request, 'listings/partials/listing_grid.html', context)
    return render(request, 'listings/home.html', context)


def auth(request):
    screen = request.GET.get('screen', 'register')
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'register':
            email = request.POST.get('email', '').strip().lower()
            password = request.POST.get('password', '')
            if User.objects.filter(email=email).exists():
                messages.error(request, 'An account with that campus email already exists.')
            elif not email.endswith(f'@{settings.CAMPUS_EMAIL_DOMAIN}'):
                messages.error(request, 'Please use your campus email address.')
            elif password != request.POST.get('confirm_password'):
                messages.error(request, 'Passwords do not match.')
            else:
                user = User.objects.create_user(
                    username=email, email=email, password=password,
                    first_name=request.POST.get('name', '').strip(),
                )
                user.save(update_fields=('avatar_initials',))
                verification_url = request.build_absolute_uri(reverse(
                    'verify-email',
                    args=(urlsafe_base64_encode(force_bytes(user.pk)), default_token_generator.make_token(user)),
                ))
                send_mail('Verify your ReFind account', f'Open this link to verify your campus email: {verification_url}', None, [user.email])
                return redirect(f"{reverse('auth')}?screen=verify")
        elif action == 'login':
            user = authenticate(request, username=request.POST.get('email', '').strip().lower(), password=request.POST.get('password', ''))
            if user is not None:
                if not user.campus_verified:
                    messages.error(request, 'Please verify your campus email before signing in.')
                    return redirect(f"{reverse('auth')}?screen=verify")
                login(request, user)
                return redirect('home')
            messages.error(request, 'Those login details were not recognised.')
    if screen not in {'register', 'login', 'verify', 'inbox', 'success'}:
        screen = 'register'
    return render(request, 'listings/auth.html', {'screen': screen})


def logout_view(request):
    logout(request)
    return redirect('home')


def verify_email(request, uid, token):
    from django.utils.http import urlsafe_base64_decode
    try:
        user = User.objects.get(pk=urlsafe_base64_decode(uid).decode())
    except (User.DoesNotExist, ValueError, UnicodeDecodeError):
        user = None
    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, 'That verification link is invalid or expired.')
        return redirect('auth')
    user.campus_verified = True
    user.save(update_fields=('campus_verified',))
    login(request, user)
    messages.success(request, 'Your campus email is verified.')
    return redirect('home')


def listing_detail(request, pk):
    listing = get_object_or_404(Listing.objects.select_related('owner'), pk=pk)
    return render(request, 'listings/detail.html', {'listing': listing, 'request_form': RequestForm()})


@login_required
def listing_create(request):
    if request.method == 'POST':
        form = ListingForm(request.POST)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.owner = request.user
            listing.save()
            messages.success(request, 'Your listing is live on ReFind.')
            return redirect('listing-detail', pk=listing.pk)
    else:
        form = ListingForm()
    return render(request, 'listings/listing_form.html', {'form': form})


@login_required
def listing_edit(request, pk):
    listing = get_object_or_404(Listing, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = ListingForm(request.POST, instance=listing)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your listing was updated.')
            return redirect('listing-detail', pk=listing.pk)
    else:
        form = ListingForm(instance=listing)
    return render(request, 'listings/listing_form.html', {'form': form, 'editing': True, 'listing': listing})


@login_required
def listing_delete(request, pk):
    listing = get_object_or_404(Listing, pk=pk, owner=request.user)
    if request.method == 'POST':
        listing.delete()
        messages.success(request, 'Listing deleted.')
        return redirect('my-listings')
    return render(request, 'listings/confirm_delete.html', {'listing': listing})


@login_required
def toggle_wishlist(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    if request.user in listing.saved_by.all():
        listing.saved_by.remove(request.user)
        saved = False
    else:
        listing.saved_by.add(request.user)
        saved = True
    if request.headers.get('HX-Request'):
        return render(request, 'listings/partials/wishlist_button.html', {'listing': listing, 'saved': saved})
    return redirect(request.META.get('HTTP_REFERER', 'home'))


@login_required
def create_request(request, pk):
    listing = get_object_or_404(Listing, pk=pk, status=Listing.Status.AVAILABLE)
    if listing.owner_id == request.user.id:
        messages.error(request, 'You cannot request your own listing.')
        return redirect('listing-detail', pk=pk)
    form = RequestForm(request.POST)
    if form.is_valid():
        marketplace_request = form.save(commit=False)
        marketplace_request.listing = listing
        marketplace_request.requester = request.user
        try:
            marketplace_request.full_clean()
            marketplace_request.save()
        except Exception as error:
            messages.error(request, str(error))
        else:
            messages.success(request, 'Request sent to the seller.')
    return redirect('listing-detail', pk=pk)


@login_required
def my_listings(request):
    listings = request.user.listings.all()
    return render(request, 'listings/my_listings.html', {'listings': listings})


@login_required
def wishlist(request):
    listings = request.user.saved_listings.select_related('owner').all()
    search = request.GET.get('q', '').strip()
    if search:
        listings = listings.filter(title__icontains=search)
    category = request.GET.get('category')
    if category:
        listings = listings.filter(category=category)
    return render(request, 'listings/wishlist.html', {'listings': listings, 'listing_count': listings.count()})


@login_required
def inbox(request, listing_id=None, partner_id=None):
    messages_qs = Message.objects.filter(Q(sender=request.user) | Q(recipient=request.user))
    conversations = messages_qs.values('listing', 'sender', 'recipient').annotate(last_sent=Count('id')).order_by('-last_sent')
    thread = Message.objects.none()
    listing = None
    partner = None
    if listing_id and partner_id:
        listing = get_object_or_404(Listing, pk=listing_id)
        partner = get_object_or_404(User, pk=partner_id)
        if request.user.id not in (listing.owner_id, partner.id):
            return redirect('inbox')
        thread = Message.objects.filter(
            Q(sender=request.user, recipient=partner) | Q(sender=partner, recipient=request.user),
            listing=listing,
        ).select_related('sender')
        thread.filter(recipient=request.user).update(is_read=True)
    return render(request, 'listings/inbox.html', {
        'conversations': conversations, 'thread': thread, 'listing': listing, 'partner': partner,
        'message_form': MessageForm(),
    })


@login_required
def send_message(request, listing_id, partner_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    partner = get_object_or_404(User, pk=partner_id)
    if request.user.id not in (listing.owner_id, partner.id) or request.method != 'POST':
        return redirect('inbox')
    form = MessageForm(request.POST)
    if form.is_valid():
        message = form.save(commit=False)
        message.listing = listing
        message.sender = request.user
        message.recipient = partner
        message.save()
    return redirect('message-thread', listing_id=listing_id, partner_id=partner_id)


@login_required
def requests_dashboard(request):
    submitted = Request.objects.filter(requester=request.user).select_related('listing', 'listing__owner')
    received = Request.objects.filter(listing__owner=request.user).select_related('listing', 'requester')
    return render(request, 'listings/requests.html', {'submitted': submitted, 'received': received})


@login_required
def request_action(request, pk, action):
    marketplace_request = get_object_or_404(Request.objects.select_related('listing', 'requester'), pk=pk)
    try:
        if action == 'accept' and request.method == 'POST':
            accept_request(marketplace_request, request.user)
        elif action == 'complete' and request.method == 'POST':
            complete_request(marketplace_request, request.user)
        elif action == 'reject' and request.method == 'POST' and marketplace_request.listing.owner_id == request.user.id:
            marketplace_request.status = Request.Status.REJECTED
            marketplace_request.save(update_fields=('status', 'updated_at'))
        elif action == 'cancel' and request.method == 'POST' and marketplace_request.requester_id == request.user.id:
            marketplace_request.status = Request.Status.CANCELLED
            marketplace_request.save(update_fields=('status', 'updated_at'))
        else:
            raise ValueError('This request action is not permitted.')
        messages.success(request, 'Request status updated.')
    except Exception as error:
        messages.error(request, str(error))
    return redirect('requests-dashboard')


@login_required
def review_request(request, pk):
    marketplace_request = get_object_or_404(Request, pk=pk, requester=request.user, status=Request.Status.COMPLETED)
    if request.method == 'POST' and marketplace_request.rating is None:
        rating = int(request.POST.get('rating', 0))
        if 1 <= rating <= 5:
            marketplace_request.rating = rating
            marketplace_request.review_text = request.POST.get('review_text', '').strip()
            marketplace_request.save(update_fields=('rating', 'review_text', 'updated_at'))
            messages.success(request, 'Thanks for reviewing the seller.')
    return redirect('requests-dashboard')


@login_required
def report_listing(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.listing = listing
            report.reporter = request.user
            report.save()
            messages.success(request, 'Thanks. We will review this listing.')
            return redirect('listing-detail', pk=pk)
    else:
        form = ReportForm()
    return render(request, 'listings/report.html', {'listing': listing, 'form': form})


@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'listings/profile.html', {'form': form})


@login_required
def admin_dashboard(request):
    if not request.user.is_staff and request.user.role != 'admin':
        return redirect('home')
    context = {
        'users_count': User.objects.count(),
        'listings_count': Listing.objects.count(),
        'requests_count': Request.objects.count(),
        'reports_count': Report.objects.filter(status=Report.Status.OPEN).count(),
        'recent_reports': Report.objects.select_related('listing', 'reporter').order_by('-created_at')[:6],
        'type_counts': Listing.objects.values('listing_type').annotate(total=Count('id')).order_by('-total'),
    }
    return render(request, 'listings/admin_dashboard.html', context)
