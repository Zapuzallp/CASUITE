from django.views.generic import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy

from home.models import Leave, Employee
from home.forms import LeaveForm
from django.views import View
from django.shortcuts import render
from django.shortcuts import get_object_or_404, redirect


#Creating leave request
class LeaveCreateView(LoginRequiredMixin, CreateView):
    model = Leave
    form_class = LeaveForm
    template_name = 'apply_leave.html'
    success_url = reverse_lazy('leave-apply')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        employee = self.request.user.employee
        kwargs["leave_summary"] = employee.get_leave_summary()
        return kwargs

    def form_valid(self, form):
        employee_profile = Employee.objects.get(user=self.request.user)
        form.instance.employee = employee_profile
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        employee_profile = Employee.objects.get(user=user)

        # Get the dictionary from the model method
        leave_data = employee_profile.get_leave_summary()

        # Inject into context
        context['leave_summary'] = leave_data
        context['all_items'] = employee_profile.leave_records.all().order_by('-created_at')

        return context


#Deleting the leave request
class LeaveDeleteView(View):
    def get(self, request, leave_id):
        leave = get_object_or_404(Leave, pk=leave_id)
        leave.delete()
        return redirect("leave-apply")