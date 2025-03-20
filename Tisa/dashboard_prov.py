import dash
from dash import dcc, html, Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
import geopandas as gpd
import rasterio
import numpy as np
import os
import glob
import pandas as pd
import re

import dash_bootstrap_components as dbc

import warnings

# Ignora tutti i warning
# warnings.filterwarnings("ignore")

# Inizializza l'app con un tema Bootstrap
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
#app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUX])

# ====================================================
# Directory per i diversi tipi di dati e configurazioni
# ====================================================
ADMIN_LAYERS_DIR = "./Datasets_Hackathon/Admin_layers/"
CLIMATE_PRECIPITATIONS_DIR = "./Datasets_Hackathon/Climate_Precipitation_Data/"
POPULATION_DENSITY_DIR = "./Datasets_Hackathon/Gridded_Population_Density_Data/"
GROSS_PRIMARY_PRODUCTION_DIR = "./Datasets_Hackathon/MODIS_Gross_Primary_Production_GPP/"
LAND_COVER_DIR = "./Datasets_Hackathon/Modis_Land_Cover_Data/"
STREAMS_ROADS_DIR = "./Datasets_Hackathon/Streamwater_Line_Road_Network/"
DEFORESTATION_DIR = "./Datasets_Hackathon/Deforestation/"
CLIMATECHANGE_DIR = "./Datasets_Hackathon/ClimateChange/"

DATA_DIRS = {
    "admin_layers": ADMIN_LAYERS_DIR,
    "climate_precipitations": CLIMATE_PRECIPITATIONS_DIR,
    "population_density": POPULATION_DENSITY_DIR,
    "gross_primary_production": GROSS_PRIMARY_PRODUCTION_DIR,
    "land_cover": LAND_COVER_DIR,
    "streams_roads": STREAMS_ROADS_DIR,
    "deforestation": DEFORESTATION_DIR,
    "climate_change": CLIMATECHANGE_DIR
}

# ====================================================
# Configurazione degli anni per ciascun tipo di mappa
# ====================================================
AVAILABLE_YEARS_BY_TYPE = {
    "admin_layers": [],
    "climate_precipitations": [2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023],
    "population_density": [2010, 2015, 2020],
    "gross_primary_production": [2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023],
    "land_cover": [2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023],
    "streams_roads": [],
    "deforestation": [],
    "climate_change": []
}

def scan_directories_for_years():
    for data_type, directory in DATA_DIRS.items():
        abs_directory = os.path.abspath(directory)
        years = set()
        year_pairs = set()

        if not os.path.exists(abs_directory):
            continue  

        shp_files = glob.glob(os.path.join(abs_directory, "**/*.shp"), recursive=True)
        tif_files = glob.glob(os.path.join(abs_directory, "**/*.tif"), recursive=True)
        all_files = shp_files + tif_files

        for file_path in all_files:
            filename = os.path.basename(file_path)
            year_pair_match = re.findall(r'(?<!\d)(\d{4})_(\d{4})(?!\d)', filename)
            if year_pair_match:
                start_year, end_year = int(year_pair_match[0][0]), int(year_pair_match[0][1])
                if 1900 <= start_year <= 2030 and 1900 <= end_year <= 2030:
                    year_pairs.add(f"{start_year}_{end_year}")
                continue
            year_matches = re.findall(r'(?<!\d)(\d{4})(?!\d)', filename)
            if year_matches:
                for year_str in year_matches:
                    try:
                        year = int(year_str[:4])
                        if 1900 <= year <= 2030:
                            years.add(year)
                    except ValueError:
                        continue
            else:
                years.add("N/A")

        if not years:
            years.add("N/A")
        if data_type not in ["deforestation", "climate_change"]:
            AVAILABLE_YEARS_BY_TYPE[data_type] = sorted(list(years))
        else:
            AVAILABLE_YEARS_BY_TYPE[data_type] = list(year_pairs)

scan_directories_for_years()

