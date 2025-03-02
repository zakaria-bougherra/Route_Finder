import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt
from geopy.distance import geodesic
from matplotlib.widgets import Button
import sys
import traceback

# Load the OSM file
osm_file_path = "Taher_map.osm"
try:
    graph = ox.graph_from_xml(osm_file_path, bidirectional=True)
    # Add edge bearings to the graph
    graph = ox.add_edge_bearings(graph)
except Exception as e:
    print(f"Error loading map file: {e}")
    print("Please ensure 'Taher_map.osm' exists in the current directory")
    sys.exit(1)

def heuristic(u, v):
    try:
        u_lat, u_lon = graph.nodes[u]["y"], graph.nodes[u]["x"]
        v_lat, v_lon = graph.nodes[v]["y"], graph.nodes[v]["x"]
        
        # Geodesic distance in meters
        distance = geodesic((u_lat, u_lon), (v_lat, v_lon)).meters  
        
        # Retrieve edge data
        edge_data = graph.get_edge_data(u, v)
        if edge_data is None:
            return float('inf')  # If no edge exists, return infinite cost

        # Select the first available edge (OSMnx creates MultiGraphs)
        edge = list(edge_data.values())[0]

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
    except Exception as e:
        print(f"Heuristic calculation error: {e}")
        return float('inf')  # Return infinite cost on error

