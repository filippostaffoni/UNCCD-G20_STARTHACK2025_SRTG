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

import dash
import dash_bootstrap_components as dbc

# Inizializza l'app con un tema Bootstrap
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])


# Inizializza l'app Dash
# app = dash.Dash(__name__)

# Directory per i diversi tipi di dati
ADMIN_LAYERS_DIR = "./Datasets_Hackathon/Admin_layers/"
CLIMATE_PRECIPITATIONS_DIR = "./Datasets_Hackathon/Climate_Precipitation_Data/"
POPULATION_DENSITY_DIR = "./Datasets_Hackathon/Gridded_Population_Density_Data/"
GROSS_PRIMARY_PRODUCTION_DIR = "./Datasets_Hackathon/MODIS_Gross_Primary_Production_GPP/"
LAND_COVER_DIR = "./Datasets_Hackathon/Modis_Land_Cover_Data/"
STREAMS_ROADS_DIR = "./Datasets_Hackathon/Streamwater_Line_Road_Network/"
DEFORESTATION_DIR = "./Datasets_Hackathon/Deforestation/"

# Mappa per accedere facilmente alle directory in base al tipo
DATA_DIRS = {
    "admin_layers": ADMIN_LAYERS_DIR,
    "climate_precipitations": CLIMATE_PRECIPITATIONS_DIR,
    "population_density": POPULATION_DENSITY_DIR,
    "gross_primary_production": GROSS_PRIMARY_PRODUCTION_DIR,
    "land_cover": LAND_COVER_DIR,
    "streams_roads": STREAMS_ROADS_DIR,
    "deforestation": DEFORESTATION_DIR
}

# =========================================================================
# CONFIGURAZIONE DEGLI ANNI PER OGNI TIPO DI MAPPA
# =========================================================================
# Questa sezione verrà riempita automaticamente in base ai file disponibili
AVAILABLE_YEARS_BY_TYPE = {
    "admin_layers": [],
    "climate_precipitations": [2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023],
    "population_density": [2010, 2015, 2020],
    "gross_primary_production": [2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023],
    "land_cover": [2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023],
    "streams_roads": [],
    "deforestation": []
}




def scan_directories_for_years():
    for data_type, directory in DATA_DIRS.items():
        abs_directory = os.path.abspath(directory)
        years = set()
        year_pairs = set()

        #print(f"\n📂 Scansione directory: {abs_directory}")  
        if not os.path.exists(abs_directory):
            #print(f"❌ ERRORE: La directory {abs_directory} non esiste!")
            continue  

        shp_files = glob.glob(os.path.join(abs_directory, "**/*.shp"), recursive=True)
        tif_files = glob.glob(os.path.join(abs_directory, "**/*.tif"), recursive=True)

        #print(f"🔍 File trovati per {data_type}: SHP={shp_files}, TIF={tif_files}")

        # if not shp_files and not tif_files:
            #print(f"⚠ ATTENZIONE: Nessun file trovato in {abs_directory}!")

        all_files = shp_files + tif_files
        for file_path in all_files:
            filename = os.path.basename(file_path)
            #print(f"🟢 Analizzando file: {filename}")  # Debug

            year_pair_match = re.findall(r'(?<!\d)(\d{4})_(\d{4})(?!\d)', filename)
            if year_pair_match:
                start_year, end_year = int(year_pair_match[0][0]), int(year_pair_match[0][1])
                if 1900 <= start_year <= 2030 and 1900 <= end_year <= 2030:
                    year_pairs.add(f"{start_year}_{end_year}")  # Salva la coppia di anni
                continue  # Passa al prossimo file
            # Nuova regex: cerca 4 cifre anche se seguite da lettere o underscore
            year_matches = re.findall(r'(?<!\d)(\d{4})(?!\d)', filename)

            if year_matches:
                for year_str in year_matches:
                    try:
                        year = int(year_str[:4])  # Prende solo le prime 4 cifre
                        if 1900 <= year <= 2030:
                            years.add(year)
                            #print(f"✅ Anno trovato: {year}")  # Debug per conferma
                    except ValueError:
                        continue
            else:
                #print(f"⚠ Il file {filename} NON contiene un anno riconosciuto, ma lo includiamo comunque!")
                years.add("N/A")

        if not years:
            #print(f"⚠ ATTENZIONE: Nessun anno trovato per {data_type}, usiamo 'N/A'")
            years.add("N/A")
        if data_type != "deforestation":
            AVAILABLE_YEARS_BY_TYPE[data_type] = sorted(list(years))
        else:
            AVAILABLE_YEARS_BY_TYPE[data_type] = list(year_pairs)
            
        #print(f"✅ Anni trovati per {data_type}: {AVAILABLE_YEARS_BY_TYPE[data_type]}")


