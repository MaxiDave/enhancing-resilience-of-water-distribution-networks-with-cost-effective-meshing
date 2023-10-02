########################################################################################################
########################################################################################################
################################### PRINT RESULTS IN MAP ###########################################
########################################################################################################
########################################################################################################

import networkx as nx
import osmnx as ox
import seaborn as sns
import numpy as np
import folium
import matplotlib.lines as mlines
import matplotlib.pyplot as plt

sns.set_theme(style="darkgrid")

# [Roser] Function that prints a clustered solution.
color_palette = ["#FF34FF", "#FF4A46", "#008941", "#006FA6", "#A30059",
"#7A4900", "#0000A6", "#63FFAC", "#B79762", "#004D43", "#8FB0FF", "#997D87",
"#5A0007", "#809693", "#FEFFE6", "#1B4400", "#4FC601", "#3B5DFF", "#4A3B53", "#FF2F80",
"#61615A", "#BA0900", "#6B7900", "#00C2A0", "#FFAA92", "#FF90C9", "#B903AA", "#D16100",
"#DDEFFF", "#000035", "#7B4F4B", "#A1C299", "#300018", "#0AA6D8", "#013349", "#00846F",
"#372101", "#FFB500", "#C2FFED", "#A079BF", "#CC0744", "#C0B9B2", "#C2FF99", "#001E09",
"#00489C", "#6F0062", "#0CBD66", "#EEC3FF", "#456D75", "#B77B68", "#7A87A1", "#788D66",
"#885578", "#FAD09F", "#FF8A9A", "#D157A0", "#BEC459", "#456648", "#0086ED", "#886F4C",
"#34362D", "#B4A8BD", "#00A6AA", "#452C2C", "#636375", "#A3C8C9", "#FF913F", "#938A81",
"#575329", "#00FECF", "#B05B6F", "#8CD0FF", "#3B9700", "#04F757", "#C8A1A1", "#1E6E00",
"#7900D7", "#A77500", "#6367A9", "#A05837", "#6B002C", "#772600", "#D790FF", "#9B9700",
"#549E79", "#FFF69F", "#201625", "#72418F", "#BC23FF", "#99ADC0", "#3A2465", "#922329",
"#5B4534", "#FDE8DC", "#404E55", "#0089A3", "#CB7E98", "#A4E804", "#324E72", "#6A3A4C"]

#############################################################################################
def print_solution(Gdir, wwtp, dest_nodes, tank_node, subgraph, filename = None):
    
    g_attr = Gdir.copy()

    # Compute colors for route from WWTP to water tanks
    edge_colors = []
    edge_linewidth = []
    for u, v in g_attr.edges():
        edge_colors.append('#9c9c9c')
        edge_linewidth.append(0.5)

    # Only consider nodes inside this box.
    min_lat, max_lat = 41.965, 42.005
    
    # Get a list of nodes to remove
    nodes_to_remove = [node for node,data in g_attr.nodes(data=True) if (data['y'] < min_lat or data['y'] > max_lat)]
    
    # Remove the nodes outside the specified bounds
    g_attr.remove_nodes_from(nodes_to_remove)

    # Compute colors for each cluster
    edge_colors = []
    edge_linewidth = []
    for u, v in g_attr.edges():
        if subgraph.has_edge(u, v):
            edge_colors.append(color_palette[1])
            edge_linewidth.append(2)
        else:
            edge_colors.append('#9c9c9c')
            edge_linewidth.append(0.5)

    fig, ax = ox.plot_graph(g_attr, bgcolor='white', figsize=(20, 20), show=False, close=False,
                            edge_color=edge_colors, node_edgecolor='#9c9c9c', node_size=0,
                            edge_linewidth=edge_linewidth)

    # Prepare LEGEND
    handles, labels = ax.get_legend_handles_labels()
    handles.append(mlines.Line2D([0], [0], color='white', marker='D', markersize=8, markerfacecolor='black',
                                 label='Water tank node'))
    all_nodes = g_attr.nodes(data=True)

    # Obtain the nodes elevations.
    elevations = []
    for node in dest_nodes:
        if node in g_attr.nodes():
            elevations.append(all_nodes[node]['elevation'])
    elev_mean = round(sum(elevations) / len(elevations), 2)
    elev_max = round(max(elevations), 2)
    elev_min = round(min(elevations), 2)

    # Set the legend.
    color = color_palette[1]
    distance = int(subgraph.size(weight="length"))
    label = str(len(dest_nodes)) + " nodes, pipe distance (m) = " + str(distance)
    patch = mlines.Line2D([0], [0], color=color, marker='o', markersize=6, markerfacecolor=color, label=label)
    handles.append(patch)

    plt.legend(handles=handles, loc="upper left", prop={'size': 25})

    # Add the water tank node
    ax.scatter(g_attr.nodes[tank_node]['x'], g_attr.nodes[tank_node]['y'], c='black', s=175, marker='D')

    # Add the destination nodes
    for node in dest_nodes:
        color = color_palette[1]
        size = 45
        marker = 'o'
        ax.scatter(g_attr.nodes[node]['x'], g_attr.nodes[node]['y'], c=color, s=size, marker=marker)

    plt.show()
    if filename != None:
        fig.savefig(filename + '.pdf', format="PDF", bbox_inches='tight')



