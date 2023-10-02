import networkx as nx
import time
import sys

import zmod_costs
import zmod_pairwise
import zmod_epanet

########################################################################################################
########################################################################################################
################################### BUDGETED ALGORITHM PRECOMPUTATIONS ###########################################
########################################################################################################
########################################################################################################

def precompute_data_lb_algorithms(G):
    """
    Given an initial city street graph with all the necessary information, precompute essential data for the LB algorithm.
    This improves A LOT the efficiency of the original LB algorithm of REWATnet, but also may require huge ammount of RAM memory in the system.
        
    Args:
        G (nx undirected graph): initial city street graph with all the necessary information.
    Returns:
        precomputed_data (object): Includes the following:
            "n_cons" (dict): Dictionary keyed by node that shows the consumption of reclaimed water demanded by the node.
            "cons_nodes" (set): Set of nodes that demand reclaimed water (no all nodes in graph G demand water).
            "shortest_paths" (dict): Precomputed shortest paths (list) for all node pairs (u,v) and (v,u) in G (dict of dicts).
            "shortest_paths_length" (dict): Precomputed shortest paths lengths (double) for all node pairs (u,v) and (v,u) in G (dict of dicts).
            "total_cons" (double): Total reclaimed water in m3/day demanded by G. 
            "edge_lengths" (dict): Dict keyed for each (u,v) and (v,u) edges in G with value the length of the specified edge. 
    """
    
    # First, get all the nodes that demand reused water. For each consumption node save its consumption in a dict.   
    n_cons = {}
    cons_nodes = set()
    for node, data in G.nodes(data = True):
        if data["consumption"] > 0:
            cons_nodes.add(node)
        n_cons[node] = data["consumption"]
    
    # Compute all the shortest paths in advance.
    shortest_paths = nx.shortest_path(G, weight='length')
    shortest_paths_length = dict(nx.shortest_path_length(G, weight='length'))
    
    # Length of all the edges (s/d and d/s).
    edge_lengths = {}
    for u,v,data in G.edges(data=True):
        edge_lengths[(u,v)] = data['length']
        edge_lengths[(v,u)] = data['length']
    
    # From all paths get extra data.
    total_cons = {}
    for origin in shortest_paths.keys():
        total_cons[origin] = {}
        for destination, path in shortest_paths[origin].items():
            if destination != origin:
                cons = 0
                for i in range(1,len(path)):
                    if n_cons[path[i]] > 0:
                        cons += n_cons[path[i]]
                total_cons[origin][destination] = cons
                
    return {
        "n_cons": n_cons, 
        "cons_nodes": cons_nodes, 
        "shortest_paths": shortest_paths, 
        "shortest_paths_length": shortest_paths_length, 
        "total_cons": total_cons, 
        "edge_lengths": edge_lengths
    }

########################################################################################################
########################################################################################################
################################### BUDGETED ALGORITHM V2 ###########################################
########################################################################################################
########################################################################################################
    
