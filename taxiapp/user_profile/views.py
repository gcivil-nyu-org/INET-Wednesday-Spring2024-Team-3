from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import UserProfile
from .forms import UserProfileForm

# View for displaying a user's profile
@login_required
def view_profile(request):
    profile = UserProfile.objects.get(user=request.user)
    return render(request, 'user_profile/view_profile.html', {'profile': profile})

# View for editing a user's profile
@login_required
def edit_profile(request):
    profile = UserProfile.objects.get(user=request.user)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('view_profile')
    else:
        form = UserProfileForm(instance=profile)

    return render(request, 'user_profile/edit_profile.html', {'form': form})