#############################################################################################
def print_solution_small(Gdir, wwtp, dest_nodes, tank_node, subgraph, filename = None):
    
    g_attr = Gdir.copy()

    # Compute colors for route from WWTP to water tanks
    edge_colors = []
    edge_linewidth = []
    for u, v in g_attr.edges():
        edge_colors.append('#9c9c9c')
        edge_linewidth.append(0.5)

    # Only consider nodes inside this box.
    min_lat, max_lat = 41.97, 42.003
    min_lon, max_lon = 2.795, 2.83
    
    # Get a list of nodes to remove
    nodes_to_remove = [node for node,data in g_attr.nodes(data=True) if (data['y'] < min_lat or data['y'] > max_lat) or ((data['x'] < min_lon or data['x'] > max_lon))]
    
    # Remove the nodes outside the specified bounds
    g_attr.remove_nodes_from(nodes_to_remove)

    # Compute colors for each cluster
    edge_colors = []
    edge_linewidth = []
    for u, v in g_attr.edges():
        if subgraph.has_edge(u, v):
            edge_colors.append(color_palette[1])
            edge_linewidth.append(4)
        else:
            edge_colors.append('#9c9c9c')
            edge_linewidth.append(0.5)

    fig, ax = ox.plot_graph(g_attr, bgcolor='white', figsize=(20, 20), show=False, close=False,
                            edge_color=edge_colors, node_edgecolor='#9c9c9c', node_size=0,
                            edge_linewidth=edge_linewidth)

    # Prepare LEGEND
    handles, labels = ax.get_legend_handles_labels()
    handles.append(mlines.Line2D([0], [0], color='white', marker='D', markersize=8, markerfacecolor='black',
                                 label='Water tank node'))
    all_nodes = g_attr.nodes(data=True)

    # Obtain the nodes elevations.
    elevations = []
    for node in dest_nodes:
        if node in g_attr.nodes():
            elevations.append(all_nodes[node]['elevation'])
    elev_mean = round(sum(elevations) / len(elevations), 2)
    elev_max = round(max(elevations), 2)
    elev_min = round(min(elevations), 2)

    # Set the legend.
    color = color_palette[1]
    distance = int(subgraph.size(weight="length"))
    label = str(len(dest_nodes)) + " nodes, pipe distance (m) = " + str(distance)
    patch = mlines.Line2D([0], [0], color=color, marker='o', markersize=6, markerfacecolor=color, label=label)
    handles.append(patch)

    plt.legend(handles=handles, loc="upper left", prop={'size': 25})

    # Add the water tank node
    ax.scatter(g_attr.nodes[tank_node]['x'], g_attr.nodes[tank_node]['y'], c='black', s=175, marker='D')

    # Add the destination nodes
    for node in dest_nodes:
        color = color_palette[1]
        size = 45
        marker = 'o'
        ax.scatter(g_attr.nodes[node]['x'], g_attr.nodes[node]['y'], c=color, s=size, marker=marker)

    plt.show()
    if filename != None:
        fig.savefig(filename + '.pdf', format="PDF", bbox_inches='tight')



