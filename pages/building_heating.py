import dash_html_components as html

from calc.emissions import predict_emissions
from .base import Page


class BuildingHeatingPage(Page):
    id = 'building-heating'
    path = '/rakennusten-lammitys'
    emission_sector = 'BuildingHeating'

    def get_content(self):
        df = predict_emissions()
        return html.Div('moi')

    def get_summary_vars(self):
        return dict()
