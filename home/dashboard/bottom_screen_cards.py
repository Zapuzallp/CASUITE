from django.contrib.auth.models import User
from home.models import Client , Payment, Lead
from django.db.models import Count,Q,Sum


def bottom_screen_card():

    # =========================================================
    # 1. REPORT: LEADERBOARD (Top Solvers)
    # =========================================================
    # Count completed assignment steps per user (Collaborative Score)

    top_solvers = User.objects.filter(is_active=True).annotate(
            solved_count=Count('taskassignmentstatus',
                               filter=Q(taskassignmentstatus__is_completed=True))
        ).order_by('-solved_count')[:5]

    # =========================================================
    # 2. Client Growth - Top 5 Client Creators/Onboards
    # =========================================================
    top_client_creators = (
            Client.objects
            .values("created_by__id", "created_by__username", "created_by__employee__profile_pic")
            .annotate(client_count=Count('id'))
            .order_by('-client_count')[:5]
        )
    
    # =========================================================
    # 3. Lead Performance - Top 5 Lead Generators
    # =========================================================
    top_lead_generators = (
            Lead.objects
            .values("created_by__id", "created_by__username", "created_by__employee__profile_pic")
            .annotate(lead_count=Count('id'))
            .order_by('-lead_count')[:5]
        )
    # =========================================================
    # 4. Top Collection Leaders
    # =========================================================
    top_collectors = (
            Payment.objects
            .filter(payment_status="PAID")
            .values("created_by__id", "created_by__username", "created_by__employee__profile_pic")
            .annotate(total_collection=Sum("amount"))
            .order_by("-total_collection")[:5]
        )
    
     # =========================================================
    # Top Performer Carousel
    # =========================================================
    top_performers = []

    solver = top_solvers.first()
    if solver:
        pic = None
        if hasattr(solver, "employee") and solver.employee.profile_pic:
            pic = solver.employee.profile_pic.url

        top_performers.append({
            "name": solver.first_name or solver.username,
            "title": "Top Solver",
            "value": f"{solver.solved_count} Tasks Solved",
            "avatar": solver.first_name[:1].upper(),
            "photo": pic
        })


    creator = top_client_creators.first()
    if creator:
        pic = None
        if hasattr(creator, "employee") and creator.employee.profile_pic:
            pic = creator.employee.profile_pic.url

        # top_performers.append({
        #     "name": creator,
        #     "title": "Top Client Onboarder",
        #     "value": f"{creator} Clients",
        #     "avatar": creator.first_name[:1].upper(),
        #     "photo": pic
        # })
        top_performers = []
    lead = top_lead_generators.first()
    if lead:
        pic = None
        if hasattr(lead, "employee") and lead.employee.profile_pic:
            pic = lead.employee.profile_pic.url

        # top_performers.append({
        #     "name": lead.created_byfirst_name or lead.username,
        #     "title": "Top Lead Generator",
        #     "value": f"{lead.lead_count} Leads",
        #     "avatar": lead.first_name[:1].upper(),
        #     "photo": pic
        # })

    collector = top_collectors.first()
    if collector and collector.get("created_by__username"):

        photo = None
        if collector.get("created_by__employee__profile_pic"):
            photo = "/media/" + str(collector["created_by__employee__profile_pic"])

        top_performers.append({
            "name": collector["created_by__username"],
            "title": "Top Collection",
            "value": f"₹{collector.get('total_collection', 0)}",
            "avatar": collector["created_by__username"][0].upper(),
            "photo": photo
        })
    else:
        top_performers.append({
            "name": "No Collections Yet",
            "title": "Top Collection",
            "value": "₹0",
            "avatar": "-",
            "photo": None
        })
    context = {
            'top_solvers': top_solvers,
            
            'top_client_creators': top_client_creators,
            'top_lead_generators': top_lead_generators,
            
             #clients
            'top_performers': top_performers,
            'top_collectors': top_collectors,
        }
    return context