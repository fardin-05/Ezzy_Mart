from django.urls import path
from . import views

urlpatterns = [
    # Login/Logout — built-in LoginView বাদ, নিজের view ব্যবহার করো
    path('login/',  views.dashboard_login, name='dashboard_login'),
    path('logout/', views.logout_view,     name='dashboard_logout'),

    # Dashboard Home
    path('',             views.dashboard_home, name='dashboard_home'),
    path('analytics/',   views.analytics,      name='analytics'),

    # Products
    path('products/',                      views.product_list,   name='product_list'),
    path('products/create/',               views.product_create, name='product_create'),
    path('products/<int:pk>/edit/',        views.product_edit,   name='product_edit'),
    path('products/<int:pk>/delete/',      views.product_delete, name='product_delete'),

    # Categories
    path('categories/',                    views.category_list,   name='category_list'),
    path('categories/<int:pk>/delete/',    views.category_delete, name='category_delete'),

    # Orders
    path('orders/',                        views.order_list,          name='order_list'),
    path('orders/<int:pk>/',               views.order_detail,        name='order_detail'),
    path('orders/<int:pk>/status/',        views.order_status_update, name='order_status_update'),

    # Customers
    path('customers/',                     views.customer_list, name='customer_list'),

    # Settings
    path('settings/',                      views.settings_view, name='settings'),
]