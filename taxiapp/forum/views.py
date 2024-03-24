from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.core.exceptions import ObjectDoesNotExist
from .models import Post, Comment, Category
from django.contrib.auth.decorators import login_required
from django.contrib import messages


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
        except ObjectDoesNotExist:
            messages.error(request, "Selected category does not exist.")
            return render(request, 'post_create.html', {'categories': categories})
        if title and content and category:
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
                post=post, content=content, author=request.user
            )
            comment.save()
        return redirect("post_detail", post_id=post.id)
    return redirect("forum_home")

def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    return render(request, 'post_detail.html', {'post': post})

def posts_api(request):
    sort_by = request.GET.get('sort_by', 'recent')
    posts = Post.objects.all().order_by('-created_at')[:10]  # Adjust the query
    posts_data = [{
        'id': post.id,
        'title': post.title,
        'content': post.content,
        'author': post.user.username,  
        'created_at': post.created_at.strftime('%Y-%m-%d %H:%M'),
        'likes': 0,  # Placeholder
    } for post in posts]
    return JsonResponse(posts_data, safe=False)