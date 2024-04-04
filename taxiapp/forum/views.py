import logging
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.core.exceptions import ObjectDoesNotExist
from .models import Post, Comment, Category, Vote
from django.contrib.auth.decorators import login_required
from django.contrib import messages

logger = logging.getLogger(__name__)


def forum_home(request):
    posts = Post.objects.all().order_by("-created_at")
    context = {"posts": posts}
    return render(request, "forum_home.html", context)


@login_required
def post_create(request):
    categories = Category.objects.all()
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        category_id = request.POST.get('category')
        try:
            category = Category.objects.get(id=category_id)
            # logger.info('cat found')
        except ObjectDoesNotExist:
            messages.error(request, "Selected category does not exist.")
            # logger.info('cat fail')
            return render(request, 'post_create.html', {'categories': categories})
        if title and content and category:
            # logger.info('new_post being created')
            new_post = Post(title=title, content=content, user=request.user, category=category)
            new_post.save()
            return redirect('post_detail', post_id=new_post.id)
    return render(request, 'post_create.html', {'categories': categories})

def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.method == "POST":
        content = request.POST.get("content")
        if content:
            comment = Comment.objects.create(
                post=post, content=content, user=request.user
            )
            comment.save()
        return redirect("post_detail", post_id=post.id)
    return redirect("forum_home")

def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    return render(request, 'post_detail.html', {'post': post})

def posts_api(request):
    sort_by = request.GET.get('sort_by', 'recent')
    posts = Post.objects.all().order_by('-created_at')[:10]
    logger.info(f'posts: {posts}')
    posts_data = [{
        'id': post.id,
        'title': post.title,
        'content': post.content,
        'author': post.user.username,
        'created_at': post.created_at.strftime('%Y-%m-%d %H:%M'),
        'likes': 0,
    } for post in posts]
    logger.info(f'post_data: {posts_data}')
    return JsonResponse(posts_data, safe=False)

@login_required
def post_delete(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.user != post.user:
        messages.error(request, "You are not authorized to delete this post.")
        return redirect("post_detail", post_id=post.id)

    if request.method == "POST":
        post.delete()
        messages.success(request, "Post deleted successfully.")
        return redirect("forum_home")

    return render(request, "post_delete.html", {"post": post})


def upvote_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    user = request.user

    vote, created = Vote.objects.get_or_create(user=user, post=post)
    if created and vote.vote_type == 'upvote':
        post.upvotes += 1
        post.save()
    elif vote and vote.vote_type == 'upvote':
        pass
    elif vote and vote.vote_type == 'downvote':
        post.upvotes +=1
        post.save()
    
    vote.vote_type = 'upvote'
    vote.save()

    post_score = post.score
    return JsonResponse({'score': post_score})

def downvote_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    user = request.user

    vote, created = Vote.objects.get_or_create(user=user, post=post)
    if created and vote.vote_type == 'downvote':
        post.downvotes +=1
        post.save()
    elif vote and vote.vote_type == 'downvote':
        pass
    elif vote and vote.vote_type == 'upvote':
        post.downvotes +=1
        post.save()

    vote.vote_type = 'downvote'
    vote.save()

    post_score = post.score
    return JsonResponse({'score': post_score})
