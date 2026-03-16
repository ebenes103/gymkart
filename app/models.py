from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import json

class Profile(models.Model):
    ROLE_CHOICES = (
        ('buyer', 'Buyer'),
        ('seller', 'Seller'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='buyer')
    seller_approved = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

class Product(models.Model):
    CATEGORY_CHOICES = (
        ('weights', 'Weights'),
        ('cardio', 'Cardio'),
        ('accessories', 'Accessories'),
    )
    
    seller = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    product_id = models.CharField(max_length=50, blank=True, null=True)
    name = models.CharField(max_length=200, blank=True, null=True)
    brand = models.CharField(max_length=200, blank=True, null=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    # Main image for grid
    image = models.ImageField(upload_to='products/main/', blank=True, null=True)
    
    # Available weights (JSON field to store multiple weight options)
    available_weights = models.JSONField(default=list, blank=True, null=True,
                                         help_text="Format: ['2kg', '5kg', '10kg', '20kg']")
    
    # Stock tracking per weight
    stock_per_weight = models.JSONField(default=dict, blank=True, null=True,
                                        help_text="Format: {'2kg': 10, '5kg': 8, '10kg': 5, '20kg': 3}")
    
    availability = models.BooleanField(default=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    def __str__(self):
        return self.name or "Unnamed Product"
    
    def get_total_stock(self):
        """Calculate total stock across all weights"""
        if self.stock_per_weight and isinstance(self.stock_per_weight, dict):
            return sum(self.stock_per_weight.values())
        return 0
    
    def get_low_stock_weights(self):
        """Return weights with stock less than 5"""
        if self.stock_per_weight and isinstance(self.stock_per_weight, dict):
            return {weight: qty for weight, qty in self.stock_per_weight.items() if qty < 5}
        return {}
    
    def get_stock_for_weight(self, weight):
        """Get stock for specific weight"""
        if self.stock_per_weight and isinstance(self.stock_per_weight, dict):
            return self.stock_per_weight.get(weight, 0)
        return 0

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='extra_images', blank=True, null=True)
    image = models.ImageField(upload_to='products/extra/', blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return f"Extra image for {self.product.name if self.product else 'Unknown'}"



class Newsletter(models.Model):
    email = models.EmailField(unique=True)  # This prevents duplicate emails
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.email
    
    class Meta:
        ordering = ['-subscribed_at']




class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, blank=True, null=True)
    weight = models.CharField(max_length=20, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1, blank=True, null=True)

    def total_price(self):
        if self.product and self.product.price:
            return self.product.price * (self.quantity or 1)
        return 0

class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, blank=True, null=True)
    added_date = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    
    class Meta:
        unique_together = ('user', 'product')
    
    def __str__(self):
        return f"{self.user.username if self.user else 'Unknown'} - {self.product.name if self.product else 'Unknown'}"