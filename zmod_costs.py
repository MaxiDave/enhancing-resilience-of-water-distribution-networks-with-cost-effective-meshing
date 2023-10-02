########################################################################################################
########################################################################################################
################################### CONSTRUCTION COSTS #################################################
########################################################################################################
########################################################################################################

import networkx as nx
import numpy as np
from collections import deque
import math

# Cost ranges: Diameters
diameters = [32,63,75,90,110,125,140,160,180,200,225,250,315,400,450,560,630]
wall_thickness = {
    32: 2,
    63: 3.8,
    75: 4.5,
    90: 5.4,
    110: 6.6,
    125: 7.4,
    140: 8.3,
    160: 9.5,
    180: 10.7,
    200: 11.9,
    225: 13.4,
    250: 14.8,
    315: 18.7,
    400: 23.7,
    450: 26.7,
    560: 33.2,
    630: 37.4
}
costs_diameter = {
    32: 71.91,
    63: 74.38,
    75: 77.45,
    90: 80.28,
    110: 83.54,
    125: 87.27,
    140: 91.29,
    160: 96.68,
    180: 116.89,
    200: 134.53,
    225: 153.50,
    250: 172.77,
    315: 217.17,
    400: 271.49,
    450: 334.66,
    560: 424.33,
    630: 489.38
}

# Cost ranges: Valves.
valve_diameter = [40, 50, 65, 80, 100, 125, 150, 200, 250, 300, 350, 400, 450, 500, 600, 700]
valve_costs = {
    40: 89.29, 
    50: 100.46, 
    65: 125.77, 
    80: 169.88, 
    100: 210.88, 
    125: 278.35, 
    150: 334.97, 
    200: 650.00, 
    250: 865.55, 
    300: 1116.81, 
    350: 1812.51, 
    400: 2388.50, 
    450: 3095.43, 
    500: 4058.26, 
    600: 8026.65, 
    700: 9014.04
}

# Cost ranges: Tanks.
tanks_m3 = [400, 2500, 5000, 10000, 20000]
tanks_costs = {
    400: 240000, 
    2500: 350000, 
    5000: 440000, 
    10000: 560000, 
    20000: 760000
}
tank_radius = {
    400: 3.56825, 
    2500: 8.92062, 
    5000: 12.61566, 
    10000: 17.84124, 
    20000: 25.231328
}

# Return the minimum cost of pipe construction per unit (meter).
def get_min_costs_diameter():
    return costs_diameter[diameters[0]]

def get_tank_radius(tank_capacity):
    return tank_radius[tank_capacity]

def get_wall_thickness(diameter):
    return wall_thickness[diameter]

def tank_cost(full_consumption):
    """
    Returns the cost of the necessary water tank with a given consumption. Finds the upper value of tanks capacity from 
    the given range and returns its cost.
        
    Args:
        full_consumption (double): full consumption in m3/day of a network.
    Returns:
        cost (int): Cost in Euros € of the necessary water tank.
    """
    index = np.searchsorted(tanks_m3, full_consumption)
    capacity = tanks_m3[index]
    cost = tanks_costs[capacity]
    return cost, capacity