def lb_algorithm_v2(G, b, origin, precomputed_data, debug=False):
    """
    Returns the optimal reclaimed water network maximizing water served, minimizing costs without resilience in mind.
    It is v2, improves efficiency from the original LB algorithm from REWATnet v1.
        
    Args:
        G (nx undirected graph): original graph.
        b (int): maximum cost (in €) of the generated G_new optimal graph.
        origin (int): Origin node of the reuse network graph. Must be a node in G.
        precomputed_data (object): Data structure including essential precomputed data to make the algorithm more efficient. 
            Check func "precompute_data_lb_algorithms" for more info.
        debug (bool): If true, print messages to the console.
        
    Returns:
        G_new: Generated optimal graph.
        result_data (object): Data structure with some essential results.
            added_nodes (set): Nodes of G_new that have been added from G.
            computation_time (double): Seconds elapsed in the computation. 
    """
    
    start = time.time()
    stop = False
    cons_nodes_remaining = precomputed_data["cons_nodes"].copy()
    if origin in cons_nodes_remaining:
        cons_nodes_remaining.remove(origin)
    cons_nodes_added = set()
    added_nodes = set()
    added_nodes.add(origin)
    added_edges = set()
    
    remaining_budget = b
    
    G_new = nx.create_empty_copy(G)
    G_original = nx.Graph(G)
    
    while not stop and len(cons_nodes_remaining) > 0:
        
        candidates = []
        
        for cons_node in cons_nodes_remaining:
            min_path_length = float('inf')
            min_path = []
            min_path_total_cons = 0
            for node in added_nodes:
                if precomputed_data["shortest_paths_length"][node][cons_node] < min_path_length:
                    min_path_length = precomputed_data["shortest_paths_length"][node][cons_node]
                    min_path = precomputed_data["shortest_paths"][node][cons_node]
                    min_path_total_cons = precomputed_data["total_cons"][node][cons_node]
            
            # Treshold to not add a candidate if the minimum cost (in €) of the shortest path passes the budget.
            min_cost = zmod_costs.get_min_costs_diameter()*min_path_length
            if min_cost < remaining_budget:
                profit = min_path_total_cons/min_path_length
                candidates.append((min_path, profit, min_path_total_cons, min_path_length))
        
        candidates_sorted = sorted(candidates, key = lambda x: x[1], reverse = True)
        if len(candidates_sorted) > 0:
            n_can = 0
            for candidate in candidates_sorted:

                min_path = candidate[0]
                profit = candidate[1]
                total_cons = candidate[2]
                min_path_length = candidate[3]

                # From the shortest path get the consumption nodes and edge path.
                # Add the edges from the edge path that are not yet in the new graph:
                cons_nodes = set()
                new_edges_path = []
                edges_path = []
                for v, w in zmod_pairwise.pairwise(min_path):
                    edges_path.append((v,w))
                    if w in precomputed_data["cons_nodes"]:
                        cons_nodes.add(w)
                    if (v,w) not in added_edges:
                        G_new.add_edge(v,w)
                        new_edges_path.append((v,w))

                # Cost of the new network.
                cost, diameters_dict = zmod_costs.get_construction_costs(G_new, origin, cons_nodes_added.union(cons_nodes), total_cons, precomputed_data)
                n_can += 1
                if cost < b:
                    # Solution found: break the loop and add the new edges to 'added_edges'.
                    for edge in new_edges_path:
                        added_edges.add(edge)
                        added_edges.add((edge[1],edge[0]))
                    break
                else:
                    for edge in new_edges_path:
                        G_new.remove_edge(*edge)

            if cost < b:
                # Add nodes to "added_nodes" and remove them from "cons_nodes".
                for node in min_path:
                    added_nodes.add(node)
                    if node in cons_nodes_remaining:
                        cons_nodes_remaining.remove(node)
                        cons_nodes_added.add(node)

                remaining_budget = b - cost
            else:
                # No more candidates.
                if debug:
                    print(" - No more candidates available.")
                stop = True
            if debug:
                print(" - Candidates evaluated: (",n_can,"/",len(candidates_sorted),"). Current cost: (",int(cost),"/",b,"€).")
        else:
            # No more candidates.
            if debug:
                print(" - No more candidates available.")
            stop = True
            
    # The resulting network has all nodes in G, so it is necessary to remove unconnected nodes (extract biggest component). 
    G_new_full = nx.Graph(G_original)
    attrs = {}
    for u,v,data in G_original.edges(data=True):
        if not G_new.has_edge(u,v):
            G_new_full.remove_edge(u,v)
        else:
            attrs[(u,v)] = {"diameter": diameters_dict[(u,v)], "age": 0, "material": "PE100", "wall_thickness": zmod_costs.get_wall_thickness(diameters_dict[(u,v)])}
    nx.set_edge_attributes(G_new_full, attrs)
    Gcc = sorted(nx.connected_components(G_new_full), key=len, reverse=True)
    G_new_full = G_new_full.subgraph(Gcc[0])
    
    # Get the total consumption of new and original network.
    total_cons = 0
    for node in added_nodes:
        total_cons += precomputed_data["n_cons"][node]
    total_cons_original = sum(list(precomputed_data["n_cons"].values()))
    
    
    # Get the total network pipe distance (in m)
    pipe_distance = int(G_new_full.size(weight="length"))
        
    end = time.time()
    
    # Resulting data structure.
    result_data = {
        "added_nodes": added_nodes,
        "cons_nodes": cons_nodes_added,
        "total_cons": total_cons,
        "pipe_distance": pipe_distance,
        "percentage_served": round(total_cons / total_cons_original * 100, 1),
        "execution_time": end-start,
        "failure_rate": 100*(0.4*(pipe_distance/1000))/G_new_full.number_of_edges()
    }
    return G_new_full, result_data

def get_size(obj, seen=None):
    """Recursively finds size of objects"""
    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    # Important mark as seen *before* entering recursion to gracefully handle
    # self-referential objects
    seen.add(obj_id)
    if isinstance(obj, dict):
        size += sum([get_size(v, seen) for v in obj.values()])
        size += sum([get_size(k, seen) for k in obj.keys()])
    elif hasattr(obj, '__dict__'):
        size += get_size(obj.__dict__, seen)
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
        size += sum([get_size(i, seen) for i in obj])
    return size

#total = 0
#for key in precomputed_data.keys():
#    size_data = get_size(precomputed_data[key])
#    print(key, size_data/1000/1000) 
#    total += (size_data/1000/1000) 
#print("Total:",total)

########################################################################################################
########################################################################################################
################### OLD LB ALGORITHM, BUT EFFICIENT AND HYDRAULICAL ####################################
########################################################################################################
########################################################################################################

