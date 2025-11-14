from django.contrib.auth.decorators import login_required
from django.shortcuts import render, HttpResponse
from ..models import Client, PrivateLimitedDetails, LLPDetails, OPCDetails, GSTDetails, AuditDetails, ITRDetails, ClientService


@login_required
def clientDetails(request, pk):

    if request.user.is_staff == True:
        try:
            client = Client.objects.get(pk=pk)
        except Client.DoesNotExist:
            return HttpResponse("Invalid client - page will render here")

        PVT = PrivateLimitedDetails.objects.filter(directors=client)
        LLP = LLPDetails.objects.filter(client=client)
        OPC = OPCDetails.objects.filter(client=client)

        ClientServices = ClientService.objects.filter(client=client)

        GSTList = []
        AuditList = []
        ITRList = []

        for service in ClientServices:
            GST = GSTDetails.objects.filter(client_service=service)
            Audit = AuditDetails.objects.filter(client_service=service)
            ITR = ITRDetails.objects.filter(client_service=service)

            GSTList += GST
            AuditList += Audit
            ITRList += ITR




        return render(request, "client/client-details.html", {"client":client, "PVT":PVT, "LLP":LLP, "OPC":OPC, "GST":GSTList, "Audit":AuditList, "ITR":ITRList})

    return HttpResponse("You are not authorized")
