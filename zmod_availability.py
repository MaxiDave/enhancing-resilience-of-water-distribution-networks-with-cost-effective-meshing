########################################################################################################
########################################################################################################
################################### DELFT FENGHUA: AVAILAVILITY ########################################
########################################################################################################
########################################################################################################

import networkx as nx
import random
import numpy as np
import zmod_print
import matplotlib.pyplot as plt

# This function simply returns a list (s0,s1,...,sn) in pairs such that [(s0,s1),(s1,s2),...,(sn-1,sn)]
import zmod_pairwise

def availability(G,nodes_check,r,p,o,precomputed_data):
    """
    Returns the node_avg_availability, node_worst_availability, and network_availavility of a given network and parameters (TU Delft).
        
    Args:
        G (nx undirected graph): graph to evaluate.
        nodes_check (list or set): consumption nodes to evaluate availability.
        r (int): number of repetitions.
        p (double): probability of failure is 1-p.
        o (int): controller.
    Returns:
        Returns the node_avg_availability, node_worst_availability, and network_availavility of a given network and parameters (TU Delft).
    """
    
    node_realizations = {}
    for node in nodes_check:
        node_realizations[node] = 0
    network_availavility = 0
    unsuplied_water_array = []
    
    for i in range(r):
        # First, generate a new graph with the origin node.
        G_new = nx.Graph()
        G_new.add_node(o)

        # Then, for each edge in G, generate a random number and if < p, add edge to G_new.
        for origin,destination in G.edges():
            rand = random.random()
            if rand < p:
                G_new.add_edge(origin,destination)
        
        paths = nx.single_source_shortest_path(G_new, o)
        all_exist = True
        unsupplied_water = 0
        for node in nodes_check:
            if node in paths:
                node_realizations[node] += 1
            else:
                all_exist = False
                unsupplied_water += precomputed_data["n_cons"][node]
        if all_exist:
            network_availavility += 1
        unsuplied_water_array.append(unsupplied_water)
        
    node_realizations = [v/r for v in node_realizations.values()] 
    node_avg_availability = np.mean(node_realizations)
    node_worst_availability = min(node_realizations)
    network_availavility = network_availavility/r
    mean_unsupplied_water = np.mean(unsuplied_water_array)
    return node_avg_availability, node_worst_availability, network_availavility, mean_unsupplied_water

########################################################################################################
########################################################################################################
###################################### WEIGHTED AVAILAVILITY ###########################################
########################################################################################################
########################################################################################################

weights = {
    "age": 0.266,
    "diameter": 0.308,
    "length": 0.167,
    "wall_thickness": 0.068,
    "material": 0.191
}

new_weights = {
    "age": 0.105,
    "diameter": 0.122,
    "length": 0.066,
    "wall_thickness": 0.027,
    "material": 0.076
}

norm_dict = {
    "age": [100,67,33,0],
    "diameter": [560,250,90,0],
    "length": [200,100,50,0],
    "wall_thickness": [33.2,14.8,3.8,0],
    "material": [["HDPE"],["MDPE_black"],["MDPE_blue","GI","LDPE_black","AC"],["UPVC","DI"]]
}

def normalize_graph(G):    
    attrs = {}
    for u,v,data in G.edges(data=True):
        attrs_obj = {}
        attributes = ["diameter","age","length","wall_thickness"]
        for attribute in attributes:
            if data[attribute] > norm_dict[attribute][0]:
                attrs_obj["norm_"+attribute] = 1
            elif data[attribute] > norm_dict[attribute][1]:
                attrs_obj["norm_"+attribute] = 0.67
            elif data[attribute] > norm_dict[attribute][2]:
                attrs_obj["norm_"+attribute] = 0.33
            else:
                attrs_obj["norm_"+attribute] = 0
        #For the moment, we only consider "HDPE" as material.
        attrs_obj["norm_material"] = 1
        attrs[(u,v)] = attrs_obj
    nx.set_edge_attributes(G, attrs)
    return G

