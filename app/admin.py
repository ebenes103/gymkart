from django.contrib import admin
from .models import Profile, Product, ProductImage, CartItem, Wishlist

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    max_num = 3

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'brand', 'category', 'price', 'get_total_stock', 'seller', 'created_at']
    list_filter = ['category', 'brand', 'availability']
    search_fields = ['name', 'brand', 'product_id']
    inlines = [ProductImageInline]
    
    def get_total_stock(self, obj):
        return obj.get_total_stock()
    get_total_stock.short_description = 'Total Stock'

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'seller_approved']
    list_filter = ['role', 'seller_approved']
    search_fields = ['user__username']

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'weight', 'quantity', 'total_price']
    list_filter = ['user']

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'added_date']
    list_filter = ['user']