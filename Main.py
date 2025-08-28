# coding: utf-8
import logging
import os
import sys
import zipfile
from arcgis.gis import GIS
from arcgis.mapping import WebMap
from arcgis.features import FeatureLayer
import json
import copy
import getpass
from tqdm import tqdm
import argparse

# Set up logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gpu_script.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

def unzip_gpu(zip_path, extract_path):
    """
    Cette fonction sert a décompresser le GPU
    :param zip_path: chemin vers l'achive .zip du GPU
    :param extract_path: chemin vers le d
    """
    try:
        if not os.path.exists(zip_path):
            raise FileNotFoundError(f"Archive not found: {zip_path}")
            
        if not zip_path.endswith('.zip'):
            raise ValueError(f"Invalid archive format: {zip_path}. Must be .zip")
            
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
            logging.info(f"Successfully extracted {zip_path} to {extract_path}")
            
    except zipfile.BadZipFile:
        logging.error(f"Corrupt or invalid zip file: {zip_path}")
        raise
    except PermissionError:
        logging.error(f"Permission denied accessing {zip_path} or {extract_path}")
        raise
    except Exception as e:
        logging.error(f"Error extracting {zip_path}: {str(e)}")
        raise



def extract_shapefile(folder):
    """
    Find .shp files in the GPU folder (case-insensitive)
    
    Args:
        folder: GPU folder path
    Returns:
        List of paths to shapefiles
    """
    filters = ['prescription', 'zone_urba']  # lowercase filters
    shapefiles = []
    
    # Get total number of files for progress bar
    total_files = sum([len(files) for r, d, files in os.walk(folder)])
    
    with tqdm(total=total_files, desc="Extracting shapefiles") as pbar:
        for root, dirs, files in os.walk(folder):
            for file in files:
                file_lower = file.lower()  # Convert filename to lowercase
                if file_lower.endswith('.shp') and any(f in file_lower for f in filters):
                    shapefiles.append(os.path.join(root, file))
                pbar.update(1)
    return shapefiles


def zip_shapefile(shapefile_paths, zip_shapefile_path):
    """
    Archive selected shapefiles for web app
    
    Args:
        shapefile_paths: Paths to shapefiles
        zip_shapefile_path: Output zip file path
    """
    extensions = ['.zip', '.shx', '.dbf', '.prj','.CPG','.sbn', '.qmd', '.shp']
    
    with zipfile.ZipFile(zip_shapefile_path, 'w') as zipf:
        with tqdm(total=len(shapefile_paths)*len(extensions), desc="Zipping files") as pbar:
            for shapefile_path in shapefile_paths:
                base = os.path.splitext(shapefile_path)[0]
                for ext in extensions:
                    file_path = base + ext
                    if os.path.exists(file_path):
                        zipf.write(file_path, os.path.basename(file_path))
                    pbar.update(1)


