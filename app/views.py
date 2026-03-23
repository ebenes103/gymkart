from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import RegisterForm, ProductForm, ProductImageFormSet, ProductRatingForm
from .models import Product, Profile, CartItem, Wishlist, ProductImage, Newsletter, ProductRating, Order, OrderItem, Return, Complaint, Refund, NotifyMe
from django.contrib.auth.models import User
from django.db.models import Q
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
import json, random, datetime


# Public pages (no login required)
def login_view(request):
    # If user is already logged in, redirect to appropriate page
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('admin_dashboard')
        try:
            profile = Profile.objects.get(user=request.user)
            if profile.role == "seller":
                if profile.seller_approved:
                    return redirect('seller_dashboard')
                else:
                    return render(request, 'waiting_approval.html')
            else:
                return redirect('home')
        except Profile.DoesNotExist:
            return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # ADMIN LOGIN
            if user.is_superuser:
                return redirect('admin_dashboard')

            try:
                profile = Profile.objects.get(user=user)

                # Buyer Login
                if profile.role == "buyer":
                    return redirect('home')

                # Seller Login
                elif profile.role == "seller":
                    if profile.seller_approved:
                        return redirect('seller_dashboard')
                    else:
                        return render(request, 'waiting_approval.html')
            except Profile.DoesNotExist:
                return redirect('home')

        else:
            return render(request, 'login.html', {'error': 'Invalid username or password'})

    return render(request, 'login.html')


def register_view(request):
    # If already logged in, redirect to home
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            role = request.POST.get('role')
            profile = user.profile
            profile.role = role
            profile.save()
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})


# Protected pages (login required)
@login_required(login_url='login')
def home(request):
    query = request.GET.get('q')
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) |
            Q(brand__icontains=query) |
            Q(category__icontains=query)
        )[:4]
    else:
        products = Product.objects.all()[:4]
    
    return render(request, 'home.html', {'products': products})


@login_required(login_url='login')
def product_list(request):
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    
    # Start with all products
    products = Product.objects.all().order_by('-created_at')
    
    # Filter by search query if provided
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(brand__icontains=query) |
            Q(category__icontains=query)
        )
    
    # Filter by category if provided
    if category:
        products = products.filter(category__iexact=category)
    
    return render(request, 'product_list.html', {'products': products})


@login_required(login_url='login')
def product_detail(request, id):
    product = get_object_or_404(Product, id=id)
    return render(request, 'product_detail.html', {'product': product})


# Seller only pages
@login_required(login_url='login')
def seller_dashboard(request):
    # Check if user is a seller
    try:
        profile = Profile.objects.get(user=request.user)
        if profile.role != 'seller':
            return redirect('home')
        if not profile.seller_approved:
            return render(request, 'waiting_approval.html')
    except Profile.DoesNotExist:
        return redirect('home')
    
    products = Product.objects.filter(seller=request.user).order_by('-created_at')
    
    total_products = products.count()
    low_stock_products = 0
    out_of_stock = 0
    
    for product in products:
        total = product.get_total_stock()
        if total == 0:
            out_of_stock += 1
        elif total < 10:
            low_stock_products += 1
    
    # Get orders containing this seller's products
    seller_products = Product.objects.filter(seller=request.user)
    
    # Active orders
    active_statuses = ['pending', 'confirmed', 'packed', 'shipped', 'out_for_delivery', 'delivered']
    active_orders = Order.objects.filter(
        items__product__in=seller_products,
        order_status__in=active_statuses
    ).distinct().order_by('-created_at')
    
    # Cancelled orders
    cancelled_orders = Order.objects.filter(
        items__product__in=seller_products,
        order_status='cancelled'
    ).distinct().order_by('-created_at')
    
    total_active_orders = active_orders.count()
    total_cancelled_orders = cancelled_orders.count()
    
    # Returns
    returns = Return.objects.filter(product__in=seller_products).order_by('-created_at')
    pending_returns = returns.filter(status='pending')
    pending_returns_count = pending_returns.count()
    
    # Refunds
    refunds = Refund.objects.filter(order__items__product__in=seller_products).distinct().order_by('-created_at')
    pending_refunds = refunds.filter(status='pending')
    pending_refunds_count = pending_refunds.count()
    
    # Admin messages (complaints against this seller)
    admin_messages = Complaint.objects.filter(seller=request.user).order_by('-created_at')
    admin_messages_count = admin_messages.count()
    
    # Get low stock items for alert
    low_stock_items = []
    for product in products:
        low_stock = product.get_low_stock_weights()
        if low_stock:
            low_stock_items.append({
                'product': product,
                'low_stock_weights': low_stock
            })
    
    context = {
        'products': products,
        'total_products': total_products,
        'low_stock_products': low_stock_products,
        'out_of_stock': out_of_stock,
        'low_stock_items': low_stock_items,
        'active_orders': active_orders,
        'cancelled_orders': cancelled_orders,
        'total_active_orders': total_active_orders,
        'total_cancelled_orders': total_cancelled_orders,
        'returns': returns,
        'pending_returns_count': pending_returns_count,
        'refunds': refunds,
        'pending_refunds_count': pending_refunds_count,
        'admin_messages': admin_messages,
        'admin_messages_count': admin_messages_count,
    }
    
    return render(request, 'seller_dashboard.html', context)


