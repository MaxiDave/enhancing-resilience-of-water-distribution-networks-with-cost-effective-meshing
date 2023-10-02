import osmnx as ox
import networkx as nx
import json
import geopy.distance
import overpy
import utm
from shapely.geometry import Polygon

# Set the treshold (in KMs).
#  This treshold will ignore consumptions that cannot be linked in a graph node with less distance than the specified.
#  For instance, it makes no sense to assign a consumption 200 meters away from the destination point.
treshold = 0.1


def link_json_consumptions(graph, usages_file):
    # Loads JSON water usages and applies particularities.
    
    # Add edge length attribute for each edge.
    g_attr = ox.distance.add_edge_lengths(graph, precision=3)
    
    # Set list of REFCAT as empty and total water consumption as 0.
    nx.set_node_attributes(g_attr, "", "REFCAT")
    nx.set_node_attributes(g_attr, 0, "consumption")
    
    # Get all the nodes of the graph with all the associated data.
    graph_fullnodes = g_attr.nodes(data = True)
    
    # Process the JSON usage file.
    with open(usages_file) as json_file_usages:
        
        usages_data = json.load(json_file_usages)
        
        for usosfinca in usages_data:
            
            # [DMA]: Get the 'usosfinca' coordinates.
            point_coords = [usosfinca['position'][0],usosfinca['position'][1]]
            
            # Find the nearest node on our graph.
            node = ox.nearest_nodes(g_attr, point_coords[1], point_coords[0])
            
            # [DMA]: Distance from node to point.
            node_full = graph_fullnodes[node]
            node_coords = (node_full['y'],node_full['x'])
            distance = geopy.distance.distance(node_coords, point_coords).km
            
            # [DMA]: Do not process the node if it does not have valid coordinates or it's too far from our graph.
            if point_coords[0] != 0 and point_coords[1] != 0 and distance < treshold:
    
                # Add REFCAT, consumptions, generations, barris, and sectors to the graph.
                new = "{" + usosfinca['RC14'] + ", " + str(usosfinca['nHabitantes']) + "}"
                if (len(graph.nodes[node]['REFCAT']) > 0):
                    new = ", " + new
                g_attr.nodes[node]["REFCAT"] = g_attr.nodes[node]["REFCAT"] + new
                g_attr.nodes[node]["consumption"] += usosfinca['waterConsumptionm3PerDay']
         
    print('JSON usages linked successfully.')
    return g_attr

# Public garden information gathering. Gets all public green areas, which we suppose needs irragation.
def link_publicgarden_consumptions(g_attr, place):

    # Get all the nodes of the graph with all the associated data.
    graph_fullnodes = g_attr.nodes(data = True)
    
    api = overpy.Overpass()
    
    r = api.query("""[out:json][timeout:25];
    // fetch area to search in
    area[name='"""+place+"""'][admin_level=8]->.searchArea;
    (
      way["leisure"="park"](area.searchArea);
      way["leisure"="garden"](area.searchArea);
      way["landuse"="grass"](area.searchArea);
    );
    // print results
    out body;
    >;
    out skel qt;
    """);
    
    #get ways places (perimeter of public gardens and parks)
    total_consumption=0
    area_total=0
    public_gardens = []
    
    class garden:
        def __init__(self, location, area, consumption):
            self.location = location
            self.area = area
            self.consumption = consumption
    
    for way in r.ways:
        points = []
        if (len(way.nodes) > 2):
            for node in way.nodes:
                utm_point = utm.from_latlon(float(node.lat),float(node.lon))
                points.append((utm_point[0], utm_point[1]))
            polygon = Polygon(points)
            area = polygon.area
            centroid = polygon.centroid
            consumption = 0.00042033256*area
            area_total += area
            public_gardens.append(garden((float(node.lat),float(node.lon)), area, consumption))
            total_consumption +=consumption
    
    for garden in public_gardens:
        point_coords = [garden.location[0],garden.location[1]]
        node = ox.nearest_nodes(g_attr, point_coords[1], point_coords[0])
        # [DMA]: Distance from node to point.
        node_full = graph_fullnodes[node]
        node_coords = (node_full['y'],node_full['x'])
        distance = geopy.distance.distance(node_coords, point_coords).km
        if distance < treshold:
            new = "{'Public garden'}"
            if (len(g_attr.nodes[node]['REFCAT']) > 0):
                new = ", " + new
            g_attr.nodes[node]["REFCAT"] = g_attr.nodes[node]["REFCAT"] + new
            g_attr.nodes[node]["consumption"] += garden.consumption
            
         
    print('Public gardens consumption:','{:,.2f}'.format(total_consumption),"m3/day")
    print('Public gardens area:','{:,.2f}'.format(area_total),"m2")
    print('Public gardens linked successfully.')
    return g_attr