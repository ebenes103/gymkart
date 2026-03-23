from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

class SessionTimeoutMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Skip for login, register, and static pages
        if request.path in [reverse('login'), reverse('register')] or request.path.startswith('/static/') or request.path.startswith('/media/'):
            return None
        
        # Check if user is authenticated
        if request.user.is_authenticated:
            # Check if session exists and is valid
            if not request.session.exists(request.session.session_key):
                from django.contrib.auth import logout
                logout(request)
                return redirect('login')
        return None