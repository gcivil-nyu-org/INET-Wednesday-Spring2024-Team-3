from django.shortcuts import render
from django.http import HttpResponse

def my_view(request):
    return HttpResponse("Hello, this is my view!")