def lb_algorithm_v1_efficient_hydro(G, b, origin, precomputed_data, debug=False):
    """
    Returns the optimal reclaimed water network maximizing water served, minimizing costs without resilience in mind.
        
    Args:
        G (nx undirected graph): original graph.
        b (int): maximum cost (in €) of the generated G_new optimal graph.
        origin (int): Origin node of the reuse network graph. Must be a node in G.
        precomputed_data (object): Data structure including essential precomputed data to make the algorithm more efficient. 
            Check func "precompute_data_lb_algorithms" for more info.
        debug (bool): If true, print messages to the console.
        
    Returns:
        G_new: Generated optimal graph.
        result_data (object): Data structure with some essential results.
            added_nodes (set): Nodes of G_new that have been added from G.
            computation_time (double): Seconds elapsed in the computation. 
    """
    
    start = time.time()
    stop = False
    cons_nodes_remaining = precomputed_data["cons_nodes"].copy()
    if origin in cons_nodes_remaining:
        cons_nodes_remaining.remove(origin)
    cons_nodes_added = set()
    added_nodes = set()
    added_nodes.add(origin)
    added_edges = set()
    
    remaining_budget = b
    
    G_new = nx.create_empty_copy(G)
    G_original = nx.Graph(G)
    G_connectivity_check = nx.Graph(G)
    
    # Check if disconnecting an edge disconnects the graph.
    connect_dict = {}
    for u,v in G_connectivity_check.edges():
        G_connectivity_check.remove_edge(u,v)
        if nx.is_connected(G_connectivity_check):
            connect_dict[(u,v)] = True
            connect_dict[(v,u)] = True
        else:
            connect_dict[(u,v)] = False
            connect_dict[(v,u)] = False
        G_connectivity_check.add_edge(u,v)
    
    while not stop and len(cons_nodes_remaining) > 0:
        
        candidates = []
        
        for cons_node in cons_nodes_remaining:
            min_path_length = float('inf')
            min_path = []
            min_path_total_cons = 0
            for node in added_nodes:
                if precomputed_data["shortest_paths_length"][node][cons_node] < min_path_length:
                    min_path_length = precomputed_data["shortest_paths_length"][node][cons_node]
                    min_path = precomputed_data["shortest_paths"][node][cons_node]
                    min_path_total_cons = precomputed_data["total_cons"][node][cons_node]
            
            # Treshold to not add a candidate if the minimum cost (in €) of the shortest path passes the budget.
            min_cost = zmod_costs.get_min_costs_diameter()*min_path_length
            if min_cost < remaining_budget:
                profit = min_path_total_cons/min_path_length
                candidates.append((min_path, profit, min_path_total_cons, min_path_length))
        
        candidates_sorted = sorted(candidates, key = lambda x: x[1], reverse = True)
        if len(candidates_sorted) > 0:
            n_can = 0
            for candidate in candidates_sorted:

                min_path = candidate[0]
                profit = candidate[1]
                total_cons = candidate[2]
                min_path_length = candidate[3]
                
                # From the shortest path get the consumption nodes and edge path.
                # Add the edges from the edge path that are not yet in the new graph:
                cons_nodes = set()
                new_edges_path = []
                edges_path = []
                for v, w in zmod_pairwise.pairwise(min_path):
                    if connect_dict[(v,w)]:
                        edges_path.append((v,w))
                    if w in precomputed_data["cons_nodes"]:
                        cons_nodes.add(w)
                    if (v,w) not in added_edges:
                        G_new.add_edge(v,w)
                        new_edges_path.append((v,w))

                # Cost of the new network. Try to compute EPANET to validate hydraulically feasible.
                # If not (detected reduction in demand) try to variate speed.
                min_speed = 0.6
                max_speed = 1
                success = False
                while not success and min_speed >= 0.4:
                    test_graph, cost, t_capacity = zmod_costs.diameter_selection_and_cost_v2(G_new, origin, precomputed_data, total_cons, min_speed, max_speed)
                    test_graph.remove_nodes_from(list(nx.isolates(test_graph)))
                    node_data, link_data, result_data = zmod_epanet.compute_epanet(test_graph, t_capacity, origin)
                    success = result_data["success"]
                    min_speed -= 0.05
                
                n_can += 1
                if cost < b:
                    # Solution found: break the loop and add the new edges to 'added_edges'.
                    #  Also store EPANET result.
                    epanet_result = {
                        "node_data": node_data, 
                        "link_data": link_data, 
                        "result_data": result_data
                    }
                    for edge in new_edges_path:
                        added_edges.add(edge)
                        added_edges.add((edge[1],edge[0]))
                    break
                else:
                    for edge in new_edges_path:
                        if G_new.has_edge(*edge):
                            G_new.remove_edge(*edge)

            if cost < b:
                # Add nodes to "added_nodes" and remove them from "cons_nodes".
                for node in min_path:
                    added_nodes.add(node)
                    if node in cons_nodes_remaining:
                        cons_nodes_remaining.remove(node)
                        cons_nodes_added.add(node)

                remaining_budget = b - cost
            else:
                # No more candidates.
                if debug:
                    print(" - No more candidates available.")
                stop = True
            if debug:
                print(" - Candidates evaluated: (",n_can,"/",len(candidates_sorted),"). Current cost: (",int(cost),"/",b,"€). 2K =",second_path)
        else:
            # No more candidates.
            if debug:
                print(" - No more candidates available.")
            stop = True
            
    # The resulting network has all nodes in G, so it is necessary to remove unconnected nodes (extract biggest component). 
    G_new_full = nx.Graph(G_original)
    attrs = {}
    for u,v,data in G_original.edges(data=True):
        if not G_new.has_edge(u,v):
            G_new_full.remove_edge(u,v)
        else:
            attrs[(u,v)] = {"flow": test_graph[u][v]["flow"], "diameter": test_graph[u][v]["diameter"], "age": 0, "material": "PE100", "wall_thickness": zmod_costs.get_wall_thickness(test_graph[u][v]["diameter"])}
            if "valve" in test_graph[u][v]:
                attrs[(u,v)]["valve"] = test_graph[u][v]["valve"]
    nx.set_edge_attributes(G_new_full, attrs)
    Gcc = sorted(nx.connected_components(G_new_full), key=len, reverse=True)
    G_new_full = G_new_full.subgraph(Gcc[0])
    
    # Get the total consumption of new and original network.
    total_cons = 0
    for node in added_nodes:
        total_cons += precomputed_data["n_cons"][node]
    total_cons_original = sum(list(precomputed_data["n_cons"].values()))
    
    
    # Get the total network pipe distance (in m)
    pipe_distance = int(G_new_full.size(weight="length"))
        
    end = time.time()
    
    # Resulting data structure.
    result_data = {
        "added_nodes": added_nodes,
        "cons_nodes": cons_nodes_added,
        "total_cons": total_cons,
        "pipe_distance": pipe_distance,
        "percentage_served": round(total_cons / total_cons_original * 100, 1),
        "execution_time": end-start,
        "failure_rate": 100*((0.4/12)*(pipe_distance/1000))/G_new_full.number_of_edges(),
        "tank_capacity": t_capacity
    }
    return G_new_full, result_data, epanet_result

