#!/usr/bin/env python3
import os
import glob
import math
import argparse
import geopandas as gpd
import matplotlib.pyplot as plt

def main():
    # Imposta gli argomenti della riga di comando:
    # - directory: cartella contenente i file .shp
    parser = argparse.ArgumentParser(description="Visualizza tutti i file shapefile presenti in una cartella")
    parser.add_argument("directory", type=str, help="Percorso alla cartella contenente i file .shp")
    args = parser.parse_args()

    # Ricerca tutti i file .shp nella directory specificata
    shapefiles = glob.glob(os.path.join(args.directory, "*.shp"))
    if not shapefiles:
        print("Nessun file .shp trovato nella directory specificata.")
        return

    # Determina la dimensione della griglia per i grafici in base al numero di shapefile trovati
    n = len(shapefiles)
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)

    # Crea la figura e gli assi
    fig, axes = plt.subplots(rows, cols, figsize=(15, 15))
    # Assicuriamoci di avere una lista di assi anche se c'è un solo grafico
    if n == 1:
        axes = [axes]
    else:
        axes = axes.flatten()

    # Itera su ogni file shapefile e crea il grafico corrispondente
    for i, shp_file in enumerate(shapefiles):
        try:
            gdf = gpd.read_file(shp_file)
        except Exception as e:
            print(f"Errore nella lettura del file {shp_file}: {e}")
            continue
        ax = axes[i]
        gdf.plot(ax=ax, edgecolor='black')
        ax.set_title(os.path.basename(shp_file))
        ax.set_xlabel("Longitudine")
        ax.set_ylabel("Latitudine")

    # Se ci sono più assi di quanti file siano stati trovati, rimuove quelli inutilizzati
    for j in range(i + 1, len(axes)):
        fig.delaxes(axes[j])
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
