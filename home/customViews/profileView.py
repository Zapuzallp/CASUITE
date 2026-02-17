from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


@login_required
def upload_profile_pic(request):
    if request.method == "POST":
        emp = request.user.employee
        pic = request.FILES.get('profile_pic')

        if pic:
            emp.profile_pic = pic
            emp.save()

    return redirect(request.META.get('HTTP_REFERER', '/'))

