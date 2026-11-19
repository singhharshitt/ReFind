from django.contrib import admin

from .models import Listing, Message, Report, Request, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'campus_verified', 'is_active', 'date_joined')
    list_filter = ('campus_verified', 'is_active', 'role')
    search_fields = ('username', 'email', 'first_name', 'last_name')


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'listing_type', 'category', 'status', 'created_at')
    list_filter = ('listing_type', 'category', 'condition', 'status')
    search_fields = ('title', 'description', 'owner__email')
    actions = ('mark_unavailable',)

    @admin.action(description='Mark selected listings unavailable')
    def mark_unavailable(self, request, queryset):
        queryset.update(status=Listing.Status.UNAVAILABLE)


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ('listing', 'requester', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('listing__title', 'requester__email')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('listing', 'sender', 'recipient', 'sent_at', 'is_read')
    list_filter = ('is_read',)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('listing', 'reporter', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('listing__title', 'reason')

# Register your models here.
