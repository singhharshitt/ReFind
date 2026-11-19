from django.shortcuts import render


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
    listings = LISTINGS.copy()
    listing_type = request.GET.get('kind')
    search = request.GET.get('q', '').strip().lower()

    if listing_type:
        listings = [listing for listing in listings if listing['kind'] == listing_type]
    if search:
        listings = [
            listing for listing in listings
            if search in listing['title'].lower()
            or search in listing['seller'].lower()
        ]

    sort = request.GET.get('sort', 'newest')
    if sort == 'price-low':
        def price_value(listing):
            digits = ''.join(character for character in listing['price'] if character.isdigit())
            return int(digits) if digits else 0
        listings.sort(key=price_value)
    return listings


def home(request):
    context = {
        'listings': _filtered_listings(request),
        'listing_count': 183,
    }
    if request.headers.get('HX-Request'):
        return render(request, 'listings/partials/listing_grid.html', context)
    return render(request, 'listings/home.html', context)


def auth(request):
    screen = request.GET.get('screen', 'register')
    if screen not in {'register', 'login', 'verify', 'inbox', 'success'}:
        screen = 'register'
    return render(request, 'listings/auth.html', {'screen': screen})
