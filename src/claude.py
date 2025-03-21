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

# Inizializza l'app Dash
app = dash.Dash(__name__)

# Directory per i diversi tipi di dati
ADMIN_LAYERS_DIR = "./data/admin_layers/"
CLIMATE_PRECIPITATIONS_DIR = "./data/climate_precipitations/"
POPULATION_DENSITY_DIR = "./data/population_density/"
GROSS_PRIMARY_PRODUCTION_DIR = "./data/gross_primary_production/"
LAND_COVER_DIR = "./data/land_cover/"
STREAMS_ROADS_DIR = "./data/streams_roads/"

# Mappa per accedere facilmente alle directory in base al tipo
DATA_DIRS = {
    "admin_layers": ADMIN_LAYERS_DIR,
    "climate_precipitations": CLIMATE_PRECIPITATIONS_DIR,
    "population_density": POPULATION_DENSITY_DIR,
    "gross_primary_production": GROSS_PRIMARY_PRODUCTION_DIR,
    "land_cover": LAND_COVER_DIR,
    "streams_roads": STREAMS_ROADS_DIR
}

# =========================================================================
# CONFIGURAZIONE MANUALE DEGLI ANNI PER OGNI TIPO DI MAPPA
# =========================================================================
# Qui dovrai impostare manualmente gli anni disponibili per ogni tipo di mappa
# Esempio:
AVAILABLE_YEARS_BY_TYPE = {
    "admin_layers": [2015, 2018, 2020, 2022],
    "climate_precipitations": [2000, 2005, 2010, 2015, 2020, 2021, 2022, 2023],
    "population_density": [2010, 2015, 2020, 2022],
    "gross_primary_production": [2018, 2019, 2020, 2021, 2022, 2023],
    "land_cover": [2010, 2015, 2020],
    "streams_roads": [2015, 2020, 2022]
}
# Aggiungi o modifica questa struttura in base ai tuoi dati effettivi
# =========================================================================

# Funzione per caricare i file disponibili da una directory specifica
def load_available_files(data_type):
    data_dir = DATA_DIRS.get(data_type, "./data/")
    
    # Cerca file shp
    shp_files = glob.glob(os.path.join(data_dir, "**/*.shp"), recursive=True)
    # Cerca file tif
    tif_files = glob.glob(os.path.join(data_dir, "**/*.tif"), recursive=True)
    
    return shp_files, tif_files

# Crea opzioni per i menu a tendina basati sui tipi di dati specificati
map_types = [
    {"label": "Admin Layers", "value": "admin_layers"},
    {"label": "Climate Precipitations", "value": "climate_precipitations"},
    {"label": "Population Density", "value": "population_density"},
    {"label": "Gross Primary Production", "value": "gross_primary_production"},
    {"label": "Land Cover", "value": "land_cover"},
    {"label": "Streams and Roads", "value": "streams_roads"}
]

# Funzione per ottenere gli anni disponibili per un tipo di mappa
def get_years_for_map_type(map_type):
    return AVAILABLE_YEARS_BY_TYPE.get(map_type, [2023])  # Default a 2023 se non trovato

# Ottieni gli anni per il tipo di mappa predefinito
default_map_type = map_types[0]['value']
default_years = get_years_for_map_type(default_map_type)
default_year = default_years[-1] if default_years else 2023  # Usa l'anno più recente come default

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
                options=[{"label": str(year), "value": year} for year in default_years],
                value=default_year,
                clearable=False
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
     Output('year-dropdown', 'value')],
    [Input('map-type-dropdown', 'value')]
)
def update_year_options(map_type):
    years = get_years_for_map_type(map_type)
    options = [{"label": str(year), "value": year} for year in years]
    # Seleziona l'anno più recente come default
    default_year = years[-1] if years else 2023
    return options, default_year

# Mappa per determinare il tipo di visualizzazione (shapefile o geotiff) in base al tipo di dato
data_type_mapping = {
    "admin_layers": {"type": "shapefile", "colorscale": None},
    "streams_roads": {"type": "shapefile", "colorscale": None},
    "climate_precipitations": {"type": "geotiff", "colorscale": "Blues"},
    "population_density": {"type": "geotiff", "colorscale": "Reds"},
    "gross_primary_production": {"type": "geotiff", "colorscale": "Greens"},
    "land_cover": {"type": "geotiff", "colorscale": "Earth"}
}

