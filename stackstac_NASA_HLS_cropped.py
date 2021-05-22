#!/usr/bin/env python
# coding: utf-8

# From Rowan Gaffney https://gist.github.com/rmg55/b144cb273d9ccfdf979e9843fdf5e651


from satsearch import Search
import intake
import stackstac, os, requests
from netrc import netrc
from subprocess import Popen
from getpass import getpass
import rasterio
from distributed import LocalCluster,Client
import datetime
import dask.array as dask_array
import dask
import dask.diagnostics

#from utils import DevNullStore,DiagnosticTimer,total_nthreads,total_ncores,total_workers,get_chunksize

import geopandas as gpd
import rioxarray
import numpy as np
import xarray as xr

from shapely.geometry import mapping


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


import os
env = dict(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', 
                   AWS_NO_SIGN_REQUEST='YES',
                   GDAL_MAX_RAW_BLOCK_CACHE_SIZE='200000000',
                   GDAL_SWATH_SIZE='200000000',
                   VSI_CURL_CACHE_SIZE='200000000',
                   GDAL_HTTP_COOKIEFILE=os.path.expanduser('~/cookies.txt'),
                   GDAL_HTTP_COOKIEJAR=os.path.expanduser('~/cookies.txt'))


os.environ.update(env)
    
# dask.config.set({'distributed.dashboard.link':'/proxy/{port}/status'})
# cluster = LocalCluster(threads_per_worker=1)
# cl = Client(cluster)
# cl

def get_STAC_items(url, collection, dates, bbox):
    results = Search.search(url=url,
                        collections=collection, 
                        datetime=dates,
                        bbox=bbox)

    return(results)


data = 'hls'
if data == 'hls':
    #Setup NASA Credentials
    urs = 'urs.earthdata.nasa.gov'    # Earthdata URL to call for authentication
    prompts = ['Enter NASA Earthdata Login Username \n(or create an account at urs.earthdata.nasa.gov): ',
               'Enter NASA Earthdata Login Password: ']
    try:
        netrcDir = os.path.expanduser(r'C:\users\rscott\.netrc')
        #netrcDir = os.path.expanduser("~/.netrc")
        netrc(netrcDir).authenticators(urs)[0]
        del netrcDir

    # Below, create a netrc file and prompt user for NASA Earthdata Login Username and Password
    except FileNotFoundError:
        if 1 == 2:
            homeDir = os.path.expanduser("~")
            Popen('touch {0}.netrc | chmod og-rw {0}.netrc | echo machine {1} >> {0}.netrc'.format(homeDir + os.sep, urs), shell=True)
            Popen('echo login {} >> {}.netrc'.format(getpass(prompt=prompts[0]), homeDir + os.sep), shell=True)
            Popen('echo password {} >> {}.netrc'.format(getpass(prompt=prompts[1]), homeDir + os.sep), shell=True)
            del homeDir, urs, prompts



url = 'https://cmr.earthdata.nasa.gov/stac/LPCLOUD' 
collection = ['HLSS30.v1.5']#'C1711924822-LPCLOUD' #HLS
bbox = [-53.0172669999999968,-9.5331669999999988,-48.4956669999999974,-3.1035670000000000]    
bbox = [-53.0232820986343754,-8.1236837545427090, -49.4688521093868800,-4.8677173521785928] #carra grav
dates = '2013-01-01/2021-03-01'

limit = 500

#stac_hls = intake.open_stac_catalog(f'https://cmr.earthdata.nasa.gov/stac/LPCLOUD/collections?limit={limit}')
carajas_grav_bounds = [-5407163.8851959239691496,-1289165.8399838600307703, -4627918.5439387122169137,-372068.2382511437172070]

stac_items = Search(url='https://cmr.earthdata.nasa.gov/stac/LPCLOUD',
                 collections=['HLSL30.v1.5'], 
                 #bbox = '-53.0172669999999968,-9.5331669999999988,-48.4956669999999974,-3.1035670000000000' ,
                 bbox = '-53.0232820986343754,-8.1236837545427090, -49.4688521093868800,-4.8677173521785928',
                 datetime='2016-04-23/2021-04-23', 
                ).items()

stack = stackstac.stack(stac_items, epsg=6933, resolution=30, resampling=1, assets=['B8A', 'B08', 'B09', 'B04', 'B12', 'B02', 'B06', 'B11', 'B07', 'B05', 'B03', 'Fmask', 'B01', 'B10'])
#stack = stackstac.stack(stac_items, epsg=6933, resolution=6000, resampling=1, assets=['B8A', 'B08', 'B09', 'B04', 'B12', 'B02', 'B06', 'B11', 'B07', 'B05', 'B03', 'Fmask', 'B01', 'B10'])
print(stack)

filename = r'F:\Brazil\CarraGrav2.shp'
brazil = gpd.read_file(filename)

cropped = stack.rio.clip(brazil.geometry.apply(mapping), crs=4326)
print(cropped)

cropped_clear = cropped[cropped["eo:cloud_cover"] < 101]
print(cropped_clear)


b02, b03 = cropped_clear.sel(band="B02"), cropped.sel(band="B03")
print(b02)

b02median = median(b02, dim="time")
print(b02median)

xmin, ymin = cropped_clear.x.min().values.item(), cropped_clear.y.min().values.item()
xmax, ymax = cropped_clear.x.max().values.item(), cropped_clear.y.max().values.item()

xmid = ( cropped_clear.x.min().values.item() + cropped_clear.x.max().values.item() ) /2
ymid = ( cropped_clear.y.min().values.item() + cropped_clear.y.max().values.item() ) /2


print("xmid", xmid, "ymid", ymid)
print(xmin, xmax, ymin, ymax)

#if 1 == 2:

b02median1 = b02median.where( (b02.x < xmid) & (b02.y < ymid), drop=True )
b02median2 = b02median.where( (b02.x < xmid) & (b02.y >= ymid), drop=True )
b02median3 = b02median.where( (b02.x >= xmid) & (b02.y < ymid), drop=True )
b02median4 = b02median.where( (b02.x >= xmid) & (b02.y >= ymid), drop=True )

quarters = [b02median1, b02median2, b02median3, b02median4]

if 1 == 2:
	with dask.diagnostics.ProgressBar():
		croppedNP = b02median.compute()
		croppedNP.rio.write_crs('epsg:6933',inplace=True)
		croppedNP.rio.to_raster(r'F:\Brazil\HLSCarraGravtest-crop-9000All' + '.tif')

if 1 == 1:
    for index, q in enumerate(quarters):
        with dask.diagnostics.ProgressBar():
            croppedNP = q.compute()
            croppedNP.rio.write_crs('epsg:6933',inplace=True)
            croppedNP.rio.to_raster(r'F:\Brazil\HLSCarraGravtest-crop-q' + str(index) + '.tif')