# Esegui la scansione all'avvio dell'applicazione
scan_directories_for_years()


# Mappa per determinare il tipo di visualizzazione (shapefile o geotiff) in base al tipo di dato
data_type_mapping = {
    "admin_layers": {"type": "shapefile", "colorscale": None},
    "streams_roads": {"type": "shapefile", "colorscale": None},
    "climate_precipitations": {"type": "geotiff", "colorscale": "Blues"},
    "population_density": {"type": "geotiff", "colorscale": "Reds"},
    "gross_primary_production": {"type": "geotiff", "colorscale": "Greens"},
    "land_cover": {"type": "geotiff", "colorscale": "Earth"},
    "deforestation": {"type": "geotiff", "colorscale": "Red"}
    
}

# Funzione per caricare i file disponibili da una directory specifica
def load_available_files(data_type, year):
    data_dir = DATA_DIRS.get(data_type)

    if not data_dir:
        return [], []
    
    abs_directory = os.path.abspath(data_dir)

    if not os.path.exists(abs_directory):
        return [], []

    # Cerca tutti i file disponibili
    shp_files = glob.glob(os.path.join(abs_directory, "**/*.shp"), recursive=True)
    tif_files = glob.glob(os.path.join(abs_directory, "**/*.tif"), recursive=True)

    # Se il tipo di dato è "admin_layers" o "streams_roads", non filtriamo per anno
    if data_type in ["admin_layers", "streams_roads"]:
        return shp_files, tif_files  # Restituisci tutti i file trovati

    # Per gli altri tipi di dati, filtra i file che contengono l'anno nel nome
    year_str = str(year)
    shp_files_filtered = [f for f in shp_files if year_str in os.path.basename(f)]
    tif_files_filtered = [f for f in tif_files if year_str in os.path.basename(f)]

    return shp_files_filtered, tif_files_filtered




# Crea opzioni per i menu a tendina basati sui tipi di dati specificati
map_types = [
    {"label": "Admin Layers", "value": "admin_layers"},
    {"label": "Climate Precipitations", "value": "climate_precipitations"},
    {"label": "Population Density", "value": "population_density"},
    {"label": "Gross Primary Production", "value": "gross_primary_production"},
    {"label": "Land Cover", "value": "land_cover"},
    {"label": "Streams and Roads", "value": "streams_roads"},
    {"label": "Deforestation prediction", "value": "deforestation"}
]

# Funzione per ottenere gli anni disponibili per un tipo di mappa
def get_years_for_map_type(map_type):
    years = AVAILABLE_YEARS_BY_TYPE.get(map_type, [])
    ####print(f"📌 Anni disponibili per {map_type}: {years}")  # Debug
    if not years:
        return ["N/A"]  # Se non trova anni, assegna "N/A"
    return sorted(years)  # Assicura che l'anno più recente sia sempre disponibile


# Ottieni gli anni per il tipo di mappa predefinito
default_map_type = map_types[0]['value']
default_years = get_years_for_map_type(default_map_type)
default_year = default_years[-1] if default_years else None  # Usa l'anno più recente come default

# Layout dell'app
app.layout = html.Div([
    html.H1("Dashboard Dati Geografici Mauritania", style={'textAlign': 'center'}),
    
    # Menu a tendina
    html.Div([
        # Menu per tipo di mappa
        html.Div([
            html.Label("Seleziona tipo di dati:"),
            dcc.Dropdown(
                id='map-type-dropdown',
                options=map_types,
                value=default_map_type,
                clearable=False
            ),
        ], style={'width': '48%', 'display': 'inline-block'}),
        
        # Menu per anno
        html.Div([
            html.Label("Seleziona anno:"),
            dcc.Dropdown(
                id='year-dropdown',
                # Le opzioni verranno aggiornate dinamicamente
                options=[{"label": str(year), "value": year} for year in default_years] if default_years else [],
                value=default_year,
                clearable=False,
                disabled=not default_years
            ),
        ], style={'width': '48%', 'display': 'inline-block', 'float': 'right'}),
    ], style={'padding': '20px'}),
    
    # Mappa centrale
    html.Div([
        dcc.Graph(
            id='main-map',
            style={'height': '70vh'}  # 70% dell'altezza della viewport
        )
    ], style={'padding': '10px'}),
    
    # Informazioni sulla mappa
    html.Div([
        html.H4("Informazioni", style={'marginBottom': '10px'}),
        html.Div(id='map-info')
    ], style={'padding': '20px'})
])