@login_required(login_url='login')
def add_product(request):
    # Check if user is an approved seller
    try:
        profile = Profile.objects.get(user=request.user)
        if profile.role != 'seller':
            messages.error(request, "Only sellers can add products.")
            return redirect('home')
        if not profile.seller_approved:
            return render(request, 'waiting_approval.html')
    except Profile.DoesNotExist:
        messages.error(request, "Profile not found.")
        return redirect('home')
    
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        formset = ProductImageFormSet(request.POST, request.FILES)
        
        if form.is_valid() and formset.is_valid():
            product = form.save(commit=False)
            product.seller = request.user
            
            # Handle available weights
            if form.cleaned_data.get('available_weights_input'):
                product.available_weights = form.cleaned_data['available_weights_input']
            
            # Handle stock per weight
            if form.cleaned_data.get('stock_per_weight_input'):
                product.stock_per_weight = form.cleaned_data['stock_per_weight_input']
            
            product.save()
            
            # Save extra images
            formset.instance = product
            formset.save()
            
            messages.success(request, "Product added successfully!")
            return redirect("seller_dashboard")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProductForm()
        formset = ProductImageFormSet()
    
    return render(request, 'add_product.html', {'form': form, 'formset': formset})


@login_required(login_url='login')
def add_product_rating(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = ProductRatingForm(request.POST)
        if form.is_valid():
            rating, created = ProductRating.objects.update_or_create(
                product=product,
                user=request.user,
                defaults={
                    'rating': form.cleaned_data['rating'],
                    'review': form.cleaned_data['review']
                }
            )
            messages.success(request, "Thank you for rating this product! ⭐")
    return redirect('product_detail', id=product_id)


@login_required(login_url='login')
def delete_product_rating(request, rating_id):
    rating = get_object_or_404(ProductRating, id=rating_id, user=request.user)
    rating.delete()
    messages.success(request, "Your rating has been removed.")
    return redirect('product_detail', id=rating.product.id)


@login_required(login_url='login')
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    # Check if user owns this product
    if product.seller != request.user:
        return redirect('seller_dashboard')
    
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        formset = ProductImageFormSet(request.POST, request.FILES, instance=product)
        
        if form.is_valid() and formset.is_valid():
            product = form.save(commit=False)
            
            # Get the parsed data from form
            if form.cleaned_data.get('available_weights_input'):
                product.available_weights = form.cleaned_data['available_weights_input']
            if form.cleaned_data.get('stock_per_weight_input'):
                product.stock_per_weight = form.cleaned_data['stock_per_weight_input']
            
            product.save()
            formset.save()
            
            return redirect('seller_dashboard')
    else:
        form = ProductForm(instance=product)
        formset = ProductImageFormSet(instance=product)
    
    return render(request, 'edit_product.html', {
        'form': form, 
        'formset': formset, 
        'product': product
    })


@login_required(login_url='login')
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    product.delete()
    return redirect("seller_dashboard")


# Cart views
@login_required(login_url='login')
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get("quantity", 1))
    weight = request.POST.get("weight", "")
    
    # Check if weight is required for this product
    if product.available_weights and not weight:
        return redirect('product_detail', id=product_id)
    
    # Check stock availability
    if weight and weight in product.stock_per_weight:
        available_stock = product.stock_per_weight[weight]
        if available_stock < quantity:
            return redirect('product_detail', id=product_id)
    elif product.get_total_stock() < quantity:
        return redirect('product_detail', id=product_id)
    
    # Create or update cart item
    cart_item, created = CartItem.objects.get_or_create(
        user=request.user,
        product=product,
        weight=weight,
        defaults={'quantity': quantity}
    )
    
    if not created:
        cart_item.quantity += quantity
        cart_item.save()
    
    return redirect('product_detail', id=product_id)