########################################################################################################
########################################################################################################
################################### BUDGETED ALGORITHM RESIL ###########################################
########################################################################################################
########################################################################################################
    
def lbr_algorithm_old(G, b, origin, precomputed_data, debug=False):
    """
    Returns the optimal reclaimed water network maximizing water served, minimizing costs with resilience in mind, 
    trying to achieve a K=2 edge connectivity.
        
    Args:
        G (nx undirected graph): original graph.
        b (int): maximum cost (in €) of the generated G_new optimal graph.
        origin (int): Origin node of the reuse network graph. Must be a node in G.
        precomputed_data (object): Data structure including essential precomputed data to make the algorithm more efficient. 
            Check func "precompute_data_lb_algorithms" for more info.
        debug (bool): If true, print messages to the console.
        
    Returns:
        G_new: Generated optimal graph.
        result_data (object): Data structure with some essential results.
            added_nodes (set): Nodes of G_new that have been added from G.
            computation_time (double): Seconds elapsed in the computation. 
    """
    
    start = time.time()
    stop = False
    cons_nodes_remaining = precomputed_data["cons_nodes"].copy()
    if origin in cons_nodes_remaining:
        cons_nodes_remaining.remove(origin)
    cons_nodes_added = set()
    added_nodes = set()
    added_nodes.add(origin)
    added_edges = set()
    
    remaining_budget = b
    
    G_new = nx.create_empty_copy(G)
    G_original = nx.Graph(G)
    G_connectivity_check = nx.Graph(G)
    
    # Check if disconnecting an edge disconnects the graph.
    connect_dict = {}
    for u,v in G_connectivity_check.edges():
        G_connectivity_check.remove_edge(u,v)
        if nx.is_connected(G_connectivity_check):
            connect_dict[(u,v)] = True
            connect_dict[(v,u)] = True
        else:
            connect_dict[(u,v)] = False
            connect_dict[(v,u)] = False
        G_connectivity_check.add_edge(u,v)
    
    while not stop and len(cons_nodes_remaining) > 0:
        
        candidates = []
        
        for cons_node in cons_nodes_remaining:
            min_path_length = float('inf')
            min_path = []
            min_path_total_cons = 0
            for node in added_nodes:
                if precomputed_data["shortest_paths_length"][node][cons_node] < min_path_length:
                    min_path_length = precomputed_data["shortest_paths_length"][node][cons_node]
                    min_path = precomputed_data["shortest_paths"][node][cons_node]
                    min_path_total_cons = precomputed_data["total_cons"][node][cons_node]
            
            # Treshold to not add a candidate if the minimum cost (in €) of the shortest path passes the budget.
            min_cost = zmod_costs.get_min_costs_diameter()*min_path_length
            if min_cost < remaining_budget:
                profit = min_path_total_cons/(min_path_length*2)
                candidates.append((min_path, profit, min_path_total_cons, min_path_length))
        
        candidates_sorted = sorted(candidates, key = lambda x: x[1], reverse = True)
        if len(candidates_sorted) > 0:
            n_can = 0
            for candidate in candidates_sorted:

                min_path = candidate[0]
                profit = candidate[1]
                total_cons = candidate[2]
                min_path_length = candidate[3]
                
                # From the shortest path get the consumption nodes and edge path.
                # Add the edges from the edge path that are not yet in the new graph:
                cons_nodes = set()
                new_edges_path = []
                edges_path = []
                for v, w in zmod_pairwise.pairwise(min_path):
                    if connect_dict[(v,w)]:
                        edges_path.append((v,w))
                    if w in precomputed_data["cons_nodes"]:
                        cons_nodes.add(w)
                    if (v,w) not in added_edges:
                        G_new.add_edge(v,w)
                        new_edges_path.append((v,w))

                # Recompute a second shortest path without the original one to add resilience (only if still the graph is connected).
                G.remove_edges_from(edges_path)

                try:
                    second_path = True
                    new_cons_nodes_path = set()
                    new_shortest_path = nx.shortest_path(G, min_path[0], min_path[len(min_path)-1], weight='length')
                    for i in range(1,len(new_shortest_path)):
                        if precomputed_data["n_cons"][new_shortest_path[i]] > 0:
                            new_cons_nodes_path.add(new_shortest_path[i])
                            cons_nodes.add(new_shortest_path[i])
                            total_cons += precomputed_data["n_cons"][new_shortest_path[i]]
                        if (new_shortest_path[i-1],new_shortest_path[i]) not in added_edges:
                            new_edges_path.append((new_shortest_path[i-1],new_shortest_path[i]))
                            G_new.add_edge(new_shortest_path[i-1],new_shortest_path[i])
                except nx.NetworkXNoPath:
                    second_path = False
                    new_shortest_path = []
                    pass

                # Re-add the original shortest path to the original network.
                G.add_edges_from(edges_path)

                # Cost of the new network.
                cost, diameters_dict, t_capacity = zmod_costs.get_construction_costs_v2(G_new, origin, cons_nodes_added.union(cons_nodes), total_cons, precomputed_data)
                n_can += 1
                if cost < b:
                    # Solution found: break the loop and add the new edges to 'added_edges'.
                    for edge in new_edges_path:
                        added_edges.add(edge)
                        added_edges.add((edge[1],edge[0]))
                    break
                else:
                    for edge in new_edges_path:
                        if G_new.has_edge(*edge):
                            G_new.remove_edge(*edge)

            if cost < b:
                # Add nodes to "added_nodes" and remove them from "cons_nodes".
                for node in new_shortest_path:
                    added_nodes.add(node)
                    if node in cons_nodes_remaining:
                        cons_nodes_remaining.remove(node)
                        cons_nodes_added.add(node)
                for node in min_path:
                    added_nodes.add(node)
                    if node in cons_nodes_remaining:
                        cons_nodes_remaining.remove(node)
                        cons_nodes_added.add(node)

                remaining_budget = b - cost
            else:
                # No more candidates.
                if debug:
                    print(" - No more candidates available.")
                stop = True
            if debug:
                print(" - Candidates evaluated: (",n_can,"/",len(candidates_sorted),"). Current cost: (",int(cost),"/",b,"€). 2K =",second_path)
        else:
            # No more candidates.
            if debug:
                print(" - No more candidates available.")
            stop = True
            
    # The resulting network has all nodes in G, so it is necessary to remove unconnected nodes (extract biggest component). 
    G_new_full = nx.Graph(G_original)
    attrs = {}
    for u,v,data in G_original.edges(data=True):
        if not G_new.has_edge(u,v):
            G_new_full.remove_edge(u,v)
        else:
            attrs[(u,v)] = {"diameter": diameters_dict[(u,v)], "age": 0, "material": "PE100", "wall_thickness": zmod_costs.get_wall_thickness(diameters_dict[(u,v)])}
    nx.set_edge_attributes(G_new_full, attrs)
    Gcc = sorted(nx.connected_components(G_new_full), key=len, reverse=True)
    G_new_full = G_new_full.subgraph(Gcc[0])
    
    # Get the total consumption of new and original network.
    total_cons = 0
    for node in added_nodes:
        total_cons += precomputed_data["n_cons"][node]
    total_cons_original = sum(list(precomputed_data["n_cons"].values()))
    
    
    # Get the total network pipe distance (in m)
    pipe_distance = int(G_new_full.size(weight="length"))
        
    end = time.time()
    
    # Resulting data structure.
    result_data = {
        "added_nodes": added_nodes,
        "cons_nodes": cons_nodes_added,
        "total_cons": total_cons,
        "pipe_distance": pipe_distance,
        "percentage_served": round(total_cons / total_cons_original * 100, 1),
        "execution_time": end-start,
        "failure_rate": 100*((0.4/12)*(pipe_distance/1000))/G_new_full.number_of_edges(),
        "tank_capacity": t_capacity
    }
    return G_new_full, result_data

