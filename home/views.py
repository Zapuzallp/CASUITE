from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.views import View

class HomeView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        # 👇 Redirect non-staff users to client dashboard
        if not user.is_staff:
            return redirect('client_dashboard')
        return render(request, "dashboard.html")