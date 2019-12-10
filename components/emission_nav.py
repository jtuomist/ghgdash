import dash_html_components as html
import dash_bootstrap_components as dbc

from pages import get_page_for_emission_sector
from calc.emissions import generate_emissions_forecast, SECTORS, HEATING_SUBSECTORS


def _make_nav_item(sector_name, emissions, indent, page):
    attrs = {}
    if page is None:
        attrs['disabled'] = True
    else:
        attrs['disabled'] = False
        attrs['href'] = page.path
    style = {}
    if indent:
        style = {'margin-left': '2rem'}
    item = dbc.ListGroupItem(
        [
            html.Span(sector_name, style=style),
            dbc.Badge("%.0f kt" % emissions, color="light", className="ml-1 float-right")
        ],
        active=False,
        action=True,
        **attrs
    )
    return item


def make_emission_nav():
    df = generate_emissions_forecast()

    df = df[df.Year == df.Year.max()]

    items = []
    # Sort sectors based on the target year emissions
    sector_emissions = df.groupby('Sector1').Emissions.sum().sort_values(ascending=False)

    for sector_name, emissions in sector_emissions.iteritems():
        sdf = df.loc[df.Sector1 == sector_name]
        page = get_page_for_emission_sector(sector_name, None)
        item = _make_nav_item(SECTORS[sector_name], emissions, False, page)
        items.append(item)

        subsectors = sdf.Sector2.unique()
        if len(subsectors) <= 1:
            continue

        sdf = sdf.sort_values('Sector2', ascending=True).set_index('Sector2').Emissions
        for subsector_name, emissions in sdf.iteritems():
            page = get_page_for_emission_sector(sector_name, subsector_name)
            item = _make_nav_item(HEATING_SUBSECTORS[subsector_name], emissions, True, page)
            items.append(item)

    return dbc.ListGroup(children=items)
