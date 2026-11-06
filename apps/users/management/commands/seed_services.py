from django.core.management.base import BaseCommand

from apps.claims.models import Claim, Service


class Command(BaseCommand):
    help = (
        "Crée un service par catégorie, puis rattache les réclamations "
        "existantes sans service à celui de leur catégorie."
    )

    def handle(self, *args, **options):
        created = 0
        for code, label in Claim.CATEGORY_CHOICES:
            _, was_created = Service.objects.get_or_create(
                name=label,
                defaults={'category': code, 'is_active': True},
            )
            created += int(was_created)

        linked = 0
        for service in Service.objects.filter(is_active=True).exclude(category=''):
            linked += Claim.objects.filter(
                service__isnull=True, category=service.category
            ).update(service=service)

        self.stdout.write(self.style.SUCCESS(
            f'{created} service(s) créé(s), {linked} réclamation(s) rattachée(s).'
        ))