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

#filename = R'C:\Users\rscott\OneDrive - OZ Minerals\Exploration2021\EASI\Data\Brazil-Para-Maranhao-Geophysics_Coverage.geojson'  #with geophysics areas
#filename = r'C:\Users\rscott\OneDrive - OZ Minerals\Exploration2021\Projeto-Sentinela\Data\Brazil_Para-Maranhao_boundary.shp'
#filename = r'F:\Brazil\Brazil1.geojson'
#brazil = gpd.read_file(filename)
filename = r'CarraGrav3.geojson'
brazil = gpd.read_file(filename)

print("TOTAL_BOUNDS",brazil.total_bounds)
xmin = brazil.total_bounds[0]
ymin = brazil.total_bounds[1]
xmax = brazil.total_bounds[2]
ymax = brazil.total_bounds[3]
#get test for maranaho here - combined carajas, para and pendock box.

#bbox = [-53.0232820986343754,-8.1236837545427090, -49.4688521093868800,-4.8677173521785928] #carra grav
bbox = [xmin, ymin, xmax, ymax]
print("bbox from bounds:", bbox)

#try 0 cloud clover from 2018??
datetime_b = "2018-04-22/2021-04-22"

t0 = datetime.now()
stac_found = satsearch.Search(
    url="https://earth-search.aws.element84.com/v0",
    bbox=bbox,
    collections=["sentinel-s2-l2a-cogs"],
    datetime=datetime_b,
    query={'eo:cloud_cover': {'eq': 0}}
    #sort=['<datetime']
).found()  
print("found",stac_found)

stac_items = satsearch.Search(
    url="https://earth-search.aws.element84.com/v0",
    bbox=bbox,
    collections=["sentinel-s2-l2a-cogs"],
    datetime=datetime_b,
    query={'eo:cloud_cover': {'eq': 0}}
    #sort=['<datetime']
).items()

print('searching time: {}'.format(datetime.now()-t0))

print("Num of Items", len(stac_items))

t0 = datetime.now()

carajas_grav_bounds = [-5407163.8851959239691496,-1289165.8399838600307703, -4627918.5439387122169137,-372068.2382511437172070]

#stack = stackstac.stack(stac_items, epsg=6933, resolution=90, resampling=1)
#stack = stackstac.stack(stac_items, epsg=6933, resolution=60, resampling=1)
#stack = stackstac.stack(stac_items, epsg=6933, resolution=90, resampling=1)
#stack = stackstac.stack(stac_items, epsg=6933, resolution=250, resampling=1)
#stack = stackstac.stack(stac_items, epsg=6933, resolution=3000, resampling=1, bounds=carajas_grav_bounds)
#stack = stackstac.stack(stac_items, epsg=6933, resolution=3000, resampling=1, fill_value=0)
#stack = stackstac.stack(stac_items, epsg=6933, resolution=10000, resampling=1, fill_value=0)
stack = stackstac.stack(stac_items, epsg=6933, resolution=30, resampling=1)
#stack = stackstac.stack(stac_items, epsg=6933, resolution=3000, resampling=1, bounds=carajas_grav_bounds, dtype='uint16', fill_value=0, chunksize=4096)

print('lazy stacking time: {}'.format(datetime.now()-t0))

print("Stack Size in GB: ", round(stack.nbytes/1e9,0))

print(stack)


