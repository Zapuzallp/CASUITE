import re
def generate_file_number(office_location):
    """
    Generates a unique file number based on office location.
    Example: KO000001, KO000002
    """

    from home.models import Client

    # Office code (first 2 letters)
    office_code = office_location.office_name[:2].upper()

    # Get latest client for this office having file_number
    last_client = (
        Client.objects
        .filter(
            office_location=office_location,
            file_number__startswith=office_code
        )
        .order_by('-file_number')
        .first()
    )

    if last_client and last_client.file_number:
        # Extract numeric part
        last_number = int(last_client.file_number.replace(office_code, ''))
        next_number = last_number + 1
    else:
        # First client for this office
        next_number = 1

    return f"{office_code}{str(next_number).zfill(6)}"


GST_REGEX = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'

def is_gst_number(value: str) -> bool:
    return bool(re.match(GST_REGEX, value))
