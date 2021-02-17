from django.shortcuts import render, HttpResponseRedirect ,redirect
from App_Order.models import  Order, Cart
from App_Payment.models import BillingAddress
from App_Payment.forms import BillingForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse

#for payemnt:
import requests
from sslcommerz_python.payment import SSLCSession
from decimal import Decimal
import socket
from django.views.decorators.csrf import csrf_exempt

# Create your views here.

@login_required
def checkout(request):
    saved_address = BillingAddress.objects.get_or_create(user=request.user)
    saved_address = saved_address[0]
    form = BillingForm(instance=saved_address)
    if request.method == 'POST':
        form = BillingForm(request.POST, instance=saved_address)
        if form.is_valid():
            form.save()
            form = BillingForm(instance=saved_address)
            messages.success(request, f'shipping address saved')

    order_qs = Order.objects.filter(user=request.user, ordered=False)
    order_items = order_qs[0].orderitems.all()
    print(order_items)
    order_total = order_qs[0].get_totals()
    return render(request, 'App_Payment/Checkout.html', context={'form':form, 'order_qs':order_qs,
     'order_total':order_total, 'order_items':order_items, 'saved_address':saved_address})

@login_required
def payment(request):
    saved_address = BillingAddress.objects.get_or_create(user=request.user)
    saved_address = saved_address[0]
    if not saved_address.is_fully_filled():
        messages.info(request, f'please complete your shipping address')
        return redirect('App_Payment:checkout')

    if not request.user.profile.is_fully_filled():
        messages.info(request, f'please complete your profile info')
        return redirect('App_Login:profile')

    
    store_id = 'tiger602292dc87dce'
    API_key = 'tiger602292dc87dce@ssl'

    mypayment = SSLCSession(sslc_is_sandbox=True, sslc_store_id=store_id, 
    sslc_store_pass=API_key)
    staus_url = request.build_absolute_uri(reverse('App_Payment:complete'))
    print(staus_url)
    
    mypayment.set_urls(success_url=staus_url, fail_url=staus_url,
    cancel_url=staus_url, ipn_url=staus_url)

    order_qs = Order.objects.filter(user=request.user, ordered=False)
    order_items = order_qs[0].orderitems.all()
    order_items_count = order_qs[0].orderitems.count()
    order_total = order_qs[0].get_totals()

    mypayment.set_product_integration(total_amount=Decimal(order_total), currency='BDT', 
    product_category='Mixed', product_name=order_items, num_of_item=order_items_count, shipping_method='Courier', 
    product_profile='None')

    current_user = request.user

    mypayment.set_customer_info(name=current_user.profile.full_name, email=current_user.email, address1=current_user.profile.address_1,
    address2=current_user.profile.address_1, city=current_user.profile.city, postcode=current_user.profile.zipcode,
    country=current_user.profile.country, phone=current_user.profile.phone)

    mypayment.set_shipping_info(shipping_to=current_user.profile.full_name, address=saved_address.address, city=saved_address.city,
    postcode=saved_address.zipcode, country=saved_address.country)

    response_data = mypayment.init_payment()
    print(response_data)
    return redirect(response_data['GatewayPageURL'])
   
    return render(request, 'App_Payment/payment.html', context={})
@csrf_exempt
def complete(request):
    if request.method == 'POST' or request.method == 'post':
        payment_data = request.POST
        status = payment_data['status']
        bank_tran_id = payment_data['bank_tran_id']

        if status == 'VALID':
            val_id = payment_data['val_id']
            tran_id = payment_data['tran_id']
            messages.success(request, f'Your Payment Completed Successfully. Page will be redirected.')
            return HttpResponseRedirect(reverse("App_Payment:purchase", kwargs={'val_id':val_id, 'tran_id':tran_id},))
        elif status == 'FAILED':
            messages.warning(request, f'your payment failed. please try again')

        elif status == 'CANCLE':
            messages.warning(request, f'you cancle your payment')
    return render(request, 'App_Payment/complete.html', context={})


@login_required
def purchase(request, val_id, tran_id):
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    order = order_qs[0]
    oderId = tran_id
    order.ordered = True
    order.orderId = oderId
    order.paymentId = val_id
    order.save()
    cart_items = Cart.objects.filter(user=request.user, purchased=False)
    for item in cart_items:
        item.purchased = True
        item.save()
    return HttpResponseRedirect(reverse("App_Shop:home"))

@login_required
def order_view(request):
    try:
        orders = Order.objects.filter(user=request.user, ordered= True)
        print(orders)
        context = {"orders":orders}
    except:
        messages.warning(request,"You don't have an active status")
        return redirect("App_Shop:home")
    return render(request, "App_Payment/order.html", context)