#############################################################################################
def print_solution_small_impr(Gdir, wwtp, dest_nodes, tank_node, subgraph, subgraph2, filename = None):
    
    g_attr = Gdir.copy()

    # Compute colors for route from WWTP to water tanks
    edge_colors = []
    edge_linewidth = []
    for u, v in g_attr.edges():
        edge_colors.append('#9c9c9c')
        edge_linewidth.append(0.5)

    # Only consider nodes inside this box.
    min_lat, max_lat = 41.97, 42.003
    min_lon, max_lon = 2.795, 2.83
    
    # Get a list of nodes to remove
    nodes_to_remove = [node for node,data in g_attr.nodes(data=True) if (data['y'] < min_lat or data['y'] > max_lat) or ((data['x'] < min_lon or data['x'] > max_lon))]
    
    # Remove the nodes outside the specified bounds
    g_attr.remove_nodes_from(nodes_to_remove)

    # Compute colors for each cluster
    edge_colors = []
    edge_linewidth = []
    for u, v in g_attr.edges():
        if subgraph.has_edge(u, v):
            edge_colors.append(color_palette[1])
            edge_linewidth.append(4)
        elif subgraph2.has_edge(u, v):
            edge_colors.append(color_palette[3])
            edge_linewidth.append(4)
        else:
            edge_colors.append('#9c9c9c')
            edge_linewidth.append(0.5)

    fig, ax = ox.plot_graph(g_attr, bgcolor='white', figsize=(20, 20), show=False, close=False,
                            edge_color=edge_colors, node_edgecolor='#9c9c9c', node_size=0,
                            edge_linewidth=edge_linewidth)

    # Prepare LEGEND
    handles, labels = ax.get_legend_handles_labels()
    handles.append(mlines.Line2D([0], [0], color='white', marker='D', markersize=8, markerfacecolor='black',
                                 label='Water tank node'))
    all_nodes = g_attr.nodes(data=True)

    # Obtain the nodes elevations.
    elevations = []
    for node in dest_nodes:
        if node in g_attr.nodes():
            elevations.append(all_nodes[node]['elevation'])
    elev_mean = round(sum(elevations) / len(elevations), 2)
    elev_max = round(max(elevations), 2)
    elev_min = round(min(elevations), 2)

    # Set the legend.
    color = color_palette[1]
    distance = int(subgraph.size(weight="length"))
    label = "Non-resilient: "+str(len(dest_nodes)) + " nodes, pipe distance (m) = " + str(distance)
    patch = mlines.Line2D([0], [0], color=color, marker='o', markersize=6, markerfacecolor=color, label=label)
    handles.append(patch)

    color = color_palette[3]
    distance = int(subgraph2.size(weight="length")) - int(subgraph.size(weight="length"))
    label = "Resilience-strenghtened: pipe distance (m) = " + str(distance)
    patch = mlines.Line2D([0], [0], color=color, marker='o', markersize=6, markerfacecolor=color, label=label)
    handles.append(patch)

    plt.legend(handles=handles, loc="upper left", prop={'size': 22})

    # Add the water tank node
    ax.scatter(g_attr.nodes[tank_node]['x'], g_attr.nodes[tank_node]['y'], c='black', s=175, marker='D')

    # Add the destination nodes
    for node in dest_nodes:
        color = color_palette[1]
        size = 45
        marker = 'o'
        ax.scatter(g_attr.nodes[node]['x'], g_attr.nodes[node]['y'], c=color, s=size, marker=marker)

    plt.show()
    if filename != None:
        fig.savefig(filename + '.pdf', format="PDF", bbox_inches='tight')

########################################################################################################
########################################################################################################
################################### FOLIUM NETWORK PLOTTING ###########################################
########################################################################################################
########################################################################################################

def plot_network_with_folium(G_original, G_result, origin, precomputed_data, to_check=[], filepath="result"):
    """
    Prints the optimal reclaimed water network obtained from some algorithm in an interactive HTML.
        
    Args:
        G_original (nx undirected graph): original city street graph.
        G_result (nx undirected graph): obtained reclaimed water network.
        filepath (string): path to store the html, by default "result.html".
        
    Returns:
        Generates the HTML file in the filesystem.
    """

    # Base graph: City streets in blue translucid color.
    m = ox.plot_graph_folium(nx.MultiDiGraph(G_original), weight=2, color="#73adff", opacity=0.4)
    
    # Resulting network graph: Reclaimed water network in opac purple. Including popup with edge lengths.
    m = ox.plot_graph_folium(nx.MultiDiGraph(G_result), popup_attribute="length", graph_map = m, weight=2, color="#a259ff")

    # Get critical edges.
    G_test = nx.Graph(G_result)
    G_critical = nx.Graph(G_result)
    for u,v in G_result.edges():
        G_test.remove_edge(u,v)
        if nx.is_connected(G_test):
            G_critical.remove_edge(u,v)
        G_test.add_edge(u,v)
    m = ox.plot_graph_folium(nx.MultiDiGraph(G_critical), graph_map = m, weight=2, color="#FF0000")
    
    # Add nodes in graph with different gradient color from red to green depending on their consumption (red = Low cons, green = High cons).
    list_cons = list(precomputed_data["n_cons"].values())
    q1 = np.quantile(list_cons, 0.25)
    q3 = np.quantile(list_cons, 0.75)
    iqr = q3-q1
    higher_fence = q3 + (1.5*iqr)
    for node, data in G_result.nodes(data = True):
        if node in precomputed_data["cons_nodes"]:
            p = data['consumption'] / higher_fence
            Green = str(255 * p)
            Red   = str(255 * (1-p))
            Blue  = str(0)
            if node in to_check:
                color_test = '#000000'
            else:
                color_test = '#888888'
            folium.Circle(location=(data['y'],data['x']),radius=2, color=color_test, fill=True, fill_opacity=1, popup=str(node)+". Consumption: "+str(data['consumption'])+" m3/day").add_to(m)
        if node == origin:
            # If the node is the WWTP, add it in black color.
            folium.Circle(location=(data['y'],data['x']),radius=5, color='black', fill=True, fill_opacity=1, popup=str(node)+". Consumption: "+str(data['consumption'])+" m3/day").add_to(m)

    m.save(filepath+".html")