def new_normalize_graph(G):    
    attrs = {}
    for u,v,data in G.edges(data=True):
        attrs_obj = {}
        attributes = ["diameter","age","wall_thickness"]
        for attribute in attributes:
            if attribute != "wall_thickness":
                if data[attribute] > norm_dict[attribute][0]:
                    attrs_obj["norm_"+attribute] = 1
                elif data[attribute] > norm_dict[attribute][1]:
                    attrs_obj["norm_"+attribute] = 0.67
                elif data[attribute] > norm_dict[attribute][2]:
                    attrs_obj["norm_"+attribute] = 0.33
                else:
                    attrs_obj["norm_"+attribute] = 0
            else:
                if data[attribute] > norm_dict[attribute][0]:
                    attrs_obj["norm_"+attribute] = 0
                elif data[attribute] > norm_dict[attribute][1]:
                    attrs_obj["norm_"+attribute] = 0.33
                elif data[attribute] > norm_dict[attribute][2]:
                    attrs_obj["norm_"+attribute] = 0.67
                else:
                    attrs_obj["norm_"+attribute] = 1
        #For the moment, we only consider "HDPE" as material.
        attrs_obj["norm_material"] = 0
        # As we now take into account the length in "p_i", set "l" as 1.
        attrs_obj["norm_length"] = 1
        attrs[(u,v)] = attrs_obj
    nx.set_edge_attributes(G, attrs)
    return G

def get_probability(failure_rate,edge_data):
    pipe_related_weight = 0.396
    p_prob = (failure_rate/100)*(1-pipe_related_weight)
    relative_pipe = ((edge_data["norm_diameter"] * weights["diameter"]) + (edge_data["norm_length"] * weights["length"]) + (edge_data["norm_age"] * weights["age"]) + (edge_data["norm_wall_thickness"] * weights["wall_thickness"]) + (edge_data["norm_material"] * weights["material"]))
    p_pipe_related = (failure_rate/100)*pipe_related_weight*relative_pipe
    return 1 - (p_prob + p_pipe_related)

def new_get_probability(failure_rate,edge_data):
    pipe_related_weight = ((edge_data["norm_diameter"] * new_weights["diameter"]) + (edge_data["norm_length"] * new_weights["length"]) + (edge_data["norm_age"] * new_weights["age"]) + (edge_data["norm_wall_thickness"] * new_weights["wall_thickness"]) + (edge_data["norm_material"] * new_weights["material"]))
    weight_sum = pipe_related_weight + 0.413 + 0.191

    q = (0.4 * 1 * 24) / (24 * 365)
    max_month_unavailability = 1 - ((1 - q)**(edge_data["length"]/1000))
    
    return 1 - (max_month_unavailability * weight_sum)

# Function to find edges in normal or reverse until blocked by 'valve' attribute.
def find_edges_until_valve(G_dir, current_node, reverse=False, path=None):
    if path is None:
        path = []

    path.append(current_node)
    
    if len(G_dir.in_edges(current_node)) == 0:
        # Reached the starting point, return the path
        return path

    if reverse:
        neighbors = G_dir.predecessors(current_node)
    else:
        neighbors = G_dir.successors(current_node)
    for neighbor_node in neighbors:
        if reverse:
            edge_data = G_dir[neighbor_node][current_node]
        else:
            edge_data = G_dir[current_node][neighbor_node]
        if 'valve' in edge_data:
            # The path is blocked by an edge with 'valve' attribute
            path.append(neighbor_node)
            return path

        result = find_edges_until_valve(G_dir, neighbor_node, reverse, path.copy())

        if result:
            return result

    return None

def pipe_failure_map(G,result_epanet):
    """
    Returns the map keyed for each edge in G that represent in value which edges will fail if the specific edge fails.
        
    Args:
        G (nx undirected graph): graph to evaluate.
    """

    # First generate a directed graph from a network design based on EPANET results.
    G_dir = nx.DiGraph()
    epanet_edge_data = result_epanet["link_data"]
    new_to_original_dir = {}
    for s,d,data in G.edges(data = True):
        if (s,d) in epanet_edge_data and epanet_edge_data[(s,d)]["flow"] >= 0:
            new_to_original_dir[(s,d)] = (s,d)
            s_new = s
            d_new = d
        elif (s,d) in epanet_edge_data:
            new_to_original_dir[(d,s)] = (s,d)
            s_new = d
            d_new = s
        elif (d,s) in epanet_edge_data and epanet_edge_data[(d,s)]["flow"] >= 0:
            new_to_original_dir[(d,s)] = (s,d)
            s_new = d
            d_new = s
        else:
            new_to_original_dir[(s,d)] = (s,d)
            s_new = s
            d_new = d
        G_dir.add_edge(s_new,d_new,**data)

    # Now, for each edge on the graph, check if its removal will remove extra edges (due to valve location).
    failure_map = {}
    for s,d,data in G_dir.edges(data=True):
        if 'valve' in data:
            failure_map[new_to_original_dir[(s,d)]] = [new_to_original_dir[(s,d)]]
        else:
            failure_array = [new_to_original_dir[(s,d)]]
            in_path = find_edges_until_valve(G_dir, s, reverse=True)
            out_path = find_edges_until_valve(G_dir, d, reverse=False)
            if in_path != None:
                for in_s,in_d in zmod_pairwise.reverse_pairwise(in_path):
                    failure_array.append(new_to_original_dir[(in_s,in_d)])
            if out_path != None:
                for out_s,out_d in zmod_pairwise.pairwise(out_path):
                    failure_array.append(new_to_original_dir[(out_s,out_d)])
            failure_map[new_to_original_dir[(s,d)]] = failure_array

    return failure_map

