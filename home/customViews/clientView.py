from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from home.forms import DocumentRequestForm
from home.models import DocumentRequest, RequestedDocument


@login_required
def clientDetails(request, pk):
    # This remains your original client lookup logic (by Django User ID)
    client = User.objects.get(id=pk)

    if request.method == "POST":
        form = DocumentRequestForm(request.POST)
        if form.is_valid():
            doc_req = form.save(commit=False)
            doc_req.client = client
            # 💡 FIX: Correctly set the creator to the logged-in user (request.user)
            doc_req.created_by = request.user
            doc_req.save()

            # Save selected documents
            for doc in form.cleaned_data['documents']:
                RequestedDocument.objects.create(
                    document_request=doc_req,
                    document_master=doc
                )

            messages.success(request, "Document Request created successfully!")
            # UX FIX: Redirect back with the tab anchor
            return redirect(request.path + '#documents')
    else:
        form = DocumentRequestForm()

    return render(request, "client/client-details.html", {
        "client": client,
        "form": form
    })