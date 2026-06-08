from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from products.models import Product, Category
from orders.models import Order, OrderItem
from .models import Cart, CartItem
from django.http import JsonResponse
from django.db import transaction


# ─── Helper: staff check ────────────────────────────

def is_staff_user(user):
    return user.is_active and (user.is_staff or user.is_superuser)


# ─── Auth ───────────────────────────────────────────

def register(request):
    if request.user.is_authenticated:
        return redirect('store_home')

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        email      = request.POST.get('email', '').strip()
        phone      = request.POST.get('phone', '').strip()
        address    = request.POST.get('address', '').strip()
        dob        = request.POST.get('dob', '').strip()
        password   = request.POST.get('password', '')
        confirm    = request.POST.get('confirm', '')

        if not first_name or not last_name:
            messages.error(request, 'First name and last name are required.')
            return redirect('register')

        if password != confirm:
            messages.error(request, 'Passwords do not match.')
            return redirect('register')

        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters.')
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return redirect('register')

        # Username auto generate from email
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user = User.objects.create_user(
            username   = username,
            email      = email,
            password   = password,
            first_name = first_name,
            last_name  = last_name,
        )

        from .models import CustomerProfile
        CustomerProfile.objects.create(
            user    = user,
            phone   = phone,
            address = address,
            dob     = dob or None,
        )

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('store_home')

    return render(request, 'store/auth/login-register.html')


def customer_login(request):
    if request.user.is_authenticated:
        if is_staff_user(request.user):
            return redirect('/dashboard/')
        return redirect('store_home')

    if request.method == 'POST':
        email    = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        try:
            user_obj = User.objects.get(email=email)
            user     = authenticate(
                request,
                username=user_obj.username,
                password=password
            )
            if user is not None:
                login(request, user)

                if is_staff_user(user):
                    return redirect('/dashboard/')

                next_url = request.GET.get('next', '')
                if next_url and next_url.startswith('/store/'):
                    return redirect(next_url)

                return redirect('store_home')
            else:
                messages.error(request, 'Incorrect password.')
        except User.DoesNotExist:
            messages.error(request, 'No account found with this email.')

    return render(request, 'store/auth/login-register.html')


def customer_logout(request):
    logout(request)
    return redirect('customer_login')


# ─── Store ──────────────────────────────────────────

def store_home(request):
    if 'buy_now' in request.session:
        request.session.pop('buy_now', None)
        request.session.modified = True

    query      = request.GET.get('q', '')
    category   = request.GET.get('category', '')
    sort       = request.GET.get('sort', '')
    categories = Category.objects.all()

    products = Product.objects.filter(status='in_stock')
    
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    if category:
        products = products.filter(category__id=category)

    if sort == 'low-high':
        products = products.order_by('price')
    elif sort == 'high-low':
        products = products.order_by('-price')
    else:
        products = products.order_by('-created_at')

    cart_count = 0
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_count = cart.get_count()
    
    return render(request, 'store/index.html', {
        'products'          : products,
        'categories'        : categories,
        'query'             : query,
        'cart_count'        : cart_count,
        'selected_category' : category,
    })


def product_detail(request, pk):
    product    = get_object_or_404(Product, pk=pk)
    categories = Category.objects.all()
    suggested  = Product.objects.filter(status='in_stock').exclude(pk=pk)[:6]
    cart_count = 0
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_count = cart.get_count()
    return render(request, 'store/product_detail.html', {
        'product'           : product,
        'categories'        : categories,
        'suggested_products': suggested,
        'cart_count'        : cart_count,
    })


# ─── Cart ───────────────────────────────────────────

@login_required(login_url='/store/login/')
def cart_view(request):
    if 'buy_now' in request.session:
        request.session.pop('buy_now', None)
        request.session.modified = True

    cart, _ = Cart.objects.get_or_create(user=request.user)
    return render(request, 'store/cart.html', {
        'cart'      : cart,
        'cart_count': cart.get_count(),
    })


