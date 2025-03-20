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

# Directory per i diversi tipi di dati
ADMIN_LAYERS_DIR = "./Datasets_Hackathon/Admin_layers/"
CLIMATE_PRECIPITATIONS_DIR = "./Datasets_Hackathon/Climate_Precipitation_Data/"
POPULATION_DENSITY_DIR = "./Datasets_Hackathon/Gridded_Population_Density_Data/"
GROSS_PRIMARY_PRODUCTION_DIR = "./Datasets_Hackathon/MODIS_Gross_Primary_Production_GPP/"
LAND_COVER_DIR = "./Datasets_Hackathon/Modis_Land_Cover_Data/"
STREAMS_ROADS_DIR = "./Datasets_Hackathon/Streamwater_Line_Road_Network/"
DEFORESTATION_DIR = "./Datasets_Hackathon/Deforestation/"
CLIMATECHANGE_DIR = "./Datasets_Hackathon/ClimateChange/"

# Mappa per accedere facilmente alle directory in base al tipo
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

# =========================================================================
# CONFIGURAZIONE DEGLI ANNI PER OGNI TIPO DI MAPPA
# =========================================================================
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
        if data_type != "deforestation" and data_type != "climate_change":
            AVAILABLE_YEARS_BY_TYPE[data_type] = sorted(list(years))
        else:
            AVAILABLE_YEARS_BY_TYPE[data_type] = list(year_pairs)

scan_directories_for_years()

# Utilizziamo la scala Viridis per tutti i dati tranne per deforestation (che verrà personalizzata)
data_type_mapping = {
    "admin_layers": {"type": "shapefile", "colorscale": None},
    "streams_roads": {"type": "shapefile", "colorscale": None},
    "climate_precipitations": {"type": "geotiff", "colorscale": "Viridis"},
    "population_density": {"type": "geotiff", "colorscale": "Viridis"},
    "gross_primary_production": {"type": "geotiff", "colorscale": "Viridis"},
    "land_cover": {"type": "geotiff", "colorscale": "Viridis"},
    "deforestation": {"type": "geotiff", "colorscale": "Viridis"},  # verrà sovrascritto nella callback
    "climate_change": {"type": "geotiff", "colorscale": "Viridis"}
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

# Opzioni per il menu "Select Data Type"
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

# Layout dell'app
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("Assaba Climatic Data", className="text-center text-primary mb-4"), width=12)
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Label("Select Data Mode:", className="fw-bold"),
                    dcc.Dropdown(
                        id='data-mode-dropdown',
                        options=[
                           {"label": "Storic Data", "value": "storic_data"},
                           {"label": "Deforestation", "value": "deforestation"}
                        ],
                        value="storic_data",
                        clearable=False
                    ),
                ])
            ], className="shadow-sm p-3"),
        ], width=4),

        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Label("Select Data Type:", className="fw-bold"),
                    dcc.Dropdown(
                        id='map-type-dropdown',
                        clearable=False
                    ),
                ])
            ], className="shadow-sm p-3"),
        ], width=4),

        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Label("Select Year:", className="fw-bold"),
                    dcc.Dropdown(
                        id='year-dropdown',
                        clearable=False
                    ),
                ])
            ], className="shadow-sm p-3"),
        ], width=4),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id='main-map', style={'height': '100%', 'width': '100%'})
                ])
            ], className="shadow-lg p-3", style={'max-width': '900px', 'margin': 'auto'}),
        ], width=12)
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Informazioni", className="text-primary"),
                    html.Div(id='map-info')
                ])
            ], className="shadow-sm p-3"),
        ], width=12)
    ])
], fluid=True)

# Callback per aggiornare il menu "Select Year"
@app.callback(
    [Output('year-dropdown', 'options'),
     Output('year-dropdown', 'value'),
     Output('year-dropdown', 'disabled')],
    [Input('map-type-dropdown', 'value')]
)
def update_year_options(map_type):
    years = get_years_for_map_type(map_type)
    options = [{"label": str(year), "value": year} for year in years]
    if not years or "N/A" in years:
        return options, "N/A", True
    default_year = max(years)
    return options, default_year, False

