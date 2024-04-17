from django.shortcuts import redirect
from django.urls import reverse
from .models import Post  

class RedirectIfPostNotFoundMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Check if 'post_id' is in the URL kwargs
        if 'post_id' in view_kwargs:
            post_id = view_kwargs['post_id']
            # Check if the Post exists
            if not Post.objects.filter(pk=post_id).exists():
                # Redirect to the forum home page
                return redirect(reverse('forum_home')) 

        return None