# Funzione per caricare e preparare i dati in base al tipo selezionato
def load_data(map_type, year):
    data_info = data_type_mapping.get(map_type)
    
    if not data_info:
        return None, "Tipo di dato non supportato"
    
    # Carica i file disponibili per il tipo di dato specifico
    shp_files, tif_files = load_available_files(map_type)
    
    if data_info["type"] == "shapefile":
        return load_shapefile(map_type, year, shp_files)
    else:  # geotiff
        return load_geotiff(map_type, year, tif_files)

# Funzione per caricare uno shapefile
def load_shapefile(map_type, year, shp_files):
    # Cerca tra i file disponibili
    for shp_file in shp_files:
        filename = os.path.basename(shp_file).lower()
        if str(year) in filename:
            try:
                return gpd.read_file(shp_file), None
            except Exception as e:
                return None, f"Errore nel caricamento del file {filename}: {str(e)}"
    
    # Se non troviamo file reali, creiamo dati simulati
    if map_type == "admin_layers":
        # Crea un semplice GeoDataFrame con i confini della Mauritania e regioni amministrative
        from shapely.geometry import Polygon
        
        # Regioni amministrative simulate
        regions = [
            {'name': 'Trarza', 'admin_level': 1, 'geometry': Polygon([(-17, 16), (-17, 18), (-15, 18), (-15, 16)])},
            {'name': 'Brakna', 'admin_level': 1, 'geometry': Polygon([(-15, 16), (-15, 18), (-13, 18), (-13, 16)])},
            {'name': 'Adrar', 'admin_level': 1, 'geometry': Polygon([(-14, 18), (-14, 21), (-12, 21), (-12, 18)])},
            {'name': 'Inchiri', 'admin_level': 1, 'geometry': Polygon([(-16, 18), (-16, 20), (-14, 20), (-14, 18)])},
            {'name': 'Tiris Zemmour', 'admin_level': 1, 'geometry': Polygon([(-12, 21), (-12, 26), (-8, 26), (-8, 21)])}
        ]
        
        gdf = gpd.GeoDataFrame(regions, crs="EPSG:4326")
        gdf['year'] = year
        return gdf, None
        
    elif map_type == "streams_roads":
        # Crea linee simulate per fiumi e strade
        from shapely.geometry import LineString
        
        # Linee per rappresentare fiumi e strade
        lines = [
            {'name': 'Main Highway', 'type': 'road', 'geometry': LineString([(-17, 18), (-12, 18), (-8, 20)])},
            {'name': 'North Road', 'type': 'road', 'geometry': LineString([(-15, 20), (-15, 24), (-10, 24)])},
            {'name': 'South Road', 'type': 'road', 'geometry': LineString([(-16, 16), (-12, 16), (-10, 18)])},
            {'name': 'River 1', 'type': 'stream', 'geometry': LineString([(-14, 26), (-14, 22), (-12, 20), (-10, 18)])},
            {'name': 'River 2', 'type': 'stream', 'geometry': LineString([(-10, 26), (-10, 22), (-12, 18), (-14, 16)])}
        ]
        
        gdf = gpd.GeoDataFrame(lines, crs="EPSG:4326")
        gdf['year'] = year
        return gdf, None
    
    return None, f"Nessun file shapefile trovato per {map_type} dell'anno {year}"

