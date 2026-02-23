def is_mobile(request):
    """
    Simple mobile detection based on user agent
    """
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    mobile_agents = [
        'mobile', 'android', 'iphone', 'ipad', 'ipod', 
        'blackberry', 'windows phone', 'opera mini'
    ]
    return any(agent in user_agent for agent in mobile_agents)