def filtre_rendrer_existant(webmap_item):
    webmap = WebMap(webmap_item)
    # Access the specific layer from the web map (adjust index as needed)
    for webmap_layer in webmap.layers[1:]:
        try:
            # Get the feature layer
            feature_layer_url = webmap_layer["url"]
            feature_layer = FeatureLayer(feature_layer_url)
            
            # Get renderer
            renderer = webmap_layer.layerDefinition.drawingInfo.renderer
            
            # Debug logging for fields
            logging.info(f"Available fields in {webmap_layer.title}:")
            for field in feature_layer.properties.fields:
                logging.info(f"Field name: {field['name']}")
            
            # Get field names case-insensitively
            field_mapping = {field['name'].upper(): field['name'] 
                           for field in feature_layer.properties.fields}
            
            # Find the actual field names
            type_field = field_mapping.get('TYPEPSC', 
                        next((v for k, v in field_mapping.items() if 'TYPEPSC' in k), None))
            stype_field = field_mapping.get('STYPEPSC',
                         next((v for k, v in field_mapping.items() if 'STYPEPSC' in k), None))
            
            if not type_field or not stype_field:
                logging.error(f"Fields not found in {webmap_layer.title}. Available fields: {list(field_mapping.keys())}")
                continue
                
            logging.info(f"Using fields: {type_field}, {stype_field}")
            
            # Query for unique combinations
            query_response = feature_layer.query(
                where='1=1',
                return_distinct_values=True,
                out_fields=f"{type_field},{stype_field}"
            )
            
            if not query_response.features:
                logging.warning(f"No features found in layer {webmap_layer.title}")
                continue
                
            # Build existing values set
            existing_values = set()
            for feature in query_response.features:
                try:
                    type_val = feature.attributes[type_field]
                    stype_val = feature.attributes[stype_field]
                    
                    if type_val is None or stype_val is None:
                        continue
                        
                    # Create value based on layer type (case insensitive)
                    layer_title_lower = webmap_layer.title.lower()
                    if "surf" in layer_title_lower:
                        evaluated_value = f'p-{type_val}-{stype_val}'
                    elif "lin" in layer_title_lower:
                        evaluated_value = f'P L {type_val} {stype_val}'
                    elif "pct" in layer_title_lower:
                        evaluated_value = f'P P {type_val} {stype_val}'
                    else:
                        continue
                        
                    existing_values.add(evaluated_value)
                    
                except KeyError as e:
                    logging.error(f"Field access error in {webmap_layer.title}: {str(e)}")
                    continue
            
            # Filter renderer
            if not existing_values:
                logging.warning(f"No valid values found for {webmap_layer.title}")
                continue
                
            filtered_renderer = copy.deepcopy(renderer)
            filtered_renderer['uniqueValueGroups'][0]['classes'] = []
            filtered_renderer['uniqueValueInfos'] = []
            
            for uv in renderer['uniqueValueInfos']:
                if uv.get('value') in existing_values:
                    filtered_renderer['uniqueValueInfos'].append(uv)
                    group_uv = {k: v for k, v in uv.items() if k != "value"}
                    group_uv["values"] = [[str(uv['value'])]]
                    filtered_renderer['uniqueValueGroups'][0]['classes'].append(group_uv)
            
            webmap_layer['layerDefinition']['drawingInfo']['renderer'] = filtered_renderer
            logging.info(f"Successfully filtered renderer for {webmap_layer.title}")
            
        except Exception as e:
            logging.error(f"Error processing layer {webmap_layer.title}: {str(e)}", exc_info=True)
            continue
    
    try:
        webmap.update()
        logging.info("Successfully updated webmap")
    except Exception as e:
        logging.error(f"Failed to update webmap: {str(e)}", exc_info=True)
        raise


def apply_renderer_to_layer(layer):
    """
    Apply appropriate renderer based on layer type
    
    Args:
        layer: The web map layer to apply renderer to
    """
    renderer_files = {
        'prescription_pct': 'DrawInfo_PCT.txt',
        'prescription_lin': 'DrawInfo_LIN.txt', 
        'prescription_surf': 'DrawInfo_SURF.txt',
        'zone_urba': 'DrawInfo_ZU.txt'
    }
    
    layer_title_lower = layer.title.lower()
    for layer_type, renderer_file in renderer_files.items():
        if layer_type in layer_title_lower:
            try:
                with open(f'./Symbology/{renderer_file}') as f:
                    layer['layerDefinition']['drawingInfo'] = json.load(f)
                break
            except FileNotFoundError:
                # Try lowercase version of renderer file
                renderer_file_lower = renderer_file.lower()
                with open(f'./Symbology//{renderer_file_lower}') as f:
                    layer['layerDefinition']['drawingInfo'] = json.load(f)
                break


