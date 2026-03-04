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
    login_with_token, 
    login_change_password,
    logout, 
    logout_all_devices,
    forgot_password,
    forget_password_change_password,
    forget_password_verify_email,
    forget_password_verify_otp,
    )

from backend.service_frontend.servicesActivity import (
    get_online_status, 
    check_userid_available, 
    get_address)

from backend.service_frontend.userProfile import (
    register, 
    verification_request, 
    update_profile_picture, 
    get_payment_method, 
    update_payment_method,
    change_password,
    view_own_profile,
    view_user_profile_by_admin,
    check_password,
    update_profile,
    update_user_profile
    )

from backend.service_frontend.servicesForUsers import (
    user_admin_page,
    admin_list,
    search_user,
    user_farmer_page,
    user_consumer_page,
    get_transaction_history_user,
    get_transaction_history_admin,
    action_status_action,
    update_admin_profile)

from backend.service_frontend.orders import (
    order_request, 
    get_order_detail, 
    all_incomming_orders_for_farmer, 
    all_consumer_orders,
    confirm_delivery,
    order_status_update)

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
    product_profile_rating,

    # Top rated user
    top_rated_farmers
)
from backend.service_frontend.serviceHome import (
    dashboard_fullfillment,
    dashboard_fullfillment_test,
    refresh_wallet,
    dashboard_fullfillmentt
)

from backend.service_frontend.product import (
    add_products,
    add_product_FromAdmin,
    all_available_categories,
    available_farm_product_on_category,
    get_product_feed,
    product_home_admin,
    product_filter_admin,
    product_details_for_users
)

from backend.service_frontend.serviceWallet import (
    req_own_wallet,
    req_wallet_by_admin,
    change_wallet_pin,
    verify_wallet_pin,
    forget_wallet_pin
)

from backend.service_frontend.internal_service import (
    update_farm_products,
    download_farm_products)

from backend.service_frontend.BigFileTransferHandler import (
    big_file_upload,
    big_file_download,
    big_file_download_v2
)