@login_required(login_url='login')
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, user=request.user)
    item.delete()
    return redirect("cart")


@login_required(login_url='login')
def cart(request):
    cart_items = CartItem.objects.filter(user=request.user)
    total = sum(item.total_price() for item in cart_items)
    return render(request, "cart.html", {
        "cart_items": cart_items,
        "total": total
    })


# Wishlist views
@login_required(login_url='login')
def wishlist(request):
    wishlist_items = Wishlist.objects.filter(user=request.user).order_by('-added_date')
    return render(request, 'wishlist.html', {'wishlist_items': wishlist_items})


@login_required(login_url='login')
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user,
        product=product
    )
    
    return redirect(request.META.get('HTTP_REFERER', 'product_list'))


@login_required(login_url='login')
def remove_from_wishlist(request, product_id):
    Wishlist.objects.filter(user=request.user, product_id=product_id).delete()
    return redirect('wishlist')


# Admin only pages
@user_passes_test(lambda u: u.is_superuser, login_url='login')
def admin_dashboard(request):
    profiles = Profile.objects.all()
    pending_sellers = Profile.objects.filter(role="seller", seller_approved=False)
    approved_sellers = Profile.objects.filter(role="seller", seller_approved=True).count()
    total_buyers = Profile.objects.filter(role="buyer").count()
    total_users = User.objects.count()
    total_newsletters = Newsletter.objects.count()
    recent_newsletters = Newsletter.objects.all()[:10]
    
    # Get complaints
    complaints = Complaint.objects.all().order_by('-created_at')
    pending_complaints_count = complaints.filter(status='pending').count()

    context = {
        "profiles": profiles,
        "pending_sellers": pending_sellers,
        "approved_sellers": approved_sellers,
        "total_buyers": total_buyers,
        "total_users": total_users,
        "total_newsletters": total_newsletters,
        "recent_newsletters": recent_newsletters,
        "complaints": complaints,
        "pending_complaints_count": pending_complaints_count,
    }

    return render(request, "admin_dashboard.html", context)


@user_passes_test(lambda u: u.is_superuser, login_url='login')
def approve_seller(request, user_id):
    profile = get_object_or_404(Profile, user__id=user_id)
    profile.seller_approved = True
    profile.save()
    return redirect("admin_dashboard")


def subscribe_newsletter(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        if email:
            subscriber, created = Newsletter.objects.get_or_create(
                email=email,
                defaults={'is_active': True}
            )
            
            if created:
                messages.success(request, f"Thank you for subscribing to our newsletter! 🎉")
            else:
                if subscriber.is_active:
                    messages.info(request, "You have already subscribed to our newsletter. Thank you! 💪")
                else:
                    subscriber.is_active = True
                    subscriber.save()
                    messages.success(request, "Welcome back! You've been resubscribed to our newsletter. 🏋️")
        else:
            messages.error(request, "Please provide a valid email address.")
    
    return redirect(request.META.get('HTTP_REFERER', 'home'))


@user_passes_test(lambda u: u.is_superuser, login_url='login')
def reject_seller(request, user_id):
    profile = get_object_or_404(Profile, user_id=user_id)
    profile.seller_approved = False
    profile.save()
    return redirect('admin_dashboard')


@login_required(login_url='login')
def notify_me(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    # Check if product is out of stock
    if product.get_total_stock() > 0:
        messages.info(request, f"{product.name} is back in stock! You can purchase it now.")
        return redirect('product_detail', id=product_id)
    
    # Create or get notification
    notification, created = NotifyMe.objects.get_or_create(
        product=product,
        user=request.user,
        defaults={'email': request.user.email}
    )
    
    if created:
        messages.success(request, f"We'll notify you when {product.name} is back in stock! 📧")
    else:
        messages.info(request, f"You're already on the waitlist for {product.name}")
    
    return redirect('product_detail', id=product_id)


# Order views
@login_required(login_url='login')
def checkout(request):
    cart_items = CartItem.objects.filter(user=request.user)
    
    if not cart_items:
        messages.error(request, "Your cart is empty!")
        return redirect('cart')
    
    total = sum(item.total_price() for item in cart_items)
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        shipping_name = request.POST.get('shipping_name')
        shipping_address = request.POST.get('shipping_address')
        shipping_city = request.POST.get('shipping_city')
        shipping_state = request.POST.get('shipping_state')
        shipping_pincode = request.POST.get('shipping_pincode')
        shipping_phone = request.POST.get('shipping_phone')
        
        # Validate shipping details
        if not all([shipping_name, shipping_address, shipping_city, shipping_state, shipping_pincode, shipping_phone]):
            messages.error(request, "Please fill all shipping details")
            return render(request, 'checkout.html', {
                'cart_items': cart_items,
                'total': total,
                'shipping_name': shipping_name,
                'shipping_address': shipping_address,
                'shipping_city': shipping_city,
                'shipping_state': shipping_state,
                'shipping_pincode': shipping_pincode,
                'shipping_phone': shipping_phone,
                'payment_method': payment_method,
            })
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            total_amount=total,
            payment_method=payment_method,
            payment_status=True if payment_method != 'cod' else False,
            shipping_name=shipping_name,
            shipping_address=shipping_address,
            shipping_city=shipping_city,
            shipping_state=shipping_state,
            shipping_pincode=shipping_pincode,
            shipping_phone=shipping_phone,
        )
        
        # Create order items and update stock
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                weight=item.weight,
                quantity=item.quantity,
                price=item.product.price
            )
            
            # Update stock
            if item.weight and item.weight in item.product.stock_per_weight:
                item.product.stock_per_weight[item.weight] -= item.quantity
                item.product.save()
        
        # Clear cart
        cart_items.delete()
        
        messages.success(request, f"Order placed successfully! Order ID: {order.order_id}")
        return redirect('order_confirmation', order_id=order.id)
    
    return render(request, 'checkout.html', {
        'cart_items': cart_items,
        'total': total,
    })


