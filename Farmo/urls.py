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
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from backend.service_frontend.authentication import login, verify_wallet_pin
from backend.service_frontend.register import register, check_userid
urlpatterns = [
    #path('admin/', admin.site.urls),
    path('api/auth/register/', register, name='register'),
    path('api/auth/check-userid/', check_userid, name='check_userid'),
    path('api/auth/login/', login, name='login'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/wallet/verify-pin/', verify_wallet_pin, name='verify_wallet_pin'),
]
