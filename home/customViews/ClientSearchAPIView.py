class ClientSearchAPIView(APIView):

    def get(self, request):
        query = request.GET.get("q")
        filters = request.GET

        qs = Client.objects.all()

        # 1️⃣ Intelligent GST Detection
        if query:
            if is_gst_number(query):
                qs = qs.filter(gst_number__iexact=query)
            else:
                qs = qs.filter(
                    Q(name__icontains=query) |
                    Q(mobile_number__icontains=query)
                )

        # 2️⃣ Custom Filters
        if filters.get("aadhaar_linked") == "true":
            qs = qs.filter(
                aadhaar_number__isnull=False,
                mobile_number__isnull=False
            )

        if filters.get("gst_enabled") == "true":
            qs = qs.filter(gst_enabled=True)

        if filters.get("valid_din") == "true":
            qs = qs.filter(
                directors__din_number__isnull=False
            ).distinct()

        data = [
            {
                "id": c.id,
                "name": c.name,
                "gst_number": c.gst_number,
                "gst_enabled": c.gst_enabled
            }
            for c in qs
        ]

        return Response(data)
