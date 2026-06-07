from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('register/',       views.register,         name='register'),
    path('login/',          views.customer_login,   name='customer_login'),
    path('logout/',         views.customer_logout,  name='customer_logout'),

    # Store
    path('',                views.store_home,       name='store_home'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),

    # Cart
    path('cart/',               views.cart_view,    name='cart_view'),
    path('cart/data/', views.cart_data, name='cart_data'),
    path('cart/add/<int:pk>/',  views.cart_add,     name='cart_add'),
    path('cart/remove/<int:pk>/', views.cart_remove, name='cart_remove'),
    path('cart/update/<int:pk>/', views.cart_update, name='cart_update'),

    # Checkout & Orders
    # path('buy-now-trigger/<int:product_id>/', views.buy_now_trigger, name='buy_now_trigger'),
    path('buy-now/<int:product_id>/', views.buy_now_trigger, name='buy_now_trigger'),
    path('checkout/',              views.checkout,       name='checkout'),
    path('orders/',                views.my_orders,      name='my_orders'),
    path('orders/<int:pk>/',       views.order_tracking, name='order_tracking'),
    path('orders/delete/<int:pk>/', views.delete_order, name='delete_order'),
]