# Callback per aggiornare il menu "Select Data Type" in base alla modalità selezionata
@app.callback(
    [Output('map-type-dropdown', 'options'),
     Output('map-type-dropdown', 'value'),
     Output('map-type-dropdown', 'disabled')],
    [Input('data-mode-dropdown', 'value')]
)
def update_map_type_options(data_mode):
    if data_mode == 'storic_data':
        options = map_types_storic
        default = options[0]["value"]
        disabled = False
        return options, default, disabled
    else:  # data_mode == 'deforestation'
        options = map_types_deforestation
        default = "deforestation"
        disabled = False
        return options, default, disabled

def load_data(map_type, year):
    if year is None:
        return None, f"Nessun dato disponibile per {map_type}"
    data_info = data_type_mapping.get(map_type)
    if not data_info:
        return None, "Tipo di dato non supportato"
    shp_files, tif_files = load_available_files(map_type, year)
    if data_info["type"] == "shapefile" and shp_files:
        return load_shapefile(shp_files[0])
    elif data_info["type"] == "geotiff" and tif_files:
        return load_geotiff(tif_files[0])
    return None, f"Nessun file trovato per {map_type} dell'anno {year}"

def load_shapefile(shp_file):
    try:
        gdf = gpd.read_file(shp_file)
        return gdf, None
    except Exception as e:
        return None, f"Errore nel caricamento del file {os.path.basename(shp_file)}: {str(e)}"

def load_geotiff(tif_file):
    try:
        with rasterio.open(tif_file) as src:
            raster_data = src.read(1).astype('float32')
            if "deforestation" in os.path.basename(tif_file).lower() or "climatechange" in os.path.basename(tif_file).lower():
                difference_data = src.read(2).astype('float32') if src.count > 1 else np.full(raster_data.shape, np.nan)
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

