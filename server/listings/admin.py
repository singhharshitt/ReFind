from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Listing, Message, Report, Request, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'full_name', 'campus_verified', 'role', 'is_active', 'date_joined')
    list_filter = ('campus_verified', 'is_active', 'role')
    search_fields = ('email', 'full_name', 'first_name', 'last_name', 'username')
    ordering = ('-date_joined',)
    fieldsets = BaseUserAdmin.fieldsets + (
        ('ReFind profile', {
            'fields': ('full_name', 'phone', 'hostel', 'bio', 'avatar', 'avatar_initials',
                       'role', 'campus_verified'),
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('ReFind profile', {
            'fields': ('email', 'full_name', 'role', 'campus_verified'),
        }),
    )
    actions = ('suspend_selected_users', 'activate_selected_users', 'verify_selected_users')

    @admin.action(description='Suspend selected users')
    def suspend_selected_users(self, request, queryset):
        queryset.exclude(is_staff=True).update(is_active=False)

    @admin.action(description='Activate selected users')
    def activate_selected_users(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description='Mark campus email verified')
    def verify_selected_users(self, request, queryset):
        queryset.update(campus_verified=True)


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'listing_type', 'category', 'status', 'created_at')
    list_filter = ('listing_type', 'category', 'condition', 'status')
    search_fields = ('title', 'description', 'owner__email')
    ordering = ('-created_at',)
    actions = ('mark_unavailable', 'mark_available')

    @admin.action(description='Mark selected listings unavailable')
    def mark_unavailable(self, request, queryset):
        queryset.update(status=Listing.Status.UNAVAILABLE)

    @admin.action(description='Mark selected listings available')
    def mark_available(self, request, queryset):
        queryset.update(status=Listing.Status.AVAILABLE)


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ('listing', 'requester', 'status', 'rating', 'created_at')
    list_filter = ('status',)
    search_fields = ('listing__title', 'requester__email')
    ordering = ('-created_at',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('listing', 'sender', 'recipient', 'sent_at', 'is_read')
    list_filter = ('is_read',)
    ordering = ('-sent_at',)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('listing', 'reporter', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('listing__title', 'reason', 'reporter__email')
    ordering = ('-created_at',)
    actions = ('resolve_reports', 'dismiss_reports')

    @admin.action(description='Mark selected reports resolved')
    def resolve_reports(self, request, queryset):
        queryset.update(status=Report.Status.RESOLVED)

    @admin.action(description='Dismiss selected reports')
    def dismiss_reports(self, request, queryset):
        queryset.update(status=Report.Status.DISMISSED)