def availability_weighted(G,precomputed_data,nodes_check,r,f,o,g_attr,result_epanet,filename=None):
    """
    Returns the node_avg_availability, node_worst_availability, and network_availavility of a given network and parameters (TU Delft).
        
    Args:
        G (nx undirected graph): graph to evaluate.
        nodes_check (list or set): consumption nodes to evaluate availability.
        r (int): number of repetitions.
        f (double): failure rate.
        o (int): controller.
    Returns:
        Returns the node_avg_availability, node_worst_availability, and network_availavility of a given network and parameters (TU Delft).
    """
    
    G = normalize_graph(G)
    failure_map = {}

    # For each edge of graph G, get the failure probability 'p'.
    edge_probabilities = {}
    for origin,destination,edge_data in G.edges(data=True):
        edge_probabilities[(origin,destination)] = get_probability(f,edge_data)

    pp = [1-p for p in edge_probabilities.values()]
    plt.boxplot(pp)
    plt.show()
    print("Pipe failure probabilities (Q1,Q2,Q3):",np.percentile(pp, 25),np.percentile(pp, 50),np.percentile(pp, 75))
    print("Pipe failure probabilities (min,max):",min(pp),max(pp))

    # Get the pipe failure map. 
    pf_map = pipe_failure_map(G,result_epanet)
    
    node_realizations = {}
    for node in nodes_check:
        node_realizations[node] = 0
    network_availavility = 0
    unsupplied_water_array = []
    
    for i in range(r):

        # First, copy the original graph.
        G_new = nx.Graph(G)

        # Then, for each edge in G, generate a random number and if > p, remove edge and associated in pipe failure map from G_new.
        edges_removed = []
        for origin,destination in G.edges():
            if (origin,destination) not in failure_map:
                failure_map[(origin,destination)] = 0
            rand = random.random()
            if rand >= edge_probabilities[(origin,destination)]:
                for (o,d) in pf_map[(origin,destination)]:
                    if (o,d) not in failure_map or failure_map[(o,d)] == 0:
                        failure_map[(o,d)] = 1
                    else:
                        failure_map[(o,d)] += 1
                    if G_new.has_edge(o,d):
                        G_new.remove_edge(o,d)
                        edges_removed.append((o,d))
        
        paths = nx.single_source_shortest_path(G_new, o)
        all_exist = True
        unsupplied_water = 0
        for node in nodes_check:
            if node in paths:
                node_realizations[node] += 1
            else:
                all_exist = False
                unsupplied_water += precomputed_data["n_cons"][node]
        if all_exist:
            network_availavility += 1
        else:
            unsupplied_water_array.append(unsupplied_water)
        
    node_realizations = [v/r for v in node_realizations.values()] 
    node_avg_availability = np.mean(node_realizations)
    node_worst_availability = min(node_realizations)
    network_availavility = network_availavility/r
    mean_unsupplied_water = np.mean(unsupplied_water_array)
    
    if filename:
        zmod_print.plot_network_with_folium_pipes(nx.Graph(g_attr), G, precomputed_data, failure_map, filepath=filename)
    
    return node_avg_availability, node_worst_availability, network_availavility, mean_unsupplied_water

