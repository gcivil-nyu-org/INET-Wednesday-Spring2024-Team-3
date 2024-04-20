from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from forum.models import Post, Comment
from .models import FriendRequest, Friendship, ChatMessage
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
    has_sent_request = False
    has_received_request = False
    received_request_id = None

    if request.user.is_authenticated:
        if request.user != user:
            is_friend = Friendship.objects.filter(
                (Q(user1=request.user, user2=user) | Q(user1=user, user2=request.user))
            ).exists()
            has_sent_request = FriendRequest.objects.filter(from_user=request.user, to_user=user, status='pending').exists()
            has_received_request = FriendRequest.objects.filter(from_user=user, to_user=request.user, status='pending').exists()
            if has_received_request:
                received_request = FriendRequest.objects.filter(from_user=user, to_user=request.user, status='pending').first()
                received_request_id = received_request.id

    context = {
        'user': user,
        'posts': page_obj_posts,
        'comments': page_obj_comments,
        'is_friend': is_friend,
        'has_sent_request': has_sent_request,
        'has_received_request': has_received_request,
        'received_request_id': received_request_id,
    }
    return render(request, 'public_user.html', context)

@login_required
def cancel_friend_request(request, user_id):
    to_user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        FriendRequest.objects.filter(from_user=request.user, to_user=to_user, status='pending').delete()
        return redirect(request.META.get('HTTP_REFERER', '/'))
    
@login_required
def send_friend_request(request, user_id):
    to_user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        friend_request, created = FriendRequest.objects.get_or_create(from_user=request.user, to_user=to_user)
        return redirect(request.META.get('HTTP_REFERER', '/'))

@login_required
def accept_friend_request(request, request_id):
    friend_request = get_object_or_404(FriendRequest, id=request_id)
    if request.method == 'POST':
        if friend_request.to_user == request.user and friend_request.status == 'pending':
            friend_request.status = 'accepted'
            friend_request.save()
            Friendship.objects.create(user1=friend_request.from_user, user2=friend_request.to_user)
            return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def reject_friend_request(request, request_id):
    friend_request = get_object_or_404(FriendRequest, id=request_id)
    if request.method == 'POST':
        if friend_request.to_user == request.user and friend_request.status == 'pending':
            friend_request.status = 'rejected'
            friend_request.delete()
            return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def unfriend(request, user_id):
    user1 = request.user
    user2 = get_object_or_404(User, id=user_id)
    Friendship.objects.filter(user1__in=[user1, user2], user2__in=[user1, user2]).delete()
    FriendRequest.objects.filter(from_user__in=[user1, user2], to_user__in=[user1, user2]).delete()
    ChatMessage.objects.filter((Q(sender=user1, receiver=user2) |
                                Q(sender=user2, receiver=user1))).delete()
    return redirect(request.META.get('HTTP_REFERER', '/'))



@login_required
def friend_requests(request):
    friend_requests = FriendRequest.objects.filter(to_user=request.user, status='pending')
    return redirect('taxiapp:profile')

@login_required
def chat_view(request, username):
    other_user = get_object_or_404(User, username=username)
    if request.method == 'POST':
        message = request.POST.get('message', '')
        if message:
            ChatMessage.objects.create(sender=request.user, receiver=other_user, message=message)
            return redirect('chat', username=username)

    messages = ChatMessage.objects.filter(
        (Q(sender=request.user, receiver=other_user) | Q(sender=other_user, receiver=request.user))
    ).order_by('timestamp')

    return render(request, 'chat.html', {'other_user': other_user, 'messages': messages})


def search_people(request):
    query = request.GET.get('query')
    users = User.objects.filter(username__icontains=query) if query else User.objects.none()
    
    if request.user.is_authenticated:
        friendships = Friendship.objects.filter(user1=request.user) | Friendship.objects.filter(user2=request.user)
        friends = [friendship.user2 if friendship.user1 == request.user else friendship.user1 for friendship in friendships]
        has_sent_request = {}
        for user in users:
            has_sent_request[user] = FriendRequest.objects.filter(from_user=request.user, to_user=user, status='pending').exists()
    else:
        friends = []
        has_sent_request = {}
        
    context = {
        'users': users,
        'friends': friends,
        'has_sent_request': has_sent_request,
    }
    return render(request, 'search_user.html', context)