# ====================================================
# Mapping dei tipi di dati e delle unità di misura
# ====================================================
data_type_mapping = {
    "admin_layers": {"type": "shapefile", "colorscale": None},
    "streams_roads": {"type": "shapefile", "colorscale": None},
    "climate_precipitations": {"type": "geotiff", "colorscale": "Viridis"},
    "population_density": {"type": "geotiff", "colorscale": "Viridis"},
    "gross_primary_production": {"type": "geotiff", "colorscale": "Viridis"},
    "land_cover": {"type": "geotiff", "colorscale": "Viridis"},
    "deforestation": {"type": "geotiff", "colorscale": "Viridis"},
    "climate_change": {"type": "geotiff", "colorscale": "Viridis"}
}

units_mapping = {
    "climate_precipitations": "mm/yr",
    "population_density": "pers/km²",
    "gross_primary_production": "Kg_C/m²/yr",
    "land_cover": "",
    "deforestation": ""
}

def load_available_files(data_type, year):
    data_dir = DATA_DIRS.get(data_type)
    if not data_dir:
        return [], []
    abs_directory = os.path.abspath(data_dir)
    if not os.path.exists(abs_directory):
        return [], []
    shp_files = glob.glob(os.path.join(abs_directory, "**/*.shp"), recursive=True)
    tif_files = glob.glob(os.path.join(abs_directory, "**/*.tif"), recursive=True)
    if data_type in ["admin_layers", "streams_roads"]:
        return shp_files, tif_files
    year_str = str(year)
    shp_files_filtered = [f for f in shp_files if year_str in os.path.basename(f)]
    tif_files_filtered = [f for f in tif_files if year_str in os.path.basename(f)]
    return shp_files_filtered, tif_files_filtered

# ====================================================
# Opzioni per "Select Data Type"
# ====================================================
map_types_storic = [
    {"label": "Admin Layers", "value": "admin_layers"},
    {"label": "Climate Precipitations", "value": "climate_precipitations"},
    {"label": "Population Density", "value": "population_density"},
    {"label": "Gross Primary Production", "value": "gross_primary_production"},
    {"label": "Land Cover", "value": "land_cover"},
    {"label": "Streams and Roads", "value": "streams_roads"}
]
map_types_deforestation = [
    {"label": "Deforestation", "value": "deforestation"},
    {"label": "Climate Changes", "value": "climate_change"}
]

def get_years_for_map_type(map_type):
    years = AVAILABLE_YEARS_BY_TYPE.get(map_type, [])
    if not years:
        return ["N/A"]
    return sorted(years)

default_map_type = map_types_storic[0]['value']
default_years = get_years_for_map_type(default_map_type)
default_year = default_years[-1] if default_years else None

