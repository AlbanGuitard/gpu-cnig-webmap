WORK IN PROGRESS

# PLU Map Generator

Convert PLU (Plan Local d'Urbanisme) data from GPU (Géoportail de l'Urbanisme) zip archives into ArcGIS Online webmaps with CNIG DDU compliant symbology.

## Description

This tool automates the process of converting PLU data exported from the French Géoportail de l'Urbanisme (GPU) into webmaps on ArcGIS Online while maintaining the official CNIG DDU (Conseil National de l'Information Géographique - Dématérialisation des Documents d'Urbanisme) symbology standards.

## Requirements

The project requires Python 3.11 and the following main dependencies:

- ArcGIS Python API 2.3.1
- Pandas 2.0.2
- NumPy 1.26.4
- GeomeT 1.0.0
- Pillow 11.3.0

Full dependencies are listed in:
- [requirements.txt](requirements.txt)
- [environment.yml](environment.yml)

## Installation

1. Create a conda environment using the provided environment file:
```shell
conda env create -f environment.yml
```

2. Activate the environment:
```shell
conda activate envArcgis
```

## Usage

Place your GPU PLU zip archive in the Data folder and run the main script:

```shell
python Main.py .\Path\to\GPUarchive.zip --link "https://YourOrganizationURL.maps.arcgis.com" --folder AGOL_folder_name --username your_AGOL_username --password your_AGOL_username
```


## Symbology

The project includes predefined symbology files in the Symbology folder:
- DrawInfo_LIN.txt - Linear features symbology
- DrawInfo_PCT.txt - Point features symbology 
- DrawInfo_SURF.txt - Surface/Polygon features symbology
- DrawInfo_ZU.txt - Urban zones symbology

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Status

⚠️ WORK IN PROGRESS

## Author

Alban Guitard (2025)# gpu-cnig-webmap

WORK IN PROGRESS

