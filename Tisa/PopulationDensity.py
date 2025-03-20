import os
import glob
import math
import rasterio
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap

def display_all_tifs(folder, boundaries):
    # Trova tutti i file TIFF nella cartella specificata
    tif_files = glob.glob(os.path.join(folder, '*.tif'))
    if not tif_files:
        print("Nessun file .tif trovato nella cartella:", folder)
        return

    # Calcola il layout della griglia
    n_files = len(tif_files)
    n_cols = math.ceil(math.sqrt(n_files))
    n_rows = math.ceil(n_files / n_cols)

    # Crea una colormap discreta con una gamma di colori più ampia
    cmap = plt.get_cmap('plasma', len(boundaries) - 1)
    norm = BoundaryNorm(boundaries, cmap.N)

    # Crea la figura con dimensioni adeguate
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 15))
    if n_files == 1:
        axes = [axes]
    else:
        axes = axes.flatten()

    # Visualizza ogni file TIFF con colorbar discreta
    for ax, tif_file in zip(axes, tif_files):
        with rasterio.open(tif_file) as src:
            img = src.read(1)
            img = np.where(img == src.nodata, np.nan, img)
            cmap = plt.get_cmap('plasma', len(boundaries) - 1)
            cmap.set_bad(color='white')  # Imposta il colore per i valori no data
            norm = BoundaryNorm(boundaries, cmap.N)
            image = ax.imshow(img, cmap=cmap, norm=norm)
            ax.set_title(os.path.basename(tif_file), fontsize=10)
            ax.tick_params(axis='both', which='major', labelsize=8)

            # Aggiungi colorbar discreta
            cbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04, ticks=boundaries)
            cbar.set_label('Popolazione per km²', fontsize=8)
            cbar.ax.tick_params(labelsize=7)

    # Rimuovi i subplot in eccesso
    for ax in axes[len(tif_files):]:
        fig.delaxes(ax)

    plt.tight_layout()
    plt.subplots_adjust(top=0.95, bottom=0.05, left=0.05, right=0.95, hspace=0.5, wspace=0.4)
    plt.show()

if __name__ == '__main__':
    folder_path = 'Datasets_Hackathon/MODIS_Gross_Primary_Production_GPP'
    boundaries = [1000, 2000, 5000, 10000]
    display_all_tifs(folder_path, boundaries)

