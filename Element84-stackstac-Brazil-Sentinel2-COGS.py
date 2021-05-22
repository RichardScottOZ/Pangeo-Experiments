#!/usr/bin/env python
import stackstac
import satsearch
from datetime import datetime
import dask.diagnostics
import rioxarray
import xarray as xr
import numpy as np
import geopandas as gpd
import geojson
import json
from datetime import datetime
from shapely.geometry import mapping
import zarr
import os

def median(array, dim, keep_attrs=False, skipna=True, **kwargs):
    """ Runs a median on an dask-backed xarray.
    
    This function does not scale!
    It will rechunk along the given dimension, so make sure 
    your other chunk sizes are small enough that it 
    will fit into memory.
    
    :param DataArray array: An xarray.DataArray wrapping a dask array
    :param dim str: The name of the dim in array to calculate the median
    """
    if type(array) is xr.Dataset:
        return array.apply(median, dim=dim, keep_attrs=keep_attrs, **kwargs)
    
    if not hasattr(array.data, 'dask'):
        return array.median(dim, keep_attrs=keep_attrs, **kwargs)
    
    array = array.chunk({dim:-1})
    axis = array.dims.index(dim)
    median_func = np.nanmedian if skipna else np.median
    blocks = dask.array.map_blocks(median_func, array.data, dtype=array.dtype, drop_axis=axis, axis=axis, **kwargs)
    
    new_coords={k: v for k, v in array.coords.items() if k != dim and dim not in v.dims}
    new_dims = tuple(d for d in array.dims if d != dim)
    new_attrs = array.attrs if keep_attrs else None
    
    return xr.DataArray(blocks, coords=new_coords, dims=new_dims, attrs=new_attrs)

env = dict(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', 
                   AWS_NO_SIGN_REQUEST='YES',
                   GDAL_MAX_RAW_BLOCK_CACHE_SIZE='200000000',
                   GDAL_SWATH_SIZE='200000000',
                   VSI_CURL_CACHE_SIZE='200000000',
                   GDAL_HTTP_COOKIEFILE=os.path.expanduser('~/cookies.txt'),
                   GDAL_HTTP_COOKIEJAR=os.path.expanduser('~/cookies.txt'))


os.environ.update(env)


bbox = [-53.0172669999999968,-9.5331669999999988,-48.4956669999999974,-3.1035670000000000]                        
bbox = [-53.0232820986343754,-8.1236837545427090, -49.4688521093868800,-4.8677173521785928] #carra grav


t0 = datetime.now()
stac_found = satsearch.Search(
    url="https://earth-search.aws.element84.com/v0",
    bbox=bbox,
    collections=["sentinel-s2-l2a-cogs"],
    datetime="2020-04-22/2021-04-22",
).found()  
print("found",stac_found)

stac_items = satsearch.Search(
    url="https://earth-search.aws.element84.com/v0",
    bbox=bbox,
    collections=["sentinel-s2-l2a-cogs"],
    datetime="2020-04-22/2021-04-22",
).items()

print('searching time: {}'.format(datetime.now()-t0))

print("Num of Items", len(stac_items))

t0 = datetime.now()

carajas_grav_bounds = [-5407163.8851959239691496,-1289165.8399838600307703, -4627918.5439387122169137,-372068.2382511437172070]

#stack = stackstac.stack(stac_items, epsg=6933, resolution=3000, resampling=1, bounds=carajas_grav_bounds)
#stack = stackstac.stack(stac_items, epsg=6933, resolution=3000, resampling=1, fill_value=0)
#stack = stackstac.stack(stac_items, epsg=6933, resolution=10000, resampling=1, fill_value=0)
stack = stackstac.stack(stac_items, epsg=6933, resolution=20000, resampling=1, fill_value=0)
#stack = stackstac.stack(stac_items, epsg=6933, resolution=3000, resampling=1, bounds=carajas_grav_bounds, dtype='uint16', fill_value=0, chunksize=4096)

print('lazy stacking time: {}'.format(datetime.now()-t0))

print("Stack Size in GB: ", round(stack.nbytes/1e9,0))

print(stack)

#filename = r'F:\Brazil\Brazil1.geojson'
#brazil = gpd.read_file(filename)
filename = r'F:\Brazil\CarraGrav2.shp'
brazil = gpd.read_file(filename)

#stack fixes - error
#'/vsicurl/https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/22M/ES2020/8/S2A_22MES_20200816_0_L2A/B02.tif' not recognized as a supported file format.
#'/vsicurl/https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/22M/DB2020/8/S2A_22MDB_20200816_0_L2A/B02.tif' not recognized as a supported file format.
#'/vsicurl/https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/22M/DB2020/8/S2A_22MDB_20200816_0_L2A/B02.tif' not recognized as a supported file format.
#'/vsicurl/https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/22M/DB2020/8/S2A_22MBA_20200816_0_L2A/B02.tif' not recognized as a supported file format.
badlist = ['S2A_22MES_20200816_0_L2A', 'S2A_22MDB_20200816_0_L2A', 'S2A_22MFB_20200816_0_L2A','S2A_22MEB_20200816_0_L2A','S2A_22MFA_20200816_0_L2A','S2A_22MCB_20200816_0_L2A','S2A_22MEA_20200816_0_L2A','S2A_22MEA_20200816_0_L2A',          'S2A_22MDA_20200816_0_L2A','S2A_22MCA_20200816_0_L2A','S2A_22MBA_20200816_0_L2A']
          
#stack = stack[~stack["id"].isin(badlist) ]
stack = stack[~stack["id"].isin(badlist) ]
#sentinel-s2-l2a-cogs/22M/ES2020
print(stack)

cropped = stack.rio.clip(brazil.geometry.apply(mapping), crs=4326)
print(cropped)

#cropped_clear = stack[stack["eo:cloud_cover"] < 67]
cropped_clear = stack[stack["eo:cloud_cover"] <= 0]
print(cropped_clear)

b02, b03 = cropped_clear.sel(band="B02"), cropped.sel(band="B03")
print(b02)

b02median = median(b02, dim="time")
print(b02median)

#3116 - write a loop to check in batches of say, 100?  the median to find bad bands #watch for when the count - need to do a robust handler
b02small_list = []

print("b02 shape", b02.shape, b02.nbytes/1e9)
 
for b in range(int(stac_found/100)):  #make this stac_found /10 for checking
    b02median_small = median(b02[b*100 : (b+1)*100], dim="time")
    b02small_list.append(b02median_small)

b02small_list_results = []

if 1 == 2:
    for index, b in enumerate(b02small_list):
        print(index)
        #if index < 13:
        
            #continue
            
        with dask.diagnostics.ProgressBar():
            #croppedNP = median(b02, dim="time").compute()
            croppedNP = b.compute()
            b02small_list_results.append(croppedNP)
        
#len(b02small_list_results)

if 1 == 1:
    with dask.diagnostics.ProgressBar():
        #croppedNP = median(b02, dim="time").compute()
        croppedNP = b02median.compute()
        #print(croppedNP)

        croppedNP.rio.write_crs('epsg:6933',inplace=True)
        #croppedNP.rio.to_raster(r'F:\Brazil\sentinel_median_carra_grav_10000_05.tif')
        croppedNP.rio.to_raster(r'F:\Brazil\sentinel_median_carra_grav_10000_0.tif')