def get_construction_costs(G, origin, cons_nodes, total_cons, precomputed_data):
    """
    Given a current reclaimed network under design process, check how much will cost to build it.
        
    Args:
        G (nx undirected graph): graph under design.
        origin (int): node of origin of the water.
        cons_nodes (int set): set of nodes that will be added (recently added in G, last iteration).
        total_cons (double): total consumption of m3/day of the network G.
        precomputed_data (object): Data structure including essential precomputed data to make the algorithm more efficient. 
            Check func "precompute_data_lb_algorithms" for more info.
    Returns:
        cost (double): Cost in Euros € to build G.
    """
    
    # First, build the flow network. For more info: https://www.cs.umd.edu/class/fall2017/cmsc451-0101/Lects/lect17-flow-circ.pdf
    
    # Create artificial super nodes of origin and destination of flow for reducing demand circulation problem to well-known max flow.
    super_node_origin = 99999999999999
    super_node_dest = 999999999999999
    G.add_edge(super_node_origin, origin, capacity=total_cons)
    for node in cons_nodes:
        G.add_edge(node, super_node_dest, capacity=precomputed_data["n_cons"][node])
    # From networkx library, 'preflow_push' seems the most efficient algorithm for maximum flows with O(n^2 x sqrt(e)), for n nodes and e edges.
    residual_network = preflow_push(G, super_node_origin, super_node_dest)
    flows = nx.get_edge_attributes(residual_network,'flow')
    G.remove_node(super_node_origin)
    G.remove_node(super_node_dest)
    
    # 'flows' contains the computed flows, get diameters and costs from that.
    # In the 'diameters_dict' store each pipe diameter both for u,v and v,u, as it is a bidirectional graph.
    cost = 0
    diameters_dict = {} 
    for u,v,data in G.edges(data=True):
        print("*************")
        print(u,v)
        print("Flows:",flows[(u,v)])
        print("Diameter:",int(math.sqrt(abs(flows[(u,v)])/24/3600*4/math.pi)*1000))
        index_diameter = np.searchsorted(diameters, int(math.sqrt(abs(flows[(u,v)])/24/3600*4/math.pi)*1000))
        diameter = diameters[index_diameter]
        cost += (costs_diameter[diameter]*precomputed_data['edge_lengths'][(u,v)])
        diameters_dict[(u,v)] = diameter
        diameters_dict[(v,u)] = diameter
        
    # Once pipe construction costs are calculated, add the valves cost. A valve is needed in each pipe intersection if degree of intersection is > 2.
    for u in G.nodes():
        degree = G.degree[u]
        if degree > 2:
            neighbors = G.neighbors(u)
            max_diam = 0
            for neighbor in neighbors:
                if diameters_dict[(u,neighbor)] > max_diam:
                    max_diam = diameters_dict[(u,neighbor)]
            index_valve_diam = np.searchsorted(valve_diameter, max_diam)
            valve_diam = valve_diameter[index_valve_diam]
            cost += valve_costs[valve_diam]
            
    print(diameters_dict)
            
    # Finally return the cost with the necessary water tank.
    t_cost,t_capacity = tank_cost(total_cons)
    return cost + t_cost, diameters_dict, t_capacity

# Consumption aggregation.
def get_construction_costs_v2(G, origin, cons_nodes, total_cons, precomputed_data):
    """
    Given a current reclaimed network under design process, check how much will cost to build it.
        
    Args:
        G (nx undirected graph): graph under design.
        origin (int): node of origin of the water.
        cons_nodes (int set): set of nodes that will be added (recently added in G, last iteration).
        total_cons (double): total consumption of m3/day of the network G.
        precomputed_data (object): Data structure including essential precomputed data to make the algorithm more efficient. 
            Check func "precompute_data_lb_algorithms" for more info.
    Returns:
        cost (double): Cost in Euros € to build G.
    """

    # Flow network not working as desired. Try to switch strategy to consumption aggregation through simple paths.
    flows = {}
    for node in cons_nodes:
        G_new = nx.Graph(G)
        end = False
        shortest_path = precomputed_data["shortest_paths"][node][origin]
        while not end:
            edges = []
            for v, w in zmod_pairwise.pairwise(shortest_path):
                edges.append((v,w))
                if (v,w) not in flows:
                    if (w,v) in flows:
                        flows[(w,v)] += precomputed_data["n_cons"][node]
                    else: 
                        flows[(v,w)] = precomputed_data["n_cons"][node]
                else:
                    flows[(v,w)] += precomputed_data["n_cons"][node]
            G_new.remove_edges_from(edges)
            try:
                shortest_path = nx.shortest_path(G_new, node, origin, weight='length')
            except nx.NetworkXNoPath:
                end = True
                pass

    # Check for empty flows.
    check_again = True
    while check_again:
        check_again = False
        for u,v in G.edges():
            if (u,v) not in flows and (v,u) not in flows:
                # Try to interpolate flows. Check for adjacent edges and get the max value.
                adj_flows = []
                for n in G.neighbors(u):
                    if n != v:
                        if (u,n) in flows:
                            adj_flows.append(flows[(u,n)])
                        elif (n,u) in flows:
                            adj_flows.append(flows[(n,u)])
                for n in G.neighbors(v):
                    if n != u:
                        if (v,n) in flows:
                            adj_flows.append(flows[(v,n)])
                        elif (n,v) in flows:
                            adj_flows.append(flows[(n,v)])
                if not adj_flows:
                    check_again = True
                else:
                    max_value = max(adj_flows)
                    flows[(u,v)] = max_value
            
    # 'flows' contains the computed flows, get diameters and costs from that.
    # In the 'diameters_dict' store each pipe diameter both for u,v and v,u, as it is a bidirectional graph.
    cost = 0
    diameters_dict = {} 
    for u,v in G.edges():
        if (u,v) not in flows:
            aux = u
            u = v
            v = aux
        index_diameter = np.searchsorted(diameters, int(math.sqrt(abs(flows[(u,v)])/24/3600*4/math.pi)*1000))
        diameter = diameters[index_diameter]
        cost += (costs_diameter[diameter]*precomputed_data['edge_lengths'][(u,v)])
        diameters_dict[(u,v)] = diameter
        diameters_dict[(v,u)] = diameter
        
    # Once pipe construction costs are calculated, add the valves cost. A valve is needed in each pipe intersection if degree of intersection is > 2.
    for u in G.nodes():
        degree = G.degree[u]
        if degree > 2:
            neighbors = G.neighbors(u)
            max_diam = 0
            for neighbor in neighbors:
                if diameters_dict[(u,neighbor)] > max_diam:
                    max_diam = diameters_dict[(u,neighbor)]
            index_valve_diam = np.searchsorted(valve_diameter, max_diam)
            valve_diam = valve_diameter[index_valve_diam]
            cost += valve_costs[valve_diam]
            
    # Finally return the cost with the necessary water tank.
    t_cost,t_capacity = tank_cost(total_cons)
    return cost + t_cost, diameters_dict, t_capacity

