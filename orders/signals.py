# orders/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.db.models import F
from .models import Order

@receiver(post_save, sender=Order)
def reduce_stock_on_delivery(sender, instance, created, **kwargs):
    
    if created:
        return

    if instance.status == 'delivered' and not instance.stock_updated:
        
        with transaction.atomic():
            
            from products.models import Product 
            for item in instance.items.all():
                if item.product:
                    
                    Product.objects.filter(pk=item.product.pk).update(
                        stock=F('stock') - item.quantity
                    )
            
            Order.objects.filter(pk=instance.pk).update(stock_updated=True)