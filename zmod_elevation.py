import osmnx as ox
from pyproj import Transformer
from owslib.util import Authentication
from owslib.wcs import WebCoverageService
import io
from rasterio.io import MemoryFile
from sklearn.neighbors import KDTree
import pandas as pd
import networkx as nx
import math


# Elevation information gathering.
def elevation(place, coordOut, precision, wcsService, version, identifier, form):
       
    #Create a graph by place name
    G = ox.graph_from_place(place, network_type='drive_service')
       
    #Convert a graph to node and/or edge GeoDataFrames.
    data = ox.graph_to_gdfs(G, nodes=True, edges=False, node_geometry=False, fill_edge_geometry=False)
    

    # dict for each node of graph to update elevation and dist while looping raster data
    attrs = {}
    for i in range(data.shape[0]):
        x = data.loc[data.iloc[i].name,'x']
        y = data.loc[data.iloc[i].name,'y']
        attrs[data.iloc[i].name] = {'elevation': math.inf, 'dist': math.inf, 'coord': (y,x)}
    
    
    #(lat,lng) of place in epsg:4326
    north = (-math.inf, 0)
    south = (math.inf, 0)
    east = (0, -math.inf)
    west = (0, math.inf)
    
    for index, row in data.iterrows():
        if(row['y'] >= north[0]):
            north = (row['y'], row['x'])
        if(row['y'] <= south[0]):
            south = (row['y'], row['x'])  
        if(row['x'] >= east[1]):
            east = (row['y'], row['x'])
        if(row['x'] <= west[1]):
            west = (row['y'], row['x'])       
    
    #bbox of place in epsg:4326 
    #min Longitude , min Latitude , max Longitude , max Latitude
    bbox=(west[1], south[0], east[1], north[0])
       
    
    """ Obtenir dades d’elevació des del ICGC per la zona a cobrir (bbox) """

    #(x,y) of place in coordOut
    transformer = Transformer.from_crs("epsg:4326", coordOut)
    northOut = transformer.transform(north[0],north[1])
    southOut = transformer.transform(south[0],south[1])
    eastOut = transformer.transform(east[0],east[1])
    westOut = transformer.transform(west[0],west[1])


    #bbox of place in coordOut
    #min Longitude , min Latitude , max Longitude , max Latitude
    bboxOut=(westOut[0], southOut[1], eastOut[0], northOut[1])

    #Rows and columns of pixels according to bbox and precision of this.precision
    widthAux = round((bboxOut[2]-bboxOut[0])/precision)
    heightAux = round((bboxOut[3]-bboxOut[1])/precision)
      
    # Adjust bbox according to number or rows and columns to get pixel size of 
    #  precisionXprecision exactly (adjust east and south)
    eastAdj = westOut[0] + (precision * widthAux)
    southAdj = northOut[1] - (precision * heightAux)
    bboxAdj = (westOut[0], southAdj, eastAdj, northOut[1])
    
    origin = (bboxAdj[0], bboxAdj[3])
        
    auth = Authentication(verify=False)

    # Create coverage object
    wcs = WebCoverageService(wcsService, version=version, auth=auth, timeout=60)

    # Access to the object by it's "data" via "getCoverage"
    response = wcs.getCoverage(identifier=identifier, bbox=bboxAdj, format=form,
                               crs=coordOut, width=widthAux, height=heightAux, 
                               verfiy=True, cert=('missing-cert.pem'))
    # Mimic data object in-memory filesystem.
    dataset_b = io.BytesIO(response.read())
        
    dataset = MemoryFile(dataset_b).open()
    #print("NoData Value: ", dataset.profile['nodata'])

    # Fetching the Raster Band(from dataset): band 1 (there's only one band)
    band = dataset.read(1)
    #print(band)
        
    #elevationMatrix = np.reshape(elevations, (heightAux,widthAux), 'C')
    elevationMatrix = band
    
    #tree = KDTree(data[['y', 'x']], metric='euclidean')

    transformer = Transformer.from_crs(coordOut,"epsg:4326");

    x = []
    y = []
    elevations = []
        
    #looping through raster data (elevations) and create KDTree
    for i in range(heightAux):
        for j in range(widthAux):
            lng=(origin[0]+(precision/2))+(precision*j)
            lat=(origin[1]-(precision/2))-(precision*i)
            coord4326 = transformer.transform(lng, lat)
            
            if elevationMatrix[i][j] < -1000.0:
                elevations.append(0.0)
            else:
                elevations.append(elevationMatrix[i][j])

            
            y.append(coord4326[0])
            x.append(coord4326[1])

    df_data = {'y': y,
        'x': x,
        'elevation': elevations}
    df = pd.DataFrame(df_data, columns = ['y', 'x', 'elevation'])

    tree = KDTree(df[['y', 'x']], metric='euclidean')

    #create a list from elevations
    elevs = []
    indexs = []

    for index, row in data.iterrows():
        coord = (row['y'],row['x'])
        dist_idx = tree.query([coord], k=1, return_distance=True)
        node_idx = dist_idx[1][0]
        elevation = df.at[node_idx[0], 'elevation']
        elevs.append(elevation)
        indexs.append(index)

    df_data = {'index': indexs,
        'elevation': elevs}

    df = pd.DataFrame(df_data, columns = ['index', 'elevation'])
    df.set_index('index', drop=True, inplace=True)

    #add 'elevation' attribute to graph G and edge grades afterwards
    nx.set_node_attributes(G, name="elevation", values=df["elevation"].to_dict())
    G = ox.add_edge_grades(G, add_absolute=True, precision=3)

    return(G)

def elevationIGN(place, printStatistics):
    coordOut = "epsg:25830"
    wcsService = 'https://servicios.idee.es/wcs-inspire/mdt'
    version = "1.0.0"
    form = "ArcGrid"

    try:
        precision = 5
        identifier = "Elevacion25830_5"
        G = elevation(place, coordOut, precision, wcsService, version, identifier, form)
        print("Showing results with 5m precision")

    except Exception as e:
        try:
            excepName = type(e).__name__
            print(e, "exception with 5m precision. Trying with 25m precision\n")
            precision = 25
            identifier = "Elevacion25830_25"
            G = elevation(place, coordOut, precision, wcsService, version, identifier, form)
            print("Showing results with 25m precision")
            return G
        except Exception:
            print("No results available")

    else:
        if printStatistics == True:
            showStatistics(G)
        return G