# This algorithm returns a BFS ordered nodes prioritized by distance.
def bfs_distance_nodes(graph, source, precomputed_data):
    visited = set()
    queue = deque([(source, 0)])  # (node, distance) tuple

    while queue:
        node, distance = queue.popleft()

        if node not in visited:
            visited.add(node)
            yield node, distance

            neighbors = sorted(graph.neighbors(node), key=lambda n: precomputed_data['edge_lengths'][(node,n)])
            for neighbor in neighbors:
                if neighbor not in visited:
                    queue.append((neighbor, distance + precomputed_data['edge_lengths'][(node,neighbor)]))

# New algorithm idea:
# - BFS with accumulative consumption. Create a map or some DS to sort this out, the idea is to then start in reverse and accumulate
#   consumption in some sort of reverse BFS manner. Quite accurate!
#  The algorithm is quite good selecting diameters.
def diameter_selection_and_cost_v2(graph, wwtp, precomputed_data, total_cons, speed_min = 0.4, speed_max = 1):
    # Compute diameter, predict flow trough the 'bfs_distance_nodes' algorithm and try to have a speed >= speed_min 
    #  (often considered as 0.6 and 1.2 for max_speed).
    visited = set()
    accum_flows = {}
    attrs = {}
    cost = 0
    bfs_ordered_nodes = sorted(bfs_distance_nodes(graph, wwtp, precomputed_data), key=lambda x: x[1], reverse = True)
    for node,distance in bfs_ordered_nodes:
        visited.add(node)
        if node not in accum_flows:
            accum_flows[node] = 0
        n_sources = 0
        degree = 0
        visited_neighbors = set()
        for neighbor in graph.neighbors(node):
            degree += 1
            if neighbor not in visited:
                n_sources += 1
            else:
                visited_neighbors.add(neighbor)
        # If len(visited_neighbors) > 2, then put a valve in those pipes.
        for neighbor in graph.neighbors(node):
            if neighbor not in visited:
                flow = (graph.nodes[node]['consumption'] + accum_flows[node])/n_sources
                if neighbor not in accum_flows:
                    accum_flows[neighbor] = flow
                else:
                     accum_flows[neighbor] += flow
                # Diameter selection.
                index_diameter = 0
                prev_speed = float('inf')
                for diam in diameters:    
                    speed = (4*flow/86400)/(math.pi*((diam/1000)**2))
                    if speed <= speed_min and prev_speed <= speed_max:
                        index_diameter -= 1
                        break
                    elif speed <= speed_min:
                        break
                    prev_speed = speed
                    index_diameter += 1
                diameter = diameters[index_diameter]
                attrs[(node,neighbor)] = {"length": precomputed_data['edge_lengths'][(node,neighbor)], "flow": flow, "diameter": diameter}
                cost += (costs_diameter[diameter]*precomputed_data['edge_lengths'][(node,neighbor)])
            elif (node,neighbor) in attrs:
                valve_candidate = (node,neighbor)
            else:
                valve_candidate = (neighbor,node)
            if len(visited_neighbors) > 1 and neighbor in visited_neighbors:
                index_valve_diam = np.searchsorted(valve_diameter, attrs[valve_candidate]["diameter"])
                valve_diam = valve_diameter[index_valve_diam]
                cost += valve_costs[valve_diam]
                attrs[valve_candidate]["valve"] = valve_diam
            
    nx.set_edge_attributes(graph, attrs)
    t_cost,t_capacity = tank_cost(total_cons)
    return nx.Graph(graph), cost+t_cost, t_capacity