def plot_network_with_folium_epanet(G_original, G_result, origin, precomputed_data, node_data, link_data, unsupplied_nodes, filepath="result_epanet"):
    """
    Prints the optimal reclaimed water network obtained from some algorithm in an interactive HTML.
        
    Args:
        G_original (nx undirected graph): original city street graph.
        G_result (nx undirected graph): obtained reclaimed water network.
        filepath (string): path to store the html, by default "result.html".
        
    Returns:
        Generates the HTML file in the filesystem.
    """

    # Base graph: City streets in blue translucid color.
    #m = ox.plot_graph_folium(nx.MultiDiGraph(G_original), weight=2, color="#73adff", opacity=0.4)

    # Velocity categories: 0-0.2, 0.2-0.4,0.4-0.6,0.6-1.2,+1.2.
    G_none = nx.Graph(G_result)
    G_0 = nx.Graph(G_result)
    G_02 = nx.Graph(G_result)
    G_04 = nx.Graph(G_result)
    G_06 = nx.Graph(G_result)
    G_12 = nx.Graph(G_result)
    for u,v in G_result.edges():
        if link_data[(u,v)]["velocity"] > 1.2:
            G_none.remove_edge(u,v)
            G_0.remove_edge(u,v)
            G_02.remove_edge(u,v)
            G_04.remove_edge(u,v)
            G_06.remove_edge(u,v)
        elif link_data[(u,v)]["velocity"] > 0.6:
            G_none.remove_edge(u,v)
            G_0.remove_edge(u,v)
            G_02.remove_edge(u,v)
            G_04.remove_edge(u,v)
            G_12.remove_edge(u,v)
        elif link_data[(u,v)]["velocity"] > 0.4:
            G_none.remove_edge(u,v)
            G_0.remove_edge(u,v)
            G_02.remove_edge(u,v)
            G_06.remove_edge(u,v)
            G_12.remove_edge(u,v)
        elif link_data[(u,v)]["velocity"] > 0.2:
            G_none.remove_edge(u,v)
            G_0.remove_edge(u,v)
            G_04.remove_edge(u,v)
            G_06.remove_edge(u,v)
            G_12.remove_edge(u,v)
        elif link_data[(u,v)]["velocity"] > 0:
            G_none.remove_edge(u,v)
            G_02.remove_edge(u,v)
            G_04.remove_edge(u,v)
            G_06.remove_edge(u,v)
            G_12.remove_edge(u,v)
        else:
            G_0.remove_edge(u,v)
            G_02.remove_edge(u,v)
            G_04.remove_edge(u,v)
            G_06.remove_edge(u,v)
            G_12.remove_edge(u,v)
            
    if G_none.number_of_edges() > 0:
        m = ox.plot_graph_folium(nx.MultiDiGraph(G_none), popup_attribute="popup_folium", weight=2, color="#000000")
    if G_0.number_of_edges() > 0 and G_none.number_of_edges() == 0:
        m = ox.plot_graph_folium(nx.MultiDiGraph(G_0), popup_attribute="popup_folium", weight=2, color="#e67c73")
    elif G_0.number_of_edges() > 0:
        m = ox.plot_graph_folium(nx.MultiDiGraph(G_0), popup_attribute="popup_folium", graph_map = m, weight=2, color="#e67c73")
    if G_02.number_of_edges() > 0:
        m = ox.plot_graph_folium(nx.MultiDiGraph(G_02), popup_attribute="popup_folium", graph_map = m, weight=2, color="#f7cb4d")
    if G_04.number_of_edges() > 0:
        m = ox.plot_graph_folium(nx.MultiDiGraph(G_04), popup_attribute="popup_folium", graph_map = m, weight=2, color="#41b375")
    if G_06.number_of_edges() > 0:
        m = ox.plot_graph_folium(nx.MultiDiGraph(G_06), popup_attribute="popup_folium", graph_map = m, weight=2, color="#7baaf7")
    if G_12.number_of_edges() > 0:
        m = ox.plot_graph_folium(nx.MultiDiGraph(G_12), popup_attribute="popup_folium", graph_map = m, weight=2, color="#ba67c8")

    # Add nodes in graph with different gradient color from red to green depending on their consumption (red = Low cons, green = High cons).
    list_cons = list(precomputed_data["n_cons"].values())
    q1 = np.quantile(list_cons, 0.25)
    q3 = np.quantile(list_cons, 0.75)
    iqr = q3-q1
    higher_fence = q3 + (1.5*iqr)
    for node, data in G_result.nodes(data = True):
        if node == origin:
            # If the node is the WWTP, add it in black color.
            folium.Circle(location=(data['y'],data['x']),radius=5, color='black', fill=True, fill_opacity=1, popup="Tank. Consumption: "+str(round(data['consumption'],2))+" m3/day").add_to(m)
        elif node in precomputed_data["cons_nodes"] and node not in unsupplied_nodes:
            p = data['consumption'] / higher_fence
            Green = str(255 * p)
            Red   = str(255 * (1-p))
            Blue  = str(0)
            folium.Circle(location=(data['y'],data['x']),radius=2, color='rgb('+Red+","+Green+","+Blue+')', fill=True, fill_opacity=1, popup=str(node)+". Consumption: "+str(round(data['consumption'],2))+" m3/day. Pressure: "+str(node_data[node]["pressure"])+ " m.").add_to(m)
        elif node in precomputed_data["cons_nodes"]:
            folium.Circle(location=(data['y'],data['x']),radius=2, color='black', fill=True, fill_opacity=1, popup=str(node)+". Not fully supplied: "+str(node_data[node]["supplied"])+"/"+str(round(data['consumption'],2))+" m3/day. Pressure: "+str(node_data[node]["pressure"])+ " m.").add_to(m)
    m.save(filepath+".html")