@login_required(login_url='login')
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order_confirmation.html', {'order': order})


@login_required(login_url='login')
def my_orders(request):
    # Active orders (not cancelled)
    active_orders = Order.objects.filter(
        user=request.user
    ).exclude(order_status='cancelled').order_by('-created_at')
    
    # Cancelled orders
    cancelled_orders = Order.objects.filter(
        user=request.user,
        order_status='cancelled'
    ).order_by('-created_at')
    
    # Return requests
    returns = Return.objects.filter(user=request.user).order_by('-created_at')
    
    # Refund requests
    refunds = Refund.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'active_orders': active_orders,
        'active_orders_count': active_orders.count(),
        'cancelled_orders': cancelled_orders,
        'cancelled_orders_count': cancelled_orders.count(),
        'returns': returns,
        'returns_count': returns.count(),
        'refunds': refunds,
        'refunds_count': refunds.count(),
        'now': timezone.now(),
    }
    
    return render(request, 'my_orders.html', context)


@login_required(login_url='login')
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order_detail.html', {'order': order})


@login_required(login_url='login')
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.order_status in ['pending', 'confirmed']:
        # Restore stock
        for item in order.items.all():
            if item.weight and item.weight in item.product.stock_per_weight:
                item.product.stock_per_weight[item.weight] += item.quantity
                item.product.save()
        
        order.order_status = 'cancelled'
        order.save()
        messages.success(request, "Order cancelled successfully!")
    else:
        messages.error(request, "Order cannot be cancelled at this stage.")
    
    return redirect('my_orders')


@login_required(login_url='login')
def seller_update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    seller_products = Product.objects.filter(seller=request.user)
    
    # Check if order contains seller's products
    if not order.items.filter(product__in=seller_products).exists():
        messages.error(request, "You don't have permission to update this order")
        return redirect('seller_dashboard')
    
    if request.method == 'POST':
        new_status = request.POST.get('order_status')
        tracking_number = request.POST.get('tracking_number')
        tracking_url = request.POST.get('tracking_url')
        
        if new_status in ['pending', 'confirmed', 'packed', 'shipped', 'out_for_delivery', 'delivered', 'cancelled']:
            order.order_status = new_status
            if tracking_number:
                order.tracking_number = tracking_number
            if tracking_url:
                order.tracking_url = tracking_url
            order.save()
            messages.success(request, f"Order status updated to {order.get_order_status_display()}")
        else:
            messages.error(request, "Invalid status")
    
    return redirect('seller_dashboard')


