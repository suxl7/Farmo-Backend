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
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from backend.service_frontend.authentication import (
    login, 
    verify_wallet_pin, 
    login_with_token, 
    logout, 
    logout_all_devices)
from backend.service_frontend.servicesActivity import (
    get_online_status, 
    check_userid_available, 
    get_address)
from backend.service_frontend.userProfile import (
    register, 
    verification_request, 
    update_profile_picture, 
    get_payment_method, 
    add_payment_method)
from backend.service_frontend.servicesProfile import view_profile
from backend.service_frontend.orders import (
    order_request, 
    get_order_detail, 
    all_incomming_orders_for_farmer, 
    all_consumer_orders)
from backend.service_frontend.servicesRating import (
    # Farmer Rating Views (Consumer rates Farmer)
    RateFarmer,
    EditFarmerRate,
    ViewFarmerRate,
    DeleteFarmerRate,
    ListFarmerRatings,
    ListRatingsByFarmer,
    farmer_profile_rating,
    
    # Consumer Rating Views (Farmer rates Consumer)
    RateConsumer,
    EditConsumerRate,
    ViewConsumerRate,
    DeleteConsumerRate,
    ListConsumerRatings,
    ListRatingsByConsumer,
    consumer_profile_rating,
    
    # Farmer as Consumer Rating Views (Farmer rates another Farmer)
    RateFarmerAsConsumer,
    EditFarmerAsConsumerRate,
    DeleteFarmerAsConsumerRate,

    # Product Rating Views
    RateProduct,
    EditProductRate,
    ViewProductRate,
    DeleteProductRate,
    ListProductRatingsByProduct,
    product_profile_rating
)


urlpatterns = [
    #path('admin/', admin.site.urls),
    # Authentication
    path('api/auth/register/', register, name='register'),
    path('api/auth/check-userid/', check_userid_available, name='check_userid_available'),
    path('api/auth/login/', login, name='login'), # checked
    path('api/auth/login-with-token/', login_with_token, name='login_with_token'), # checked
    path('api/auth/logout/', logout, name='logout'),
    path('api/auth/logout-all/', logout_all_devices, name='logout_all_devices'),
    # User
    path('api/user/update-profile-picture/', update_profile_picture, name='update_profile_picture'),
    path('api/user/verification-request/', verification_request, name='verification_request'),
    path('api/user/online-status/', get_online_status, name='get_online_status'),
    path('api/wallet/verify-pin/', verify_wallet_pin, name='verify_wallet_pin'),
    path('api/user/profile/', view_profile, name='view_profile'),
    path('api/farmer/order-request/', order_request, name='order_request'),
    path('api/farmer/all-incomming-orders/', all_incomming_orders_for_farmer, name='all_incomming_orders_for_farmer'),
    path('api/consumer/all-orders/', all_consumer_orders, name='all_consumer_orders'),
    path('api/farmer/order-detail/', get_order_detail, name='get_order_detail'),
    # Address and others
    path('api/user/address/', get_address, name='get_address'),
    path('api/user/payment-method/', add_payment_method, name='add_payment_method'),
    path('api/user/get-payment-method/', get_payment_method, name='get_payment_method'),
    # Ratingo
    path('api/rating/farmer/create/', RateFarmer.as_view(), name='rate_farmer'),
    path('api/rating/farmer/edit/<int:pk>/', EditFarmerRate.as_view(), name='edit_farmer_rate'),
    path('api/rating/farmer/view/<int:pk>/', ViewFarmerRate.as_view(), name='view_farmer_rate'),
    path('api/rating/farmer/delete/<int:pk>/', DeleteFarmerRate.as_view(), name='delete_farmer_rate'),
    path('api/rating/farmer/list/', ListFarmerRatings.as_view(), name='list_farmer_ratings'),
    path('api/rating/farmer/list/<int:farmer_id>/', ListRatingsByFarmer.as_view(), name='list_ratings_by_farmer'),
    path('api/rating/farmer/profile/', farmer_profile_rating, name='farmer_profile_rating'),
    path('api/rating/consumer/create/', RateConsumer.as_view(), name='rate_consumer'),
    path('api/rating/consumer/edit/<int:pk>/', EditConsumerRate.as_view(), name='edit_consumer_rate'),
    path('api/rating/consumer/view/<int:pk>/', ViewConsumerRate.as_view(), name='view_consumer_rate'),
    path('api/rating/consumer/delete/<int:pk>/', DeleteConsumerRate.as_view(), name='delete_consumer_rate'),
    path('api/rating/consumer/list/', ListConsumerRatings.as_view(), name='list_consumer_ratings'),
    path('api/rating/consumer/list/<int:consumer_id>/', ListRatingsByConsumer.as_view(), name='list_ratings_by_consumer'),
    path('api/rating/consumer/profile/', consumer_profile_rating, name='consumer_profile_rating'),
    path('api/rating/farmer-as-consumer/create/', RateFarmerAsConsumer.as_view(), name='rate_farmer_as_consumer'),
    path('api/rating/farmer-as-consumer/edit/<int:pk>/', EditFarmerAsConsumerRate.as_view(), name='edit_farmer_as_consumer_rate'),
    path('api/rating/farmer-as-consumer/delete/<int:pk>/', DeleteFarmerAsConsumerRate.as_view(), name='delete_farmer_as_consumer_rate'),
    path('api/rating/product/create/', RateProduct.as_view(), name='rate_product'),
    path('api/rating/product/edit/<int:pk>/', EditProductRate.as_view(), name='edit_product_rate'),
    path('api/rating/product/view/<int:pk>/', ViewProductRate.as_view(), name='view_product_rate'),
    path('api/rating/product/delete/<int:pk>/', DeleteProductRate.as_view(), name='delete_product_rate'),
    path('api/rating/product/list/<int:product_id>/', ListProductRatingsByProduct.as_view(), name='list_product_ratings_by_product'),
    path('api/rating/product/profile/', product_profile_rating, name='product_profile_rating')
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
