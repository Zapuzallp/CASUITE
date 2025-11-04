import csv
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from home.models import UserProfile  # Adjust this import based on your actual UserProfile model location


class Command(BaseCommand):
    help = 'Import users and their profiles from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='The CSV file to import')

    def handle(self, *args, **options):
        csv_file = options['csv_file']

        with open(csv_file, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                username = row['username']
                email = row['email']
                first_name = row['first_name']
                last_name = row['last_name']
                password = row['password']

                # Create or update User instance
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': email,
                        'first_name': first_name,
                        'last_name': last_name
                    }
                )
                if created:
                    user.set_password(password)
                    user.save()

                # Prepare UserProfile data
                profile_data = {
                    'department': row['department'],
                    'group': row['group'],
                    'joiningDate': row['joiningDate'],
                    'dob': row['dob'],
                    'fullAddress': row['fullAddress'],
                    'phone': row['phone'],
                    'auth_token': row['auth_token'],
                    # 'userId': row['userId'],
                    # 'superVisorUserName': row['superVisorUserName'],
                    'emp_code': row['emp_code'],
                    'official_contact_no': row['official_contact_no'],
                    # 'official_email': row['official_email'],
                    'personal_email': row['personal_email'],
                    # 'blood_group': row['blood_group'],
                    'father_name': row['father_name'],
                    'mother_name': row['mother_name'],
                    'emergency_contact_no': row['emergency_contact_no'],
                    'aadhar_no': row['aadhar_no'],
                    'pan_no': row['pan_no'],
                    'qualification': row['qualification'],
                    'location_of_joining': row['location_of_joining'],
                }

                # Handle the photo field if provided in the CSV
                photo_path = row.get('photo')
                if photo_path:
                    profile_data['photo'] = photo_path

                # Create or update UserProfile instance
                profile, profile_created = UserProfile.objects.update_or_create(
                    user=user,
                    defaults=profile_data
                )

        self.stdout.write(self.style.SUCCESS('Successfully imported users and profiles'))