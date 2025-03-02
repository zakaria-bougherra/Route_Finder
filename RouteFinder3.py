import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt
from geopy.distance import geodesic
import numpy as np

# Set the matplotlib style to dark
plt.style.use('dark_background')

# Load graph from OSM file
osm_file_path = "Taher_map.osm" 
graph = ox.graph_from_xml(osm_file_path, bidirectional=True)

# Add edge bearings
graph = ox.add_edge_bearings(graph)

# Define origin and destination places
origin_place = "Crédit Populaire d'Algérie, شارع بوكروم الطاهر, Taher, Taher District, Jijel, 18002, Algeria"
destination_place = "Daira de Taher"

# Geocode locations
origin_point = ox.geocode(origin_place)
destination_point = ox.geocode(destination_place) 

# Find nearest nodes in the graph
origin_node = ox.distance.nearest_nodes(graph, X=origin_point[1], Y=origin_point[0])
destination_node = ox.distance.nearest_nodes(graph, X=destination_point[1], Y=destination_point[0])

# Simple heuristic using only geodesic distance
def simple_heuristic(u, v):
    u_lat, u_lon = graph.nodes[u]["y"], graph.nodes[u]["x"]
    v_lat, v_lon = graph.nodes[v]["y"], graph.nodes[v]["x"]
    
    # Geodesic distance in meters
    return geodesic((u_lat, u_lon), (v_lat, v_lon)).meters

# Advanced heuristic with multiple factors
def advanced_heuristic(u, v):
    u_lat, u_lon = graph.nodes[u]["y"], graph.nodes[u]["x"]
    v_lat, v_lon = graph.nodes[v]["y"], graph.nodes[v]["x"]
    
    # Geodesic distance in meters
    distance = geodesic((u_lat, u_lon), (v_lat, v_lon)).meters  
    
    # Retrieve edge data
    edge_data = graph.get_edge_data(u, v)
    if edge_data is None:
        return float('inf')  # If no edge exists, return infinite cost

    # Select the first available edge (OSMnx creates MultiGraphs)
    edge = list(edge_data.values())[0] if edge_data else None
    if edge is None:
        return float('inf')

    # Get road type (default to 'residential' if unknown)
    road_type = edge.get("highway", "residential")
    
    # Base speed per road type (in km/h)
    speed_mapping = {
        "motorway": 100,   # 100 km/h for highways
        "primary": 80,     # 80 km/h for main roads
        "secondary": 60,   # 60 km/h for secondary roads
        "residential": 40  # 40 km/h for city streets
    }
    
    base_speed_kmh = speed_mapping.get(road_type, 40)  # Default to 40 km/h
    base_speed_mps = (base_speed_kmh * 1000) / 3600  # Convert to m/s

    # Road Condition
    road_condition = edge.get("road_condition", "good")
    condition_factor = {
        "good": 1.0,     # No effect
        "average": 0.8,  # 20% speed reduction
        "poor": 0.5      # 50% speed reduction
    }
    speed_mps = base_speed_mps * condition_factor.get(road_condition, 1.0)

    # Traffic Congestion 
    traffic_level = edge.get("traffic", "low")
    traffic_factor = {
        "low": 1.0,       # No effect
        "medium": 0.7,    # 30% slower
        "high": 0.4       # 60% slower
    }
    speed_mps *= traffic_factor.get(traffic_level, 1.0)

    # Estimated time in seconds
    return distance / speed_mps if speed_mps > 0 else float('inf')

# Find paths using both heuristics
try:
    simple_path = nx.astar_path(graph, origin_node, destination_node, heuristic=simple_heuristic, weight="length")
except nx.NetworkXNoPath:
    simple_path = None

try:
    advanced_path = nx.astar_path(graph, origin_node, destination_node, heuristic=advanced_heuristic, weight="length")
except nx.NetworkXNoPath:
    advanced_path = None

# Calculate path lengths if both paths exist
if simple_path and advanced_path:
    simple_length = sum(graph[simple_path[i]][simple_path[i+1]][0].get('length', 0) for i in range(len(simple_path)-1))
    advanced_length = sum(graph[advanced_path[i]][advanced_path[i+1]][0].get('length', 0) for i in range(len(advanced_path)-1))

