@echo off
setlocal

:: Set your default values here
set LINK="https://your-org.maps.arcgis.com/"
set FOLDER="Your_AGOL_FOLDER"

:: Get command line arguments
set /p GPU_PATHS="Enter GPU archive paths (comma-separated): "
set /p USERNAME="Enter ArcGIS Online username: "

:: Run the Python script
python "Main.py" ^
    "%GPU_PATHS%" ^
    --link "%LINK%" ^
    --folder "%FOLDER%" ^
    --username "%USERNAME%"

if errorlevel 1 (
    echo Script failed with error code %errorlevel%
    pause
    exit /b %errorlevel%
)

echo Script completed successfully
pause