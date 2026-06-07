from django.db import models
from django.contrib.auth.models import User
from products.models import Product


class Cart(models.Model):
    user       = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_total(self):
        return sum(item.get_subtotal() for item in self.cartitem_set.all())

    def get_count(self):
        return sum(item.quantity for item in self.cartitem_set.all())


class CartItem(models.Model):
    cart     = models.ForeignKey(Cart, on_delete=models.CASCADE)
    product  = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    def get_subtotal(self):
        return self.product.price * self.quantity
    
class CustomerProfile(models.Model):
    user    = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    phone   = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    dob     = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.phone}"