from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from forum.models import Post, Comment

from django.core.paginator import Paginator

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