# ====================================================
# Dizionario per le traduzioni
# ====================================================
translations = {
    "en": {
         "header": "Assaba Climatic Data",
         "data_type_label": "Select Data Type:",
         "year_label": "Select Year:",
         "info_title": "Info",
         "language_label": "Select Language:",
         "dropdown_option_admin_layers": "Admin Layers",
         "dropdown_option_climate_precipitations": "Climate Precipitations",
         "dropdown_option_population_density": "Population Density",
         "dropdown_option_gross_primary_production": "Gross Primary Production",
         "dropdown_option_land_cover": "Land Cover",
         "dropdown_option_streams_roads": "Streams and Roads",
         "dropdown_option_deforestation": "Deforestation",
         "dropdown_option_climate_change": "Climate Changes",
         "storic_data_button": "Historic Data",
         "deforestation_button": "Deforestation",
         "xaxis_title": "Longitude (°)",
         "yaxis_title": "Latitude (°)",
         "no_data_available": "No data available",
         "click_pixel_msg": "Click on a pixel on the map to plot the historic graph",
         "storic_not_available": "Historic graph not available for this data type",
         "error_click_data": "Error in clicked data",
         "historic_trend": "Historic trend of the clicked pixel",
         "year": "Year",
         "value": "Value",
         "current_year": "Current year",
         "no_data_available_for": "No data available for",
         "error": "Error",
         "data_type_not_supported": "Data type not supported",
         "error_loading_shapefile": "Error: impossible to load shapefile.",
         "error_loading_geotiff": "Error: impossible to load GeoTIFF file.",
         "district_id": "District ID",
         "minimum_value": "Minimum value",
         "maximum_value": "Maximum value",
         "average_value": "Average value"
    },
    "fr": {
         "header": "Données Climatiques Assaba",
         "data_type_label": "Sélectionnez le type de données:",
         "year_label": "Sélectionnez l'année:",
         "info_title": "Informations",
         "language_label": "Choisir la langue:",
         "dropdown_option_admin_layers": "Couches Administratives",
         "dropdown_option_climate_precipitations": "Précipitations Climatiques",
         "dropdown_option_population_density": "Densité de Population",
         "dropdown_option_gross_primary_production": "Production Primaire Brute",
         "dropdown_option_land_cover": "Couverture Terrestre",
         "dropdown_option_streams_roads": "Cours d'Eau et Routes",
         "dropdown_option_deforestation": "Déforestation",
         "dropdown_option_climate_change": "Changements Climatiques",
         "storic_data_button": "Données Historiques",
         "deforestation_button": "Déforestation",
         "xaxis_title": "Longitude (°)",
         "yaxis_title": "Latitude (°)",
         "no_data_available": "Aucune donnée disponible",
         "click_pixel_msg": "Cliquez sur un pixel sur la carte pour afficher le graphique historique",
         "storic_not_available": "Graphique historique non disponible pour ce type de données",
         "error_click_data": "Erreur dans les données cliquées",
         "historic_trend": "Tendance historique du pixel cliqué",
         "year": "Année",
         "value": "Valeur",
         "current_year": "Année courante",
         "no_data_available_for": "Aucune donnée disponible pour",
         "error": "Erreur",
         "data_type_not_supported": "Type de données non pris en charge",
         "error_loading_shapefile": "Erreur: impossible de charger le fichier shapefile.",
         "error_loading_geotiff": "Erreur: impossible de charger le fichier GeoTIFF.",
         "district_id": "ID du District",
         "minimum_value": "Valeur minimale",
         "maximum_value": "Valeur maximale",
         "average_value": "Valeur moyenne"
    }
}

# ====================================================
# Layout con Sidebar Fissa e selezione della lingua
# ====================================================
app.layout = html.Div([
    # Sidebar fissa a sinistra
    html.Div(
        [
            html.H2("Menu", className="display-4", style={"color": "black", "textAlign": "center"}),
            html.Hr(),
            dbc.Button("Storic Data", id="storic-data-btn", n_clicks=0, color="secondary",
                       className="mb-2", style={"width": "100%"}),
            dbc.Button("Deforestation", id="deforestation-btn", n_clicks=0, color="secondary",
                       style={"width": "100%"}),
            # Dropdown per la lingua posizionato in basso (spostato più in alto rispetto al precedente)
            html.Div(
                [
                    html.Label("Select Language:", id="language-label", className="fw-bold", style={"marginTop": "20px"}),
                    dcc.Dropdown(
                        id="language-dropdown",
                        options=[
                            {"label": "English", "value": "en"},
                            {"label": "French", "value": "fr"}
                        ],
                        value="en",
                        clearable=False,
                        style={"width": "100%"}
                    )
                ],
                style={"position": "absolute", "bottom": "80px", "left": "20px", "right": "20px"}
            )
        ],
        style={
            "position": "fixed",
            "top": "0",
            "left": "0",
            "bottom": "0",
            "width": "250px",
            "padding": "20px",
            "backgroundColor": "#dcdcdc",
            "overflowY": "auto"
        }
    ),
    # Contenuto principale (offset dalla sidebar)
    html.Div(
        dbc.Container([
            dbc.Row([
                dbc.Col(html.H1(id="header-title", children="Assaba Climatic Data", className="text-center text-primary mb-4"), width=12)
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Label(id="data-type-label", children="Select Data Type:", className="fw-bold"),
                            dcc.Dropdown(
                                id='map-type-dropdown',
                                clearable=False
                            ),
                        ])
                    ], className="shadow-sm p-3"),
                ], width=6),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Label(id="year-label", children="Select Year:", className="fw-bold"),
                            dcc.Dropdown(
                                id='year-dropdown',
                                clearable=False
                            ),
                        ])
                    ], className="shadow-sm p-3"),
                ], width=6),
            ], className="mb-4"),
            # Riga con mappa principale e grafico storico
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            dcc.Graph(id='main-map', style={'height': '100%', 'width': '100%'})
                        ])
                    ], className="shadow-lg p-3"),
                ], width=6),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            dcc.Graph(id='historical-plot', style={'height': '100%', 'width': '100%'})
                        ])
                    ], className="shadow-lg p-3"),
                ], width=6),
            ], className="mb-4"),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4(id="info-title", children="Info", className="text-primary"),
                            html.Div(id='map-info')
                        ])
                    ], className="shadow-sm p-3"),
                ], width=12)
            ])
        ], fluid=True),
        style={
            "marginLeft": "270px",
            "padding": "20px"
        }
    )
])