#stack fixes - error
#'/vsicurl/https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/22M/ES2020/8/S2A_22MES_20200816_0_L2A/B02.tif' not recognized as a supported file format.
#'/vsicurl/https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/22M/DB2020/8/S2A_22MDB_20200816_0_L2A/B02.tif' not recognized as a supported file format.
#'/vsicurl/https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/22M/DB2020/8/S2A_22MDB_20200816_0_L2A/B02.tif' not recognized as a supported file format.
#'/vsicurl/https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/22M/DB2020/8/S2A_22MBA_20200816_0_L2A/B02.tif' not recognized as a supported file format.
badlist = ['S2A_22MES_20200816_0_L2A','S2A_22MDB_20200816_0_L2A','S2A_22MFB_20200816_0_L2A','S2A_22MEB_20200816_0_L2A','S2A_22MFA_20200816_0_L2A','S2A_22MCB_20200816_0_L2A','S2A_22MEA_20200816_0_L2A',
'S2A_22MDV_20200816_0_L2A','S2A_22MDA_20200816_0_L2A','S2A_22MCA_20200816_0_L2A','S2A_22MBA_20200816_0_L2A','S2A_22MEV_20200816_0_L2A','S2A_22MCV_20200816_0_L2A','S2A_22MBV_20200816_0_L2A',\
'S2A_22MBU_20200816_0_L2A','S2A_22MCU_20200816_0_L2A','S2A_22MDU_20200816_0_L2A','S2A_22MEU_20200816_0_L2A','S2A_22MCT_20200816_0_L2A','S2A_22MET_20200816_0_L2A','S2A_22MBS_20200816_0_L2A',\
'S2A_22MCT_20200816_0_L2A','S2A_22MCS_20200816_0_L2A','S2A_22MBS_20200816_0_L2A','S2A_22MDS_20200816_0_L2A','S2A_22MET_20200816_0_L2A',\
'S2B_23MRP_20200809_0_L2A','S2B_23NLA_20200729_0_L2A','S2A_23MRT_20200807_0_L2A','S2B_23MRM_20200809_0_L2A','S2A_21LZL_20200816_0_L2A','S2A_23NLA_20200803_0_L2A','S2B_23MRN_20200809_0_L2A',\
'S2A_22LBR_20200816_0_L2A','S2B_23MRP_20200730_0_L2A','S2B_23NKA_20200729_0_L2A','S2B_23MRM_20200730_0_L2A','S2A_23MRR_20200804_0_L2A','S2A_21LZK_20200816_0_L2A','S2A_23MRQ_20200804_0_L2A',\
'S2A_23MRS_20200728_0_L2A','S2A_21MZM_20200816_0_L2A','S2A_23MRU_20200807_0_L2A','S2A_23MRS_20200807_0_L2A','S2B_23NLA_20200808_0_L2A','S2B_23MRN_20200730_0_L2A'
]
          
stack = stack[~stack["id"].isin(badlist) ]
#stack = stack[stack["id"].isin(badlist) ]  #try only bad scenes
print(stack)

cropped = stack.rio.clip(brazil.geometry.apply(mapping), crs=4326)
print(cropped)

cropped_clear = cropped
print(cropped_clear)

cropped_clear["NDVI"] = (cropped_clear.sel(band="B08") - cropped_clear.sel(band="B04") ) / (cropped_clear.sel(band="B08") + cropped_clear.sel(band="B04") )

print("\n\nCROPPED CLEAR POST NDVI\n\n", cropped_clear)

cropped_clear["NDVIMIN"] = cropped_clear["NDVI"].min(dim="time", skipna=True)

print("\n\nCROPPED CLEAR NDVI\n\n", cropped_clear)

print(cropped_clear)

b02, b03 = cropped_clear.sel(band="B02"), cropped_clear.sel(band="B03")

print("\n\nBand 02\n\n")
print(b02)

with dask.diagnostics.ProgressBar():

    b02 = b02.where( b02["NDVI"] <= b02["NDVIMIN"], drop=True  )


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
            
        #with dask.diagnostics.ProgressBar():
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
        #croppedNP.rio.to_raster(r'F:\Brazil\sentinel_median_carra_grav_10000_1.tif')
        #croppedNP.rio.to_raster(r'F:\Brazil\sentinel_median_carra_grav_90_1.tif')
        #croppedNP.rio.to_raster(r'F:\Brazil\sentinel_median_carra_grav_60_1.tif')
        
        croppedNP.rio.to_raster(r'F:\Brazil\sentinel_median_carra_grav_30_0_NDVI.tif')