# Funzione per caricare un GeoTIFF
def load_geotiff(map_type, year, tif_files):
    # Cerca tra i file disponibili
    for tif_file in tif_files:
        filename = os.path.basename(tif_file).lower()
        if str(year) in filename:
            try:
                with rasterio.open(tif_file) as src:
                    raster_data = src.read(1)  # Leggi il primo canale
                    return {
                        'data': raster_data,
                        'bounds': src.bounds,
                        'crs': src.crs,
                        'transform': src.transform,
                        'filename': os.path.basename(tif_file)
                    }, None
            except Exception as e:
                return None, f"Errore nel caricamento del file {filename}: {str(e)}"
    
    # Se non troviamo file reali, creiamo dati simulati
    width, height = 100, 100
    data = None
    
    if map_type == "climate_precipitations":
        # Dati di precipitazioni simulati
        data = np.random.gamma(2, 10, (height, width))
        # Aggiungi un pattern geografico
        x, y = np.meshgrid(np.linspace(-17, -8, width), np.linspace(16, 26, height))
        data = data * np.exp(-((x+12)**2 + (y-21)**2) / 50)
        title = f"Precipitazioni {year} (mm)"
        units = "mm"
        
    elif map_type == "population_density":
        # Dati di densità di popolazione simulati
        data = np.zeros((height, width))
        # Aggiungi alcuni centri urbani
        centers = [
            (width//3, height//3, 100),  # (x, y, popolazione massima)
            (2*width//3, height//3, 50),
            (width//2, 2*height//3, 80)
        ]
        for x, y, pop in centers:
            for i in range(height):
                for j in range(width):
                    dist = np.sqrt((i - y)**2 + (j - x)**2)
                    if dist < 15:
                        data[i, j] += pop * np.exp(-dist/8)
        title = f"Densità di popolazione {year} (persone/km²)"
        units = "persone/km²"
        
    elif map_type == "gross_primary_production":
        # Dati di produzione primaria lorda simulati
        data = np.random.normal(5, 2, (height, width))
        # Aggiungi un pattern geografico
        x, y = np.meshgrid(np.linspace(-17, -8, width), np.linspace(16, 26, height))
        data = data * (1 - np.exp(-((x+12)**2 + (y-21)**2) / 200))
        data = np.clip(data, 0, None)  # Non può essere negativo
        title = f"Produzione primaria lorda {year} (gC/m²/giorno)"
        units = "gC/m²/giorno"
        
    elif map_type == "land_cover":
        # Dati di copertura del suolo simulati (valori categorici)
        data = np.zeros((height, width))
        # Crea diverse aree con diversi tipi di copertura del suolo
        # 1: Foresta, 2: Prateria, 3: Coltivazione, 4: Urbano, 5: Acqua, 6: Desertico
        
        # Principalmente desertico
        data.fill(6)
        
        # Aggiungi alcune aree di prateria
        for _ in range(3):
            x, y = np.random.randint(0, width), np.random.randint(0, height)
            radius = np.random.randint(5, 15)
            for i in range(height):
                for j in range(width):
                    if ((i-y)**2 + (j-x)**2) < radius**2:
                        data[i, j] = 2
        
        # Aggiungi aree di coltivazione vicino ai fiumi
        y = np.linspace(0, height-1, height)
        x = width//2 + width//10 * np.sin(y/10)
        for i in range(height):
            for j in range(width):
                if abs(j - x[i]) < 3:
                    data[i, j] = 5  # Acqua (fiume)
                elif abs(j - x[i]) < 8:
                    data[i, j] = 3  # Coltivazione
        
        # Aggiungi aree urbane
        for _ in range(2):
            x, y = np.random.randint(0, width), np.random.randint(0, height)
            radius = np.random.randint(2, 5)
            for i in range(height):
                for j in range(width):
                    if ((i-y)**2 + (j-x)**2) < radius**2:
                        data[i, j] = 4
        
        title = f"Copertura del suolo {year}"
        units = "categorie"
    
    if data is None:
        return None, f"Nessun dato disponibile per {map_type} dell'anno {year}"
    
    # Definisci i limiti geografici approssimativi della Mauritania
    bounds = (-17.0, 16.0, -8.0, 26.0)  # (minx, miny, maxx, maxy)
    
    return {
        'data': data,
        'bounds': bounds,
        'title': title,
        'units': units,
        'year': year
    }, None

# Callback per aggiornare la mappa
@app.callback(
    [Output('main-map', 'figure'),
     Output('map-info', 'children')],
    [Input('map-type-dropdown', 'value'),
     Input('year-dropdown', 'value')]
)
def update_map(map_type, year):
    data, error = load_data(map_type, year)
    
    if error:
        fig = go.Figure()
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
    
    if data_info["type"] == "shapefile":
        # Visualizza shapefile
        gdf = data
        
        if map_type == "admin_layers":
            fig = px.choropleth_mapbox(
                gdf,
                geojson=gdf.geometry.__geo_interface__,
                locations=gdf.index,
                color='admin_level',
                color_continuous_scale=px.colors.sequential.Viridis,
                mapbox_style="carto-positron",
                zoom=5,
                center={"lat": 20.5, "lon": -12.5},
                opacity=0.7,
                labels={'admin_level': 'Livello amministrativo'}
            )
            fig.update_layout(title=f"Regioni amministrative della Mauritania - {year}")
            
            info = [
                html.P(f"Tipo di dati: Regioni amministrative"),
                html.P(f"Anno: {year}"),
                html.P(f"Numero di regioni: {len(gdf)}")
            ]
            
        elif map_type == "streams_roads":
            # Crea due tracce separate per strade e fiumi
            fig = go.Figure()
            
            # Filtra per tipo
            roads = gdf[gdf['type'] == 'road']
            streams = gdf[gdf['type'] == 'stream']
            
            # Aggiungi strade
            for idx, row in roads.iterrows():
                x, y = row.geometry.xy
                fig.add_trace(go.Scattermapbox(
                    mode='lines',
                    lon=list(x),
                    lat=list(y),
                    line=dict(width=3, color='red'),
                    name=row['name']
                ))
            
            # Aggiungi fiumi
            for idx, row in streams.iterrows():
                x, y = row.geometry.xy
                fig.add_trace(go.Scattermapbox(
                    mode='lines',
                    lon=list(x),
                    lat=list(y),
                    line=dict(width=3, color='blue'),
                    name=row['name']
                ))
            
            fig.update_layout(
                mapbox_style="carto-positron",
                mapbox_zoom=5,
                mapbox_center={"lat": 20.5, "lon": -12.5},
                title=f"Strade e fiumi della Mauritania - {year}"
            )
            
            info = [
                html.P(f"Tipo di dati: Strade e fiumi"),
                html.P(f"Anno: {year}"),
                html.P(f"Numero di strade: {len(roads)}"),
                html.P(f"Numero di fiumi: {len(streams)}")
            ]
        
        else:
            fig = go.Figure()
            fig.update_layout(
                title=f"Tipo di dato non supportato: {map_type}",
                annotations=[dict(
                    text="Tipo di dato non supportato",
                    showarrow=False,
                    xref="paper", yref="paper",
                    x=0.5, y=0.5
                )]
            )
            info = [html.P(f"Tipo di dato non supportato: {map_type}")]
    
    else:
        # Visualizza GeoTIFF
        raster = data
        
        # Ottieni i limiti geografici
        bounds = raster.get('bounds')
        if isinstance(bounds, tuple) and len(bounds) == 4:
            minx, miny, maxx, maxy = bounds
        else:
            minx, miny, maxx, maxy = -17.0, 16.0, -8.0, 26.0  # Default bounds
        
        # Ottieni i dati raster
        raster_data = raster.get('data')
        height, width = raster_data.shape
        
        # Crea matrici per le coordinate
        lons = np.linspace(minx, maxx, width)
        lats = np.linspace(maxy, miny, height)  # Nota: invertito per corrispondere all'ordine dei pixel
        
        # Crea la figura
        fig = go.Figure()
        
        colorscale = data_info["colorscale"]
        
        if map_type == "land_cover":
            # Per la copertura del suolo, usa una scala di colori discreta
            colorscale = [
                [0/6, 'rgb(0,0,0)'],      # 0: Non classificato (nero)
                [1/6, 'rgb(0,100,0)'],    # 1: Foresta (verde scuro)
                [2/6, 'rgb(144,238,144)'],# 2: Prateria (verde chiaro)
                [3/6, 'rgb(255,255,0)'],  # 3: Coltivazione (giallo)
                [4/6, 'rgb(128,128,128)'],# 4: Urbano (grigio)
                [5/6, 'rgb(0,0,255)'],    # 5: Acqua (blu)
                [1.0, 'rgb(255,228,181)'] # 6: Desertico (beige)
            ]
            
            fig.add_trace(go.Heatmap(
                z=raster_data,
                x=lons,
                y=lats,
                colorscale=colorscale,
                colorbar=dict(
                    title=raster.get('units', ''),
                    tickvals=[0.5, 1.5, 2.5, 3.5, 4.5, 5.5],
                    ticktext=['Non class.', 'Foresta', 'Prateria', 'Coltivazione', 'Urbano', 'Acqua', 'Desertico']
                ),
                hoverinfo='none',
                showscale=True
            ))
        else:
            fig.add_trace(go.Heatmap(
                z=raster_data,
                x=lons,
                y=lats,
                colorscale=colorscale,
                colorbar=dict(title=raster.get('units', '')),
                hoverinfo='z',
                showscale=True
            ))
        
        fig.update_layout(
            title=raster.get('title', f"{map_type} - {year}"),
            autosize=True,
            yaxis=dict(
                scaleanchor="x",
                scaleratio=1,
            )
        )
        
        info = [
            html.P(f"Tipo di dati: {map_type.replace('_', ' ').title()}"),
            html.P(f"Anno: {year}"),
            html.P(f"Dimensioni: {raster_data.shape[0]} x {raster_data.shape[1]} pixel"),
            html.P(f"Valore minimo: {raster_data.min():.2f}"),
            html.P(f"Valore massimo: {raster_data.max():.2f}"),
            html.P(f"Valore medio: {raster_data.mean():.2f}")
        ]
    
    # Aggiorna il layout della figura
    fig.update_layout(
        autosize=True,
        margin={"r": 0, "t": 30, "l": 0, "b": 0},
    )
    
    return fig, info

# Esegui l'app
if __name__ == '__main__':
    app.run(debug=True)