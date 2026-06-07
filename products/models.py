from django.db import models
from cloudinary.models import CloudinaryField


class Category(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name
    
    
    class Meta:
        verbose_name_plural = 'Categories'


class Product(models.Model):

    STATUS = [
        ('in_stock',    'In Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('sold_out',    'Sold Out'),
        ('up_coming', 'Up_coming'),
    ]

    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)
    description = models.TextField(null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    image = CloudinaryField('image', folder='ezzy-mart', blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='in_stock')
    badge = models.CharField(max_length=100, blank=True, default='New')
    size = models.CharField(max_length=100, blank=True, default='Standard Pack')
    is_highlighted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.name
    

