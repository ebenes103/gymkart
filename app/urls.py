from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('home/', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('product/<int:id>/', views.product_detail, name='product_detail'),
    
    # Seller URLs
    path('seller-dashboard/', views.seller_dashboard, name='seller_dashboard'),
    path('add-product/', views.add_product, name='add_product'),
    path('edit-product/<int:product_id>/', views.edit_product, name='edit_product'),
    path('delete-product/<int:product_id>/', views.delete_product, name='delete_product'),
    
    # Seller Order URLs
    path('seller-update-order/<int:order_id>/', views.seller_update_order_status, name='seller_update_order_status'),
    
    # Cart URLs
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart, name='cart'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    
    # Wishlist URLs
    path('wishlist/', views.wishlist, name='wishlist'),
    path('add-to-wishlist/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('remove-from-wishlist/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    
    # Rating URLs
    path('add-product-rating/<int:product_id>/', views.add_product_rating, name='add_product_rating'),
    path('delete-product-rating/<int:rating_id>/', views.delete_product_rating, name='delete_product_rating'),
    
    # Order URLs
    path('checkout/', views.checkout, name='checkout'),
    path('order-confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('order-detail/<int:order_id>/', views.order_detail, name='order_detail'),
    path('cancel-order/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('request-refund/<int:order_id>/', views.request_refund, name='request_refund'),
    
    # Payment URLs
    path('payment-success/', views.payment_success, name='payment_success'),
    path('payment-failed/', views.payment_failed, name='payment_failed'),
    
    # Return URLs
    path('request-return/<int:order_id>/<int:product_id>/', views.request_return, name='request_return'),
    path('seller-returns/', views.seller_returns, name='seller_returns'),
    path('seller-update-return/<int:return_id>/', views.seller_update_return, name='seller_update_return'),
    
    # Complaint URLs
    path('file-complaint/', views.file_complaint, name='file_complaint'),
    path('my-complaints/', views.my_complaints, name='my_complaints'),
    path('admin-complaints/', views.admin_complaints, name='admin_complaints'),
    path('resolve-complaint/<int:complaint_id>/', views.resolve_complaint, name='resolve_complaint'),
    
    # Newsletter URL
    path('subscribe-newsletter/', views.subscribe_newsletter, name='subscribe_newsletter'),
    
    # Admin URLs
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('approve-seller/<int:user_id>/', views.approve_seller, name='approve_seller'),
    path('reject-seller/<int:user_id>/', views.reject_seller, name='reject_seller'),
    
    # Notify Me URL
    path('notify-me/<int:product_id>/', views.notify_me, name='notify_me'),
    
    # Refund URLs
    path('seller-update-refund/<int:refund_id>/', views.seller_update_refund, name='seller_update_refund'),
    path('seller-upload-refund-proof/<int:refund_id>/', views.seller_upload_refund_proof, name='seller_upload_refund_proof'),
    path('admin-verify-refund/<int:refund_id>/', views.admin_verify_refund, name='admin_verify_refund'),
    
    path('logout/', views.logout_view, name='logout'),
]