# Callback per aggiornare le opzioni dell'anno in base al tipo di mappa selezionato

@app.callback(
    [Output('year-dropdown', 'options'),
     Output('year-dropdown', 'value'),
     Output('year-dropdown', 'disabled')],
    [Input('map-type-dropdown', 'value')]
)
def update_year_options(map_type):
    years = get_years_for_map_type(map_type)
    ###print(f"📌 Anni disponibili nel menu per {map_type}: {years}")  # Debug

    options = [{"label": str(year), "value": year} for year in years]

    if not years or "N/A" in years:
        return options, "N/A", True  # Se non ci sono anni, disabilita il menu

    default_year = max(years)  # Scegli il più alto disponibile
    ###print(f"✅ Anno selezionato automaticamente: {default_year}")  # Debug
    return options, default_year, False



# Funzione per caricare e preparare i dati in base al tipo selezionato
def load_data(map_type, year):
    if year is None:
        return None, f"Nessun dato disponibile per {map_type}"

    data_info = data_type_mapping.get(map_type)
    if not data_info:
        return None, "Tipo di dato non supportato"

    shp_files, tif_files = load_available_files(map_type, year)

    # Se è uno shapefile
    if data_info["type"] == "shapefile" and shp_files:
        return load_shapefile(shp_files[0])  # Carica il primo file trovato

    # Se è un GeoTIFF
    elif data_info["type"] == "geotiff" and tif_files:
        return load_geotiff(tif_files[0])  # Carica il primo file trovato

    return None, f"Nessun file trovato per {map_type} dell'anno {year}"



# Funzione per caricare uno shapefile
def load_shapefile(shp_file):
    try:
        ####print(f"📂 Tentativo di caricare: {shp_file}")  # Debug
        gdf = gpd.read_file(shp_file)
        ####print("✅ Shapefile caricato con successo!")
        ####print(gdf.head())  # Mostra le prime righe
        return gdf, None
    except Exception as e:
        ####print(f"❌ Errore nel caricamento dello shapefile: {shp_file}: {e}")
        return None, f"Errore nel caricamento del file {os.path.basename(shp_file)}: {str(e)}"

# Funzione per caricare un GeoTIFF
def load_geotiff(tif_file):
    try:
        with rasterio.open(tif_file) as src:
            raster_data = src.read(1).astype('float32')  # Leggi il primo canale
            
            if "deforestation" in os.path.basename(tif_file).lower():
                print(f"🔍 Rilevato file di deforestazione: {tif_file}. Escludendo valori 255...")
                raster_data[raster_data == 255] = np.nan 
                raster_data = np.flipud(raster_data)
                # Sostituisci il valore 255 con NaN
            
            # Converti valori nodata a NaN per una migliore visualizzazione
            if src.nodata is not None:
                raster_data = raster_data.astype('float32')
                raster_data[raster_data == src.nodata] = np.nan
                
            return {
                'data': raster_data,
                'bounds': src.bounds,
                'crs': src.crs,
                'transform': src.transform,
                'filename': os.path.basename(tif_file)
            }, None
    except Exception as e:
        return None, f"Errore nel caricamento del file {os.path.basename(tif_file)}: {str(e)}"

