import logging
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.core.exceptions import ObjectDoesNotExist
from .models import Post, Comment, Category, Vote
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import F, ExpressionWrapper, IntegerField

logger = logging.getLogger(__name__)

def forum_home(request):
    user = request.user

    # Handle sorting
    sort_by = request.GET.get("sort_by", "recent")
    if sort_by == "popular":
        posts = Post.objects.annotate(
            calculated_score=ExpressionWrapper(
                F("upvotes") - F("downvotes"), output_field=IntegerField()
            )
        ).order_by("-calculated_score")
    else:
        posts = Post.objects.all().order_by("-created_at")

    # Prepare the vote_dict if the user is authenticated
    vote_dict = {}
    if user.is_authenticated:
        votes = Vote.objects.filter(user=user, post__in=posts).values('post_id', 'vote_type')
        vote_dict = {vote['post_id']: vote['vote_type'] for vote in votes}
    print(vote_dict)
    return render(request, "forum_home.html", {'posts': posts, 'vote_dict': vote_dict})

@login_required
def post_create(request):
    categories = Category.objects.all()

    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")
        category_id = request.POST.get("category")

        if not title.strip():
            messages.error(request, "Title cannot be empty.")
            return render(request, "post_create.html", {"categories": categories})

        if not content.strip():
            messages.error(request, "Content cannot be empty.")
            return render(request, "post_create.html", {"categories": categories})

        try:
            category = Category.objects.get(id=category_id)
        except ObjectDoesNotExist:
            messages.error(request, "Selected category does not exist.")
            return render(request, "post_create.html", {"categories": categories})

        new_post = Post(
            title=title, content=content, user=request.user, category=category
        )
        new_post.save()
        return redirect("post_detail", post_id=new_post.id)

    return render(request, "post_create.html", {"categories": categories})


def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.method == "POST":
        content = request.POST.get("content")

        if not content.strip():
            messages.error(request, "Comment cannot be empty.")
            return redirect("post_detail", post_id=post.id)

        comment = Comment.objects.create(
            post=post, content=content, user=request.user
        )
        comment.save()
        return redirect("post_detail", post_id=post.id)

    return redirect("forum_home")


def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    return render(request, "post_detail.html", {"post": post})


def posts_api(request):
    sort_by = request.GET.get("sort_by", "recent")
    posts = Post.objects.all().order_by("-created_at")[:10]
    logger.info(f"posts: {posts}")
    posts_data = [
        {
            "id": post.id,
            "title": post.title,
            "content": post.content,
            "author": post.user.username,
            "created_at": post.created_at.strftime("%Y-%m-%d %H:%M"),
            "likes": 0,
        }
        for post in posts
    ]
    logger.info(f"post_data: {posts_data}")
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
    else:
        return render(request, "post_delete.html", {"post": post})


def upvote_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    user = request.user

    vote, created = Vote.objects.get_or_create(user=user, post=post, defaults={'vote_type': 'upvote'})

    if vote.vote_type == "upvote":
        if created:
            post.upvotes += 1
        else:
            # Toggle to neutral if already upvoted
            vote.delete()
            post.upvotes -= 1
    elif vote.vote_type == "downvote":
        # Change downvote to upvote
        post.downvotes -= 1
        post.upvotes += 1
        vote.vote_type = "upvote"
        vote.save()

    post.save()
    return JsonResponse({"score": post.upvotes - post.downvotes})

def downvote_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    user = request.user

    vote, created = Vote.objects.get_or_create(user=user, post=post, defaults={'vote_type': 'downvote'})

    if vote.vote_type == "downvote":
        if created:
            post.downvotes += 1
        else:
            # Toggle to neutral if already downvoted
            vote.delete()
            post.downvotes -= 1
    elif vote.vote_type == "upvote":
        # Change upvote to downvote
        post.upvotes -= 1
        post.downvotes += 1
        vote.vote_type = "downvote"
        vote.save()

    post.save()
    return JsonResponse({"score": post.upvotes - post.downvotes})



@login_required
def delete_comment(request, post_id, comment_id):
    post = get_object_or_404(Post, id=post_id)
    comment = get_object_or_404(Comment, id=comment_id)

    if request.user != comment.user and not request.user.is_superuser:
        messages.error(request, "You are not authorized to delete this comment.")
        return redirect("post_detail", post_id=post.id)
    if request.method == "POST":
        comment.delete()

        return redirect("post_detail", post_id=post.id)

    context = {"comment": comment, "post": post}
    return redirect("post_detail", post_id=post_id)
