from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def clientDetails(request, pk):
    return render(request, "client/client-details.html")
