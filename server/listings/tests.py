from django.test import TestCase
from django.urls import reverse


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
