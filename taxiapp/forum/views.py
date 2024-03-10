from django.shortcuts import render, get_object_or_404, redirect
from .models import ForumPost, Comment


def forum_home(request):
    posts = ForumPost.objects.all().order_by(
        "-created_at"
    )  # Fetch all posts and order them by creation date
    context = {"posts": posts}
    return render(request, "forum_home.html", context)


def post_create(request):
    if request.method == "POST":
        post_content = request.POST.get("post_content")
        if post_content:
            # Create a new ForumPost object and save it
            new_post = ForumPost(content=post_content, author=request.user)
            new_post.save()
            return redirect("forum_home")
    return redirect("forum_home")


def post_detail(request, post_id):
    post = get_object_or_404(ForumPost, id=post_id)
    return render(request, "post_detail.html", {"post": post})


def add_comment(request, post_id):
    post = get_object_or_404(ForumPost, id=post_id)
    if request.method == "POST":
        content = request.POST.get("content")
        if content:
            comment = Comment.objects.create(
                post=post, content=content, author=request.user
            )
            comment.save()
        return redirect("post_detail", post_id=post.id)
    return redirect("forum_home")
