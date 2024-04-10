from django.db.models import Q
from django.http import HttpResponseForbidden
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

    is_friend = False

    if request.user.is_authenticated and request.user != user:
        is_friend = Friendship.objects.filter(
            (Q(user1=request.user, user2=user) | Q(user1=user, user2=request.user))
        ).exists()

    context = {
        'user': user,
        'posts': page_obj_posts,
        'comments': page_obj_comments,
        'is_friend': is_friend,

    }
    return render(request, 'public_user.html', context)


@login_required
def send_friend_request(request, user_id):
    to_user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        friend_request, created = FriendRequest.objects.get_or_create(from_user=request.user, to_user=to_user)
        print(created)

        if created:
            return redirect('public_user', username=to_user.username)
    return redirect('public_user', username=to_user.username)


@login_required
def accept_friend_request(request, request_id):
    friend_request = get_object_or_404(FriendRequest, id=request_id)
    if request.method == 'POST':
        if friend_request.to_user == request.user and friend_request.status == 'pending':
            friend_request.status = 'accepted'
            friend_request.save()
            Friendship.objects.create(user1=friend_request.from_user, user2=friend_request.to_user)
    return redirect('friend_requests')


@login_required
def reject_friend_request(request, request_id):
    friend_request = get_object_or_404(FriendRequest, id=request_id)

    if request.method == 'POST':
        if friend_request.to_user == request.user and friend_request.status == 'pending':
            friend_request.status = 'rejected'
            friend_request.save()
    return redirect('friend_requests')


@login_required
def unfriend(request, user_id):
    user1 = request.user
    user2 = get_object_or_404(User, id=user_id)
    Friendship.objects.filter(user1__in=[user1, user2], user2__in=[user1, user2]).delete()
    FriendRequest.objects.filter(from_user__in=[user1, user2], to_user__in=[user1, user2]).delete()
    return redirect('public_user', username=user2.username)


@login_required
def friend_requests(request):
    friend_requests = FriendRequest.objects.filter(to_user=request.user, status='pending')
    return redirect('public_user', username=request.user.username)
