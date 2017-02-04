from django.contrib.auth import login
from allauth.socialaccount.models import SocialAccount
from stockmarket.models import *
from customer.models import *

from django.utils import *

from django.http import HttpResponse, JsonResponse
from django.shortcuts import *
from django.views.decorators.http import require_POST

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from django.views.decorators.csrf import csrf_exempt

from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from rest_framework.response import Response
from rest_framework.views import APIView
from django.core import serializers

import json

@api_view(["GET"])
def customerList(request, format = None):
	tuples = Customer.objects.all()
	customer_serialized = serializers.serialize('json', tuples)
	return HttpResponse(customer_serialized, content_type="application/json")

@api_view(["GET"])
def customerDetail(request, format = None):
	customer = get_object_or_404(Customer, user=request.user)
	response_data ={}
	response_data['fbid'] = SocialAccount.objects.get(user = customer.user).uid
	response_data['name'] = customer.user.first_name + ' ' + customer.user.last_name
	response_data['account_balance'] = customer.account_balance
	response_data['loan_balance'] = Loan.objects.filter(customer=customer).first().amount
	response_data['worth'] = customer.worth()
	return JsonResponse(response_data)

@api_view(["GET"])
def stockHolding(request, format = None):
	tuples = StockHolding.objects.filter(customer__user = request.user).all()
	serialized = serializers.serialize('json', tuples)
	return HttpResponse(serialized, content_type="application/json")

@api_view(["GET"])
def stockShorted(request, format = None):
	# shorted_quantity=get_object_or_404(StockHolding, user=request.user, company__pk=request.GET.get('id')).quantity
	tuples = StockShorted.objects.filter(customer__user = request.user).all()
	serialized = serializers.serialize('json', tuples)
	return HttpResponse(serialized, content_type="application/json")
	# return HttpResponse(str(shorted_quntity))

@api_view(["GET"])
def customerActivity(request, format=None):
	tuples = CustomerActivity.objects.filter(customer__user = request.user).all()
	serialized = serializers.serialize('json', tuples)
	return HttpResponse(serialized, content_type="application/json")

@api_view(["POST"])
def buy(request, format=None):
	customer = get_object_or_404(Customer, user=request.user)
	company = get_object_or_404(Company, pk=request.POST.get('id'))
	quantity = int(request.POST.get('quantity'))
	if quantity is None:
		return JsonResponse({"success":False})
	if 0 < quantity <= min(customer.account_balance//company.stock_price, company.available_quantity):
		stockHolding = get_object_or_404(StockHolding, company=company, customer=customer)
		stockHolding.quantity += quantity
		customer.account_balance -= company.stock_price * quantity
		company.available_quantity -= quantity
		customerActivity = CustomerActivity(customer=customer, action='BUY', timestamp=timezone.now(), quantity=quantity, price=company.stock_price)
		customerActivity.save()
		customer.save()
		company.save()
		stockHolding.save()
		return JsonResponse({"success":True})
	return JsonResponse({"success":False})

@api_view(["POST"])
def sell(request, format=None):
	customer = get_object_or_404(Customer, user=request.user)
	company = get_object_or_404(Company, pk=request.POST.get('id'))
	quantity = int(request.POST.get('quantity'))
	stockHolding = get_object_or_404(StockHolding, company=company, customer=customer)
	if quantity is None:
		return JsonResponse({"success":False})
	if 0 < quantity <= stockHolding.quantity:
		stockHolding.quantity -= quantity
		customer.account_balance += company.stock_price * quantity
		company.available_quantity += quantity
		customerActivity = CustomerActivity(customer=customer, action='SELL', timestamp=timezone.now(), quantity=quantity, price=company.stock_price)
		customerActivity.save()
		customer.save()
		company.save()
		stockHolding.save()
		return JsonResponse({"success":True})
	return JsonResponse({"success":False})

@api_view(["POST"])
def short(request, format=None):
	customer = get_object_or_404(Customer, user=request.user)
	company = get_object_or_404(Company, pk=request.POST.get('id'))
	quantity = int(request.POST.get('quantity'))
	if quantity is None:
		return JsonResponse({"success":False})
	if 0 < quantity <= company.available_quantity:
		stockShorted = get_object_or_404(StockShorted, company=company, customer=customer)
		stockShorted.quantity += quantity
		customer.account_balance += company.stock_price * quantity
		# company.available_quantity -= quantity
		customerActivity = CustomerActivity(customer=customer, action='SHORT', timestamp=timezone.now(), quantity=quantity, price=company.stock_price)
		customerActivity.save()
		customer.save()
		company.save()
		stockShorted.save()
		return JsonResponse({"success":True})
	return JsonResponse({"success":False})

@api_view(["POST"])
def cover(request, format=None):
	customer = get_object_or_404(Customer, user=request.user)
	company = get_object_or_404(Company, pk=request.POST.get('id'))
	stockShorted = get_object_or_404(StockShorted, company=company, customer=customer)
	quantity = int(request.POST.get('quantity'))
	if quantity is None:
		return JsonResponse({"success":False})
	if 0 < quantity <= stockShorted.quantity:
		stockShorted.quantity -= quantity
		customer.account_balance -= company.stock_price * quantity
		# company.available_quantity -= quantity
		customerActivity = CustomerActivity(customer=customer, action='COVER', timestamp=timezone.now(), quantity=quantity, price=company.stock_price)
		customerActivity.save()
		customer.save()
		company.save()
		stockShorted.save()
		return JsonResponse({"success":True})
	return JsonResponse({"success":False})


def createCustomer(request, format = None):	
	if not request.user.is_authenticated:	
		user = SocialAccount.objects.get(uid = request.GET.get("fbid")).user
		login(request, user)
	else:
		user = request.user
	try:
		customer = Customer.objects.get(user = user)
	except Customer.DoesNotExist:
		customer = Customer(user = user, account_balance = 25000)
		companies = Company.objects.all()
		customer.save()
		for company in companies:
			sh = StockHolding(company=company, customer=customer, quantity=0)
			ss = StockShorted(company=company, customer=customer, quantity=0)
			sh.save()
			ss.save()
	return HttpResponseRedirect('/')