urlpatterns = [
    #path('admin/', admin.site.urls),


    path("api/internal/update-farm-products/", update_farm_products, name="update_farm_products"),
    path("api/internal/download-farm-products/", download_farm_products, name="download_farm_products"),
    
    #BigFile Upload/Download
    path('api/file/upload/', big_file_upload, name='big_file_upload'),
    path('api/file/download/', big_file_download, name='big_file_download'),
    path('api/file/download2/', big_file_download_v2, name='big_file_download_v2'),

    # Dashboard
    path('api/home/dashboardd/', dashboard_fullfillmentt, name='dashboard_fullfillmentt'),
    # Authentication
    path('api/auth/check-userid/', check_userid_available, name='check_userid_available'),
    path('api/auth/login/', login, name='login'), # checked
    path('api/auth/login-with-token/', login_with_token, name='login_with_token'), # checked
    path('api/auth/login-change-password/', login_change_password, name='login_change_password'),
    path('api/auth/logout/', logout, name='logout'),
    path('api/auth/logout-all/', logout_all_devices, name='logout_all_devices'),
    path('api/auth/register/', register, name='register'), # checked
    path('api/auth/forgot-password/', forgot_password, name='forgot_password'), # checked
    path('api/auth/forgot-password-verify-email/', forget_password_verify_email, name='forget_password_verify_email'), # checked
    path('api/auth/forgot-password-verify-otp/', forget_password_verify_otp, name='forget_password_verify_otp'), # checked
    path('api/auth/forgot-password-change-password/', forget_password_change_password, name='forget_password_change_password'), # checked

    # User
    path('api/user/update-profile/', update_profile, name='update_profile'),
    path('api/user/user-profile/update/', update_user_profile, name='update_user_profile'),
    path('api/user/address/', get_address, name='get_address'),
    path('api/user/payment-method/', update_payment_method, name='add_payment_method'),
    path('api/user/get-payment-method/', get_payment_method, name='get_payment_method'),
    path('api/user/check-password/', check_password, name='check_password'),
    path('api/user/update-profile-picture/', update_profile_picture, name='update_profile_picture'),
    path('api/user/view-profile/', view_own_profile, name='view_profile'),
    path('api/user/verification-request/', verification_request, name='verification_request'),
    path('api/user/online-status/', get_online_status, name='get_online_status'),
    path('api/user/transaction-history/', get_transaction_history_user, name='get_transaction_history_user'),
    
   
    # Wallet
    path('api/user/wallet/verify-pin/', verify_wallet_pin, name='verify_wallet_pin'),
    path('api/user/wallet/req-own-wallet/', req_own_wallet, name='req_own_wallet'),
    path('api/user/wallet/change-wallet-pin/', change_wallet_pin, name='change_wallet_pin'),
    path('api/user/wallet/forget-wallet-pin/', forget_wallet_pin, name='forget_wallet_pin'),

    # Admin
    path('api/admin/search-user/', search_user, name='search_user'),
    path('api/admin/view-user-profile/', view_user_profile_by_admin, name='view_user_profile'),
    path('api/admin/wallet/req-wallet-by-admin/', req_wallet_by_admin, name='req_wallet_by_admin'),
    path("api/admin/farmer/", user_farmer_page, name="user_farmer_page"),
    path('api/admin/consumer/', user_consumer_page, name='user_consumer_page'),
    path('api/admin/admin-list/', admin_list, name='admin_list'),
    path('api/admin/top-rated-farmers/', top_rated_farmers, name='top_rated_farmers'),
    path('api/admin/transaction-history/', get_transaction_history_admin, name='get_transaction_history_admin'),
    path('api/admin/admin-page/', user_admin_page, name='user_admin_page'),
    path('api/admin/action-status-action/', action_status_action, name='action_status_admin'),
    path('api/admin/update-user-profile/', update_admin_profile, name='update_user_profile'),


    
    # Rating
    path('api/farmer/rating/create/', RateFarmer.as_view(), name='rate_farmer'),
    path('api/farmer/rating/edit/<int:pk>/', EditFarmerRate.as_view(), name='edit_farmer_rate'),
    path('api/farmer/rating/view/<int:pk>/', ViewFarmerRate.as_view(), name='view_farmer_rate'),
    path('api/farmer/rating/delete/<int:pk>/', DeleteFarmerRate.as_view(), name='delete_farmer_rate'),
    path('api/farmer/rating/list/', ListFarmerRatings.as_view(), name='list_farmer_ratings'),
    path('api/farmer/rating/list/<int:farmer_id>/', ListRatingsByFarmer.as_view(), name='list_ratings_by_farmer'),
    path('api/farmer/rating/profile/', farmer_profile_rating, name='farmer_profile_rating'),
    path('api/farmer/rating-as-consumer/create/', RateFarmerAsConsumer.as_view(), name='rate_farmer_as_consumer'),
    path('api/farmer/rating-as-consumer/edit/<int:pk>/', EditFarmerAsConsumerRate.as_view(), name='edit_farmer_as_consumer_rate'),
    path('api/farmer/rating-as-consumer/delete/<int:pk>/', DeleteFarmerAsConsumerRate.as_view(), name='delete_farmer_as_consumer_rate'),
    path('api/farmer/product-rating/create/', RateProduct.as_view(), name='rate_product'),
    path('api/farmer/product-rating/edit/<int:pk>/', EditProductRate.as_view(), name='edit_product_rate'),
    path('api/farmer/product-rating/view/<int:pk>/', ViewProductRate.as_view(), name='view_product_rate'),
    path('api/farmer/product-rating/delete/<int:pk>/', DeleteProductRate.as_view(), name='delete_product_rate'),
    path('api/farmer/product-rating/list/<int:product_id>/', ListProductRatingsByProduct.as_view(), name='list_product_ratings_by_product'),
    path('api/farmer/product-rating/profile/', product_profile_rating, name='product_profile_rating'),
    path('api/consumer/rating/create/', RateConsumer.as_view(), name='rate_consumer'),
    path('api/consumer/rating/edit/<int:pk>/', EditConsumerRate.as_view(), name='edit_consumer_rate'),
    path('api/consumer/rating/view/<int:pk>/', ViewConsumerRate.as_view(), name='view_consumer_rate'),
    path('api/consumer/rating/delete/<int:pk>/', DeleteConsumerRate.as_view(), name='delete_consumer_rate'),
    path('api/consumer/rating/list/', ListConsumerRatings.as_view(), name='list_consumer_ratings'),
    path('api/consumer/rating/list/<int:consumer_id>/', ListRatingsByConsumer.as_view(), name='list_ratings_by_consumer'),
    path('api/consumer/rating/profile/', consumer_profile_rating, name='consumer_profile_rating'),
   
    # Home
    path('api/home/dashboard/', dashboard_fullfillment, name='dashboard_fullfillment'),
    path('api/home/dashboard-test/', dashboard_fullfillment_test, name='dashboard_fullfillment_robin'),
    path('api/home/refresh-wallet/', refresh_wallet, name='refresh_wallet'),

    # Profile
    path('api/user/change-password/', change_password, name='change_password'), #checked
    
    # Product
    path('api/admin/product/', product_home_admin, name='product_home_admin'),
    path('api/product/add/', add_products, name='add_products'),
    path('api/admin/product/add/', add_product_FromAdmin, name='add_product_FromAdmin'),
    path('api/product/category/', all_available_categories, name='all_available_categories'),
    path('api/product/category/products/', available_farm_product_on_category, name='available_farm_product_on_category'),
    path('api/product/feed/', get_product_feed, name='get_product_feed'),
    path('api/product/filter/', product_filter_admin, name='product_filter_admin'),
    path('api/product/users/details/', product_details_for_users, name='product_details_for_users'),

    #Order
    path('api/user/order/request/', order_request, name='order_request'),
    path('api/user/farmer/all-incomming-orders/', all_incomming_orders_for_farmer, name='all_incomming_orders_for_farmer'),
    path('api/user/consumer/all-orders/', all_consumer_orders, name='all_consumer_orders'),
    path('api/user/order/detail/', get_order_detail, name='get_order_detail'),
    path('api/user/order/confirm-delivery/', confirm_delivery, name='confirm_delivery'),
    path('api/user/order/status-update/', order_status_update, name='order_status_update'),

]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
