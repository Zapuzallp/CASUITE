from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta

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
                return redirect('dashboard')
            messages.error(request, 'Invalid Credentials')
            return redirect("login")
        except Exception as e:
            messages.error(request, f'User not present in centralized data {str(e)}')
            return redirect("login")

class LogoutView(View):
    def get(self, request):
        if request.user.is_authenticated:
            logout(request)
            messages.info(request, 'You have successfully Logged Out')
        return redirect('login')