# Callback per aggiornare la mappa
@app.callback(
    [Output('main-map', 'figure'),
     Output('map-info', 'children')],
    [Input('map-type-dropdown', 'value'),
     Input('year-dropdown', 'value')]
)
def update_map(map_type, year):
    ###print(f"\n🗺 Chiamata `update_map()` per {map_type}, anno {year}")

    # Inizializziamo `fig` e `info` per evitare errori
    fig = go.Figure()
    info = [html.P("⚠ Nessun dato disponibile.")]

    if year is None:
        ###print("⚠ Nessun anno selezionato, mostrando messaggio di avviso.")
        fig.update_layout(
            mapbox_style="carto-positron",
            mapbox_zoom=5,
            mapbox_center={"lat": 20.5, "lon": -12.5},
            autosize=True,  # Permette alla mappa di adattarsi allo schermo senza distorsioni
            margin={"r": 10, "t": 50, "l": 10, "b": 10},  # Imposta i margini per evitare allungamenti
            height=700,  # Imposta un'altezza fissa per evitare che si distorca
        )

        return fig, html.P(f"Nessun dato disponibile per {map_type}")

    ###print("📡 Tentativo di caricare i dati...")
    data, error = load_data(map_type, year)

    if error:
        ###print(f"❌ ERRORE in `load_data()`: {error}")
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

    ###print("✅ Dati caricati correttamente!")

    data_info = data_type_mapping.get(map_type)

    if not data_info:
        ###print("❌ ERRORE: Tipo di dato non riconosciuto")
        return fig, html.P(f"Errore: tipo di dato non supportato ({map_type})")

    if data_info["type"] == "shapefile":
        gdf = data
        if gdf is None or gdf.empty:
            ###print("❌ ERRORE: Il dataframe `gdf` è vuoto o None!")
            return fig, html.P("Errore: impossibile caricare il file shapefile.")

        ###print(f"📊 DataFrame caricato: {len(gdf)} righe.")

        # Determiniamo la colonna per la colorazione
        color_column = None
        potential_columns = ['admin_level', 'level', 'type', 'class', 'category']
        for col in potential_columns:
            if col in gdf.columns:
                color_column = col
                break

        if color_column is None:
            ###print("⚠ Nessuna colonna valida trovata per la colorazione, usando indice.")
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
            zoom=5,
            center={"lat": 20.5, "lon": -12.5},
            opacity=0.7,
            labels={color_column: color_title}
        )

        ###print("✅ Mappa generata con successo!")

        info = [
            html.P(f"Tipo di dati: {map_type.replace('_', ' ').title()}"),
            html.P(f"Anno: {year}"),
            html.P(f"Numero di elementi: {len(gdf)}"),
            html.P(f"Colonne disponibili: {', '.join(gdf.columns)}")
        ]
    
    elif data_info["type"] == "geotiff":
        raster = data
        if raster is None:
            ###print("❌ ERRORE: `raster` è None!")
            return fig, html.P("Errore: impossibile caricare il file GeoTIFF.")

        ###print("📡 Raster caricato correttamente.")

        # Estrarre dati dal raster
        raster_data = raster.get('data')
        bounds = raster.get('bounds', (-17.0, 16.0, -8.0, 26.0))  # Default in caso di errore
        minx, miny, maxx, maxy = bounds

        height, width = raster_data.shape
        lons = np.linspace(minx, maxx, width)
        lats = np.linspace(maxy, miny, height)

        fig = go.Figure()
        fig.add_trace(go.Heatmap(z=raster_data, x=lons, y=lats, colorscale="Viridis", showscale=True))
        fig.update_layout(
            title=f"{map_type.replace('_', ' ').title()} - {year}",
            autosize=True,
            height=700,  # Altezza fissa per evitare distorsioni
            yaxis=dict(
                scaleanchor="x",  # Mantiene il rapporto di aspetto corretto
                scaleratio=1,  # Assicura che non venga allungata
            ),
            margin={"r": 10, "t": 50, "l": 10, "b": 10}
        )

        ###print("✅ Raster visualizzato con successo!")

        info = [
            html.P(f"Tipo di dati: {map_type.replace('_', ' ').title()}"),
            html.P(f"Anno: {year}"),
            html.P(f"Dimensioni raster: {raster_data.shape}"),
            html.P(f"Valore minimo: {np.nanmin(raster_data):.2f}"),
            html.P(f"Valore massimo: {np.nanmax(raster_data):.2f}"),
            html.P(f"Valore medio: {np.nanmean(raster_data):.2f}")
        ]

    ###print("✅ `update_map()` completata!")
    return fig, info


# Esegui l'app
if __name__ == '__main__':
    app.run(debug=True)