@login_required(login_url='/store/login/')
def cart_add(request, pk):
    product = get_object_or_404(Product, pk=pk)
    cart, _ = Cart.objects.get_or_create(user=request.user)

    qty = int(request.GET.get('qty', 1))
    item, created = CartItem.objects.get_or_create(cart=cart, product=product)

    if created:
        item.quantity = qty
    else:
        item.quantity += qty

    item.save()

    return JsonResponse({
        "success": True,
        "count": cart.get_count()
    })


@login_required(login_url='/store/login/')
def cart_remove(request, pk):
    cart = Cart.objects.get(user=request.user)
    CartItem.objects.filter(cart=cart, product__pk=pk).delete()
    return redirect('cart_view')


@login_required(login_url='/store/login/')
def cart_update(request, pk):
    cart     = Cart.objects.get(user=request.user)
    item     = get_object_or_404(CartItem, cart=cart, product__pk=pk)
    quantity = int(request.POST.get('quantity', 1))
    if quantity < 1:
        item.delete()
    else:
        item.quantity = quantity
        item.save()
    return redirect('cart_view')


@login_required(login_url='/store/login/')
def cart_data(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)

    items = []
    for i in cart.cartitem_set.all():
        items.append({
            "name": i.product.name,
            "qty": i.quantity,
            "price": i.product.price,
        })

    return JsonResponse({
        "items": items,
        "count": cart.get_count()
    })


# ─── Checkout (ডাইনামিক ডেলিভারি চার্জসহ মডিফাইড) ───

@login_required(login_url='/store/login/')
def checkout(request):
    from orders.models import OrderStatusLog
    cart, _ = Cart.objects.get_or_create(user=request.user)

    buy_now_session = request.session.get('buy_now')
    is_buy_now = bool(buy_now_session)

    # ─── GET: পেজ দেখানো ───
    if request.method == 'GET':
        cart_items = []
        cart_total = 0

        if is_buy_now:
            product_id = buy_now_session.get('product_id')
            qty        = int(buy_now_session.get('qty', 1))
            product    = get_object_or_404(Product, pk=product_id)
            subtotal   = product.price * qty

            cart_items = [{'product': product, 'quantity': qty, 'subtotal': subtotal}]
            cart_total = subtotal
        else:
            items = cart.cartitem_set.select_related('product').all()
            if not items.exists():
                messages.warning(request, "Your cart is empty!")
                return redirect('store_home')

            for item in items:
                subtotal = item.product.price * item.quantity
                cart_items.append({
                    'product':  item.product,
                    'quantity': item.quantity,
                    'subtotal': subtotal,
                })
                cart_total += subtotal

        return render(request, 'store/checkout.html', {
            'cart_items': cart_items,
            'cart_total': cart_total,
            'cart_count': cart.get_count(),
            'is_buy_now': is_buy_now,
        })

    # ─── POST: order save ───
    elif request.method == 'POST':
        buy_now_session = request.session.get('buy_now')
        is_buy_now      = bool(buy_now_session)

        if not is_buy_now:
            is_buy_now = request.POST.get('is_buy_now') == 'True'

        order_items_data = []
        total_amount     = 0

        if is_buy_now:
            if not buy_now_session:
                messages.error(request, "Session expired. Please try again.")
                return redirect('store_home')

            product_id = buy_now_session.get('product_id')
            qty        = int(buy_now_session.get('qty', 1))
            product    = get_object_or_404(Product, pk=product_id)

            total_amount = product.price * qty
            order_items_data.append({
                'product':  product,
                'quantity': qty,
                'price':    product.price,
            })
        else:
            items = cart.cartitem_set.select_related('product').all()
            if not items.exists():
                messages.error(request, "No items to order.")
                return redirect('store_home')

            for i in items:
                total_amount += i.product.price * i.quantity
                order_items_data.append({
                    'product':  i.product,
                    'quantity': i.quantity,
                    'price':    i.product.price,
                })

        # 🆕 ─── ডাইনামিক ডেলিভারি চার্জ ক্যালকুলেশন লজিক ───
        district = request.POST.get('district', '').strip().lower()
        
        # আপনি চাইলে এখান থেকে সহজেই চার্জের রেট যেকোনো সময় বাড়াতে বা কমাতে পারবেন
        inside_dhaka_charge = 60
        outside_dhaka_charge = 120

        if district == 'dhaka':
            delivery_charge = inside_dhaka_charge
        else:
            delivery_charge = outside_dhaka_charge

        # গ্র্যান্ড টোটাল = প্রোডাক্টের দাম + ডেলিভারি চার্জ
        total_amount += delivery_charge
        # ──────────────────────────────────────────────────

        try:
            with transaction.atomic():
                order = Order.objects.create(
                    customer   = request.user,
                    status     = 'pending',
                    total      = total_amount,  # এখানে চার্জসহ টোটাল অ্যামাউন্ট সেভ হচ্ছে
                    full_name  = request.POST.get('full_name', ''),
                    phone      = request.POST.get('phone', ''),
                    email      = request.POST.get('email', ''),
                    district   = request.POST.get('district', ''),
                    upazila    = request.POST.get('upazila', ''),
                    address    = request.POST.get('address', ''),
                    order_note = request.POST.get('order_note', ''),
                )

                for item in order_items_data:
                    OrderItem.objects.create(
                        order    = order,
                        product  = item['product'],
                        quantity = item['quantity'],
                        price    = item['price'],
                    )

                OrderStatusLog.objects.create(
                    order  = order,
                    status = 'pending',
                    note   = 'Order placed via Buy Now.' if is_buy_now else 'Order placed via Cart.'
                )

                if is_buy_now:
                    request.session.pop('buy_now', None)
                    request.session.modified = True
                else:
                    cart.cartitem_set.all().delete()

            messages.success(request, "Order placed successfully!")
            return redirect('order_tracking', pk=order.pk)

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('checkout')

    return redirect('store_home')


