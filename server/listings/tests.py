from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import Listing, Message, Request, User
from .services import accept_request, complete_request

class MarketplacePageTests(TestCase):
    def test_home_page_renders_components(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Find · Buy · Sell · Exchange · Donate')
        self.assertContains(response, 'ReFind')
        self.assertContains(response, 'MacBook Air M1 (2020)')

    def test_search_filters_listing_grid(self):
        response = self.client.get(reverse('home'), {'q': 'Canon'})

        self.assertContains(response, 'Canon EOS 300D II')
        self.assertNotContains(response, 'MacBook Air M1 (2020)')

    def test_listing_type_filter(self):
        response = self.client.get(reverse('home'), {'kind': 'donation'})

        self.assertContains(response, 'Study Chair')
        self.assertContains(response, 'Winter Essentials Set')
        self.assertNotContains(response, 'MacBook Air M1 (2020)')

    def test_htmx_request_returns_listing_grid_partial(self):
        response = self.client.get(
            reverse('home'),
            {'q': 'Chair'},
            HTTP_HX_REQUEST='true',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'listings/partials/listing_grid.html')

    def test_authenticated_user_can_create_and_view_listing(self):
        user = User.objects.create_user(username='student@ipu.in', email='student@ipu.in', password='StrongPass123!')
        self.client.force_login(user)
        response = self.client.post(reverse('listing-create'), {
            'title': 'Desk lamp',
            'description': 'Bright and compact.',
            'category': 'essentials',
            'condition': 'good',
            'listing_type': 'sell',
            'price': '500',
        })

        listing = Listing.objects.get(title='Desk lamp')
        self.assertRedirects(response, reverse('listing-detail', args=[listing.pk]))
        self.assertContains(self.client.get(response.url), 'Desk lamp')

    def test_register_creates_verified_campus_account(self):
        response = self.client.post(reverse('auth'), {
            'action': 'register',
            'name': 'Campus Student',
            'email': 'campus@ipu.in',
            'password': 'StrongPass123!',
            'confirm_password': 'StrongPass123!',
        })

        self.assertRedirects(response, f"{reverse('auth')}?screen=verify")
        user = User.objects.get(email='campus@ipu.in')
        self.assertFalse(user.campus_verified)
        verify_url = reverse('verify-email', args=(
            urlsafe_base64_encode(force_bytes(user.pk)),
            default_token_generator.make_token(user),
        ))
        self.assertRedirects(self.client.get(verify_url), reverse('home'))
        self.assertTrue(User.objects.get(email='campus@ipu.in').campus_verified)

    def test_accepting_request_reserves_listing_and_rejects_competing_requests(self):
        owner = User.objects.create_user(username='owner@ipu.in', email='owner@ipu.in', password='StrongPass123!')
        first = User.objects.create_user(username='first@ipu.in', email='first@ipu.in', password='StrongPass123!')
        second = User.objects.create_user(username='second@ipu.in', email='second@ipu.in', password='StrongPass123!')
        listing = Listing.objects.create(
            owner=owner, title='Textbook', description='Useful', category='books',
            condition='good', listing_type='sell', price=100,
        )
        first_request = Request.objects.create(listing=listing, requester=first)
        second_request = Request.objects.create(listing=listing, requester=second)

        accept_request(first_request, owner)

        listing.refresh_from_db()
        second_request.refresh_from_db()
        self.assertEqual(listing.status, Listing.Status.RESERVED)
        self.assertEqual(first_request.status, Request.Status.ACCEPTED)
        self.assertEqual(second_request.status, Request.Status.REJECTED)

    def test_completed_request_can_be_reviewed_only_by_requester(self):
        owner = User.objects.create_user(username='seller@ipu.in', email='seller@ipu.in', password='StrongPass123!')
        buyer = User.objects.create_user(username='buyer@ipu.in', email='buyer@ipu.in', password='StrongPass123!')
        listing = Listing.objects.create(
            owner=owner, title='Calculator', description='Works', category='books',
            condition='good', listing_type='sell', price=100,
        )
        marketplace_request = Request.objects.create(
            listing=listing, requester=buyer, status=Request.Status.ACCEPTED,
        )
        complete_request(marketplace_request, owner)
        marketplace_request.refresh_from_db()

        self.assertEqual(marketplace_request.status, Request.Status.COMPLETED)
        response = self.client.post(reverse('review-request', args=[marketplace_request.pk]), {'rating': 5})
        self.assertEqual(response.status_code, 302)
        self.client.force_login(buyer)
        self.client.post(reverse('review-request', args=[marketplace_request.pk]), {'rating': 5, 'review_text': 'Great seller'})
        marketplace_request.refresh_from_db()
        self.assertEqual(marketplace_request.rating, 5)
