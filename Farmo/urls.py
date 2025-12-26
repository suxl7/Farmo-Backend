"""
URL configuration for Farmo project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
#from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from backend.service_frontend.authentication import login, verify_wallet_pin, login_with_token, logout, logout_all_devices
from backend.service_frontend.servicesActivity import get_online_status, check_userid_available
from backend.service_frontend.userProfile import register, verification_request, update_profile_picture
from backend.service_frontend.viewProfile import profile_view, protected_example


urlpatterns = [
    #path('admin/', admin.site.urls),
    path('api/auth/register/', register, name='register'),
    path('api/auth/check-userid/', check_userid_available, name='check_userid_available'),
    path('api/auth/login/', login, name='login'),
    path('api/auth/login-with-token/', login_with_token, name='login_with_token'),
    path('api/auth/logout/', logout, name='logout'),
    path('api/auth/logout-all/', logout_all_devices, name='logout_all_devices'),
    path('api/user/update-profile-picture/', update_profile_picture, name='update_profile_picture'),
    path('api/user/verification-request/', verification_request, name='verification_request'),
    path('api/user/online-status/', get_online_status, name='get_online_status'),
    path('api/wallet/verify-pin/', verify_wallet_pin, name='verify_wallet_pin'),
    path('api/user/profile/', profile_view, name='profile_view'),
    path('api/protected/', protected_example, name='protected_example'),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
