import dash
from dash import dcc
from dash import html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px

# Caricamento dati di esempio
df = px.data.gapminder()  # Dataset integrato in Plotly

# Inizializzazione dell'app Dash con Bootstrap
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

# Layout della dashboard
app.layout = dbc.Container([
    html.H1("Dashboard Interattiva con Dash e Plotly", className="text-center mt-4"),
    
    dbc.Row([
        dbc.Col([
            html.Label("Seleziona un continente:"),
            dcc.Dropdown(
                id="continent-dropdown",
                options=[{"label": c, "value": c} for c in df["continent"].unique()],
                value="Europe",
                clearable=False,
                style={"width": "100%"}
            )
        ], width=4)
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            dcc.Graph(id="scatter-plot")
        ])
    ])
], fluid=True)

# Callback per aggiornare il grafico
@app.callback(
    Output("scatter-plot", "figure"),
    Input("continent-dropdown", "value")
)
def update_graph(selected_continent):
    filtered_df = df[df["continent"] == selected_continent]
    fig = px.scatter(
        filtered_df, x="gdpPercap", y="lifeExp", size="pop", color="country",
        title=f"Relazione tra PIL pro capite e Aspettativa di Vita ({selected_continent})",
        log_x=True, size_max=50
    )
    return fig

# Avviare l'app
if __name__ == "__main__":
    app.run(debug=True)