# Refund views
@login_required(login_url='login')
def request_refund(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Check if order can be cancelled (only pending/confirmed orders)
    if order.order_status not in ['pending', 'confirmed']:
        messages.error(request, "This order cannot be cancelled at this stage.")
        return redirect('order_detail', order_id=order.id)
    
    # Check if COD - no refund needed
    if order.payment_method == 'cod':
        # For COD orders, just cancel without refund
        for item in order.items.all():
            if item.weight and item.weight in item.product.stock_per_weight:
                item.product.stock_per_weight[item.weight] += item.quantity
                item.product.save()
        
        order.order_status = 'cancelled'
        order.save()
        messages.success(request, "Order cancelled successfully!")
        return redirect('my_orders')
    
    # For UPI and Card payments - show refund form
    if request.method == 'POST':
        refund_reason = request.POST.get('refund_reason')
        
        if order.payment_method == 'upi':
            upi_id = request.POST.get('upi_id')
            if not upi_id:
                messages.error(request, "Please provide UPI ID for refund")
                return render(request, 'refund_form.html', {'order': order})
            
            Refund.objects.create(
                order=order,
                user=request.user,
                amount=order.total_amount,
                payment_method='upi',
                refund_reason=refund_reason,
                upi_id=upi_id,
                status='pending'
            )
        
        elif order.payment_method == 'card':
            account_holder_name = request.POST.get('account_holder_name')
            bank_name = request.POST.get('bank_name')
            account_number = request.POST.get('account_number')
            ifsc_code = request.POST.get('ifsc_code')
            card_last4 = request.POST.get('card_last4')
            
            if not all([account_holder_name, bank_name, account_number, ifsc_code]):
                messages.error(request, "Please provide all bank details for refund")
                return render(request, 'refund_form.html', {'order': order})
            
            Refund.objects.create(
                order=order,
                user=request.user,
                amount=order.total_amount,
                payment_method='card',
                refund_reason=refund_reason,
                account_holder_name=account_holder_name,
                bank_name=bank_name,
                account_number=account_number,
                ifsc_code=ifsc_code,
                card_number=card_last4,
                status='pending'
            )
        
        # Cancel the order
        for item in order.items.all():
            if item.weight and item.weight in item.product.stock_per_weight:
                item.product.stock_per_weight[item.weight] += item.quantity
                item.product.save()
        
        order.order_status = 'cancelled'
        order.save()
        
        messages.success(request, f"Order cancelled! Refund request submitted. Amount ₹{order.total_amount} will be refunded within 3-5 business days.")
        return redirect('my_orders')
    
    return render(request, 'refund_form.html', {'order': order})

@login_required(login_url='login')
def seller_update_refund(request, refund_id):
    refund = get_object_or_404(Refund, id=refund_id)
    
    # Check if the refund belongs to this seller's products
    seller_products = Product.objects.filter(seller=request.user)
    if not refund.order.items.filter(product__in=seller_products).exists():
        messages.error(request, "You don't have permission to update this refund")
        return redirect('seller_dashboard')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'accept':
            refund.status = 'approved'
            refund.save()
            messages.success(request, f"Refund of ₹{refund.amount} has been approved. Processing will begin.")
            
        elif action == 'reject':
            rejection_reason = request.POST.get('rejection_reason')
            if not rejection_reason or not rejection_reason.strip():
                messages.error(request, "Please provide a reason for rejecting the refund.")
                return redirect('seller_dashboard')
            
            refund.status = 'rejected'
            refund.rejection_reason = rejection_reason.strip()
            refund.save()
            messages.warning(request, f"Refund request rejected. Reason: {rejection_reason}")
            
        elif action == 'accept_after_warning':
            # Seller accepts refund after admin warning
            refund.status = 'approved'
            refund.save()
            messages.success(request, f"Refund of ₹{refund.amount} has been approved after admin review. Processing will begin.")
    
    return redirect('seller_dashboard')
# Return views
@login_required(login_url='login')
def request_return(request, order_id, product_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    product = get_object_or_404(Product, id=product_id)
    
    # Check if order is delivered
    if order.order_status != 'delivered':
        messages.error(request, "Return can only be requested for delivered orders.")
        return redirect('order_detail', order_id=order.id)
    
    # Check if within 7 days
    days_since_delivery = (timezone.now().date() - order.updated_at.date()).days
    if days_since_delivery > 7:
        messages.error(request, f"Return window has expired. You can only return within 7 days of delivery.")
        return redirect('order_detail', order_id=order.id)
    
    # Check if already returned
    existing_return = Return.objects.filter(order=order, product=product).first()
    if existing_return:
        messages.error(request, f"You have already requested a return for this product. Status: {existing_return.get_status_display()}")
        return redirect('order_detail', order_id=order.id)
    
    if request.method == 'POST':
        return_type = request.POST.get('return_type')
        reason = request.POST.get('reason')
        image = request.FILES.get('image')
        
        if not return_type or not reason:
            messages.error(request, "Please fill all required fields.")
            return render(request, 'return_form.html', {'order': order, 'product': product})
        
        return_request = Return.objects.create(
            order=order,
            user=request.user,
            product=product,
            return_type=return_type,
            reason=reason,
            image=image
        )
        
        messages.success(request, f"Return request submitted successfully! Request ID: {return_request.id}")
        return redirect('my_orders')
    
    return render(request, 'return_form.html', {'order': order, 'product': product})


@login_required(login_url='login')
def seller_returns(request):
    if not request.user.profile.role == 'seller':
        return redirect('home')
    
    seller_products = Product.objects.filter(seller=request.user)
    returns = Return.objects.filter(product__in=seller_products).order_by('-created_at')
    return render(request, 'seller_returns.html', {'returns': returns})


@login_required(login_url='login')
def seller_update_return(request, return_id):
    return_obj = get_object_or_404(Return, id=return_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            return_obj.status = 'approved'
            return_obj.save()
            messages.success(request, "Return approved!")
            
        elif action == 'reject':
            return_obj.status = 'rejected'
            return_obj.save()
            messages.warning(request, "Return rejected. Buyer can file a complaint.")
    
    return redirect('seller_returns')


# Complaint views
@login_required(login_url='login')
def file_complaint(request):
    if request.method == 'POST':
        seller_id = request.POST.get('seller_id')
        order_id = request.POST.get('order_id')
        complaint_type = request.POST.get('complaint_type')
        description = request.POST.get('description')
        image = request.FILES.get('image')
        
        seller = get_object_or_404(User, id=seller_id)
        order = get_object_or_404(Order, id=order_id) if order_id else None
        
        complaint = Complaint.objects.create(
            user=request.user,
            seller=seller,
            order=order,
            complaint_type=complaint_type,
            description=description,
            image=image
        )
        
        messages.success(request, f"Complaint filed successfully! Complaint ID: {complaint.id}. Admin will review and get back to you.")
        return redirect('my_complaints')
    
    sellers = User.objects.filter(profile__role='seller', profile__seller_approved=True)
    return render(request, 'file_complaint.html', {'sellers': sellers})


@login_required(login_url='login')
def my_complaints(request):
    complaints = Complaint.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'my_complaints.html', {'complaints': complaints})

@user_passes_test(lambda u: u.is_superuser, login_url='login')
def admin_complaints(request):
    # Redirect to admin dashboard which already has complaints tab
    return redirect('admin_dashboard')

@user_passes_test(lambda u: u.is_superuser, login_url='login')
def resolve_complaint(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        admin_remark = request.POST.get('admin_remark')
        
        if not admin_remark:
            messages.error(request, "Please provide remarks for your decision.")
            return redirect('admin_complaints')
        
        if action == 'approve_buyer':
            complaint.status = 'resolved'
            complaint.admin_remark = f"Decision: Buyer's favor. {admin_remark}"
            complaint.resolved_at = timezone.now()
            complaint.save()
            
            # Update the related refund status to admin_warning
            if complaint.order and hasattr(complaint.order, 'refund'):
                refund = complaint.order.refund
                refund.status = 'admin_warning'
                refund.admin_warning_note = admin_remark
                refund.admin_warning_date = timezone.now()
                refund.save()
            
            messages.success(request, f"Complaint resolved in buyer's favor. Warning sent to seller {complaint.seller.username}. Seller can now process the refund.")
            
        elif action == 'approve_seller':
            complaint.status = 'rejected'
            complaint.admin_remark = f"Decision: Seller's favor. {admin_remark}"
            complaint.resolved_at = timezone.now()
            complaint.save()
            messages.success(request, f"Complaint resolved in seller's favor. Buyer has been notified.")
            
        elif action == 'remove_seller':
            seller = complaint.seller
            profile = Profile.objects.get(user=seller)
            profile.seller_approved = False
            profile.save()
            
            complaint.status = 'resolved'
            complaint.admin_remark = f"Seller removed due to repeated complaints. {admin_remark}"
            complaint.resolved_at = timezone.now()
            complaint.save()
            
            messages.success(request, f"Seller {seller.username} has been removed from the platform.")
    
    return redirect('admin_complaints')

# Logout view
def logout_view(request):
    logout(request)
    return redirect('login')