from django.shortcuts import render
from home.models import Tutorial


def tutorial_list(request):

    tutorials = Tutorial.objects.all()

    return render(request, "tutorial_list.html", {
        "tutorials": tutorials
    })