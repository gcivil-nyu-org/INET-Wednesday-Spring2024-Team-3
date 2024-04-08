from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from forum.models import Post, Comment
from .models import FriendRequest, Friendship
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

def public_user_profile(request, username):
    user = get_object_or_404(User, username=username)
    posts = Post.objects.filter(user=user).order_by('-created_at')
    comments = Comment.objects.filter(user=user).order_by('-created_at')

    paginator_posts = Paginator(posts, 5)
    paginator_comments = Paginator(comments, 5)

    page_number = request.GET.get('page')
    page_obj_posts = paginator_posts.get_page(page_number)
    page_obj_comments = paginator_comments.get_page(page_number)

    context = {
        'user': user,
        'posts': page_obj_posts,
        'comments': page_obj_comments,
    }
    return render(request, 'public_user.html', context)


@login_required
def send_friend_request(request, user_id):
    if request.method == 'POST':
        from_user = request.user
        to_user = get_object_or_404(User, id=user_id)
        friend_request, created = FriendRequest.objects.get_or_create(from_user=from_user, to_user=to_user)
        if created:
            return redirect('public_user', user_id=user_id)
    return redirect('public_user', user_id=user_id)

@login_required
def accept_friend_request(request, request_id):
    friend_request = get_object_or_404(FriendRequest, id=request_id)
    if friend_request.to_user == request.user:
        friend_request.status = 'accepted'
        friend_request.save()
        Friendship.objects.create(user1=friend_request.from_user, user2=friend_request.to_user)
    return redirect('friend_requests')

@login_required
def unfriend(request, user_id):
    user1 = request.user
    user2 = get_object_or_404(User, id=user_id)
    Friendship.objects.filter(user1__in=[user1, user2], user2__in=[user1, user2]).delete()
    return redirect('public_user', user_id=user_id)

@login_required
def friend_requests(request):
    friend_requests = FriendRequest.objects.filter(to_user=request.user, status='pending')
    return render(request, 'friend_requests.html', {'friend_requests': friend_requests})