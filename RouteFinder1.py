import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt
from geopy.distance import geodesic
from matplotlib.widgets import Button
import sys

# 1. LOAD AND PREPARE GRAPH
osm_file_path = "Taher_map.osm"
try:
    graph = ox.graph_from_xml(osm_file_path, bidirectional=True)
    graph = ox.add_edge_bearings(graph)
except Exception as e:
    print(f"Error loading map file: {e}")
    sys.exit(1)

# 2. HEURISTIC FUNCTIONS
def simple_heuristic(u, v):
    u_pts = (graph.nodes[u]["y"], graph.nodes[u]["x"])
    v_pts = (graph.nodes[v]["y"], graph.nodes[v]["x"])
    return geodesic(u_pts, v_pts).meters

def advanced_heuristic(u, v):
    u_lat, u_lon = graph.nodes[u]["y"], graph.nodes[u]["x"]
    v_lat, v_lon = graph.nodes[v]["y"], graph.nodes[v]["x"]
    distance = geodesic((u_lat, u_lon), (v_lat, v_lon)).meters 
    
    edge_data = graph.get_edge_data(u, v)
    if not edge_data: return float('inf')
    edge = list(edge_data.values())[0]

    road_type = edge.get("highway", "residential")
    speed_map = {"motorway": 100, "primary": 80, "secondary": 60, "residential": 40}
    base_speed = (speed_map.get(road_type, 40) * 1000) / 3600
    
    cond_factor = {"good": 1.0, "average": 0.8, "poor": 0.5}.get(edge.get("road_condition", "good"), 1.0)
    traf_factor = {"low": 1.0, "medium": 0.7, "high": 0.4}.get(edge.get("traffic", "low"), 1.0)
    
    speed_mps = base_speed * cond_factor * traf_factor
    return distance / speed_mps if speed_mps > 0 else float('inf')

# 3. INTERACTIVE SETUP
def interactive_dual_route_finder():
    plt.style.use('dark_background')
    # Using 'constrained_layout' helps prevent the window from collapsing or overlapping
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    fig.patch.set_facecolor('#121212')

    def draw_base_maps():
        ax1.clear()
        ax2.clear()
        ox.plot_graph(graph, ax=ax1, show=False, close=False, 
                      node_color='#333333', edge_color='#444444', bgcolor='#1e1e1e', node_size=0)
        ox.plot_graph(graph, ax=ax2, show=False, close=False, 
                      node_color='#333333', edge_color='#444444', bgcolor='#1e1e1e', node_size=0)
        ax1.set_title("Simple (Distance Only)", color='white')
        ax2.set_title("Advanced (Speed/Traffic)", color='white')

    draw_base_maps()

    state = {'origin': None, 'destination': None}

    def on_click(event):
        if event.inaxes not in [ax1, ax2]: return
        
        node = ox.distance.nearest_nodes(graph, X=event.xdata, Y=event.ydata)
        node_x, node_y = graph.nodes[node]['x'], graph.nodes[node]['y']

        if state['origin'] is None:
            state['origin'] = node
            for ax in [ax1, ax2]:
                ax.plot(node_x, node_y, 'o', color='#ff6b6b', markersize=10, label='Start')
            fig.canvas.draw()
        
        elif state['destination'] is None:
            state['destination'] = node
            for ax in [ax1, ax2]:
                ax.plot(node_x, node_y, 'o', color='#4ecdc4', markersize=10, label='End')
            calc_btn.set_active(True)
            fig.canvas.draw()

    def calculate(event):
        if state['origin'] and state['destination']:
            try:
                # Calculate paths
                path_s = nx.astar_path(graph, state['origin'], state['destination'], 
                                       heuristic=simple_heuristic, weight="length")
                path_a = nx.astar_path(graph, state['origin'], state['destination'], 
                                       heuristic=advanced_heuristic, weight="length")

                # Important: Use show=False and close=False to keep window open
                ox.plot_graph_route(graph, path_s, route_color='#00BFFF', route_linewidth=5, 
                                    ax=ax1, show=False, close=False)
                ox.plot_graph_route(graph, path_a, route_color='#FF4500', route_linewidth=5, 
                                    ax=ax2, show=False, close=False)
                
                fig.canvas.draw_idle() # Refresh without closing
            except Exception as e:
                print(f"Routing Error: {e}")

    def reset(event):
        state['origin'] = None
        state['destination'] = None
        draw_base_maps()
        calc_btn.set_active(False)
        fig.canvas.draw()

    # Layout buttons
    fig.canvas.mpl_connect('button_press_event', on_click)
    ax_calc = plt.axes([0.55, 0.05, 0.15, 0.06])
    ax_reset = plt.axes([0.3, 0.05, 0.15, 0.06])
    calc_btn = Button(ax_calc, 'Find Routes', color='#2c3e50', hovercolor='#2980b9')
    reset_btn = Button(ax_reset, 'Reset', color='#2c3e50', hovercolor='#c0392b')
    
    calc_btn.on_clicked(calculate)
    reset_btn.on_clicked(reset)

    plt.show()

if __name__ == "__main__":
    interactive_dual_route_finder()