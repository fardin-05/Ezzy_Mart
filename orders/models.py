from django.db import models
from django.contrib.auth.models import User
from products.models import Product

class Order(models.Model):
    STATUS = [
        ('pending',     'Pending'),
        ('in_courier',  'In Courier'),
        ('delivered',   'Delivered'),
        ('cancelled',   'Cancelled'),
        ('returned',    'Returned'),
    ]
    customer   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    status     = models.CharField(max_length=20, choices=STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    full_name  = models.CharField(max_length=255, blank=True, null=True)
    phone      = models.CharField(max_length=20, blank=True, null=True)
    email      = models.EmailField(blank=True, null=True)
    district   = models.CharField(max_length=100, blank=True, null=True)
    upazila    = models.CharField(max_length=100, blank=True, null=True)
    address    = models.TextField(blank=True, null=True)
    order_note = models.TextField(blank=True, null=True)
    stock_updated = models.BooleanField(default=False)

    def __str__(self):
        return f"Order #{self.id} - {self.customer}"


class OrderItem(models.Model):
    order    = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product  = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField(default=1)
    price    = models.DecimalField(max_digits=10, decimal_places=2)


# ✅ নতুন — প্রতিটা status change log রাখবে
class OrderStatusLog(models.Model):
    order      = models.ForeignKey(Order, related_name='status_logs', on_delete=models.CASCADE)
    status     = models.CharField(max_length=20)
    changed_at = models.DateTimeField(auto_now_add=True)
    note       = models.TextField(blank=True)

    def __str__(self):
        return f"Order #{self.order.id} → {self.status} at {self.changed_at}"
    
