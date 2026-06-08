import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from django.utils import timezone
from django.utils.dateparse import parse_date
from datetime import timedelta
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from products.models import Product, Category
from orders.models import Order, OrderItem, OrderStatusLog


# ─── Helper ─────────────────────────────────────────────────────────────────

def is_admin(user):
    return user.is_active and user.is_staff


# admin_required decorator — fail হলে dashboard login এ যাবে
def admin_required(function):
    decorated = login_required(login_url='/dashboard/login/')(
        user_passes_test(is_admin, login_url='/dashboard/login/')(function)
    )
    return decorated


# ─── Auth ────────────────────────────────────────────────────────────────────

def dashboard_login(request):
    if request.user.is_authenticated:
        if is_admin(request.user):
            return redirect('dashboard_home')
        else:
            logout(request)
            messages.error(request, 'You do not have admin access.')
            return redirect('dashboard_login')

    if request.method == 'POST':
        email    = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        user_obj = User.objects.filter(email=email, is_staff=True).first()

        if user_obj is None:
            messages.error(request, 'No admin account found with this email.')
            return render(request, 'dashboard/login.html')

        user = authenticate(request, username=user_obj.username, password=password)

        if user is not None and is_admin(user):
            login(request, user)
            return redirect('dashboard_home')
        else:
            messages.error(request, 'Incorrect password.')

    return render(request, 'dashboard/login.html')


def logout_view(request):
    logout(request)
    return redirect('dashboard_login')


# ─── Settings ────────────────────────────────────────────────────────────────

