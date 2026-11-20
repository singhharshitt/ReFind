from django.urls import path

from . import views

urlpatterns = [
    # Public
    path('', views.home, name='home'),

    # Authentication
    path('auth/', views.auth, name='auth'),
    path('auth/verify/<uid>/<token>/', views.verify_email, name='verify-email'),
    path('logout/', views.logout_view, name='logout'),

    # Listings
    path('listings/new/', views.listing_create, name='listing-create'),
    path('listings/mine/', views.my_listings, name='my-listings'),
    path('listings/<int:pk>/', views.listing_detail, name='listing-detail'),
    path('listings/<int:pk>/edit/', views.listing_edit, name='listing-edit'),
    path('listings/<int:pk>/delete/', views.listing_delete, name='listing-delete'),
    path('listings/<int:pk>/unavailable/', views.listing_mark_unavailable, name='listing-unavailable'),
    path('listings/<int:pk>/wishlist/', views.toggle_wishlist, name='toggle-wishlist'),
    path('listings/<int:pk>/request/', views.create_request, name='create-request'),
    path('listings/<int:pk>/report/', views.report_listing, name='report-listing'),
    path('listings/<int:pk>/message/', views.start_conversation, name='start-conversation'),

    # Wishlist
    path('wishlist/', views.wishlist, name='wishlist'),

    # Inbox / Messaging
    path('inbox/', views.inbox, name='inbox'),
    path('inbox/<int:listing_id>/<int:partner_id>/', views.inbox, name='message-thread'),
    path('inbox/<int:listing_id>/<int:partner_id>/send/', views.send_message, name='send-message'),

    # Requests / Transactions
    path('requests/', views.requests_dashboard, name='requests-dashboard'),
    path('requests/<int:pk>/review/', views.review_request, name='review-request'),
    path('requests/<int:pk>/<str:action>/', views.request_action, name='request-action'),

    # Profile
    path('profile/', views.profile, name='profile'),

    # Admin dashboard (custom stats page, separate from /admin/)
    path('dashboard/', views.admin_dashboard, name='admin-dashboard'),
]