# Manual approach to ensure both maps are in the same window
if simple_path or advanced_path:
    # Create a single figure with axes
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
    
    # Define colors for dark theme
    bgcolor = '#121212'  # Very dark background
    edge_color = '#555555'  # Dark gray for streets
    
    # Get the nodes and edges from the graph
    nodes = list(graph.nodes)
    node_points = [(graph.nodes[node]['x'], graph.nodes[node]['y']) for node in nodes]
    x_vals = [point[0] for point in node_points]
    y_vals = [point[1] for point in node_points]
    
    # Set the extent of the plot to contain all nodes
    west, east = min(x_vals), max(x_vals)
    south, north = min(y_vals), max(y_vals)
    
    # Add a small buffer for visual appeal
    buffer_ratio = 0.05
    width_buffer = (east - west) * buffer_ratio
    height_buffer = (north - south) * buffer_ratio
    
    # Plot simple path
    if simple_path:
        # Set background color for ax1
        ax1.set_facecolor(bgcolor)
        
        # Draw all edges as gray lines for the road network
        for u, v, data in graph.edges(data=True):
            if 'geometry' in data:
                xs, ys = data['geometry'].xy
            else:
                xs = [graph.nodes[u]['x'], graph.nodes[v]['x']]
                ys = [graph.nodes[u]['y'], graph.nodes[v]['y']]
            ax1.plot(xs, ys, color=edge_color, lw=0.8, alpha=0.5, zorder=1)
        
        # Draw the simple path as a blue line
        simple_path_edges = list(zip(simple_path[:-1], simple_path[1:]))
        for u, v in simple_path_edges:
            data = graph.get_edge_data(u, v)[0]
            if 'geometry' in data:
                xs, ys = data['geometry'].xy
            else:
                xs = [graph.nodes[u]['x'], graph.nodes[v]['x']]
                ys = [graph.nodes[u]['y'], graph.nodes[v]['y']]
            ax1.plot(xs, ys, color='#00BFFF', lw=3, alpha=1, zorder=2)
        
        # Set axis limits
        ax1.set_xlim(west - width_buffer, east + width_buffer)
        ax1.set_ylim(south - height_buffer, north + height_buffer)
        
        # Set title with bright text
        ax1.set_title("Route with Simple Geodesic Distance Heuristic", fontsize=14, color="white")
        ax1.set_xlabel("Longitude", color="white")
        ax1.set_ylabel("Latitude", color="white")
        ax1.tick_params(colors="white")
    
    # Plot advanced path
    if advanced_path:
        # Set background color for ax2
        ax2.set_facecolor(bgcolor)
        
        # Draw all edges as gray lines for the road network
        for u, v, data in graph.edges(data=True):
            if 'geometry' in data:
                xs, ys = data['geometry'].xy
            else:
                xs = [graph.nodes[u]['x'], graph.nodes[v]['x']]
                ys = [graph.nodes[u]['y'], graph.nodes[v]['y']]
            ax2.plot(xs, ys, color=edge_color, lw=0.8, alpha=0.5, zorder=1)
        
        # Draw the advanced path as a red line
        advanced_path_edges = list(zip(advanced_path[:-1], advanced_path[1:]))
        for u, v in advanced_path_edges:
            data = graph.get_edge_data(u, v)[0]
            if 'geometry' in data:
                xs, ys = data['geometry'].xy
            else:
                xs = [graph.nodes[u]['x'], graph.nodes[v]['x']]
                ys = [graph.nodes[u]['y'], graph.nodes[v]['y']]
            ax2.plot(xs, ys, color='#FF4500', lw=3, alpha=1, zorder=2)
        
        # Set axis limits
        ax2.set_xlim(west - width_buffer, east + width_buffer)
        ax2.set_ylim(south - height_buffer, north + height_buffer)
        
        # Set title with bright text
        ax2.set_title("Route with Advanced Multi-Factor Heuristic\n(Distance, Speed, Road Condition, Traffic)", 
                      fontsize=14, color="white")
        ax2.set_xlabel("Longitude", color="white")
        ax2.set_ylabel("Latitude", color="white")
        ax2.tick_params(colors="white")
    
    # Add path length comparison text at the bottom
    if simple_path and advanced_path:
        plt.figtext(0.5, 0.01, 
                   f"Simple Path: {simple_length:.1f}m | Advanced Path: {advanced_length:.1f}m", 
                   ha="center", fontsize=12, color="white", 
                   bbox={"facecolor":"#333333", "alpha":0.8, "pad":5})
    
    # Ensure tight layout with space at the bottom for text
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.1)
    
    # Show the plot in a single window
    plt.show()