def plot_network_with_folium_cycles(G_original, G_result, cycles, filepath="result_cycles"):
    
    # Base graph: City streets in blue translucid color.
    #m = ox.plot_graph_folium(nx.MultiDiGraph(G_original), weight=2, color="#73adff", opacity=0.4)

    cycles = set([item for sublist in cycles for item in sublist])

    G_no = nx.Graph(G_result)
    G_yes = nx.Graph(G_result)
    for u,v in G_result.edges():
        if u in cycles and v in cycles:
            G_no.remove_edge(u,v)
        else:
            G_yes.remove_edge(u,v)
            
    if G_no.number_of_edges() > 0:
        m = ox.plot_graph_folium(nx.MultiDiGraph(G_no), weight=2, color="#000000")
    if G_yes.number_of_edges() > 0:
        m = ox.plot_graph_folium(nx.MultiDiGraph(G_yes), graph_map = m, weight=2, color="#ba67c8")

    # Add nodes in graph with different gradient color from red to green depending on their consumption (red = Low cons, green = High cons).
    for node, data in G_result.nodes(data = True):
        if node == origin:
            # If the node is the WWTP, add it in black color.
            folium.Circle(location=(data['y'],data['x']),radius=5, color='black', fill=True, fill_opacity=1, popup="WWTP. Consumption: "+str(data['consumption'])+" m3/day").add_to(m)
        else:
            folium.Circle(location=(data['y'],data['x']),radius=2, color='rgb(0,0,0)', fill=True, fill_opacity=1, popup=str(node)+". Consumption: "+str(data['consumption'])+" m3/day. Pressure: "+str(node_data[node]["pressure"])+ " m.").add_to(m)
    
    m.save(filepath+".html")
    
