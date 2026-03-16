from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import RegisterForm, ProductForm, ProductImageFormSet
from .models import Product, Profile, CartItem, Wishlist, ProductImage, Newsletter
from django.contrib.auth.models import User
from django.db.models import Q
from django.contrib import messages
import json

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
        print(f"Filtering by category: {category}")  # Debug line
        products = products.filter(category__iexact=category)
        print(f"Found {products.count()} products")  # Debug line
    
    # Debug: print all unique categories in database
    all_categories = Product.objects.values_list('category', flat=True).distinct()
    print(f"Available categories in DB: {list(all_categories)}")
    
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
        'low_stock_items': low_stock_items
    }
    
    return render(request, 'seller_dashboard.html', context)


@login_required(login_url='login')
def add_product(request):
    # Check if user is an approved seller
    try:
        profile = Profile.objects.get(user=request.user)
        if profile.role != 'seller':
            return redirect('home')
        if not profile.seller_approved:
            return render(request, 'waiting_approval.html')
    except Profile.DoesNotExist:
        return redirect('home')
    
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        formset = ProductImageFormSet(request.POST, request.FILES)
        
        if form.is_valid() and formset.is_valid():
            product = form.save(commit=False)
            product.seller = request.user
            
            # Get the parsed data from form
            product.available_weights = form.cleaned_data['available_weights_input']
            product.stock_per_weight = form.cleaned_data['stock_per_weight_input']
            
            product.save()
            
            # Save extra images
            formset.instance = product
            formset.save()
            
            return redirect("seller_dashboard")
    else:
        form = ProductForm()
        formset = ProductImageFormSet()
    
    return render(request, 'add_product.html', {'form': form, 'formset': formset})


@login_required(login_url='login')
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    # Check if user owns this product
    if product.seller != request.user:
        return redirect('seller_dashboard')
    
    if request.method == "POST":
        print("POST data:", request.POST)  # Debug: see what data is coming
        print("FILES data:", request.FILES)  # Debug: see what files are coming
        
        form = ProductForm(request.POST, request.FILES, instance=product)
        formset = ProductImageFormSet(request.POST, request.FILES, instance=product)
        
        print("Form is valid?", form.is_valid())  # Debug: check if form is valid
        print("Form errors:", form.errors)  # Debug: see form errors
        print("Formset is valid?", formset.is_valid())  # Debug: check if formset is valid
        print("Formset errors:", formset.errors)  # Debug: see formset errors
        
        if form.is_valid() and formset.is_valid():
            product = form.save(commit=False)
            
            # Get the parsed data from form
            if form.cleaned_data.get('available_weights_input'):
                product.available_weights = form.cleaned_data['available_weights_input']
            if form.cleaned_data.get('stock_per_weight_input'):
                product.stock_per_weight = form.cleaned_data['stock_per_weight_input']
            
            product.save()
            formset.save()
            
            print("Product saved successfully!")  # Debug: confirm save
            return redirect('seller_dashboard')
        else:
            # If form is invalid, stay on the same page but with errors
            print("Form has errors, staying on edit page")
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
    total_newsletters = Newsletter.objects.count()  # Add this
    recent_newsletters = Newsletter.objects.all()[:10]  # Get recent 10 subscribers

    context = {
        "profiles": profiles,
        "pending_sellers": pending_sellers,
        "approved_sellers": approved_sellers,
        "total_buyers": total_buyers,
        "total_users": total_users,
        "total_newsletters": total_newsletters,
        "recent_newsletters": recent_newsletters,  # Add this
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
            # Check if email already exists
            subscriber, created = Newsletter.objects.get_or_create(
                email=email,
                defaults={'is_active': True}
            )
            
            if created:
                # New subscriber
                messages.success(request, f"Thank you for subscribing to our newsletter! 🎉")
            else:
                # Already subscribed
                if subscriber.is_active:
                    messages.info(request, "You have already subscribed to our newsletter. Thank you! 💪")
                else:
                    # Reactivate if previously unsubscribed
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


# Logout view
def logout_view(request):
    logout(request)
    return redirect('login')