def novalves_availability_weighted(G,precomputed_data,nodes_check,r,f,o,g_attr,result_epanet,filename=None):
    """
    Returns the node_avg_availability, node_worst_availability, and network_availavility of a given network and parameters (TU Delft).
        
    Args:
        G (nx undirected graph): graph to evaluate.
        nodes_check (list or set): consumption nodes to evaluate availability.
        r (int): number of repetitions.
        f (double): failure rate.
        o (int): controller.
    Returns:
        Returns the node_avg_availability, node_worst_availability, and network_availavility of a given network and parameters (TU Delft).
    """
    
    G = normalize_graph(G)
    failure_map = {}

    # For each edge of graph G, get the failure probability 'p'.
    edge_probabilities = {}
    for origin,destination,edge_data in G.edges(data=True):
        edge_probabilities[(origin,destination)] = get_probability(f,edge_data)

    # Get the pipe failure map. 
    pf_map = pipe_failure_map(G,result_epanet)
    
    node_realizations = {}
    for node in nodes_check:
        node_realizations[node] = 0
    network_availavility = 0
    
    for i in range(r):

        G_new = nx.Graph()
        G_new.add_node(o)

        # Then, for each edge in G, generate a random number and if < p, add edge to G_new.
        for origin,destination in G.edges():
            if (origin,destination) not in failure_map:
                failure_map[(origin,destination)] = 0
            rand = random.random()
            if rand < edge_probabilities[(origin,destination)]:
                G_new.add_edge(origin,destination)
            else:
                failure_map[(origin,destination)] += 1
        
        paths = nx.single_source_shortest_path(G_new, o)
        all_exist = True
        for node in nodes_check:
            if node in paths:
                node_realizations[node] += 1
            else:
                all_exist = False
        if all_exist:
            network_availavility += 1
        
    node_realizations = [v/r for v in node_realizations.values()] 
    node_avg_availability = np.mean(node_realizations)
    node_worst_availability = min(node_realizations)
    network_availavility = network_availavility/r
    
    if filename:
        zmod_print.plot_network_with_folium_pipes(nx.Graph(g_attr), G, precomputed_data, failure_map, filepath=filename)
    
    return node_avg_availability, node_worst_availability, network_availavility

def new_availability_weighted(G,precomputed_data,nodes_check,r,f,o,g_attr,result_epanet,filename=None):
    """
    Returns the node_avg_availability, node_worst_availability, and network_availavility of a given network and parameters (TU Delft).
        
    Args:
        G (nx undirected graph): graph to evaluate.
        nodes_check (list or set): consumption nodes to evaluate availability.
        r (int): number of repetitions.
        f (double): failure rate.
        o (int): controller.
    Returns:
        Returns the node_avg_availability, node_worst_availability, and network_availavility of a given network and parameters (TU Delft).
    """
    
    G = new_normalize_graph(G)
    G_new = nx.Graph(G)
    failure_map = {}

    # For each edge of graph G, get the failure probability 'p'.
    edge_probabilities = {}
    for origin,destination,edge_data in G.edges(data=True):
        edge_probabilities[(origin,destination)] = new_get_probability(f,edge_data)

    pp = [1-p for p in edge_probabilities.values()]
    #plt.boxplot(pp)
    #plt.show()
    print("Pipe failure probabilities (Q1,Q2,Q3):",np.percentile(pp, 25),np.percentile(pp, 50),np.percentile(pp, 75))
    print("Pipe failure probabilities (min,max):",min(pp),max(pp))

    # Get the pipe failure map. 
    pf_map = pipe_failure_map(G,result_epanet)
    
    node_realizations = {}
    for node in nodes_check:
        node_realizations[node] = 0
    network_availavility = 0
    unsupplied_water_array = []
    
    for i in range(r):

        # Then, for each edge in G, generate a random number and if > p, remove edge and associated in pipe failure map from G_new.
        edges_removed = []
        for origin,destination in G.edges():
            if (origin,destination) not in failure_map:
                failure_map[(origin,destination)] = 0
            rand = random.random()
            if rand >= edge_probabilities[(origin,destination)]:
                for (o,d) in pf_map[(origin,destination)]:
                    if (o,d) not in failure_map or failure_map[(o,d)] == 0:
                        failure_map[(o,d)] = 1
                    else:
                        failure_map[(o,d)] += 1
                    if G_new.has_edge(o,d):
                        G_new.remove_edge(o,d)
                        edges_removed.append((o,d))
        
        paths = nx.single_source_shortest_path(G_new, o)
        all_exist = True
        unsupplied_water = 0
        for node in nodes_check:
            if node in paths:
                node_realizations[node] += 1
            else:
                all_exist = False
                unsupplied_water += precomputed_data["n_cons"][node]
        if all_exist:
            network_availavility += 1
        else:
            unsupplied_water_array.append(unsupplied_water)

        # Recover removed edges.
        G_new.add_edges_from(edges_removed)
        
    node_realizations = [v/r for v in node_realizations.values()] 
    node_avg_availability = np.mean(node_realizations)
    node_worst_availability = min(node_realizations)
    network_availavility = network_availavility/r
    mean_unsupplied_water = np.mean(unsupplied_water_array)

    # Compute MTBF.
    MTBF = (-network_availavility*(1/365))/(network_availavility - 1)
    AFY = 1 / MTBF
    YAUW = AFY * mean_unsupplied_water
    
    
    if filename:
        zmod_print.plot_network_with_folium_pipes(nx.Graph(g_attr), G, precomputed_data, failure_map, filepath=filename)
    
    return node_avg_availability, node_worst_availability, network_availavility, mean_unsupplied_water, AFY, YAUW
