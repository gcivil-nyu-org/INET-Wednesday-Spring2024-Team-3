from django.shortcuts import render

def tools_home(request):
    return render(request, 'tools_home.html')