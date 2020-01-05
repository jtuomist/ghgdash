from .main_sector_base import MainSectorPage


class TransportationPage(MainSectorPage):
    id = 'transportation'
    path = '/liikenne'
    emission_sector = ('Transportation',)
    emission_name = 'Liikenteen päästöt'