# Same as before, but some diameters are already fixed in 'graph'.
def diameter_selection_and_cost_v2_improvement(graph, wwtp, precomputed_data, total_cons, speed_min = 0.4, speed_max = 1):
    # Compute diameter, predict flow trough the 'bfs_distance_nodes' algorithm and try to have a speed >= speed_min 
    #  (often considered as 0.6 and 1.2 for max_speed).
    visited = set()
    accum_flows = {}
    attrs = {}
    cost = 0
    bfs_ordered_nodes = sorted(bfs_distance_nodes(graph, wwtp, precomputed_data), key=lambda x: x[1], reverse = True)
    for node,distance in bfs_ordered_nodes:
        visited.add(node)
        if node not in accum_flows:
            accum_flows[node] = 0
        n_sources = 0
        degree = 0
        visited_neighbors = set()
        for neighbor in graph.neighbors(node):
            degree += 1
            if neighbor not in visited:
                n_sources += 1
            else:
                visited_neighbors.add(neighbor)
        # If len(visited_neighbors) > 2, then put a valve in those pipes.
        for neighbor in graph.neighbors(node):
            if neighbor not in visited:
                flow = (precomputed_data['n_cons'][node] + accum_flows[node])/n_sources
                if neighbor not in accum_flows:
                    accum_flows[neighbor] = flow
                else:
                     accum_flows[neighbor] += flow
                    
                # Diameter selection. Check if diameter is preset.
                if 'diameter' in graph[node][neighbor]:
                    attrs[(node,neighbor)] = {"length": precomputed_data['edge_lengths'][(node,neighbor)], "flow": flow, "diameter": graph[node][neighbor]['diameter']}
                elif 'diameter' in graph[neighbor][node]:
                    attrs[(node,neighbor)] = {"length": precomputed_data['edge_lengths'][(node,neighbor)], "flow": flow, "diameter": graph[neighbor][node]['diameter']}
                else:
                    index_diameter = 0
                    prev_speed = float('inf')
                    for diam in diameters:    
                        speed = (4*flow/86400)/(math.pi*((diam/1000)**2))
                        if speed <= speed_min and prev_speed <= speed_max:
                            index_diameter -= 1
                            break
                        elif speed <= speed_min:
                            break
                        prev_speed = speed
                        index_diameter += 1
                    diameter = diameters[index_diameter]
                    attrs[(node,neighbor)] = {"length": precomputed_data['edge_lengths'][(node,neighbor)], "flow": flow, "diameter": diameter, "newpipe": True}
                    cost += (costs_diameter[diameter]*precomputed_data['edge_lengths'][(node,neighbor)])
            elif (node,neighbor) in attrs:
                valve_candidate = (node,neighbor)
            else:
                valve_candidate = (neighbor,node)
            if len(visited_neighbors) > 1 and neighbor in visited_neighbors:
                index_valve_diam = np.searchsorted(valve_diameter, attrs[valve_candidate]["diameter"])
                valve_diam = valve_diameter[index_valve_diam]
                cost += valve_costs[valve_diam]
                attrs[valve_candidate]["valve"] = valve_diam
            
    nx.set_edge_attributes(graph, attrs)
    t_cost,t_capacity = tank_cost(total_cons)
    return nx.Graph(graph), cost, t_capacity