# ====================================================
# Callback per aggiornare "Select Year" in base al Data Type
# ====================================================
@app.callback(
    [Output('year-dropdown', 'options'),
     Output('year-dropdown', 'value'),
     Output('year-dropdown', 'disabled')],
    [Input('map-type-dropdown', 'value'),
     Input('language-dropdown', 'value')]
)
def update_year_options(map_type, language):
    years = get_years_for_map_type(map_type)
    options = [{"label": str(year), "value": year} for year in years]
    if not years or "N/A" in years:
        return options, "N/A", True
    default_year = max(years)
    return options, default_year, False

# ====================================================
# Callback per aggiornare il "Select Data Type" in base al pulsante premuto
# ====================================================
@app.callback(
    [Output('map-type-dropdown', 'options'),
     Output('map-type-dropdown', 'value'),
     Output('map-type-dropdown', 'disabled')],
    [Input('storic-data-btn', 'n_clicks'),
     Input('deforestation-btn', 'n_clicks'),
     Input('language-dropdown', 'value')]
)
def update_map_type_options(storic_clicks, deforestation_clicks, language):
    ctx = dash.callback_context
    if not ctx.triggered:
        mode = 'storic_data'
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if button_id == 'deforestation-btn':
            mode = 'deforestation'
        else:
            mode = 'storic_data'
            
    # Traduci le opzioni del menu a tendina in base alla lingua selezionata
    if mode == 'storic_data':
        options = [
            {"label": translations[language]["dropdown_option_admin_layers"], "value": "admin_layers"},
            {"label": translations[language]["dropdown_option_climate_precipitations"], "value": "climate_precipitations"},
            {"label": translations[language]["dropdown_option_population_density"], "value": "population_density"},
            {"label": translations[language]["dropdown_option_gross_primary_production"], "value": "gross_primary_production"},
            {"label": translations[language]["dropdown_option_land_cover"], "value": "land_cover"},
            {"label": translations[language]["dropdown_option_streams_roads"], "value": "streams_roads"}
        ]
        default = options[0]["value"]
        disabled = False
    else:
        options = [
            {"label": translations[language]["dropdown_option_deforestation"], "value": "deforestation"},
            {"label": translations[language]["dropdown_option_climate_change"], "value": "climate_change"}
        ]
        default = "deforestation"
        disabled = False
    return options, default, disabled

# ====================================================
# Funzioni per caricare i dati (shapefile e geotiff)
# ====================================================
def load_data(map_type, year):
    if year is None:
        return None, f"No data available for {map_type}"
    data_info = data_type_mapping.get(map_type)
    if not data_info:
        return None, "Data type not supported"
    shp_files, tif_files = load_available_files(map_type, year)
    if data_info["type"] == "shapefile" and shp_files:
        return load_shapefile(shp_files[0])
    elif data_info["type"] == "geotiff" and tif_files:
        return load_geotiff(tif_files[0])
    return None, f"No file found {map_type} in {year}"

def load_shapefile(shp_file):
    try:
        gdf = gpd.read_file(shp_file)
        return gdf, None
    except Exception as e:
        return None, f"Failed loading {os.path.basename(shp_file)}: {str(e)}"