@admin_required
def settings_view(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password', '')
        new_password     = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
        elif new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
        elif len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters.')
        else:
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Password changed successfully!')

    return render(request, 'dashboard/settings.html')


# ─── Dashboard Home ──────────────────────────────────────────────────────────

@admin_required
def dashboard_home(request):
    today  = timezone.now().date()
    last_7 = today - timedelta(days=6)

    daily_labels  = []
    daily_orders  = []
    daily_revenue = []

    for i in range(7):
        day        = last_7 + timedelta(days=i)
        day_orders = Order.objects.filter(created_at__date=day)
        daily_labels.append(day.strftime("%b %d"))
        daily_orders.append(day_orders.count())
        daily_revenue.append(
            float(day_orders.filter(status='delivered')
                  .aggregate(Sum('total'))['total__sum'] or 0)
        )

    status_data = [
        Order.objects.filter(status='pending').count(),
        Order.objects.filter(status='in_courier').count(),
        Order.objects.filter(status='delivered').count(),
        Order.objects.filter(status='cancelled').count(),
        Order.objects.filter(status='returned').count(),
    ]

    context = {
        'total_products'  : Product.objects.count(),
        'total_orders'    : Order.objects.count(),
        'total_customers' : User.objects.filter(is_staff=False).count(),
        'total_revenue'   : Order.objects.filter(status='delivered')
                            .aggregate(Sum('total'))['total__sum'] or 0,

        'pending_count'   : status_data[0],
        'in_courier_count': status_data[1],
        'delivered_count' : status_data[2],
        'cancelled_count' : status_data[3],
        'returned_count'  : status_data[4],

        'recent_orders'   : Order.objects.order_by('-created_at')[:10],

        'daily_labels'    : json.dumps(daily_labels),
        'daily_orders'    : json.dumps(daily_orders),
        'daily_revenue'   : json.dumps(daily_revenue),
        'status_data'     : json.dumps(status_data),
    }
    return render(request, 'dashboard/home.html', context)


# ─── Analytics ───────────────────────────────────────────────────────────────

@admin_required
def analytics(request):
    today       = timezone.now().date()
    date_from   = request.GET.get('date_from', str(today - timedelta(days=30)))
    date_to     = request.GET.get('date_to',   str(today))
    single_date = request.GET.get('single_date', '')

    if single_date:
        d      = parse_date(single_date)
        orders = Order.objects.filter(created_at__date=d)
        start  = d
        delta  = 1
    else:
        orders = Order.objects.filter(
            created_at__date__gte=date_from,
            created_at__date__lte=date_to,
        )
        start = parse_date(date_from)
        end   = parse_date(date_to)
        delta = (end - start).days + 1

    stats = {
        'total'      : orders.count(),
        'pending'    : orders.filter(status='pending').count(),
        'in_courier' : orders.filter(status='in_courier').count(),
        'delivered'  : orders.filter(status='delivered').count(),
        'cancelled'  : orders.filter(status='cancelled').count(),
        'returned'   : orders.filter(status='returned').count(),
        'revenue'    : float(orders.filter(status='delivered')
                       .aggregate(Sum('total'))['total__sum'] or 0),
    }

    trend_labels  = []
    trend_revenue = []
    trend_orders  = []

    for i in range(min(delta, 60)):
        day        = start + timedelta(days=i)
        day_orders = orders.filter(created_at__date=day)
        trend_labels.append(day.strftime("%b %d"))
        trend_revenue.append(
            float(day_orders.filter(status='delivered')
                  .aggregate(Sum('total'))['total__sum'] or 0)
        )
        trend_orders.append(day_orders.count())

    status_data = [
        stats['pending'], stats['in_courier'], stats['delivered'],
        stats['cancelled'], stats['returned'],
    ]

    context = {
        'stats'         : stats,
        'orders'        : orders.order_by('-created_at'),
        'date_from'     : date_from,
        'date_to'       : date_to,
        'single_date'   : single_date,
        'trend_labels'  : json.dumps(trend_labels),
        'trend_revenue' : json.dumps(trend_revenue),
        'trend_orders'  : json.dumps(trend_orders),
        'status_data'   : json.dumps(status_data),
    }
    return render(request, 'dashboard/analytics.html', context)


# ─── Products ────────────────────────────────────────────────────────────────

@admin_required
def product_list(request):
    products = Product.objects.select_related('category').all()
    return render(request, 'dashboard/products/list.html', {'products': products})


@admin_required
def product_create(request):
    categories = Category.objects.all()
    if request.method == 'POST':
        Product.objects.create(
            name        = request.POST['name'],
            price       = request.POST['price'],
            stock       = request.POST['stock'],
            status      = request.POST['status'],
            badge       = request.POST.get('badge', 'New'),
            size        = request.POST.get('size', 'Standard Pack'),
            is_highlighted = request.POST.get('is_highlighted') == 'on',
            description = request.POST.get('description', ''),
            image       = request.FILES.get('image'),
            category_id = request.POST.get('category') or None,
        )
        return redirect('product_list')
    return render(request, 'dashboard/products/form.html', {'categories': categories})


@admin_required
def product_edit(request, pk):
    product    = get_object_or_404(Product, pk=pk)
    categories = Category.objects.all()
    if request.method == 'POST':
        product.name          = request.POST['name']
        product.price         = request.POST['price']
        product.stock         = request.POST['stock']
        product.status        = request.POST['status']
        product.badge         = request.POST.get('badge', 'New')
        product.size          = request.POST.get('size', 'Standard Pack')
        product.is_highlighted = request.POST.get('is_highlighted') == 'on'
        product.description   = request.POST.get('description', '')
        product.category_id   = request.POST.get('category') or None
        if request.FILES.get('image'):
            product.image = request.FILES['image']
        product.save()
        return redirect('product_list')
    return render(request, 'dashboard/products/form.html', {
        'product'   : product,
        'categories': categories,
    })


@admin_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    return redirect('product_list')


# ─── Categories ──────────────────────────────────────────────────────────────

@admin_required
def category_list(request):
    categories = Category.objects.all()
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if name:
            Category.objects.create(name=name)
        return redirect('category_list')
    return render(request, 'dashboard/products/categories.html', {'categories': categories})


@admin_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.delete()
    return redirect('category_list')


# ─── Orders ──────────────────────────────────────────────────────────────────

@admin_required
def order_list(request):
    orders = Order.objects.select_related('customer').order_by('-created_at')
    return render(request, 'dashboard/orders/list.html', {'orders': orders})


@admin_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    return render(request, 'dashboard/orders/detail.html', {'order': order})


@admin_required
def order_status_update(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status', '')
        note       = request.POST.get('note', '')
        order.status = new_status
        order.save()
        OrderStatusLog.objects.create(
            order  = order,
            status = new_status,
            note   = note,
        )
    return redirect('order_detail', pk=pk)


# ─── Customers ───────────────────────────────────────────────────────────────

@admin_required
def customer_list(request):
    customers = User.objects.filter(is_staff=False).order_by('-date_joined')
    return render(request, 'dashboard/customers/list.html', {'customers': customers})