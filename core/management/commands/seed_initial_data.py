from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import Domain, User, UserRole


class Command(BaseCommand):
    help = "Seed the default admin user and starter domains."

    def handle(self, *args, **options):
        admin, _created = User.objects.get_or_create(
            email=settings.ADMIN_EMAIL.lower(),
            defaults={
                "role": UserRole.ADMIN,
                "is_verified": True,
                "is_staff": True,
            },
        )
        admin.role = UserRole.ADMIN
        admin.is_verified = True
        admin.is_staff = True
        admin.set_password(settings.ADMIN_PASSWORD)
        admin.save()

        for identifier, label in [("us-east", "US East"), ("eu-west", "EU West")]:
            Domain.objects.update_or_create(
                identifier=identifier,
                defaults={"label": label, "is_active": True},
            )

        self.stdout.write(self.style.SUCCESS("Seeded admin user and starter domains."))
