from django.shortcuts import redirect
from functools import wraps

def login_required_firebase(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'uid' not in request.session:
            return redirect("login")  # Redirect to login if not authenticated
        return view_func(request, *args, **kwargs)
    return wrapper