########################################################################################################
########################################################################################################
################################### BUDGETED ALGORITHM RESIL ###########################################
########################################################################################################
########################################################################################################
def lbr_algorithm_hydraulic(G, b, origin, precomputed_data, debug=False):
    """
    Returns the optimal reclaimed water network maximizing water served, minimizing costs with resilience in mind, 
    trying to achieve a K=2 edge connectivity, and ensuring hydraulical feasibility.
        
    Args:
        G (nx undirected graph): original graph.
        b (int): maximum cost (in €) of the generated G_new optimal graph.
        origin (int): Origin node of the reuse network graph. Must be a node in G.
        precomputed_data (object): Data structure including essential precomputed data to make the algorithm more efficient. 
            Check func "precompute_data_lb_algorithms" for more info.
        debug (bool): If true, print messages to the console.
        
    Returns:
        G_new: Generated optimal graph.
        result_data (object): Data structure with some essential results.
            added_nodes (set): Nodes of G_new that have been added from G.
            computation_time (double): Seconds elapsed in the computation. 
    """
    
    start = time.time()
    stop = False
    cons_nodes_remaining = precomputed_data["cons_nodes"].copy()
    if origin in cons_nodes_remaining:
        cons_nodes_remaining.remove(origin)
    cons_nodes_added = set()
    added_nodes = set()
    added_nodes.add(origin)
    added_edges = set()
    
    remaining_budget = b
    
    G_new = nx.create_empty_copy(G)
    G_original = nx.Graph(G)
    G_connectivity_check = nx.Graph(G)
    
    # Check if disconnecting an edge disconnects the graph.
    connect_dict = {}
    for u,v in G_connectivity_check.edges():
        G_connectivity_check.remove_edge(u,v)
        if nx.is_connected(G_connectivity_check):
            connect_dict[(u,v)] = True
            connect_dict[(v,u)] = True
        else:
            connect_dict[(u,v)] = False
            connect_dict[(v,u)] = False
        G_connectivity_check.add_edge(u,v)
    
    while not stop and len(cons_nodes_remaining) > 0:
        
        candidates = []
        
        for cons_node in cons_nodes_remaining:
            min_path_length = float('inf')
            min_path = []
            min_path_total_cons = 0
            for node in added_nodes:
                if precomputed_data["shortest_paths_length"][node][cons_node] < min_path_length:
                    min_path_length = precomputed_data["shortest_paths_length"][node][cons_node]
                    min_path = precomputed_data["shortest_paths"][node][cons_node]
                    min_path_total_cons = precomputed_data["total_cons"][node][cons_node]
            
            # Treshold to not add a candidate if the minimum cost (in €) of the shortest path passes the budget.
            min_cost = zmod_costs.get_min_costs_diameter()*min_path_length
            if min_cost < remaining_budget:
                profit = min_path_total_cons/(min_path_length*2)
                candidates.append((min_path, profit, min_path_total_cons, min_path_length))
        
        candidates_sorted = sorted(candidates, key = lambda x: x[1], reverse = True)
        if len(candidates_sorted) > 0:
            n_can = 0
            for candidate in candidates_sorted:

                min_path = candidate[0]
                profit = candidate[1]
                total_cons = candidate[2]
                min_path_length = candidate[3]
                
                # From the shortest path get the consumption nodes and edge path.
                # Add the edges from the edge path that are not yet in the new graph:
                cons_nodes = set()
                new_edges_path = []
                edges_path = []
                for v, w in zmod_pairwise.pairwise(min_path):
                    if connect_dict[(v,w)]:
                        edges_path.append((v,w))
                    if w in precomputed_data["cons_nodes"]:
                        cons_nodes.add(w)
                    if (v,w) not in added_edges:
                        G_new.add_edge(v,w)
                        new_edges_path.append((v,w))

                # Recompute a second shortest path without the original one to add resilience (only if still the graph is connected).
                G.remove_edges_from(edges_path)

                try:
                    second_path = True
                    new_cons_nodes_path = set()
                    new_shortest_path = nx.shortest_path(G, min_path[0], min_path[len(min_path)-1], weight='length')
                    for i in range(1,len(new_shortest_path)):
                        if precomputed_data["n_cons"][new_shortest_path[i]] > 0:
                            new_cons_nodes_path.add(new_shortest_path[i])
                            cons_nodes.add(new_shortest_path[i])
                            total_cons += precomputed_data["n_cons"][new_shortest_path[i]]
                        if (new_shortest_path[i-1],new_shortest_path[i]) not in added_edges:
                            new_edges_path.append((new_shortest_path[i-1],new_shortest_path[i]))
                            G_new.add_edge(new_shortest_path[i-1],new_shortest_path[i])
                except nx.NetworkXNoPath:
                    print(" - NO PATH!")
                    second_path = False
                    new_shortest_path = []
                    pass

                # Re-add the original shortest path to the original network.
                G.add_edges_from(edges_path)

                # Cost of the new network. Try to compute EPANET to validate hydraulically feasible.
                # If not (detected reduction in demand) try to variate speed.
                min_speed = 0.6
                max_speed = 1
                success = False
                while not success and min_speed >= 0.4:
                    test_graph, cost, t_capacity = zmod_costs.diameter_selection_and_cost_v2(G_new, origin, precomputed_data, total_cons, min_speed, max_speed)
                    test_graph.remove_nodes_from(list(nx.isolates(test_graph)))
                    node_data, link_data, result_data = zmod_epanet.compute_epanet(test_graph, t_capacity, origin)
                    success = result_data["success"]
                    min_speed -= 0.05
                
                n_can += 1
                if cost < b:
                    # Solution found: break the loop and add the new edges to 'added_edges'.
                    #  Also store EPANET result.
                    epanet_result = {
                        "node_data": node_data, 
                        "link_data": link_data, 
                        "result_data": result_data
                    }
                    for edge in new_edges_path:
                        added_edges.add(edge)
                        added_edges.add((edge[1],edge[0]))
                    break
                else:
                    for edge in new_edges_path:
                        if G_new.has_edge(*edge):
                            G_new.remove_edge(*edge)

            if cost < b:
                # Add nodes to "added_nodes" and remove them from "cons_nodes".
                for node in new_shortest_path:
                    added_nodes.add(node)
                    if node in cons_nodes_remaining:
                        cons_nodes_remaining.remove(node)
                        cons_nodes_added.add(node)
                for node in min_path:
                    added_nodes.add(node)
                    if node in cons_nodes_remaining:
                        cons_nodes_remaining.remove(node)
                        cons_nodes_added.add(node)

                remaining_budget = b - cost
            else:
                # No more candidates.
                if debug:
                    print(" - No more candidates available.")
                stop = True
            if debug:
                print(" - Candidates evaluated: (",n_can,"/",len(candidates_sorted),"). Current cost: (",int(cost),"/",b,"€). 2K =",second_path)
        else:
            # No more candidates.
            if debug:
                print(" - No more candidates available.")
            stop = True
            
    # The resulting network has all nodes in G, so it is necessary to remove unconnected nodes (extract biggest component). 
    G_new_full = nx.Graph(G_original)
    attrs = {}
    for u,v,data in G_original.edges(data=True):
        if not G_new.has_edge(u,v):
            G_new_full.remove_edge(u,v)
        else:
            attrs[(u,v)] = {"flow": test_graph[u][v]["flow"], "diameter": test_graph[u][v]["diameter"], "age": 0, "material": "PE100", "wall_thickness": zmod_costs.get_wall_thickness(test_graph[u][v]["diameter"])}
            if "valve" in test_graph[u][v]:
                attrs[(u,v)]["valve"] = test_graph[u][v]["valve"]
    nx.set_edge_attributes(G_new_full, attrs)
    Gcc = sorted(nx.connected_components(G_new_full), key=len, reverse=True)
    G_new_full = G_new_full.subgraph(Gcc[0])
    
    # Get the total consumption of new and original network.
    total_cons = 0
    for node in added_nodes:
        total_cons += precomputed_data["n_cons"][node]
    total_cons_original = sum(list(precomputed_data["n_cons"].values()))
    
    
    # Get the total network pipe distance (in m)
    pipe_distance = int(G_new_full.size(weight="length"))
        
    end = time.time()
    
    # Resulting data structure.
    result_data = {
        "added_nodes": added_nodes,
        "cons_nodes": cons_nodes_added,
        "total_cons": total_cons,
        "pipe_distance": pipe_distance,
        "percentage_served": round(total_cons / total_cons_original * 100, 1),
        "execution_time": end-start,
        "failure_rate": 100*((0.4/12)*(pipe_distance/1000))/G_new_full.number_of_edges(),
        "tank_capacity": t_capacity
    }
    return G_new_full, result_data, epanet_result