# ─── Order Tracking ─────────────────────────────────

@login_required(login_url='/store/login/')
def order_tracking(request, pk):
    order = get_object_or_404(Order, pk=pk, customer=request.user)
    return render(request, 'store/order_tracking.html', {
        'order'     : order,
        'cart_count': 0,
    })


@login_required(login_url='/store/login/')
def my_orders(request):
    orders  = Order.objects.filter(customer=request.user).order_by('-created_at')
    cart, _ = Cart.objects.get_or_create(user=request.user)
    return render(request, 'store/my_orders.html', {
        'orders'    : orders,
        'cart_count': cart.get_count(),
    })


# ─── Buy Now Handlers ───────────────────────────────

@login_required(login_url='/store/login/')
def buy_now(request):
    product_id = request.GET.get('product')
    qty = int(request.GET.get('qty', 1))

    if not product_id:
        return redirect('store_home')

    request.session['buy_now'] = {
        'product_id': int(product_id),
        'qty': qty
    }
    request.session.modified = True

    return redirect('checkout')


@login_required(login_url='/store/login/')
def buy_now_trigger(request, product_id):
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        
        request.session['buy_now'] = {
            'product_id': int(product_id),
            'qty': quantity
        }
        request.session.modified = True
        
        return redirect('checkout')
        
    return redirect('store_home')


# ─── Delete/Cancel Order ────────────────────────────

def delete_order(request, pk):

    if is_staff_user(request.user):
        order = get_object_or_404(Order, pk=pk)
    else:
        
        if not request.user.is_authenticated:
            return redirect('/store/login/')
        order = get_object_or_404(Order, pk=pk, customer=request.user)

    order.delete()
    messages.success(request, f"Order #{pk} has been deleted successfully.")
    
    referer_url = request.META.get('HTTP_REFERER')
    
    if referer_url:
        return redirect(referer_url)
    

    if is_staff_user(request.user):
        return redirect('order_list') 
    return redirect('my_orders')      