def load_geotiff(tif_file):
    try:
        with rasterio.open(tif_file) as src:
            raster_data = src.read(1).astype('float32')
            if src.count > 1:
                difference_data = src.read(2).astype('float32')
            else:
                difference_data = np.full(raster_data.shape, np.nan)
            if "deforestation" in os.path.basename(tif_file).lower() or "climatechange" in os.path.basename(tif_file).lower():
                print(f"🔍 Rilevato file di deforestazione: {tif_file}. Escludendo valori 255...")
                raster_data[raster_data == -1] = np.nan 
                raster_data = np.flipud(raster_data)
                difference_data = np.flipud(difference_data)
            if src.nodata is not None:
                raster_data = raster_data.astype('float32')
                raster_data[raster_data == src.nodata] = np.nan
                difference_data[difference_data == src.nodata] = np.nan
            return {
                'data': raster_data,
                'difference': difference_data,
                'bounds': src.bounds,
                'crs': src.crs,
                'transform': src.transform,
                'filename': os.path.basename(tif_file)
            }, None
    except Exception as e:
        return None, f"Errore nel caricamento del file {os.path.basename(tif_file)}: {str(e)}"

# ====================================================
# Callback per aggiornare la mappa e le info
# ====================================================
@app.callback(
    [Output('main-map', 'figure'),
     Output('map-info', 'children')],
    [Input('map-type-dropdown', 'value'),
     Input('year-dropdown', 'value'),
     Input('language-dropdown', 'value')]
)
def update_map(map_type, year, language):
    fig = go.Figure()
    
    if year is None:
        title = f"{translations[language]['no_data_available_for']} {map_type}"
        fig.update_layout(
            title=title,
            xaxis=dict(title=translations[language]["xaxis_title"]),
            yaxis=dict(title=translations[language]["yaxis_title"], scaleanchor="x", scaleratio=1),
            autosize=True,
            height=700,
            margin={"r": 10, "t": 50, "l": 10, "b": 10}
        )
        return fig, html.P(title)
    
    data, error = load_data(map_type, year)
    if error:
        error_message = f"{translations[language]['error']}: {error}"
        fig.update_layout(
            title=error_message,
            annotations=[dict(
                text=error_message,
                showarrow=False,
                xref="paper", yref="paper",
                x=0.5, y=0.5
            )]
        )
        return fig, html.P(error_message)
    
    data_info = data_type_mapping.get(map_type)
    if not data_info:
        error_message = f"{translations[language]['error']}: {translations[language]['data_type_not_supported']} ({map_type})"
        return fig, html.P(error_message)
    
    if data_info["type"] == "shapefile":
        gdf = data
        if gdf is None or gdf.empty:
            return fig, html.P(translations[language]["error_loading_shapefile"])
        color_column = None
        potential_columns = ['admin_level', 'level', 'type', 'class', 'category']
        for col in potential_columns:
            if col in gdf.columns:
                color_column = col
                break
        if color_column is None:
            gdf["index_col"] = gdf.index.astype(str)
            color_column = "index_col"
            color_title = translations[language]["district_id"]
        else:
            color_title = color_column.replace('_', ' ').title()
        fig = px.choropleth_mapbox(
            gdf,
            geojson=gdf.geometry.__geo_interface__,
            locations=gdf.index,
            color=color_column,
            color_continuous_scale=px.colors.sequential.Viridis,
            mapbox_style="carto-positron",
            zoom=6,
            center={"lat": 16.7, "lon": -11.5},
            opacity=0.7,
            labels={color_column: color_title}
        )
        info = []
    
    elif data_info["type"] == "geotiff":
        raster = data
        if raster is None:
            return fig, html.P(translations[language]["error_loading_geotiff"])
        
        raster_data = raster.get('data')
        bounds = raster.get('bounds', (-17.0, 16.0, -8.0, 26.0))
        minx, miny, maxx, maxy = bounds
        height, width = raster_data.shape
        lons = np.linspace(minx, maxx, width)
        lats = np.linspace(maxy, miny, height)
        fig = go.Figure()
        
        # Ottieni il nome tradotto del tipo di mappa
        map_type_display = next((item["label"] for item in [
            {"label": translations[language]["dropdown_option_admin_layers"], "value": "admin_layers"},
            {"label": translations[language]["dropdown_option_climate_precipitations"], "value": "climate_precipitations"},
            {"label": translations[language]["dropdown_option_population_density"], "value": "population_density"},
            {"label": translations[language]["dropdown_option_gross_primary_production"], "value": "gross_primary_production"},
            {"label": translations[language]["dropdown_option_land_cover"], "value": "land_cover"},
            {"label": translations[language]["dropdown_option_streams_roads"], "value": "streams_roads"},
            {"label": translations[language]["dropdown_option_deforestation"], "value": "deforestation"},
            {"label": translations[language]["dropdown_option_climate_change"], "value": "climate_change"}
        ] if item["value"] == map_type), map_type.replace('_', ' ').title())
        
        if map_type == "gross_primary_production":
            bp = [0, 150, 300, 450, 600, 750, 900, 1100, 1500, 4000, 60000]
            normalized_ticks = np.linspace(0, 1, len(bp))
            normalized_data = np.interp(raster_data, bp, normalized_ticks)
            colorbar = dict(
                tickmode="array",
                tickvals=list(normalized_ticks),
                ticktext=[str(v) for v in bp],
                title=units_mapping.get(map_type, "")
            )
            fig.add_trace(go.Heatmap(z=normalized_data, x=lons, y=lats,
                                       colorscale="Viridis", showscale=True,
                                       zmin=0, zmax=1, colorbar=colorbar))
        elif map_type == "deforestation" or map_type == "climate_change":
            raster_data = data["data"]
            diff_data = data["difference"]
            # Nuova scala colori: valori bassi in un colore neutro che sfuma in rosso per valori alti
            # Maschera i valori dove raster_data != 1
                # Inizializziamo la visualizzazione con NaN (punti esclusi)
            visualization_mask = np.full_like(diff_data, np.nan)

            # Dove `raster_data == 1` e `diff < 0`, coloriamo di rosso (0)
            visualization_mask[(raster_data == 1) & (diff_data < 0)] = 0  

            # Dove `raster_data == 1` e `diff > 0`, coloriamo di verde (1)
            visualization_mask[(raster_data == 1) & (diff_data > 0)] = 1  

            # Dove `raster_data == 0`, coloriamo di grigio (0.5) ma mostriamo il valore di `diff` nel tooltip
            visualization_mask[raster_data == 0] = 0.5 
            custom_colorscale = [
                [0.0, "red"],
                [0.5, "lightgray"],
                [1.0, "green"]
            ]
            if map_type == "deforestation":
                hover_text = np.array([
                    [
                        f"{translations[language]['dropdown_option_deforestation']}: {int(raster_data[i, j]) if not np.isnan(raster_data[i, j]) else 'N/A'}<br>"
                        f"CO₂ Diff: {diff_data[i, j]:.2f}" if not np.isnan(diff_data[i, j]) else "N/A"
                        for j in range(width)
                    ] 
                    for i in range(height)
                ])
            else:
                hover_text = np.array([
                    [
                        f"Precipitation anomalies: {int(raster_data[i, j]) if not np.isnan(raster_data[i, j]) else 'N/A'}<br>"
                        f"Prec Diff: {diff_data[i, j]:.2f}" if not np.isnan(diff_data[i, j]) else "N/A"
                        for j in range(width)
                    ] 
                    for i in range(height)
                ])
            fig.add_trace(go.Heatmap(z=visualization_mask, x=lons, y=lats,
                                       colorscale=custom_colorscale, showscale=True,
                                       hoverinfo="text", text=hover_text, zmin=0, zmax=1))
        else:
            fig.add_trace(go.Heatmap(z=raster_data, x=lons, y=lats,
                                       colorscale="Viridis", showscale=True,
                                       colorbar=dict(title=units_mapping.get(map_type, ""))))
        
        fig.update_layout(
            title=f"{map_type_display} - {year}",
            xaxis=dict(title=translations[language]["xaxis_title"]),
            yaxis=dict(title=translations[language]["yaxis_title"], scaleanchor="x", scaleratio=1),
            autosize=True,
            height=700,
            margin={"r": 10, "t": 50, "l": 10, "b": 10}
        )
        # Informazioni tradotte
        info = [
           html.P([
                html.Span(f"{translations[language]['minimum_value']}: {np.nanmin(raster_data):.2f}"),
                html.Span("  |  "),
                html.Span(f"{translations[language]['maximum_value']}: {np.nanmax(raster_data):.2f}"),
                html.Span("  |  "),
                html.Span(f"{translations[language]['average_value']}: {np.nanmean(raster_data):.2f}")
            ])
        ]
    
    return fig, info

