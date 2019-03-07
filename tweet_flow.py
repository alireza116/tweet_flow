import networkx as nx
import csv
import fiona
from shapely.geometry import LineString
from shapely.geometry import Point
from shapely.ops import linemerge
from shapely.ops import nearest_points
from shapely.geometry import MultiPoint
import shapely
import geopandas
from scipy.spatial import cKDTree  
import numpy as np
import pandas as pd



# add an edgelist csvFIle for the city of choice.
with open("losangeles/LosAngeles_Edgelist.csv") as edgeListFile:
    csvReader = csv.DictReader(edgeListFile)
    edgelist = [i for i in csvReader]

#read shapefiles for nodes in the network.
shapeNodes = fiona.open("losangeles/laNodesWGS.shp")
idPointDict = {p["properties"]["OBJECTID"]:p["geometry"]["coordinates"] for p in shapeNodes}

#read shapefiles for nodes and edges.
nodes = geopandas.read_file("losangeles/laNodesWGS.shp")
edges = geopandas.read_file("losangeles/laLinksWGS.shp")

#create a dictionary for edgeID edgeLinestring
shapeEdges = fiona.open("losangeles/laLinksWGS.shp")
edgeDict = {e["properties"]["OBJECTID"]:LineString(e["geometry"]["coordinates"]) for e in shapeEdges} 

#read tweets, here it is in the format of a shapefile.
tweets = geopandas.read_file("losangeles/losangeles.shp")


userNames = tweets["userName"].unique()

#function for finding closest node on the graph to a tweet location
def ckdnearest(gdA, gdB, bcol):   
    nA = np.array(list(zip(gdA.geometry.x, gdA.geometry.y)) )
    nB = np.array(list(zip(gdB.geometry.x, gdB.geometry.y)) )
    btree = cKDTree(nB)
    dist, idx = btree.query(nA,k=1)
    df = pd.DataFrame.from_dict({'distance': dist.astype(int),
                             'bcol' : gdB.loc[idx, bcol].values })
    return df

closestNodes = ckdnearest(tweets,nodes,"OBJECTID")

tweets["closestNode"] = closestNodes["bcol"]


dates = pd.to_datetime(tweets['postedtime'])

tweets["postedtime"] = dates


tweets["date"] = [postedtime.date() for postedtime in tweets["postedtime"]]

g = nx.DiGraph()

for edge in edgelist:
    g.add_edge(int(edge["START_NODE"]),int(edge["END_NODE"]),edgeID=int(edge["EDGE"]),weight=float(edge["LENGTH"]))

def getShortestPath(start,end):
    try:
        shortestPath = nx.shortest_path(g,source=start,target=end,weight="weight")
        lines = []
        for i,start in enumerate(shortestPath):
            if i < len(shortestPath)-1:
                end = shortestPath[i+1]
                edge = g[start][end]
                edgeID = edge["edgeID"]
                line = edgeDict[edge["edgeID"]]
                lines.append(line)
        lineMerge = linemerge(lines)
        return lineMerge
    except:
        return None

def getFeatureGeoJson(shapelyLine):
    features =  geopandas.GeoSeries(shapelyLine).__geo_interface__["features"]
    return features

def getShortestPaths(tweets):
    shortestPaths = []
    tweets = list(tweets.iterrows())
    for i in range(len(tweets)-1):
        firstTweet = tweets[i][1]
        secondTweet = tweets[i+1][1]
        if (firstTweet["closestNode"]!=secondTweet["closestNode"]):
            sp = getShortestPath(firstTweet["closestNode"],secondTweet["closestNode"])
            if sp is not None:
                shortestPaths.append(sp)
    return shortestPaths


def getUserShortestPaths(user):
    userTweets = tweets[tweets["userName"]==user]
    userTweets = userTweets.sort_values("postedtime")
    dates = userTweets["date"].unique()
    userShortestPaths = []
    for date in dates:
        dayTweets = userTweets[userTweets["date"] ==date]
        if len(dayTweets) > 1:
            dayShortestPaths = getShortestPaths(dayTweets)
        userShortestPaths += dayShortestPaths
    return userShortestPaths



