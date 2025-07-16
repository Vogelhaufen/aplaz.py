# Auto-scraped Python code
from django.core.management.base import BaseCommand
from tranio.main.models import Advert
from tranio.main.helpers import ExcelLikeCSV
from tranio.shortcuts import generate_new_file, DOMAIN_BY_LANG


class AdvertsWithManagersToXLS(ExcelLikeCSV):
    settings = [
        ("url", 40, lambda ad: f"https://tranio.ru{ad.link}"),
        ("Локация", 20, lambda ad: ad.place.name if ad.place else ""),
        ("Название ЖК", 25, lambda ad: ad.complex_name or ""),
        ("Цена (от)", 15, lambda ad: ad.price_euro or ""),
        ("Дата создания", 20, lambda ad: ad.created_at.strftime('%Y-%m-%d %H:%M') if ad.created_at else ""),
        ("Дата обновления", 20, lambda ad: ad.changed_at.strftime('%Y-%m-%d %H:%M') if ad.changed_at else ""),
        ("Партнёр", 25, lambda ad: ad.partner.name if ad.partner else ""),
        ("Менеджер", 30,
         lambda ad: f"{ad.deserve_manager.get_full_name()} <{ad.deserve_manager.email}>" if ad.deserve_manager else ""),
    ]


def generate_adverts_with_managers_xlsx() -> str:
    filename, filepath = generate_new_file('adverts_with_managers.xlsx', 'private')
    adverts = Advert.objects.filter(deserve_manager__isnull=False)
    AdvertsWithManagersToXLS().to_file(filepath, adverts)
    return filepath


if __name__ == "__main__":
    filepath = generate_adverts_with_managers_xlsx()
    print(f'Файл выгрузки: {filepath}')
