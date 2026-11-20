from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.shortcuts import render
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('listings.urls')),
    # Django built-in password-reset flow
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='listings/password_reset.html',
        email_template_name='listings/emails/password_reset_email.txt',
        subject_template_name='listings/emails/password_reset_subject.txt',
        success_url='/password-reset/sent/',
    ), name='password_reset'),
    path('password-reset/sent/', auth_views.PasswordResetDoneView.as_view(
        template_name='listings/password_reset_done.html',
    ), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='listings/password_reset_confirm.html',
        success_url='/password-reset/complete/',
    ), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='listings/password_reset_complete.html',
    ), name='password_reset_complete'),
]

handler403 = 'refind.urls.permission_denied_view'
handler404 = 'refind.urls.page_not_found_view'
handler500 = 'refind.urls.server_error_view'


def permission_denied_view(request, exception=None):
    return render(request, 'listings/errors/403.html', status=403)


def page_not_found_view(request, exception=None):
    return render(request, 'listings/errors/404.html', status=404)


def server_error_view(request):
    return render(request, 'listings/errors/500.html', status=500)


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
