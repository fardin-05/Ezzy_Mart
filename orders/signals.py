# orders/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.db.models import F
from .models import Order

@receiver(post_save, sender=Order)
def reduce_stock_on_delivery(sender, instance, created, **kwargs):
    """
    যখনই অর্ডারের স্ট্যাটাস 'delivered' হবে, তখনই প্রোডাক্ট অ্যাপের 
    প্রোডাক্ট মডেল থেকে স্টক (কোয়ান্টিটি) মাইনাস হবে।
    """
    # অর্ডার কেবল প্রথমবার তৈরি হলে (যা ডিফল্ট pending থাকে) স্টক কমবে না
    if created:
        return

    # চেক করা হচ্ছে: স্ট্যাটাস 'delivered' কিনা এবং এই অর্ডারের স্টক আগে কখনো কমানো হয়েছে কিনা
    if instance.status == 'delivered' and not instance.stock_updated:
        
        # ডাটাবেজ সেফটি এবং একই সেকেন্ডে একাধিক অর্ডারের কনকারেন্সি লক নিশ্চিত করতে এটমিক ট্রানজেকশন
        with transaction.atomic():
            
            # সার্কুলার ইম্পোর্ট এরর এড়াতে ফাংশনের ভেতরে প্রোডাক্ট মডেল ইম্পোর্ট করা হয়েছে
            from products.models import Product 
            
            # অর্ডারের আন্ডারে থাকা সব অর্ডারের আইটেমগুলো লুপ করা হচ্ছে
            for item in instance.items.all():
                
                # প্রোডাক্টটি যদি ডিবিতে এক্সিস্ট করে (ForeignKey SET_NULL এর কারণে এটি চেক করা সেফ)
                if item.product:
                    # F expression ব্যবহার করে সরাসরি ডাটাবেজ লেভেলে স্টক মাইনাস করা হচ্ছে
                    Product.objects.filter(pk=item.product.pk).update(
                        stock=F('stock') - item.quantity
                    )
            
            # এই অর্ডারের স্টক যে কমে গেছে তা ডাটাবেজে True করে মার্ক করে রাখা হলো
            # এখানে .save() না করে .update() করা হয়েছে যাতে পুনরায় post_save সিগন্যাল ট্রিগার হয়ে লুপে না পড়ে
            Order.objects.filter(pk=instance.pk).update(stock_updated=True)