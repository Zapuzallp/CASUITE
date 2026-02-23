from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from django.views import View
import re

class LoginView(View):
    def get(self, request):
        return render(request, 'auth/login.html')

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)

                user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
                is_mobile = bool(re.search(r"iphone|ipad|android", user_agent))
                if user.is_staff:
                    return redirect('dashboard')
                else:
                    return redirect('client_dashboard')

            else:
                messages.error(request, 'Invalid Credentials')
                return redirect("login")
        except Exception as e:
            messages.error(request, f'User not present in centralized data: {str(e)}')
            return redirect("login")


class LogoutView(View):
    def get(self, request):
        if request.user.is_authenticated:
            logout(request)
            messages.info(request, 'You have successfully Logged Out')
        return redirect('login')
