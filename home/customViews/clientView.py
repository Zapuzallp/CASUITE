from django.contrib.auth.decorators import login_required
from django.shortcuts import render, HttpResponse
from ..models import Client, PrivateLimitedDetails, LLPDetails, OPCDetails, GSTDetails, AuditDetails, ITRDetails, ClientService
from datetime import datetime, date, time, timedelta


@login_required
def clientDetails(request, pk):

    if request.user.is_staff == True:
        try:
            client = Client.objects.get(pk=pk)
        except Client.DoesNotExist:
            return HttpResponse("Invalid client - page will render here")

        client_since_year = None
        client_since_month = None
        client_since_date = None


        current_year = datetime.now().year
        client_year = client.created_at.year

        if current_year == client_year:
            current_month = datetime.now().month
            client_month = client.created_at.month
            client_since_month = client_month - current_month

            if current_month == client_month:
                current_date = datetime.now().date().day
                client_date = client.created_at.date().day
                client_since_date = current_date - client_date
        else:
            client_since_year = client_year-current_year


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




        return render(request, "client/client-details.html", {"client":client, "PVT":PVT, "LLP":LLP, "OPC":OPC, "GST":GSTList, "Audit":AuditList, "ITR":ITRList, "client_since_month":client_since_month, "client_since_year":client_since_year, "client_since_date":client_since_date})

    return HttpResponse("You are not authorized")
