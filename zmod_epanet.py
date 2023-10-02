import networkx as nx
import subprocess
import re
import pandas as pd

import zmod_costs

def compute_epanet(graph, tank_capacity, wwtp, debug=False):
    # Try to generate INP file for a graph and return simulation results.
    title="Girona Test for Hydraulically feasible and resilient network designs"
    pipes_dict = {}
    with open('EPANET-2.2/bin/input.inp', 'w') as f:
        # Title section
        f.write('[TITLE]\n')
        f.write(title+'\n')
        f.write('\n')
        
        # Junctions section (nodes).
        f.write('[JUNCTIONS]\n')
        f.write(';'+'ID'.ljust(10, " ")+'Elev'.ljust(22, " ")+'Demand'.ljust(22, " ")+'Pattern'.ljust(15, " ")+'\n')
        for node,data in graph.nodes(data=True):
            if node != wwtp:
                f.write(str(node).ljust(11, " "))
                f.write(str(data["elevation"]).ljust(22, " "))
                f.write(str(data["consumption"]).ljust(22, " "))
                f.write("".ljust(15, " "))
                f.write(';\n')
        f.write('\n')
        # Reservoirs section (empty).
        f.write('[RESERVOIRS]\n')
        f.write(';'+'ID'.ljust(10, " ")+'Head'.ljust(22, " ")+'Pattern'.ljust(15, " ")+';\n')
        f.write('\n')
        
        # Tanks section.
        wwtp_data = graph.nodes(data=True)[wwtp]
        f.write('[TANKS]\n')
        f.write(';'+'ID'.ljust(10, " ")+'Elevation'.ljust(22, " ")+'InitLevel'.ljust(15, " ")+'MinLevel'.ljust(15, " ")+'MaxLevel'.ljust(15, " ")+'Diameter'.ljust(22, " ")+'MinVol'.ljust(15, " ")+'VolCurve'.ljust(15, " ")+'\n')
        f.write(str(wwtp).ljust(11, " "))
        f.write(str(wwtp_data["elevation"]).ljust(22, " "))
        f.write("5".ljust(15, " "))
        f.write("0.2".ljust(15, " "))
        f.write("10".ljust(15, " "))
        f.write(str(zmod_costs.get_tank_radius(tank_capacity)*2).ljust(22, " "))
        f.write("0".ljust(15, " "))
        f.write("".ljust(13, " "))
        f.write(';\n\n')
        
        # Pipes section.
        f.write('[PIPES]\n')
        p_id = 1
        f.write(';'+'ID'.ljust(10, " ")+'Node1'.ljust(10, " ")+'Node2'.ljust(10, " ")+'Length'.ljust(22, " ")+'Diameter'.ljust(15, " ")+'Roughness'.ljust(15, " ")+'MinorLoss'.ljust(15, " ")+'Status'.ljust(15, " ")+'\n')
        for node1,node2,data in graph.edges(data=True):
            pipes_dict[p_id] = (node1,node2)
            f.write(str(p_id).ljust(11, " "))
            f.write(str(node1).ljust(10, " "))
            f.write(str(node2).ljust(10, " "))
            f.write(str(data["length"]).ljust(22, " "))
            f.write(str(data["diameter"]).ljust(15, " "))
            f.write("155".ljust(15, " "))
            f.write("0".ljust(15, " "))
            f.write("Open".ljust(15, " "))
            f.write("".ljust(15, " "))
            f.write(';\n')
            p_id += 1
        f.write('\n')
        #attrs = {(2106,1020): {"diameter": 400}}
        #nx.set_edge_attributes(graph,attrs)

        # Pumps section.
        f.write('[PUMPS]\n')
        f.write(';'+'ID'.ljust(10, " ")+'Node1'.ljust(10, " ")+'Node2'.ljust(10, " ")+'Properties'.ljust(25, " ")+'\n')
        #f.write("Pump1".ljust(11, " "))
        #f.write("2106".ljust(10, " "))
        #f.write("1020".ljust(10, " "))
        #f.write("HEAD Curve1 ;".ljust(25, " "))
        f.write('\n')
        #f.write('\n')
        #f.write("Pump2".ljust(11, " "))
        #f.write("1787".ljust(10, " "))
        #f.write("1241".ljust(10, " "))
        #f.write("POWER 20 ;".ljust(25, " "))
        #f.write('\n')
        f.write('\n')
        
        # Sections that has to exist but empty.
        #f.write('[PUMPS]\n')
        #f.write(';'+'ID'.ljust(10, " ")+'Node1'.ljust(10, " ")+'Node2'.ljust(10, " ")+'Parameters'.ljust(10, " ")+'\n')
        #f.write('\n')
        f.write('[VALVES]\n')
        f.write(';'+'ID'.ljust(10, " ")+'Node1'.ljust(10, " ")+'Node2'.ljust(10, " ")+'Diameter'.ljust(15, " ")+'Type'.ljust(10, " ")+'Setting'.ljust(15, " ")+'MinorLoss'.ljust(15, " ")+'\n')
        f.write('\n')
        f.write('[TAGS]\n')
        f.write('\n')
        f.write('[DEMANDS]\n')
        f.write(';'+'Junction'.ljust(10, " ")+'Demand'.ljust(10, " ")+'Pattern'.ljust(10, " ")+'Category'.ljust(10, " ")+'\n')
        f.write('\n')
        f.write('[STATUS]\n')
        f.write(';'+'ID'.ljust(10, " ")+'Status/Setting'.ljust(10, " ")+'\n')
        f.write('\n')
        f.write('[PATTERNS]\n')
        f.write(';'+'ID'.ljust(10, " ")+'Multipliers'.ljust(10, " ")+'\n')
        f.write('\n')
        f.write('[CURVES]\n')
        f.write(';'+'ID'.ljust(10, " ")+'X-Value'.ljust(10, " ")+'Y-Value'.ljust(10, " ")+'\n')
        #f.write("Curve1".ljust(11, " "))
        #f.write("5000".ljust(10, " "))
        #f.write("130".ljust(10, " "))
        f.write(';\n\n')
        f.write('[CONTROLS]\n')
        f.write('\n')
        f.write('[RULES]\n')
        f.write('\n')
        f.write('[ENERGY]\n')
        f.write('Global Efficiency'.ljust(25, " ")+'75'+'\n')
        f.write('Global Price'.ljust(25, " ")+'0'+'\n')
        f.write('Demand Charge'.ljust(25, " ")+'0'+'\n')
        f.write('\n')
        
        # Emitters section.
        f.write('[EMITTERS]\n')
        f.write(';'+'Junction'.ljust(10, " ")+'Coefficient'.ljust(15, " ")+'\n')
        for node in graph.nodes():
            if node != wwtp:
                f.write(str(node).ljust(11, " "))
                f.write("0".ljust(15, " "))
                f.write(';\n')
        f.write('\n')

        # Quality section.
        f.write('[QUALITY]\n')
        f.write(';'+'Node'.ljust(10, " ")+'InitQual'.ljust(15, " ")+'\n')
        f.write(str(wwtp).ljust(11, " "))
        f.write("60".ljust(15, " "))
        f.write(';\n\n')
        
        # More empty sections that nobody understand.
        f.write('[SOURCES]\n')
        f.write(';'+'Node'.ljust(10, " ")+'Type'.ljust(15, " ")+'Quality'.ljust(15, " ")+'Pattern'.ljust(15, " ")+'\n')
        f.write('\n')
        f.write('[REACTIONS]\n')
        f.write(';'+'Type'.ljust(10, " ")+'Pipe/Tank'.ljust(15, " ")+'Coefficient'.ljust(15, " ")+'\n')
        f.write('\n')
        f.write('[REACTIONS]\n')
        f.write('Order Bulk'.ljust(25, " ")+'1'+'\n')
        f.write('Order Tank'.ljust(25, " ")+'1'+'\n')
        f.write('Order Wall'.ljust(25, " ")+'1'+'\n')
        f.write('Global Bulk'.ljust(25, " ")+'0'+'\n')
        f.write('Global Wall'.ljust(25, " ")+'0'+'\n')
        f.write('Limiting Potential'.ljust(25, " ")+'0'+'\n')
        f.write('Roughness Correlation'.ljust(25, " ")+'0'+'\n')
        f.write('\n')
        f.write('[MIXING]\n')
        f.write(';'+'Tank'.ljust(10, " ")+'Model'.ljust(15, " ")+'\n')
        f.write('\n')
        f.write('[TIMES]\n')
        f.write('Duration'.ljust(25, " ")+'0:00'+'\n')
        f.write('Hydraulic Timestep'.ljust(25, " ")+'1:00'+'\n')
        f.write('Quality Timestep'.ljust(25, " ")+'0:05'+'\n')
        f.write('Pattern Timestep'.ljust(25, " ")+'2:00'+'\n')
        f.write('Pattern Start'.ljust(25, " ")+'0:00'+'\n')
        f.write('Report Timestep'.ljust(25, " ")+'1:00'+'\n')
        f.write('Report Start'.ljust(25, " ")+'0:00'+'\n')
        f.write('Start ClockTime'.ljust(25, " ")+'12 am'+'\n')
        f.write('Statistic'.ljust(25, " ")+'NONE'+'\n')
        f.write('\n')
        f.write('[REPORT]\n')
        f.write('Status'.ljust(25, " ")+'Full'+'\n')
        f.write('Summary'.ljust(25, " ")+'Yes'+'\n')
        f.write('Page'.ljust(25, " ")+'0'+'\n')
        f.write('Nodes'.ljust(25, " ")+'All'+'\n')
        f.write('Links'.ljust(25, " ")+'All'+'\n')
        f.write('\n')
        
        # Options
        f.write('[OPTIONS]\n')
        f.write('Units'.ljust(25, " ")+'CMD'+'\n')
        f.write('Headloss'.ljust(25, " ")+'H-W'+'\n')
        f.write('Specific Gravity'.ljust(25, " ")+'1'+'\n')
        f.write('Viscosity'.ljust(25, " ")+'1'+'\n')
        f.write('Trials'.ljust(25, " ")+'40'+'\n')
        f.write('Accuracy'.ljust(25, " ")+'0.001'+'\n')
        f.write('CHECKFREQ'.ljust(25, " ")+'2'+'\n')
        f.write('MAXCHECK'.ljust(25, " ")+'10'+'\n')
        f.write('DAMPLIMIT'.ljust(25, " ")+'0'+'\n')
        f.write('Unbalanced'.ljust(25, " ")+'Continue 10'+'\n')
        f.write('Pattern'.ljust(25, " ")+'1'+'\n')
        f.write('Demand Multiplier'.ljust(25, " ")+'1.0'+'\n')
        f.write('Emitter Exponent'.ljust(25, " ")+'0.5'+'\n')
        f.write('Minimum Pressure'.ljust(25, " ")+'15'+'\n')
        f.write('Required Pressure'.ljust(25, " ")+'30'+'\n')
        f.write('Demand Model'.ljust(25, " ")+'PDA'+'\n')
        f.write('Quality'.ljust(25, " ")+'None'+'\n')
        f.write('Diffusivity'.ljust(25, " ")+'1'+'\n')
        f.write('Tolerance'.ljust(25, " ")+'0.01'+'\n')
        f.write('\n')
        
        # Node coordinates.
        f.write('[COORDINATES]\n')
        f.write(';'+'Node'.ljust(10, " ")+'X-Coord'.ljust(22, " ")+'Y-Coord'.ljust(22, " ")+'\n')
        for node,data in graph.nodes(data=True):
            f.write(str(node).ljust(11, " "))
            f.write(str(data["x"]).ljust(22, " "))
            f.write(str(data["y"]).ljust(22, " "))
            f.write('\n')
        f.write('\n')
        
        # More random options
        f.write('[VERTICES]\n')
        f.write(';'+'Link'.ljust(10, " ")+'X-Coord'.ljust(22, " ")+'Y-Coord'.ljust(22, " ")+'\n')
        f.write('\n')
        f.write('[LABELS]\n')
        f.write(';'+'X-Coord'.ljust(10, " ")+'Y-Coord'.ljust(22, " ")+'Label & Anchor Node'.ljust(22, " ")+'\n')
        f.write('\n')
        f.write('[BACKDROP]\n')
        f.write('UNITS'.ljust(15, " ")+'None'.ljust(15, " ")+'\n')
        f.write('FILE'.ljust(15, " ")+'\n')
        f.write('OFFSET'.ljust(15, " ")+'0.00'.ljust(15, " ")+'0.00'.ljust(15, " ")+'\n')
        f.write('\n')
        
        # Finally
        f.write('[END]\n')

    # Now compute EPANET and process result file.
    if debug:
        print("Running EPANET 2.2 ...")
    process = subprocess.Popen("./EPANET-2.2/bin/runepanet ./EPANET-2.2/bin/input.inp ./EPANET-2.2/bin/report.txt", shell=True, stdout=subprocess.PIPE)
    process.wait()
    if process.returncode == 0 and debug:
        print(" - EPANET ran successfully")
    elif debug:
        print(" - ERROR in EPANET:", process.returncode)
        return -1, -1, -1

    # Now process report.txt file.
    r1 = re.compile(r"Balanced after \d+ trials")
    r2 = re.compile(r"Node Results:")
    r3 = re.compile(r"Link Results:")
    
    line_counter = 0
    line_node = 0
    line_percentage = 0
    print_l = False
    with open("./EPANET-2.2/bin/report.txt", "r") as f_in:
        for l in f_in:
            if print_l:
                print_l = False
                line_demand_reduced = l.strip()
            line_counter += 1
            if r1.search(l):
                line_percentage = line_counter
                print_l = True
            if r2.search(l):
                line_node = line_counter + 4
            if r3.search(l):
                line_counter += 4
                break
    
    node_results = pd.read_csv("./EPANET-2.2/bin/report.txt", skiprows=line_node, nrows=graph.number_of_nodes()-1, on_bad_lines='skip', header=None, sep=r"\s+", names=["Node", "Supplied demand (m3/d)", "Head (m)", "Pressure (m)"])
    link_results = pd.read_csv("./EPANET-2.2/bin/report.txt", skiprows=line_counter, nrows=graph.number_of_edges(), on_bad_lines='skip', header=None, sep=r"\s+", names=["Link ID", "Flow (m3/d)", "Velocity (m/s)", "Headloss (/1000m)"])

    result_data = {}
    result_data["success"] = True
    if "nodes had demands reduced by a total" in line_demand_reduced:
        result_data["success"] = False
        if debug:
            print("- Alert! Demand reduced detected!")
            print("  -", line_demand_reduced)
        line_list = line_demand_reduced.split(" ")
        result_data["n_nodes_reduced"] = int(line_list[0])
        result_data["percentage_reduced"] = float(line_list[len(line_list)-1][:-1])
    elif debug:
        print("- Seems the output is OK, network is feasible.")
    
    node_data = {}
    link_data = {}
    consumptions = nx.get_node_attributes(graph, "consumption")
    result_data["max_pressure"] = 0
    result_data["min_pressure"] = float('inf')
    result_data["max_speed"] = 0
    result_data["min_speed"] = float('inf')
    result_data["unsupplied_nodes"] = set()
    for index, row in node_results.iterrows():
        node_data[int(row["Node"])] = {
            "supplied": float(row["Supplied demand (m3/d)"]),
            "head": float(row["Head (m)"]),
            "pressure": float(row["Pressure (m)"])
        }
        if not result_data["success"] and round(float(row["Supplied demand (m3/d)"]),2) < round(float(consumptions[int(row["Node"])]),2):
            #print(int(row["Node"]), round(float(row["Supplied demand (m3/d)"]),2), round(float(consumptions[int(row["Node"])]),2))
            result_data["unsupplied_nodes"].add(int(row["Node"]))
        if float(row["Pressure (m)"]) < result_data["min_pressure"]:
            result_data["min_pressure"] = float(row["Pressure (m)"])
        if float(row["Pressure (m)"]) > result_data["max_pressure"]:
            result_data["max_pressure"] = float(row["Pressure (m)"])
    for index, row in link_results.iterrows():
        link_data[pipes_dict[row["Link ID"]]] = {
            "flow": float(row["Flow (m3/d)"]),
            "velocity": float(row["Velocity (m/s)"]),
            "headloss": float(row["Headloss (/1000m)"])
        }
        if float(row["Velocity (m/s)"]) < result_data["min_speed"] and float(row["Velocity (m/s)"]) > 0:
            result_data["min_speed"] = float(row["Velocity (m/s)"])
        if float(row["Velocity (m/s)"]) > result_data["max_speed"]:
            result_data["max_speed"] = float(row["Velocity (m/s)"])

    if result_data["min_pressure"] < 15:
        result_data["success"] = False
        if debug:
            print(" - Bad minimum pressure, should be at least 15 and we obtained", result_data["min_pressure"])
    if result_data["max_pressure"] > 60:
        result_data["success"] = False
        if debug:
            print(" - Bad maximum pressure, should be less than 60 and we obtained", result_data["max_pressure"])
    if result_data["max_speed"] > 1.2:
        result_data["success"] = False
        if debug:
            print(" - Bad maximum speed, should be less than 1.2 and we obtained", result_data["max_speed"])
    
    #zmod_print.plot_network_with_folium_hydraulic(nx.Graph(g_attr), graph, node_data)
    return node_data, link_data, result_data