def plot_network_with_folium_hydraulic(G_original, G_result, origin, node_data, filepath="./EPANET-2.2/bin/interactive"):
    """
    Prints the optimal reclaimed water network after EPANET execution.
        
    Args:
        G_original (nx undirected graph): original city street graph.
        G_result (nx undirected graph): obtained reclaimed water network.
        filepath (string): path to store the html, by default "result.html".
        
    Returns:
        Generates the HTML file in the filesystem.
    """

    # Base graph: City streets in blue translucid color.
    m = ox.plot_graph_folium(nx.MultiDiGraph(G_original), weight=2, color="#73adff", opacity=0.4)
    
    # Resulting network graph: Reclaimed water network in opac purple. Including popup with edge lengths.
    m = ox.plot_graph_folium(nx.MultiDiGraph(G_result), popup_attribute="length", graph_map = m, weight=2, color="#a259ff")

    # Get critical edges.
    G_test = nx.Graph(G_result)
    G_critical = nx.Graph(G_result)
    for u,v in G_result.edges():
        G_test.remove_edge(u,v)
        if nx.is_connected(G_test):
            G_critical.remove_edge(u,v)
        G_test.add_edge(u,v)
    m = ox.plot_graph_folium(nx.MultiDiGraph(G_critical), graph_map = m, weight=2, color="#FF0000")
    
    for node, data in G_result.nodes(data = True):
        if node == origin:
            # If the node is the WWTP, add it in black color.
            folium.Circle(location=(data['y'],data['x']),radius=5, color='black', fill=True, fill_opacity=1, popup="Tank. Consumption: "+str(data['consumption'])+" m3/day").add_to(m)
        elif data["consumption"] > 0:
            if round(node_data[node]["supplied"],2) >= round(data["consumption"],2):
                folium.Circle(location=(data['y'],data['x']),radius=2, color='rgb(0,255,0)', fill=True, fill_opacity=1, popup="Consumption: "+str(data['consumption'])+" m3/day").add_to(m)
            else:
                folium.Circle(location=(data['y'],data['x']),radius=2, color='rgb(255,0,0)', fill=True, fill_opacity=1, popup=str(node)+". Not fully supplied: "+str(node_data[node]["supplied"])+"/"+str(data['consumption'])+" m3/day").add_to(m)

    m.save(filepath+".html")
    
def plot_network_with_folium_valves(G_original, G_result, origin, node_data, filepath="./EPANET-2.2/bin/valves"):
    """
    Prints the network in Folium with colors according to which edge has valves.
        
    Args:
        G_original (nx undirected graph): original city street graph.
        G_result (nx undirected graph): obtained reclaimed water network.
        filepath (string): path to store the html, by default "result.html".
        
    Returns:
        Generates the HTML file in the filesystem.
    """

    # Base graph: City streets in blue translucid color.
    m = ox.plot_graph_folium(nx.MultiDiGraph(G_original), weight=2, color="#73adff", opacity=0.4)
    
    # Resulting network graph: Reclaimed water network in opac purple. Including popup. 
    #  If the edge has valve, then print it in black.

    # Get critical edges.
    G_valve = nx.Graph(G_result)
    G_novalve = nx.Graph(G_result)
    for u,v,data in G_result.edges(data = True):
        if "valve" in data:
            G_novalve.remove_edge(u,v)
        else:
            G_valve.remove_edge(u,v)
            
    if G_valve.number_of_edges() > 0:
        m = ox.plot_graph_folium(nx.MultiDiGraph(G_valve), popup_attribute="popup_folium", weight=2, color="#0000FF")
    if G_novalve.number_of_edges() > 0:
        m = ox.plot_graph_folium(nx.MultiDiGraph(G_novalve), popup_attribute="popup_folium", graph_map = m, weight=2, color="#FF0000")
    
    for node, data in G_result.nodes(data = True):
        if node == origin:
            # If the node is the WWTP, add it in black color.
            folium.Circle(location=(data['y'],data['x']),radius=5, color='black', fill=True, fill_opacity=1, popup="Tank. Consumption: "+str(data['consumption'])+" m3/day").add_to(m)
        elif data["consumption"] > 0:
            if round(node_data[node]["supplied"],2) >= round(data["consumption"],2):
                folium.Circle(location=(data['y'],data['x']),radius=2, color='rgb(0,255,0)', fill=True, fill_opacity=1, popup="Consumption: "+str(data['consumption'])+" m3/day").add_to(m)
            else:
                folium.Circle(location=(data['y'],data['x']),radius=2, color='rgb(255,0,0)', fill=True, fill_opacity=1, popup=str(node)+". Not fully supplied: "+str(node_data[node]["supplied"])+"/"+str(data['consumption'])+" m3/day").add_to(m)

    m.save(filepath+".html")
