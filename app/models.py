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
    
    # Rating methods
    def get_average_rating(self):
        ratings = self.ratings.all()
        if ratings:
            return sum(r.rating for r in ratings) / len(ratings)
        return 0
    
    def get_rating_count(self):
        return self.ratings.count()
    
    def get_rating_distribution(self):
        distribution = {1:0, 2:0, 3:0, 4:0, 5:0}
        for rating in self.ratings.all():
            distribution[rating.rating] += 1
        return distribution

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='extra_images', blank=True, null=True)
    image = models.ImageField(upload_to='products/extra/', blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return f"Extra image for {self.product.name if self.product else 'Unknown'}"

class Newsletter(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.email
    
    class Meta:
        ordering = ['-subscribed_at']

class NotifyMe(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='notifications')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_notified = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('product', 'user')
    
    def __str__(self):
        return f"{self.user.email} - {self.product.name}"

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

class ProductRating(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    review = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('product', 'user')
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name} - {self.rating}★"

class Order(models.Model):
    ORDER_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('packed', 'Packed'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )
    
    PAYMENT_METHOD_CHOICES = (
        ('cod', 'Cash on Delivery'),
        ('upi', 'UPI'),
        ('card', 'Card'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    order_id = models.CharField(max_length=20, unique=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.BooleanField(default=False)  # True = paid, False = pending
    order_status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    
    # Shipping details
    shipping_name = models.CharField(max_length=200, blank=True, null=True)
    shipping_address = models.TextField(blank=True, null=True)
    shipping_city = models.CharField(max_length=100, blank=True, null=True)
    shipping_state = models.CharField(max_length=100, blank=True, null=True)
    shipping_pincode = models.CharField(max_length=10, blank=True, null=True)
    shipping_phone = models.CharField(max_length=15, blank=True, null=True)
    
    # Tracking
    tracking_number = models.CharField(max_length=50, blank=True, null=True)
    tracking_url = models.URLField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.order_id:
            import random
            import datetime
            self.order_id = f"GYM{datetime.datetime.now().strftime('%Y%m%d')}{random.randint(1000, 9999)}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Order {self.order_id} - {self.user.username}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    weight = models.CharField(max_length=20, blank=True, null=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price at time of order
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

class Return(models.Model):
    RETURN_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    )
    
    RETURN_TYPE_CHOICES = (
        ('refund', 'Refund'),
        ('replacement', 'Replacement'),
    )
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='returns')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    return_type = models.CharField(max_length=20, choices=RETURN_TYPE_CHOICES)
    reason = models.TextField()
    image = models.ImageField(upload_to='returns/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=RETURN_STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Return {self.id} - {self.order.order_id}"

class Complaint(models.Model):
    COMPLAINT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('investigating', 'Investigating'),
        ('resolved', 'Resolved'),
        ('rejected', 'Rejected'),
    )
    
    COMPLAINT_TYPE_CHOICES = (
        ('seller_refused_return', 'Seller Refused Return'),
        ('seller_refused_refund', 'Seller Refused Refund'),
        ('damaged_product', 'Damaged Product'),
        ('wrong_product', 'Wrong Product'),
        ('other', 'Other'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='complaints')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='complaints_received')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)
    complaint_type = models.CharField(max_length=30, choices=COMPLAINT_TYPE_CHOICES)
    description = models.TextField()
    image = models.ImageField(upload_to='complaints/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=COMPLAINT_STATUS_CHOICES, default='pending')
    admin_remark = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"Complaint {self.id} - {self.user.username} vs {self.seller.username}"
class Refund(models.Model):
    REFUND_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('admin_warning', 'Admin Warning - Action Required'),
    )
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='refund')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=10)
    refund_reason = models.TextField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    admin_warning_note = models.TextField(blank=True, null=True)  # Add this field
    admin_warning_date = models.DateTimeField(blank=True, null=True)  # Add this field
    
    # For UPI Refund
    upi_id = models.CharField(max_length=100, blank=True, null=True)
    
    # For Card Refund
    card_number = models.CharField(max_length=20, blank=True, null=True)
    account_holder_name = models.CharField(max_length=200, blank=True, null=True)
    bank_name = models.CharField(max_length=200, blank=True, null=True)
    account_number = models.CharField(max_length=20, blank=True, null=True)
    ifsc_code = models.CharField(max_length=15, blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=REFUND_STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Refund for {self.order.order_id} - {self.status}"