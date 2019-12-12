import dash_html_components as html
import dash_bootstrap_components as dbc

from pages import get_page_for_emission_sector
from calc.emissions import predict_emissions, SECTORS

from variables import get_variable


def _make_nav_item(sector_name, emissions, indent, page, bold=False, active=False):
    attrs = {}
    if page is None:
        attrs['disabled'] = True
    else:
        attrs['disabled'] = False
        attrs['href'] = page.path
    style = {}
    if indent:
        style = {'marginLeft': '2rem'}
    if bold:
        style = {'fontWeight': 'bold'}

    if active:
        attrs['active'] = True

    item = dbc.ListGroupItem(
        [
            html.Span(sector_name, style=style),
            dbc.Badge("%.0f kt" % emissions, color="light", className="ml-1 float-right")
        ],
        action=True,
        **attrs
    )
    return item


def make_emission_nav(current_page):
    df = predict_emissions()
    target_year = get_variable('target_year')

    df = df[df.Year == df.Year.max()]

    items = []

    current_sector = current_page.emission_sector if current_page and current_page.emission_sector else None

    # Sort sectors based on the target year emissions
    sector_emissions = df.groupby('Sector1').Emissions.sum().sort_values(ascending=False)
    for sector_name, emissions in sector_emissions.iteritems():
        sector_metadata = SECTORS[sector_name]
        sdf = df.loc[df.Sector1 == sector_name]
        page = get_page_for_emission_sector(sector_name, None)

        subsectors = sdf.Sector2.unique()

        if current_sector and sector_name == current_sector[0] and len(subsectors) <= 1:
            active = True
        else:
            active = False

        item = _make_nav_item(sector_metadata['name'], emissions, False, page, active=active)
        items.append(item)

        if len(subsectors) <= 1:
            continue

        sdf = sdf.sort_values('Sector2', ascending=True).set_index('Sector2').Emissions
        for subsector_name, emissions in sdf.iteritems():
            if current_sector and sector_name == current_sector[0] and subsector_name == current_sector[1]:
                active = True
            else:
                active = False

            page = get_page_for_emission_sector(sector_name, subsector_name)
            item = _make_nav_item(
                sector_metadata['subsectors'][subsector_name]['name'], emissions, True, page, active=active
            )
            items.append(item)

    sum_emissions = sector_emissions.sum()
    items.append(_make_nav_item('Yhteensä', sum_emissions, False, None, bold=True))

    return html.Div([
        html.H6('Päästöt vuonna %s' % target_year),
        dbc.ListGroup(children=items)
    ])