def create_arcgis_webapp(gpu_paths, agol_link, agol_folder, username, password):
    """
    Create web maps and web applications in ArcGIS Online
    
    This function:
    1. Gets input paths for GPU archives
    2. Validates AGOL credentials
    3. Processes each GPU archive
    4. Creates web maps with appropriate renderers
    5. Publishes maps to AGOL

    Args:
        gpu_paths: List of paths to GPU archives
        agol_link: ArcGIS Online organization URL
        agol_folder: ArcGIS Online folder for publishing
        username: ArcGIS Online username
        password: ArcGIS Online password
    """
        # Validate all paths before processing
    for path in gpu_paths:
        if not os.path.exists(path):
            raise FileNotFoundError(f"GPU archive not found: {path}")

    if not username or not password:
        raise ValueError("Username and password are required")

    try:
        gis = GIS(agol_link, username, password)
        logging.info("Successfully connected to ArcGIS Online")
    except Exception as e:
        logging.error(f"Failed to connect to ArcGIS Online: {str(e)}")
        raise

    # Process each GPU archive with progress bar
    with tqdm(total=len(path_GPU_list), desc="Processing GPU archives") as pbar:
        for path_GPU in path_GPU_list:
            try:
                logging.info(f"Processing archive: {path_GPU}")
                
                # Extract GPU
                extract_path = os.path.splitext(path_GPU)[0]
                unzip_gpu(path_GPU, extract_path)

                # Get shapefiles
                shapefile_paths = extract_shapefile(extract_path)
                if not shapefile_paths:
                    logging.warning(f"No shapefiles found in: {extract_path}")
                    continue

                # Create zip archive
                shapefile_zip_path = os.path.join(
                    os.path.splitext(path_GPU)[0], 
                    f"LAYERS_GPU_{os.path.basename(os.path.splitext(path_GPU)[0])}.zip"
                )
                
                try:
                    zip_shapefile(shapefile_paths, shapefile_zip_path)
                except Exception as e:
                    logging.error(f"Failed to zip shapefiles: {str(e)}")
                    continue

                # Publish to AGOL
                try:
                    shapefile_nom = os.path.splitext(os.path.basename(shapefile_zip_path))[0]
                    item_properties = {
                        'type': 'Shapefile',
                        'title': shapefile_nom,
                        'tags': 'arcgis, python, GPU, PLU'
                    }
                    
                    published_item = gis.content.add(
                        item_properties,
                        data=shapefile_zip_path,
                        folder=agol_folder
                    )
                    published_layer = published_item.publish()
                    logging.info(f"Successfully published {shapefile_nom}")
                    
                except Exception as e:
                    logging.error(f"Failed to publish {shapefile_nom} in {agol_folder} folder: {str(e)}")
                    continue

                # Create and configure web map
                try:
                    wm = WebMap()
                    wm.add_layer(published_layer)
                
                    # Apply renderers with progress
                    for i in tqdm(range(len(wm.layers)), desc="Applying renderers"):
                        try:
                            apply_renderer_to_layer(wm.layers[i])
                        except Exception as e:
                            logging.error(f"Failed to apply renderer to layer {i}: {str(e)}")

                # Save web map
                    item_properties_wm = {
                        "title": f"{shapefile_nom}_WebMap",
                        "type": "Web Map",
                        "snippet": "GPU Web Map",
                        "tags": "python, arcgis, GPU, PLU, WebMap"
                    }
                    wm_item = wm.save(item_properties_wm, folder=agol_folder)
                    wm_item.share(everyone=True)
                    logging.info(f"Successfully created web map: {shapefile_nom}_WebMap")
                    
                    # Filter renderers
                    try:
                        filtre_rendrer_existant(wm_item)
                    except Exception as e:
                        logging.error(f"Failed to filter renderers: {str(e)}")
                        continue
                        
                except Exception as e:
                    logging.error(f"Failed to create web map for {shapefile_nom}: {str(e)}")
                    continue

            except Exception as e:
                logging.error(f"Failed processing {path_GPU}: {str(e)}")
            finally:
                pbar.update(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process GPU archives and create ArcGIS Online web maps.')
    parser.add_argument('gpu_paths', help='Comma-separated paths to GPU archives')
    parser.add_argument('--link', required=True, help='ArcGIS Online organization URL')
    parser.add_argument('--folder', required=True, help='ArcGIS Online folder for publishing')
    parser.add_argument('--username', required=True, help='ArcGIS Online username')
    parser.add_argument('--password', help='ArcGIS Online password (if not provided, will prompt)')
    
    args = parser.parse_args()
    
    # Split GPU paths
    path_GPU_list = [p.strip() for p in args.gpu_paths.split(",")]
    
    # Get password securely if not provided
    password = args.password if args.password else getpass.getpass("Enter ArcGIS Online password: ")
    
    try:
        create_arcgis_webapp(
            gpu_paths=path_GPU_list,
            agol_link=args.link,
            agol_folder=args.folder,
            username=args.username,
            password=password
        )
    except Exception as e:
        logging.error(f"Script terminated with error: {str(e)}")
        sys.exit(1)