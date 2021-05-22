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

import requests
import rasterio

env = dict(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', 
                   AWS_NO_SIGN_REQUEST='YES',
                   GDAL_MAX_RAW_BLOCK_CACHE_SIZE='200000000',
                   GDAL_SWATH_SIZE='200000000',
                   VSI_CURL_CACHE_SIZE='200000000',
                   GDAL_HTTP_COOKIEFILE=os.path.expanduser('~/cookies.txt'),
                   GDAL_HTTP_COOKIEJAR=os.path.expanduser('~/cookies.txt'))


os.environ.update(env)



#stack fixes - error
#'/vsicurl/https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/22M/ES2020/8/S2A_22MES_20200816_0_L2A/B02.tif' not recognized as a supported file format.
#'/vsicurl/https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/22M/DB2020/8/S2A_22MDB_20200816_0_L2A/B02.tif' not recognized as a supported file format.
#'/vsicurl/https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/22M/DB2020/8/S2A_22MDB_20200816_0_L2A/B02.tif' not recognized as a supported file format.
#'/vsicurl/https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/22M/DB2020/8/S2A_22MBA_20200816_0_L2A/B02.tif' not recognized as a supported file format.
badlist = ['S2A_22MES_20200816_0_L2A', 'S2A_22MDB_20200816_0_L2A', 'S2A_22MFB_20200816_0_L2A','S2A_22MEB_20200816_0_L2A','S2A_22MFA_20200816_0_L2A','S2A_22MCB_20200816_0_L2A','S2A_22MEA_20200816_0_L2A','S2A_22MDV_20200816_0_L2A',          'S2A_22MDA_20200816_0_L2A','S2A_22MCA_20200816_0_L2A','S2A_22MBA_20200816_0_L2A','S2A_22MEV_20200816_0_L2A','S2A_22MCV_20200816_0_L2A','S2A_22MBV_20200816_0_L2A',\
'S2A_22MBU_20200816_0_L2A','S2A_22MCU_20200816_0_L2A','S2A_22MDU_20200816_0_L2A','S2A_22MEU_20200816_0_L2A','S2A_22MCT_20200816_0_L2A','S2A_22MET_20200816_0_L2A','S2A_22MBS_20200816_0_L2A',\
'S2A_22MCT_20200816_0_L2A','S2A_22MCS_20200816_0_L2A','S2A_22MBS_20200816_0_L2A','S2A_22MDS_20200816_0_L2A','S2A_22MET_20200816_0_L2A'\
]

#'/vsicurl/https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/22M/DB2020/8/S2A_22MBA_20200816_0_L2A/B02.tif'

#https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/22N/FG2020/8/S2A_22MBA_20200816_0_L2A/B02.tif

badlist2 = ['S2A_22NFG_20200816_0_L2A']

bandlist = ['B02','B03','B04','B05','B06','B07','B08','B8A','B11','B12']
for x in badlist2:
	for strband in bandlist:
		url = 'https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/22M/DB2020/8/' + x + '/' + strband + '.tif'
		print(url)
		try:
			#rasterresp = requests.get(url)
			with rasterio.open(url) as src:
				pass
				print(strband, "ok")
		except Exception as badbandE:
			print(strband, "missing", badbandE)
	