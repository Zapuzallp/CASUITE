from django.shortcuts import render, redirect
from django.contrib import messages
from home.forms import TutorialForm
from home.models import Tutorial
from django.shortcuts import render, redirect, get_object_or_404


def tutorial_list(request):
    is_admin = request.user.is_superuser or getattr(request.user.employee, "role", "") == "ADMIN"

    if request.method == "POST":
        if not is_admin:
            messages.error(request, "Not authorized")
            return redirect("tutorial_list")

        Tutorial.objects.create(
            title=request.POST.get("title"),
            description=request.POST.get("description"),
            video_url=request.POST.get("video_url"),
            category=request.POST.get("category", "General"), # Make sure category is saved
            custom_thumbnail=request.FILES.get("custom_thumbnail")
        )

        messages.success(request, "Tutorial added successfully!")
        return redirect("tutorial_list")

    # IMPORTANT: order_by('category') is required for the {% regroup %} tag to work in the template
    tutorials = Tutorial.objects.all().order_by('category', '-created_at')

    return render(request, "tutorial_list.html", {
        "tutorials": tutorials,
        "is_admin": is_admin
    })


def add_tutorial(request):

    # Permission check
    if not (request.user.is_superuser or request.user.employee.role == "ADMIN"):
        messages.error(request, "You are not authorized to add tutorials.")
        return redirect('tutorial_list')

    if request.method == "POST":
        form = TutorialForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Tutorial added successfully!")
            return redirect('tutorial_list')
    else:
        form = TutorialForm()

    return render(request, "add_tutorial.html", {"form": form})


def delete_tutorial(request, tutorial_id):
    # Permission check
    is_admin = request.user.is_superuser or getattr(request.user.employee, "role", "") == "ADMIN"

    if not is_admin:
        messages.error(request, "Not authorized to delete tutorials.")
        return redirect("tutorial_list")

    if request.method == "POST":
        tutorial = get_object_or_404(Tutorial, id=tutorial_id)
        tutorial.delete()
        messages.success(request, "Tutorial deleted successfully!")

    return redirect("tutorial_list")