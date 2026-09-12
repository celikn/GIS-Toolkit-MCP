FROM python:3.12-slim

WORKDIR /app

# GDAL/PROJ runtime libs for rasterio/geopandas. rasterio/pyogrio ship prebuilt
# manylinux wheels (incl. arm64) for these pinned versions, so no compiler
# toolchain or GDAL dev headers are needed here — unlike gis-mcp.Dockerfile,
# which has to build ancient rasterio/fiona pins from source.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal-dev libproj-dev libgeos-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV GIS_TOOLKIT_TRANSPORT=streamable-http
ENV GIS_TOOLKIT_PORT=9020
EXPOSE 9020

CMD ["python3", "server.py"]
