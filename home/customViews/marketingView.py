from django.views import View
from django.shortcuts import redirect
from django.contrib import messages


class ComposeMailView(View):
    def post(self, request, client_id):
        to_emails = request.POST.get('to_email')
        cc_emails = request.POST.get('cc_email')
        bcc_emails = request.POST.get('bcc_email')
        message = request.POST.get('email_body')

        if not to_emails:
            messages.error(request, "To email is required")
            return redirect(request.META.get("HTTP_REFERER", "/"))

        to_list = [e.strip() for e in to_emails.split(',') if e.strip()]
        cc_list = [e.strip() for e in cc_emails.split(',')] if cc_emails else []
        bcc_list = [e.strip() for e in bcc_emails.split(',')] if bcc_emails else []

        #  Demo processing only
        print("=== COMPOSE MAIL DEMO ===")
        print("TO:", to_list)
        print("CC:", cc_list)
        print("BCC:", bcc_list)
        print("BODY:", message)
        print("========================")

        messages.success(request, "Mail processed successfully (Demo Mode)")
        return redirect(request.META.get("HTTP_REFERER", "/"))

class SendPaymentReminderView(View):
    def post(self, request, client_id):
        # Get form data
        status = request.POST.get('invoice_status')
        send_email = request.POST.get('send_email')
        send_whatsapp = request.POST.get('send_whatsapp')

        messages.success(request, "Payment Reminder processed (Demo Mode)")
        return redirect(request.META.get("HTTP_REFERER", "/"))


class SendAccountStatementView(View):
    def post(self, request, client_id):
        # Get form data
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')
        send_email = request.POST.get('send_email')
        send_whatsapp = request.POST.get('send_whatsapp')

        messages.success(request, "Account Statement processed (Demo Mode)")
        return redirect(request.META.get("HTTP_REFERER", "/"))