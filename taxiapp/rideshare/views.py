from django.shortcuts import render
from django.http import HttpResponse


def rideshare_home_view(request):
    return HttpResponse("Hello, this is the rideshare home view!")