# ====================================================
# Callback per aggiornare il grafico storico al click sulla mappa
# ====================================================
@app.callback(
    Output('historical-plot', 'figure'),
    [Input('main-map', 'clickData'),
     Input('map-type-dropdown', 'value'),
     Input('year-dropdown', 'value'),
     Input('language-dropdown', 'value')]
)
def update_historical_plot(clickData, map_type, current_year, language):
    if clickData is None:
        fig = go.Figure()
        fig.update_layout(title=translations[language]["click_pixel_msg"])
        return fig

    data_info = data_type_mapping.get(map_type)
    if data_info is None or data_info["type"] != "geotiff":
        fig = go.Figure()
        fig.update_layout(title=translations[language]["storic_not_available"])
        return fig

    try:
        point = clickData['points'][0]
        lon = point['x']
        lat = point['y']
    except Exception as e:
        fig = go.Figure()
        fig.update_layout(title=translations[language]["error_click_data"])
        return fig

    years = get_years_for_map_type(map_type)
    values = []
    valid_years = []
    for year in years:
        data, error = load_data(map_type, year)
        if error or data is None:
            values.append(np.nan)
            valid_years.append(year)
            continue
        raster = data
        raster_data = raster.get('data')
        transform = raster.get('transform')
        try:
            col, row = ~transform * (lon, lat)
            col = int(round(col))
            row = int(round(row))
            if row < 0 or row >= raster_data.shape[0] or col < 0 or col >= raster_data.shape[1]:
                pixel_value = np.nan
            else:
                pixel_value = raster_data[row, col]
        except Exception as e:
            pixel_value = np.nan
        values.append(pixel_value)
        valid_years.append(year)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=valid_years,
        y=values,
        mode='lines+markers',
        name=translations[language]["value"]
    ))
    if current_year in valid_years:
        index = valid_years.index(current_year)
        fig.add_trace(go.Scatter(
            x=[current_year],
            y=[values[index]],
            mode='markers',
            marker=dict(size=12, color='red'),
            name=translations[language]["current_year"]
        ))
    fig.update_layout(
        title=f"{translations[language]['historic_trend']} ({lon:.2f}, {lat:.2f})",
        xaxis_title=translations[language]["year"],
        yaxis_title=translations[language]["value"],
        height=700,
        margin={"r": 10, "t": 50, "l": 10, "b": 10}
    )
    return fig

# ====================================================
# Callback per aggiornare le scritte in base alla lingua scelta
# ====================================================
@app.callback(
    [Output("header-title", "children"),
     Output("data-type-label", "children"),
     Output("year-label", "children"),
     Output("info-title", "children"),
     Output("language-label", "children")],
    Input("language-dropdown", "value")
)
def update_language(lang):
    return (translations[lang]["header"],
            translations[lang]["data_type_label"],
            translations[lang]["year_label"],
            translations[lang]["info_title"],
            translations[lang]["language_label"])
@app.callback(
    [Output("storic-data-btn", "children"),
     Output("deforestation-btn", "children")],
    Input("language-dropdown", "value")
)
def update_sidebar_buttons(lang):
    return translations[lang]["storic_data_button"], translations[lang]["deforestation_button"]


if __name__ == '__main__':
    app.run(debug=True)
