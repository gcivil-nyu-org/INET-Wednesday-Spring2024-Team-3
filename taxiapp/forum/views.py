from django.shortcuts import render


def forum_home_view(request):
    return render(request, "forum_home.html")
