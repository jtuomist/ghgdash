from .main_sector_base import MainSectorPage


class BuildingHeatingPage(MainSectorPage):
    id = 'building-heating'
    path = '/rakennusten-lammitys'
    emission_sector = ('BuildingHeating',)
    emission_name = 'Lämmityksen päästöt'