########################################################################################################
########################################################################################################
################################### IMPROVE NETWORK RESILIEN ###########################################
########################################################################################################
########################################################################################################
    
def improve_resilience(G, to_improve, b, origin, precomputed_data, total_cons, debug=False):
    """
    Improves the resilience of an existing network "to_improve" with a limited budget in mind.
    Performance indicator for candidates: Meshedness coeficcient.
        
    Args:
        G (nx undirected graph): original graph.
        b (int): maximum cost (in €) of the generated G_new optimal graph.
        origin (int): Origin node of the reuse network graph. Must be a node in G.
        precomputed_data (object): Data structure including essential precomputed data to make the algorithm more efficient. 
            Check func "precompute_data_algorithms" for more info.
        debug (bool): If true, print messages to the console.
        
    Returns:
        G_new: Generated optimal graph.
        result_data (object): Data structure with some essential results.
            added_nodes (set): Nodes of G_new that have been added from G.
            computation_time (double): Seconds elapsed in the computation. 
    """

    start = time.time()
    stop = False
    cons_nodes_remaining = list(to_improve.nodes())
    if origin in cons_nodes_remaining:
        cons_nodes_remaining.remove(origin)
    cons_nodes_added = set()
    new_pipes = set()
    
    remaining_budget = b
    
    G_original = nx.Graph(G)
    
    while not stop and len(cons_nodes_remaining) > 0:
        
        candidates = []
        
        for cons_node in cons_nodes_remaining:
            min_path = nx.shortest_path(to_improve, source=origin, target=cons_node, weight='length')
            edges_path = []
            accum_cons = 0
            for v, w in zmod_pairwise.pairwise(min_path):
                G.remove_edge(v,w)
                if not nx.is_connected(G):
                    G.add_edge(v,w)
                else: 
                    edges_path.append((v,w))
                if w in precomputed_data["cons_nodes"]:
                    accum_cons += precomputed_data["n_cons"][w]

            alt_path = nx.shortest_path(G, min_path[0], min_path[len(min_path)-1], weight='length')
            alt_path_length = nx.shortest_path_length(G, min_path[0], min_path[len(min_path)-1], weight='length')
            
            # Re-add the original shortest path to the original network.
            G.add_edges_from(edges_path)
            
            # Treshold to not add a candidate if the minimum cost (in €) of the shortest path passes the budget.
            min_cost = zmod_costs.get_min_costs_diameter()*alt_path_length
            if min_cost < remaining_budget:
                profit = accum_cons/alt_path_length
                candidates.append((min_path,alt_path, profit, accum_cons, alt_path_length))
        
        candidates_sorted = sorted(candidates, key = lambda x: x[1], reverse = True)
        if len(candidates_sorted) > 0:
            n_can = 0
            for candidate in candidates_sorted:

                min_path = candidate[0]
                alt_path = candidate[1]
                profit = candidate[2]
                accum_cons = candidate[3]
                alt_path_length = candidate[4]

                edges_to_add = [] 
                for v, w in zmod_pairwise.pairwise(alt_path):
                    if not to_improve.has_node(v):
                        to_improve.add_node(v, **G.nodes[v])
                    elif not to_improve.has_node(w):
                        to_improve.add_node(w, **G.nodes[w])
                    if not to_improve.has_edge(v,w):
                        edges_to_add.append((v,w))
                to_improve.add_edges_from(edges_to_add)

                # Cost of the new network. Try to compute EPANET to validate hydraulically feasible.
                # If not (detected reduction in demand) try to variate speed.
                min_speed = 0.6
                max_speed = 1
                success = False
                while not success and min_speed >= 0.4:
                    test_graph, cost, t_capacity = zmod_costs.diameter_selection_and_cost_v2_improvement(nx.Graph(to_improve), origin, precomputed_data, total_cons, min_speed, max_speed)
                    test_graph.remove_nodes_from(list(nx.isolates(test_graph)))
                    node_data, link_data, result_data = zmod_epanet.compute_epanet(test_graph, t_capacity, origin)
                    success = result_data["success"]
                    min_speed -= 0.05
                
                n_can += 1
                if cost < b:
                    # Solution found: break the loop'.
                    for edge in edges_to_add:
                        new_pipes.add((v,w))
                    #  Also store EPANET result.
                    epanet_result = {
                        "node_data": node_data, 
                        "link_data": link_data, 
                        "result_data": result_data
                    }
                    break
                else:
                    to_improve.remove_edges_from(edges_to_add)
                    isolated_nodes = list(nx.isolates(to_improve))
                    to_improve.remove_nodes_from(isolated_nodes)

            if cost < b:
                # Add nodes to "added_nodes" and remove them from "cons_nodes".
                for node in min_path:
                    if node in cons_nodes_remaining:
                        cons_nodes_remaining.remove(node)
                for node in alt_path:
                    if node in cons_nodes_remaining:
                        cons_nodes_remaining.remove(node)
                #cons_nodes_remaining.remove(min_path[len(min_path)-1])

                remaining_budget = b - cost
            else:
                # No more candidates.
                if debug:
                    print(" - No more candidates available.")
                stop = True
            if debug:
                print(" - Candidates evaluated: (",n_can,"/",len(candidates_sorted),"). Current cost: (",int(cost),"/",b,"€).")
        else:
            # No more candidates.
            if debug:
                print(" - No more candidates available.")
            stop = True
            
    # The resulting network has all nodes in G, so it is necessary to remove unconnected nodes (extract biggest component). 
    G_new_full = nx.Graph(G_original)
    attrs = {}
    for u,v,data in G_original.edges(data=True):
        if not to_improve.has_edge(u,v):
            G_new_full.remove_edge(u,v)
        else:
            attrs[(u,v)] = {"flow": test_graph[u][v]["flow"], "diameter": test_graph[u][v]["diameter"], "age": 0, "material": "PE100", "wall_thickness": zmod_costs.get_wall_thickness(test_graph[u][v]["diameter"])}
            if "valve" in test_graph[u][v]:
                attrs[(u,v)]["valve"] = test_graph[u][v]["valve"]
    nx.set_edge_attributes(G_new_full, attrs)
    Gcc = sorted(nx.connected_components(G_new_full), key=len, reverse=True)
    G_new_full = G_new_full.subgraph(Gcc[0])
    
    
    # Get the total network pipe distance (in m)
    pipe_distance = int(G_new_full.size(weight="length"))
        
    end = time.time()
    
    # Resulting data structure.
    result_data = {
        "pipe_distance": pipe_distance,
        "new_pipes": new_pipes,
        "execution_time": end-start,
        "failure_rate": 100*((0.4/12)*(pipe_distance/1000))/G_new_full.number_of_edges(),
        "tank_capacity": t_capacity
    }
    return G_new_full, result_data, epanet_result