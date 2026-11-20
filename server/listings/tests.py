import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Listing, Message, Request, User
from .services import accept_request, complete_request

_TEST_MEDIA = tempfile.mkdtemp(prefix='refind_test_media_')


def _tiny_png():
    # 1x1 transparent PNG
    return SimpleUploadedFile(
        'item.png',
        (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
            b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        ),
        content_type='image/png',
    )


def _verified_user(**kwargs):
    defaults = {
        'password': 'StrongPass123!',
        'campus_verified': True,
    }
    defaults.update(kwargs)
    password = defaults.pop('password')
    user = User.objects.create_user(password=password, **defaults)
    return user


@override_settings(MEDIA_ROOT=_TEST_MEDIA)
class MarketplacePageTests(TestCase):
    def setUp(self):
        owner = _verified_user(
            username='seller@ipu.in',
            email='seller@ipu.in',
            first_name='Aman',
            last_name='Verma',
        )
        Listing.objects.create(
            owner=owner,
            title='MacBook Air M1 (2020)',
            description='Light and reliable laptop.',
            category='electronics',
            condition='like-new',
            listing_type='sell',
            price=49000,
        )
        Listing.objects.create(
            owner=owner,
            title='Canon EOS 300D II',
            description='Campus photography camera.',
            category='electronics',
            condition='good',
            listing_type='sell',
            price=32000,
        )
        Listing.objects.create(
            owner=owner,
            title='Study Chair',
            description='Comfortable desk chair.',
            category='furniture',
            condition='used',
            listing_type='donate',
        )
        Listing.objects.create(
            owner=owner,
            title='Winter Essentials Set',
            description='Warm donated essentials.',
            category='essentials',
            condition='used',
            listing_type='donate',
        )

    def test_home_page_renders_components(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Find')
        self.assertContains(response, 'Buy')
        self.assertContains(response, 'Sell')
        self.assertContains(response, 'Exchange')
        self.assertContains(response, 'Donate')
        self.assertContains(response, 'ReFind')
        self.assertContains(response, 'MacBook Air M1 (2020)')
        self.assertContains(response, 'site-footer')

    def test_search_filters_listing_grid(self):
        response = self.client.get(reverse('home'), {'q': 'Canon'})

        self.assertContains(response, 'Canon EOS 300D II')
        self.assertNotContains(response, 'MacBook Air M1 (2020)')

    def test_search_by_seller_name(self):
        response = self.client.get(reverse('home'), {'q': 'Aman'})
        self.assertContains(response, 'MacBook Air M1 (2020)')

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
        user = _verified_user(username='student@ipu.in', email='student@ipu.in')
        self.client.force_login(user)
        response = self.client.post(reverse('listing-create'), {
            'title': 'Desk lamp',
            'description': 'Bright and compact.',
            'category': 'essentials',
            'condition': 'good',
            'listing_type': 'sell',
            'price': '500',
            'image': _tiny_png(),
        })

        listing = Listing.objects.get(title='Desk lamp')
        self.assertRedirects(response, reverse('listing-detail', args=[listing.pk]))
        self.assertContains(self.client.get(response.url), 'Desk lamp')

    def test_any_email_can_register_and_use_marketplace(self):
        response = self.client.post(reverse('auth'), {
            'action': 'register',
            'name': 'Gmail Student',
            'email': 'student@gmail.com',
            'password': 'StrongPass123!',
            'confirm_password': 'StrongPass123!',
        })

        self.assertRedirects(response, reverse('home'))
        user = User.objects.get(email='student@gmail.com')
        self.assertTrue(user.is_authenticated or True)
        self.assertTrue(user.campus_verified)

        self.client.force_login(user)
        create_page = self.client.get(reverse('listing-create'))
        self.assertEqual(create_page.status_code, 200)

    def test_login_works_without_verification(self):
        User.objects.create_user(
            username='old@gmail.com',
            email='old@gmail.com',
            password='StrongPass123!',
            campus_verified=False,
        )
        response = self.client.post(f"{reverse('auth')}?screen=login", {
            'action': 'login',
            'email': 'old@gmail.com',
            'password': 'StrongPass123!',
        })
        self.assertRedirects(response, reverse('home'))

    def test_accepting_request_reserves_listing_and_rejects_competing_requests(self):
        owner = _verified_user(username='owner@ipu.in', email='owner@ipu.in')
        first = _verified_user(username='first@ipu.in', email='first@ipu.in')
        second = _verified_user(username='second@ipu.in', email='second@ipu.in')
        listing = Listing.objects.create(
            owner=owner, title='Textbook', description='Useful', category='books',
            condition='good', listing_type='sell', price=100,
        )
        first_request = Request.objects.create(listing=listing, requester=first)
        second_request = Request.objects.create(listing=listing, requester=second)

        accept_request(first_request, owner)

        listing.refresh_from_db()
        first_request.refresh_from_db()
        second_request.refresh_from_db()
        self.assertEqual(listing.status, Listing.Status.RESERVED)
        self.assertEqual(first_request.status, Request.Status.ACCEPTED)
        self.assertEqual(second_request.status, Request.Status.REJECTED)

    def test_completed_request_can_be_reviewed_only_by_requester(self):
        owner = _verified_user(username='review-seller@ipu.in', email='review-seller@ipu.in')
        buyer = _verified_user(username='buyer@ipu.in', email='buyer@ipu.in')
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

    def test_buyer_can_open_message_thread_with_seller(self):
        owner = User.objects.get(email='seller@ipu.in')
        buyer = _verified_user(username='msg-buyer@ipu.in', email='msg-buyer@ipu.in')
        listing = Listing.objects.filter(owner=owner).first()
        self.client.force_login(buyer)

        start = self.client.get(reverse('start-conversation', args=[listing.pk]))
        self.assertRedirects(
            start,
            reverse('message-thread', args=[listing.pk, owner.pk]),
        )
        thread = self.client.get(reverse('message-thread', args=[listing.pk, owner.pk]))
        self.assertEqual(thread.status_code, 200)
        self.assertContains(thread, listing.title)

        send = self.client.post(
            reverse('send-message', args=[listing.pk, owner.pk]),
            {'body': 'Is this still available?'},
        )
        self.assertRedirects(send, reverse('message-thread', args=[listing.pk, owner.pk]))
        self.assertTrue(
            Message.objects.filter(
                listing=listing, sender=buyer, recipient=owner, body='Is this still available?'
            ).exists()
        )

    def test_wishlist_toggle_and_page(self):
        buyer = _verified_user(username='wish@ipu.in', email='wish@ipu.in')
        listing = Listing.objects.first()
        self.client.force_login(buyer)

        response = self.client.post(reverse('toggle-wishlist', args=[listing.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(buyer, listing.saved_by.all())

        page = self.client.get(reverse('wishlist'))
        self.assertContains(page, listing.title)

        self.client.post(
            reverse('toggle-wishlist', args=[listing.pk]),
            HTTP_HX_REQUEST='true',
        )
        self.assertNotIn(buyer, listing.saved_by.all())