def interactive_route_finder():
    # Set up dark theme for matplotlib
    plt.style.use('dark_background')
    
    # Create figure and plot the graph
    fig, ax = plt.subplots(figsize=(12, 9))
    fig.patch.set_facecolor('#121212')  # Dark background for the entire figure
    ax.set_facecolor('#1e1e1e')  # Slightly lighter background for the plot area
    
    try:
        # Plot the base map with dark theme colors
        ox.plot_graph(graph, ax=ax, show=False, close=False, 
                     node_color='#333333', edge_color='#666666', 
                     bgcolor='#1e1e1e', node_size=0)
    except Exception as e:
        print(f"Error plotting graph: {e}")
        ax.text(0.5, 0.5, f"Error plotting map: {str(e)}", 
                ha='center', va='center', transform=ax.transAxes, color='white')
        plt.show()
        return
    
    # Store selected points
    selected_points = {'origin': None, 'destination': None}
    origin_marker = [None]
    destination_marker = [None]
    origin_label = [None]
    destination_label = [None]
    route_lines = []
    
    def on_click(event):
        try:
            # Ignore clicks outside the data area
            if event.inaxes != ax:
                return
            
            # Get clicked coordinates
            x, y = event.xdata, event.ydata
            
            # Find nearest node
            node = ox.distance.nearest_nodes(graph, X=x, Y=y)
            node_x = graph.nodes[node]['x']
            node_y = graph.nodes[node]['y']
            
            # Determine if this is origin or destination
            if selected_points['origin'] is None:
                selected_points['origin'] = node
                # Remove previous marker if exists
                if origin_marker[0]:
                    origin_marker[0].remove()
                if origin_label[0]:
                    origin_label[0].remove()
                
                # Add new marker for origin
                origin_marker[0] = ax.plot(node_x, node_y, 'o', color='#ff6b6b', markersize=12, markeredgecolor='white', markeredgewidth=1.5)[0]
                origin_label[0] = ax.text(node_x, node_y, 'Start', fontsize=12, color='white',
                        bbox=dict(facecolor='#ff6b6b', alpha=0.9, boxstyle='round,pad=0.5'), ha='center', va='bottom')
                plt.draw()
                plt.title("Now click to select destination", color='white', fontsize=14)
                
            elif selected_points['destination'] is None:
                selected_points['destination'] = node
                # Remove previous marker if exists
                if destination_marker[0]:
                    destination_marker[0].remove()
                if destination_label[0]:
                    destination_label[0].remove()
                
                # Add new marker for destination
                destination_marker[0] = ax.plot(node_x, node_y, 'o', color='#4ecdc4', markersize=12, markeredgecolor='white', markeredgewidth=1.5)[0]
                destination_label[0] = ax.text(node_x, node_y, 'Destination', fontsize=12, color='white',
                        bbox=dict(facecolor='#4ecdc4', alpha=0.9, boxstyle='round,pad=0.5'), ha='center', va='bottom')
                plt.draw()
                calculate_button.set_active(True)
                plt.title("Click 'Calculate Route' button to find the path", color='white', fontsize=14)
        except Exception as e:
            print(f"Error in on_click: {e}")
            plt.title(f"Error selecting point: {str(e)}", color='white')
            plt.draw()
    
    def clear_selections(event):
        try:
            # Reset selected points dictionary
            selected_points['origin'] = None
            selected_points['destination'] = None
            
            # Remove markers and labels (with proper checks)
            if origin_marker[0] is not None:
                if origin_marker[0] in ax.lines:
                    origin_marker[0].remove()
                origin_marker[0] = None
                
            if destination_marker[0] is not None:
                if destination_marker[0] in ax.lines:
                    destination_marker[0].remove()
                destination_marker[0] = None
                
            if origin_label[0] is not None:
                if origin_label[0] in ax.texts:
                    origin_label[0].remove()
                origin_label[0] = None
                
            if destination_label[0] is not None:
                if destination_label[0] in ax.texts:
                    destination_label[0].remove()
                destination_label[0] = None
            
            # Clear any existing route lines
            for line in route_lines:
                if line in ax.lines:
                    line.remove()
            route_lines.clear()
            
            # Remove any route info text or other texts
            texts_to_keep = []
            for text in ax.texts[:]:
                if text == origin_label[0] or text == destination_label[0]:
                    texts_to_keep.append(text)
                else:
                    text.remove()
            
            # Redraw the base map to ensure complete refresh
            ax.clear()
            ox.plot_graph(graph, ax=ax, show=False, close=False, 
                     node_color='#333333', edge_color='#666666', 
                     bgcolor='#1e1e1e', node_size=0)
                    
            calculate_button.set_active(False)
            plt.title("Click on map to select starting point", color='white', fontsize=14)
            plt.draw()
        except Exception as e:
            print(f"Error in clear_selections: {e}")
            traceback.print_exc()
            plt.title(f"Error clearing selections", color='white')
            plt.draw()
    
    def calculate_route(event):
        try:
            origin = selected_points['origin']
            destination = selected_points['destination']
            
            if origin is None or destination is None:
                plt.title("Please select both origin and destination points", color='white', fontsize=14)
                plt.draw()
                return
            
            # Find the shortest path
            shortest_path = nx.astar_path(graph, origin, destination, heuristic=heuristic, weight="length")
            
            # Calculate route statistics
            route_length = sum(graph[u][v][0].get('length', 0) for u, v in zip(shortest_path[:-1], shortest_path[1:]))
            route_length_km = route_length / 1000  # Convert to kilometers
            
            # Calculate estimated time based on average speed
            # Using a simplified version of the heuristic for time estimation
            estimated_time_min = 0
            for u, v in zip(shortest_path[:-1], shortest_path[1:]):
                edge = list(graph.get_edge_data(u, v).values())[0]
                road_type = edge.get("highway", "residential")
                speed_mapping = {"motorway": 100, "primary": 80, "secondary": 60, "residential": 40}
                speed_kmh = speed_mapping.get(road_type, 40)
                segment_length_km = edge.get('length', 0) / 1000
                segment_time_h = segment_length_km / speed_kmh
                estimated_time_min += segment_time_h * 60
            
            # Clear previous route lines
            for line in route_lines:
                if line in ax.lines:
                    line.remove()
            route_lines.clear()
            
            # Remove any route info text
            for text in ax.texts[:]:
                if text not in [origin_label[0], destination_label[0]]:
                    text.remove()
            
            # Plot the new route with BLUE color as requested
            # Using a bright, vibrant blue (#1a75ff) that stands out on dark background
            route_plot = ox.plot_graph_route(
                graph, shortest_path, route_color='#1a75ff', route_linewidth=4, 
                route_alpha=0.8, ax=ax, show=False, close=False
            )
            
            # Store the route lines for later removal
            for line in ax.lines:
                if line not in [origin_marker[0], destination_marker[0]]:
                    route_lines.append(line)
            
            # Add a route stats box
            stats_text = f"Distance: {route_length_km:.2f} km\nEst. Time: {estimated_time_min:.1f} min"
            plt.figtext(0.75, 0.85, stats_text, fontsize=12, color='white',
                       bbox=dict(facecolor='#333333', alpha=0.9, boxstyle='round,pad=0.5', edgecolor='#1a75ff'))
            
            # Update title with route information
            plt.title(f"Route found! ({len(shortest_path)} nodes)", color='white', fontsize=14)
            plt.draw()
            
        except nx.NetworkXNoPath:
            plt.title("No route found between selected points", color='white', fontsize=14)
            plt.draw()
        except Exception as e:
            print(f"Error calculating route: {e}")
            print(traceback.format_exc())
            plt.title(f"Error calculating route", color='white', fontsize=14)
            plt.draw()
    
    # Set up the click event
    fig.canvas.mpl_connect('button_press_event', on_click)
    
    # Add buttons for control with improved styling
    plt.subplots_adjust(bottom=0.2)  # Make room for buttons
    
    # Calculate route button
    calculate_button_ax = plt.axes([0.6, 0.05, 0.3, 0.075])
    calculate_button_ax.set_facecolor('#383838')
    calculate_button = Button(calculate_button_ax, 'Calculate Route', color='#1e1e1e', hovercolor='#1a75ff') # Blue hover
    calculate_button.label.set_color('white')
    calculate_button.on_clicked(calculate_route)
    calculate_button.set_active(False)  # Start disabled
    
    # Clear selection button
    clear_button_ax = plt.axes([0.1, 0.05, 0.3, 0.075])
    clear_button_ax.set_facecolor('#383838')
    clear_button = Button(clear_button_ax, 'Clear Selection', color='#1e1e1e', hovercolor='#ff6b6b')
    clear_button.label.set_color('white')
    clear_button.on_clicked(clear_selections)
    
    # Instructions
    plt.title("Click on map to select starting point", color='white', fontsize=14)
    plt.figtext(0.5, 0.01, "First click: Set start point | Second click: Set destination | Then click 'Calculate Route'",
               ha="center", fontsize=10, color='white', 
               bbox={"facecolor":"#383838", "alpha":0.9, "pad":5, "boxstyle": "round,pad=0.5"})
    
    # Display the map and keep window open
    plt.show()

if __name__ == "__main__":
    interactive_route_finder()