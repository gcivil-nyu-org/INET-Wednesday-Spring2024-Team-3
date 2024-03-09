from django.shortcuts import render
from django.http import HttpResponse

def forum_home_view(request):
    return HttpResponse("Hello, this is the forum home view!")
