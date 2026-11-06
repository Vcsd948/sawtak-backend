import os
import sys
import django

# Ajouter le chemin du projet
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.users.models import Role
from apps.claims.models import Category, Service


def init_roles():
    """Créer les rôles par défaut"""
    roles = [
        {'name': 'Citoyen', 'code': 'citoyen'},
        {'name': 'Agent', 'code': 'agent'},
        {'name': 'Responsable', 'code': 'responsable'},
        {'name': 'Administrateur', 'code': 'administrateur'},
    ]
    for role_data in roles:
        _, created = Role.objects.get_or_create(  # 👈 '_' au lieu de 'role'
            code=role_data['code'],
            defaults={'name': role_data['name']}
        )
        if created:
            print(f"✅ Rôle '{role_data['name']}' créé")
        else:
            print(f"ℹ️ Rôle '{role_data['name']}' existe déjà")


def init_categories():
    """Créer les catégories par défaut"""
    categories = [
        {'name': 'Voirie', 'code': 'voirie', 'color': '#2196F3'},
        {'name': 'Électricité', 'code': 'electricite', 'color': '#FF9800'},
        {'name': 'Eau', 'code': 'eau', 'color': '#2196F3'},
        {'name': 'Assainissement', 'code': 'assainissement', 'color': '#009688'},
        {'name': 'Gestion des déchets', 'code': 'dechets', 'color': '#4CAF50'},
        {'name': 'Éclairage public', 'code': 'eclairage', 'color': '#FFC107'},
        {'name': 'Espaces verts', 'code': 'espaces_verts', 'color': '#8BC34A'},
        {'name': 'Bâtiments municipaux', 'code': 'batiments', 'color': '#795548'},
        {'name': 'Transport et mobilité', 'code': 'transport', 'color': '#9C27B0'},
        {'name': 'Urbanisme', 'code': 'urbanisme', 'color': '#607D8B'},
        {'name': 'Sécurité', 'code': 'securite', 'color': '#F44336'},
        {'name': 'Santé publique', 'code': 'sante', 'color': '#E91E63'},
        {'name': 'Éducation', 'code': 'education', 'color': '#3F51B5'},
        {'name': 'Autres', 'code': 'autres', 'color': '#9E9E9E'},
    ]
    for cat_data in categories:
        _, created = Category.objects.get_or_create(  # 👈 '_' au lieu de 'category'
            code=cat_data['code'],
            defaults={'name': cat_data['name'], 'color': cat_data['color']}
        )
        if created:
            print(f"✅ Catégorie '{cat_data['name']}' créée")
        else:
            print(f"ℹ️ Catégorie '{cat_data['name']}' existe déjà")


def init_services():
    """Créer les services par défaut"""
    services = [
        {'name': 'Service Voirie', 'code': 'service_voirie'},
        {'name': 'Service Électricité', 'code': 'service_electricite'},
        {'name': 'Service Eau et Assainissement', 'code': 'service_eau'},
        {'name': 'Service Assainissement', 'code': 'service_assainissement'},
        {'name': 'Service Gestion des déchets', 'code': 'service_dechets'},
        {'name': 'Service Éclairage public', 'code': 'service_eclairage'},
        {'name': 'Service Espaces verts', 'code': 'service_espaces_verts'},
        {'name': 'Service Bâtiments municipaux', 'code': 'service_batiments'},
        {'name': 'Service Transport', 'code': 'service_transport'},
        {'name': 'Service Urbanisme', 'code': 'service_urbanisme'},
        {'name': 'Service Sécurité', 'code': 'service_securite'},
        {'name': 'Service Santé publique', 'code': 'service_sante'},
        {'name': 'Service Éducation', 'code': 'service_education'},
        {'name': 'Service Autres', 'code': 'service_autres'},
    ]
    for serv_data in services:
        _, created = Service.objects.get_or_create(  # 👈 '_' au lieu de 'service'
            code=serv_data['code'],
            defaults={'name': serv_data['name']}
        )
        if created:
            print(f"✅ Service '{serv_data['name']}' créé")
        else:
            print(f"ℹ️ Service '{serv_data['name']}' existe déjà")


def main():
    print("🚀 Initialisation des données de base...")
    init_roles()
    init_categories()
    init_services()
    print("✅ Initialisation terminée !")


if __name__ == "__main__":
    main()