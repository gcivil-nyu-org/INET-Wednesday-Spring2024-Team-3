from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login

# Login view
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Redirect to a success page.
            return redirect('home')  # Adjust 'home' to your desired redirect path
        else:
            # Return an error message
            return render(request, 'login.html', {'error': 'Invalid credentials'})
    return render(request, 'login.html')

# Registration view
def register_view(request):
    if request.method == 'POST':
        # Your registration logic here
        # Create a user and authenticate or return error
        ...
    return render(request, 'register.html')

def home_view(request):
    return render(request, 'home.html')
