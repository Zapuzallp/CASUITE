from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from datetime import datetime, date, timedelta
import calendar
from django.contrib import messages
from home.models import Attendance, OfficeDetails, Leave
from django.db.models import Sum, Q
from django.shortcuts import get_object_or_404
from home.models import Client, Payment

class PaymentCollectionReportView(LoginRequiredMixin, View):

    def get_financial_year_dates(self):
        today = date.today()
        if today.month >= 4:
            start = date(today.year, 4, 1)
            end = date(today.year + 1, 3, 31)
        else:
            start = date(today.year - 1, 4, 1)
            end = date(today.year, 3, 31)
        return start, end

    def get(self, request):

        clients = Client.objects.all()

        fy_start, fy_end = self.get_financial_year_dates()

        client_name = request.GET.get("client", "")
        selected_client = request.GET.get("client")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")

        if start_date:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        else:
            start_date = fy_start

        if end_date:
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            end_date = fy_end

        # IMPORTANT: Only Paid Payments
        payments = Payment.objects.filter(
            payment_status="PAID",  # VERY IMPORTANT
            payment_date__range=(start_date, end_date)
        )

        # Client Filter
        if selected_client:
            payments = payments.filter(
                invoice__client_id=selected_client
            )

        # USER WISE GROUPING
        report_data = (
            payments
            .values(
                "invoice__client__id",
                "invoice__client__client_name"
            )
            .annotate(
                credit=Sum("amount")
            )
            .order_by("-credit")
        )

        payment_details = None

        if selected_client:
            payment_details = (
                Payment.objects
                .filter(
                    payment_status="PAID",
                    payment_date__range=(start_date, end_date),
                    invoice__client_id=selected_client
                )
                .select_related("invoice__client")
                .order_by("-payment_date")
            )

        context = {
            "clients": clients,
            "selected_client": selected_client,
            "report_data": report_data,
            "start_date": start_date,
            "end_date": end_date,
            "payment_details": payment_details,
            "client_name": client_name,
        }

        return render(request, "payment_collection_report.html", context)


class PaymentCollectionDetailView(LoginRequiredMixin, View):

    def get(self, request, client_id):

        client = get_object_or_404(Client, id=client_id)

        # GET params
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        search = request.GET.get("search", "")

        payments = Payment.objects.filter(
            payment_status="PAID",
            invoice__client_id=client_id
        )

        # Date Filter
        if start_date:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            payments = payments.filter(payment_date__gte=start_date)

        if end_date:
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            payments = payments.filter(payment_date__lte=end_date)

        # Search Filter
        if search:
            payments = payments.filter(
                Q(id__icontains=search) |
                Q(transaction_id__icontains=search)
            )

        payments = payments.order_by("-payment_date")

        total_collection = payments.aggregate(
            total=Sum("amount")
        )["total"] or 0

        context = {
            "client": client,
            "payments": payments,
            "total_collection": total_collection,
            "start_date": start_date,
            "end_date": end_date,
            "search": search,
        }

        return render(
            request,
            "payment_collection_detail.html",
            context
        )