@app.callback(
    [Output('main-map', 'figure'),
     Output('map-info', 'children')],
    [Input('map-type-dropdown', 'value'),
     Input('year-dropdown', 'value')]
)
def update_map(map_type, year):
    fig = go.Figure()
    info = [html.P("⚠ Nessun dato disponibile.")]
    
    if year is None:
        fig.update_layout(
            mapbox_style="carto-positron",
            mapbox_zoom=5,
            mapbox_center={"lat": 20.5, "lon": -12.5},
            autosize=True,
            margin={"r": 10, "t": 50, "l": 10, "b": 10},
            height=700,
        )
        return fig, html.P(f"Nessun dato disponibile per {map_type}")
    
    data, error = load_data(map_type, year)
    if error:
        fig.update_layout(
            title=f"Errore: {error}",
            annotations=[dict(
                text=error,
                showarrow=False,
                xref="paper", yref="paper",
                x=0.5, y=0.5
            )]
        )
        return fig, html.P(f"Errore: {error}")
    
    data_info = data_type_mapping.get(map_type)
    if not data_info:
        return fig, html.P(f"Errore: tipo di dato non supportato ({map_type})")
    
    if data_info["type"] == "shapefile":
        gdf = data
        if gdf is None or gdf.empty:
            return fig, html.P("Errore: impossibile caricare il file shapefile.")
        color_column = None
        potential_columns = ['admin_level', 'level', 'type', 'class', 'category']
        for col in potential_columns:
            if col in gdf.columns:
                color_column = col
                break
        if color_column is None:
            gdf["index_col"] = gdf.index.astype(str)
            color_column = "index_col"
            color_title = "ID Regione"
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
        info = [
            html.P(f"Tipo di dati: {map_type.replace('_', ' ').title()}"),
            html.P(f"Anno: {year}"),
            html.P(f"Numero di elementi: {len(gdf)}"),
            html.P(f"Colonne disponibili: {', '.join(gdf.columns)}")
        ]
    
    elif data_info["type"] == "geotiff":
        raster = data
        if raster is None:
            return fig, html.P("Errore: impossibile caricare il file GeoTIFF.")
        
        raster_data = raster.get('data')
        bounds = raster.get('bounds', (-17.0, 16.0, -8.0, 26.0))
        minx, miny, maxx, maxy = bounds
        height, width = raster_data.shape
        lons = np.linspace(minx, maxx, width)
        lats = np.linspace(maxy, miny, height)
        fig = go.Figure()
        if map_type == "population_density":
            bp = [0, 1, 2, 4, 8, 15, 30, 50, 100, 200, 500, 1000]
            normalized_ticks = np.linspace(0, 1, len(bp))
            normalized_data = np.interp(raster_data, bp, normalized_ticks)
            colorbar = dict(
                tickmode="array",
                tickvals=list(normalized_ticks),
                ticktext=[str(v) for v in bp]
            )
            fig.add_trace(go.Heatmap(z=normalized_data, x=lons, y=lats,
                                       colorscale="Viridis", showscale=True,
                                       zmin=0, zmax=1, colorbar=colorbar))
        elif map_type == "gross_primary_production":
            bp = [0, 150, 300, 450, 600, 750, 900, 1100, 1500, 4000, 60000]
            normalized_ticks = np.linspace(0, 1, len(bp))
            normalized_data = np.interp(raster_data, bp, normalized_ticks)
            colorbar = dict(
                tickmode="array",
                tickvals=list(normalized_ticks),
                ticktext=[str(v) for v in bp]
            )
            fig.add_trace(go.Heatmap(z=normalized_data, x=lons, y=lats,
                                       colorscale="Viridis", showscale=True,
                                       zmin=0, zmax=1, colorbar=colorbar))
        elif map_type == "deforestation" or map_type == "climate_change":
            raster_data = data["data"]
            co2_diff_data = data["difference"]
            # Nuova scala colori: valori bassi in un colore neutro che sfuma in rosso per valori alti
            # Maschera i valori dove raster_data != 1
                # Inizializziamo la visualizzazione con NaN (punti esclusi)
            visualization_mask = np.full_like(co2_diff_data, np.nan)

            # Dove `raster_data == 1` e `diff < 0`, coloriamo di rosso (0)
            visualization_mask[(raster_data == 1) & (co2_diff_data < 0)] = 0  

            # Dove `raster_data == 1` e `diff > 0`, coloriamo di verde (1)
            visualization_mask[(raster_data == 1) & (co2_diff_data > 0)] = 1  

            # Dove `raster_data == 0`, coloriamo di grigio (0.5) ma mostriamo il valore di `diff` nel tooltip
            visualization_mask[raster_data == 0] = 0.5 
            # Definisci la scala colori: grigio per 0, rosso per negativo, verde per positivo
            custom_colorscale = [
                [0.0, "red"],      # Diff < 0 → Rosso
                [0.5, "lightgray"], # Valori neutri per raster_data == 0
                [1.0, "green"]      # Diff > 0 → Verde
            ]
            hover_text = np.array([
                [
                    f"Deforestation: {int(raster_data[i, j]) if not np.isnan(raster_data[i, j]) else 'N/A'}<br>"
                    f"CO₂ Diff: {co2_diff_data[i, j]:.2f}" if not np.isnan(co2_diff_data[i, j]) else "N/A"
                    for j in range(width)
                ] 
                for i in range(height)
            ])
            fig.add_trace(go.Heatmap(z=visualization_mask, x=lons, y=lats,
                                       colorscale=custom_colorscale, showscale=True,
                                       hoverinfo="text", text=hover_text))
        else:
            fig.add_trace(go.Heatmap(z=raster_data, x=lons, y=lats,
                                       colorscale="Viridis", showscale=True))
        fig.update_layout(
            title=f"{map_type.replace('_', ' ').title()} - {year}",
            autosize=True,
            height=700,
            yaxis=dict(
                scaleanchor="x",
                scaleratio=1,
            ),
            margin={"r": 10, "t": 50, "l": 10, "b": 10}
        )
        info = [
            html.P(f"Tipo di dati: {map_type.replace('_', ' ').title()}"),
            html.P(f"Anno: {year}"),
            html.P(f"Dimensioni raster: {raster_data.shape}"),
            html.P(f"Valore minimo: {np.nanmin(raster_data):.2f}"),
            html.P(f"Valore massimo: {np.nanmax(raster_data):.2f}"),
            html.P(f"Valore medio: {np.nanmean(raster_data):.2f}")
        ]
    
    return fig, info

if __name__ == '__main__':
    app.run(debug=True)
