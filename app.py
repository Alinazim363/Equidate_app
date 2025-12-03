"""
Equidate - Fair Dating Meetup Finder
Streamlit Frontend Application
"""

import os
from math import radians, degrees, sin, cos, atan2

import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from geopy.extra.rate_limiter import RateLimiter
from pymongo import MongoClient
import pandas as pd

# Load environment variables - works for both local (.env) and Streamlit Cloud (secrets)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Running on Streamlit Cloud - dotenv not needed
    pass

# --- Page Configuration ---
st.set_page_config(
    page_title="Equidate - Find Your Fair Meetup Spot",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Global Geolocator (single instance) ---
geolocator = Nominatim(user_agent="equidate_streamlit_app")
geocode_raw = RateLimiter(geolocator.geocode, min_delay_seconds=1)

# --- Custom CSS for Styling ---
st.markdown("""
<style>
    /* Overall page background */
    .main {
        background: linear-gradient(135deg, #ffeaf3 0%, #f7f7ff 50%, #ffe8f0 100%);
    }

    /* Main header styling */
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #ff5c93;
        text-align: left;
        margin-bottom: 0.5rem;
    }

    .sub-header {
        font-size: 1.05rem;
        color: #666;
        text-align: left;
        margin-bottom: 0.5rem;
    }

    /* Sidebar styling */
    .sidebar-header {
        font-size: 1.3rem;
        font-weight: 600;
        color: #ff5c93;
        margin-bottom: 1rem;
    }

    /* Stats boxes */
    .stat-box {
        background: #ffffff;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
        border-left: 4px solid #ff5c93;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    }

    .stat-number {
        font-size: 1.8rem;
        font-weight: 700;
        color: #ff5c93;
    }

    .stat-label {
        font-size: 0.85rem;
        color: #666;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #ff5c93 0%, #ff7eb3 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        font-weight: 600;
        width: 100%;
        transition: transform 0.2s, box-shadow 0.2s;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(255, 92, 147, 0.4);
    }

    /* Loading spinner text - make it black */
    .stSpinner > div > div {
        color: #1f1f1f !important;
    }
    
    /* Spinner text */
    div[data-testid="stSpinner"] > div {
        color: #1f1f1f !important;
    }

    /* Venue card styling - make the expander look like cards */
    div[data-testid="stExpander"] {
        background: linear-gradient(135deg, #ff5c93 0%, #ff7eb3 100%) !important;
        border: 2px solid #ff5c93 !important;
        border-radius: 10px !important;
        margin-bottom: 12px !important;
        box-shadow: 0 2px 8px rgba(255, 92, 147, 0.2) !important;
        overflow: hidden;
    }

    div[data-testid="stExpander"]:hover {
        box-shadow: 0 4px 12px rgba(255, 92, 147, 0.3) !important;
        transform: translateY(-2px);
        transition: all 0.2s ease;
    }

    /* Make expander header text WHITE and visible */
    div[data-testid="stExpander"] details summary {
        background: linear-gradient(135deg, #ff5c93 0%, #ff7eb3 100%) !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        padding: 12px 16px !important;
    }

    div[data-testid="stExpander"] details summary p,
    div[data-testid="stExpander"] details summary strong {
        color: #ffffff !important;
    }

    /* Style the expanded content area with white background */
    div[data-testid="stExpander"] details[open] {
        background-color: #ffffff !important;
    }
    
    div[data-testid="stExpander"] div[role="button"] {
        background: linear-gradient(135deg, #ff5c93 0%, #ff7eb3 100%) !important;
    }

    /* Make metric labels and values BLACK in debug section */
    div[data-testid="stMetric"] label {
        color: #1f1f1f !important;
    }
    
    div[data-testid="stMetricValue"] {
        color: #1f1f1f !important;
    }

    div[data-testid="stMetricLabel"] {
        color: #1f1f1f !important;
    }

    /* Scrollable venue container */
    .scrollable-venues {
        max-height: 600px;
        overflow-y: auto;
        overflow-x: hidden;
        padding-right: 10px;
    }

    /* Custom scrollbar for venue section */
    .scrollable-venues::-webkit-scrollbar {
        width: 8px;
    }

    .scrollable-venues::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }

    .scrollable-venues::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #ff5c93 0%, #ff7eb3 100%);
        border-radius: 10px;
    }

    .scrollable-venues::-webkit-scrollbar-thumb:hover {
        background: #ff5c93;
    }
</style>
""", unsafe_allow_html=True)


# --- Database Connection ---
@st.cache_resource
def get_database():
    """Connect to MongoDB and return the venues collection."""
    try:
        # Try to get MONGO_URI from environment variable or Streamlit secrets
        mongo_uri = os.getenv("MONGO_URI")
        
        # If not in environment, try Streamlit secrets
        if not mongo_uri:
            try:
                mongo_uri = st.secrets["MONGO_URI"]
            except:
                pass
        
        if not mongo_uri:
            st.error("MongoDB URI not found. Please check your environment variables or Streamlit secrets.")
            return None
            
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)
        # Test connection
        client.server_info()
        db = client["Equidate_db"]
        venues_collection = db["Venues"]

        # Don't try to create index - it already exists
        # Just verify we can access the collection
        count = venues_collection.count_documents({}, limit=1)
        
        return venues_collection
    except Exception as e:
        st.error(f"Failed to connect to MongoDB: {str(e)}")
        return None


# --- Geocoding Functions ---
@st.cache_data(ttl=3600)
def geocode_address(address: str):
    """Convert a human-readable address to (latitude, longitude)."""
    try:
        location = geocode_raw(address, timeout=10)

        if not location:
            return None, None, f"Could not find location: {address}"

        return location.latitude, location.longitude, None
    except GeocoderTimedOut:
        return None, None, "Geocoding timed out. Please try again."
    except GeocoderUnavailable:
        return None, None, "Geocoding service unavailable. Please try again later."
    except Exception as e:
        return None, None, f"Geocoding error: {str(e)}"


def calculate_midpoint(lat1, lon1, lat2, lon2):
    """Calculate the geographic midpoint between two coordinates using spherical geometry."""
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Convert to Cartesian coordinates
    x1, y1, z1 = cos(lat1) * cos(lon1), cos(lat1) * sin(lon1), sin(lat1)
    x2, y2, z2 = cos(lat2) * cos(lon2), cos(lat2) * sin(lon2), sin(lat2)

    # Average the coordinates
    x, y, z = (x1 + x2) / 2, (y1 + y2) / 2, (z1 + z2) / 2

    # Convert back to lat/lon
    lon_mid = atan2(y, x)
    hyp = (x**2 + y**2) ** 0.5
    lat_mid = atan2(z, hyp)

    return degrees(lat_mid), degrees(lon_mid)


# --- Database Query Functions ---
def query_nearby_venues(venues_collection, mid_lat, mid_lon, max_distance=1500, category=None, limit=15):
    """Query MongoDB for venues near the midpoint using $geoNear aggregation."""
    import time
    
    if venues_collection is None:
        return [], None

    pipeline = [
        {
            "$geoNear": {
                "near": {
                    "type": "Point",
                    "coordinates": [mid_lon, mid_lat]  # MongoDB uses [lon, lat]
                },
                "distanceField": "distance",
                "maxDistance": max_distance,
                "spherical": True
            }
        }
    ]

    # Add category filter if specified
    if category and category != "All Categories":
        pipeline[0]["$geoNear"]["query"] = {
            "category": {"$regex": category, "$options": "i"}
        }

    pipeline.append({"$limit": limit})

    try:
        start_time = time.time()
        results = list(venues_collection.aggregate(pipeline))
        query_time = time.time() - start_time
        
        # Create debug info dictionary
        debug_info = {
            "pipeline": pipeline,
            "query_time_ms": round(query_time * 1000, 2),
            "results_count": len(results),
            "max_distance_m": max_distance,
            "category_filter": category if category and category != "All Categories" else "None"
        }
        
        return results, debug_info
    except Exception as e:
        error_msg = str(e)
        st.error(f"Database query error: {error_msg}")
        
        # Provide more specific error messages
        if "single index" in error_msg.lower():
            st.error("🔍 Index issue detected. The 'loc' field needs a 2dsphere index. Please check MongoDB Atlas Indexes tab.")
        elif "coordinates" in error_msg.lower():
            st.error("📍 Coordinate format issue. Please verify your venue documents have GeoJSON format.")
        
        return [], None


# --- Map Creation ---
def create_map(lat1, lon1, lat2, lon2, mid_lat, mid_lon, venues):
    """Create a Folium map with markers for both addresses, midpoint, and venues."""

    # Create map centered on midpoint
    m = folium.Map(
        location=[mid_lat, mid_lon],
        zoom_start=14,
        tiles="CartoDB positron"
    )

    # Add marker for Address 1 (Blue)
    folium.Marker(
        [lat1, lon1],
        popup="<b>Person 1's Location</b>",
        tooltip="Person 1",
        icon=folium.Icon(color="blue", icon="user", prefix="fa")
    ).add_to(m)

    # Add marker for Address 2 (Green)
    folium.Marker(
        [lat2, lon2],
        popup="<b>Person 2's Location</b>",
        tooltip="Person 2",
        icon=folium.Icon(color="green", icon="user", prefix="fa")
    ).add_to(m)

    # Add marker for Midpoint (Red star)
    folium.Marker(
        [mid_lat, mid_lon],
        popup="<b>Fair Meetup Point</b><br>Equidistant from both locations",
        tooltip="Midpoint",
        icon=folium.Icon(color="red", icon="star", prefix="fa")
    ).add_to(m)

    # Add circle to show search radius
    folium.Circle(
        [mid_lat, mid_lon],
        radius=st.session_state.get('search_radius', 1500),
        color="#FF6B6B",
        fill=True,
        fillOpacity=0.1,
        weight=2
    ).add_to(m)

    # Add markers for each venue
    for venue in venues:
        coords = venue.get("loc", {}).get("coordinates", [])
        if len(coords) >= 2:
            venue_lon, venue_lat = coords[0], coords[1]

            # Create popup content
            rating_val = venue.get('rating')
            if rating_val and rating_val != 'N/A':
                try:
                    rating_stars = '⭐' * int(float(rating_val))
                except ValueError:
                    rating_stars = 'N/A'
            else:
                rating_stars = 'N/A'

            popup_html = f"""
            <div style="width: 200px;">
                <h4 style="margin: 0; color: #333;">{venue.get('name', 'Unknown')}</h4>
                <p style="margin: 5px 0; font-size: 12px; color: #666;">
                    <b>Category:</b> {venue.get('category', 'N/A')}<br>
                    <b>Rating:</b> {rating_stars} ({venue.get('rating', 'N/A')})<br>
                    <b>Price:</b> {venue.get('price', 'N/A')}<br>
                    <b>Distance:</b> {int(venue.get('distance', 0))}m from midpoint<br>
                    <b>Address:</b> {venue.get('address', 'N/A')}
                </p>
            </div>
            """

            folium.Marker(
                [venue_lat, venue_lon],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=venue.get('name', 'Venue'),
                icon=folium.Icon(color="purple", icon="cutlery", prefix="fa")
            ).add_to(m)

    # Draw lines from each person to midpoint
    folium.PolyLine(
        [[lat1, lon1], [mid_lat, mid_lon]],
        color="blue",
        weight=2,
        opacity=0.6,
        dash_array="5, 10"
    ).add_to(m)

    folium.PolyLine(
        [[lat2, lon2], [mid_lat, mid_lon]],
        color="green",
        weight=2,
        opacity=0.6,
        dash_array="5, 10"
    ).add_to(m)

    return m


# --- Main Application ---
def main():
    # Top row: title on left, logo on right
    left_col, right_col = st.columns([4, 1])

    with left_col:
        st.markdown('<h1 class="main-header">📍 Equidate</h1>', unsafe_allow_html=True)
        st.markdown(
            '<p class="sub-header">Meet-in-the-middle venue finder powered by MongoDB geospatial queries.</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<p style="color: #888; font-size: 0.9rem; font-style: italic; margin-top: -0.5rem;">Note: Currently limited to venues within Manhattan, New York.</p>',
            unsafe_allow_html=True,
        )

    with right_col:
        logo_path = os.path.join("static", "logo.png")
        if os.path.exists(logo_path):
            st.image(logo_path, use_column_width=True)

    # Sidebar for inputs
    with st.sidebar:
        st.markdown('<p class="sidebar-header">🗺️ Enter Your Locations</p>', unsafe_allow_html=True)

        # Address inputs
        address1 = st.text_input(
            "Person 1's Address",
            placeholder="e.g., 350 5th Ave, New York, NY",
            help="Enter the first person's starting location",
        )

        address2 = st.text_input(
            "Person 2's Address",
            placeholder="e.g., 20 W 34th St, New York, NY",
            help="Enter the second person's starting location",
        )

        st.markdown("---")
        st.markdown('<p class="sidebar-header">⚙️ Search Options</p>', unsafe_allow_html=True)

        # Category filter
        categories = ["All Categories", "Italian", "Mexican", "Korean", "Ramen", "Bar", "Restaurant", "Cafe"]
        selected_category = st.selectbox(
            "Venue Category",
            categories,
            help="Filter results by type of venue",
        )

        # Search radius
        search_radius = st.slider(
            "Search Radius (meters)",
            min_value=500,
            max_value=3000,
            value=1500,
            step=100,
            help="How far from the midpoint to search",
        )
        st.session_state["search_radius"] = search_radius

        # Number of results
        max_results = st.slider(
            "Maximum Results",
            min_value=5,
            max_value=25,
            value=10,
            step=5,
        )

        st.markdown("---")

        # Search button
        search_clicked = st.button("🔍 Find Meetup Spots", use_container_width=True)

    # Handle search
    if search_clicked:
        if not address1 or not address2:
            st.warning("⚠️ Please enter both addresses to find a fair meetup spot.")
            return

        # Custom loading message with black text
        loading_placeholder = st.empty()
        loading_placeholder.markdown(
            """
            <div style="
                text-align: center;
                padding: 3rem;
                background: #ffffff;
                border-radius: 12px;
                margin: 2rem 0;
                border: 2px solid #ff5c93;
                box-shadow: 0 4px 12px rgba(255, 92, 147, 0.15);
            ">
                <h2 style="color: #ff5c93; margin-bottom: 1rem;">🔍 Finding Your Perfect Meetup Spot...</h2>
                <p style="color: #1f1f1f; font-size: 1.1rem;">
                    Calculating midpoint and searching for nearby venues
                </p>
                <div style="
                    width: 50px;
                    height: 50px;
                    border: 5px solid #f3f3f3;
                    border-top: 5px solid #ff5c93;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin: 1.5rem auto;
                "></div>
                <style>
                    @keyframes spin {
                        0% { transform: rotate(0deg); }
                        100% { transform: rotate(360deg); }
                    }
                </style>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Geocode addresses
        lat1, lon1, error1 = geocode_address(address1)
        lat2, lon2, error2 = geocode_address(address2)

        if error1:
            loading_placeholder.empty()
            st.error(f"❌ Address 1 Error: {error1}")
            return
        if error2:
            loading_placeholder.empty()
            st.error(f"❌ Address 2 Error: {error2}")
            return

        # Calculate midpoint
        mid_lat, mid_lon = calculate_midpoint(lat1, lon1, lat2, lon2)

        # Connect to database and query venues
        venues_collection = get_database()
        venues, query_debug_info = query_nearby_venues(
            venues_collection,
            mid_lat,
            mid_lon,
            max_distance=search_radius,
            category=selected_category if selected_category != "All Categories" else None,
            limit=max_results,
        )

        # Clear loading message
        loading_placeholder.empty()

        # Store results in session state
        st.session_state["results"] = {
            "lat1": lat1,
            "lon1": lon1,
            "lat2": lat2,
            "lon2": lon2,
            "mid_lat": mid_lat,
            "mid_lon": mid_lon,
            "venues": venues,
            "address1": address1,
            "address2": address2,
            "selected_category": selected_category,
            "max_results": max_results,
            "search_radius": search_radius,
            "query_debug_info": query_debug_info,
        }

    # Display results if available
    if "results" in st.session_state:
        results = st.session_state["results"]

        # Stats row
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(
                """
            <div class="stat-box">
                <div class="stat-number">{}</div>
                <div class="stat-label">Venues Found</div>
            </div>
            """.format(
                    len(results["venues"])
                ),
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown(
                """
            <div class="stat-box">
                <div class="stat-number">{:.4f}°</div>
                <div class="stat-label">Midpoint Latitude</div>
            </div>
            """.format(
                    results["mid_lat"]
                ),
                unsafe_allow_html=True,
            )

        with col3:
            st.markdown(
                """
            <div class="stat-box">
                <div class="stat-number">{:.4f}°</div>
                <div class="stat-label">Midpoint Longitude</div>
            </div>
            """.format(
                    results["mid_lon"]
                ),
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # Map and results columns
        map_col, results_col = st.columns([3, 2])

        with map_col:
            # Dark heading
            st.markdown(
                "<h3 style='color:#1f1f1f; font-weight:600;'>🗺️ Interactive Map</h3>",
                unsafe_allow_html=True,
            )

            m = create_map(
                results["lat1"],
                results["lon1"],
                results["lat2"],
                results["lon2"],
                results["mid_lat"],
                results["mid_lon"],
                results["venues"],
            )
            st_folium(m, width=None, height=500, use_container_width=True)

            # Legend with dark text
            st.markdown(
                """
            <div style="color:#1f1f1f; font-size:0.9rem; margin-top:0.5rem;">
                <strong>Map Legend:</strong><br>
                • 🔵 Blue marker: Person 1's location<br>
                • 🟢 Green marker: Person 2's location<br>
                • ⭐ Red star: Fair midpoint<br>
                • 🟣 Purple markers: Suggested venues
            </div>
            """,
                unsafe_allow_html=True,
            )

        with results_col:
            # Dark heading
            st.markdown(
                "<h3 style='color:#1f1f1f; font-weight:600;'>📋 Nearby Venues</h3>",
                unsafe_allow_html=True,
            )

            if not results["venues"]:
                st.info(
                    "No venues found in this area. Try increasing the search radius or changing the category."
                )
            else:
                # Build all venue cards HTML with proper escaping
                import html
                
                venues_html = '<div class="scrollable-venues">'
                
                for i, venue in enumerate(results["venues"], 1):
                    distance = int(venue.get("distance", 0))
                    rating = venue.get("rating", "N/A")
                    price = venue.get("price", "")

                    # Create rating stars
                    if rating and rating != "N/A":
                        try:
                            stars = "⭐" * int(float(rating))
                        except ValueError:
                            stars = "No rating"
                    else:
                        stars = "No rating"

                    # Properly escape all text content
                    venue_name = html.escape(str(venue.get("name", "Unknown Venue")))
                    venue_address = html.escape(str(venue.get("address", "N/A")))
                    venue_category = html.escape(str(venue.get('category', 'N/A')))
                    price_display = html.escape(str(price if price else 'N/A'))
                    stars_escaped = html.escape(stars)

                    # Google Maps link
                    maps_query = f"{venue.get('name', 'Unknown Venue')} {venue.get('address', 'N/A')}".replace(" ", "+")
                    maps_url = f"https://www.google.com/maps/search/?api=1&query={maps_query}"

                    # Add card to HTML - single line to avoid issues
                    card_html = f'<div style="background: linear-gradient(135deg, rgb(255, 92, 147) 0%, rgb(255, 126, 179) 100%); border-radius: 12px; padding: 16px; margin-bottom: 16px; box-shadow: 0 4px 12px rgba(255, 92, 147, 0.25); border: 2px solid rgb(255, 92, 147);"><h4 style="color: rgb(255, 255, 255); margin: 0 0 12px 0; font-weight: 600;">{i}. {venue_name} – {distance}m away</h4><p style="color: rgb(255, 255, 255); margin: 6px 0; font-size: 0.95rem;"><b>Category:</b> {venue_category}</p><p style="color: rgb(255, 255, 255); margin: 6px 0; font-size: 0.95rem;"><b>Rating:</b> {stars_escaped} ({rating})</p><p style="color: rgb(255, 255, 255); margin: 6px 0; font-size: 0.95rem;"><b>Price:</b> {price_display}</p><p style="color: rgb(255, 255, 255); margin: 6px 0; font-size: 0.95rem;"><b>Address:</b> {venue_address}</p><p style="color: rgb(255, 255, 255); margin: 6px 0; font-size: 0.95rem;"><b>Distance from midpoint:</b> {distance} meters</p><a href="{maps_url}" target="_blank" style="color: rgb(255, 255, 255); background-color: rgba(255, 255, 255, 0.2); padding: 8px 16px; border-radius: 6px; text-decoration: none; display: inline-block; margin-top: 8px; font-weight: 600; border: 1px solid rgba(255, 255, 255, 0.3);">📍 Open in Google Maps</a></div>'
                    
                    venues_html += card_html
                
                # Close scrollable container
                venues_html += '</div>'
                
                # Render all at once
                st.markdown(venues_html, unsafe_allow_html=True)

        # Additional info
        st.markdown("---")
        st.markdown(
            """
        <div style="text-align: center; color: #444; font-size: 0.9rem;">
            <p>💡 <b>Tip:</b> Click on any marker on the map for more details about that location.</p>
            <p>The midpoint is calculated using spherical geometry for accuracy.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # --- Developer Debug Section (button at bottom) ---
        if "show_debug" not in st.session_state:
            st.session_state["show_debug"] = False

        if st.button("🧑‍💻 Toggle Developer Debug Info", use_container_width=True):
            st.session_state["show_debug"] = not st.session_state["show_debug"]

        if st.session_state["show_debug"]:
            with st.expander("🔧 Developer Debug Info", expanded=True):
                # Add styling for black text in debug section
                st.markdown("""
                <style>
                    .debug-section {
                        color: #1f1f1f !important;
                    }
                    .debug-section h3 {
                        color: #ff5c93 !important;
                    }
                    .debug-section p, .debug-section li {
                        color: #333 !important;
                    }
                </style>
                <div class="debug-section">
                """, unsafe_allow_html=True)
                
                st.markdown('<h3 style="color: #ff5c93;">🗄️ MongoDB Query Details</h3>', unsafe_allow_html=True)
                
                if results.get("query_debug_info"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Query Execution Time", f"{results['query_debug_info']['query_time_ms']} ms")
                    with col2:
                        st.metric("Results Returned", results['query_debug_info']['results_count'])
                    with col3:
                        st.metric("Max Distance", f"{results['query_debug_info']['max_distance_m']} m")
                    
                    st.markdown('<p style="color: #1f1f1f; font-weight: 600;">MongoDB Aggregation Pipeline:</p>', unsafe_allow_html=True)
                    st.json(results["query_debug_info"]["pipeline"])
                    
                    st.markdown("""
                    <div style="color: #1f1f1f;">
                    <p><strong>Pipeline Explanation:</strong></p>
                    <ul>
                        <li><strong>$geoNear</strong>: Performs geospatial query using 2dsphere index</li>
                        <li><strong>near</strong>: Target coordinates (midpoint) in GeoJSON format [longitude, latitude]</li>
                        <li><strong>distanceField</strong>: Adds calculated distance to each result</li>
                        <li><strong>maxDistance</strong>: Maximum radius in meters</li>
                        <li><strong>spherical</strong>: Uses spherical geometry for accurate Earth distances</li>
                        <li><strong>$limit</strong>: Limits number of results returned</li>
                    </ul>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("---")
                st.markdown('<h3 style="color: #ff5c93;">📍 Geocoding & Coordinates</h3>', unsafe_allow_html=True)
                
                # Calculate distance between the two addresses
                from math import radians, sin, cos, sqrt, atan2
                R = 6371000  # Earth's radius in meters
                
                lat1_rad = radians(results["lat1"])
                lat2_rad = radians(results["lat2"])
                delta_lat = radians(results["lat2"] - results["lat1"])
                delta_lon = radians(results["lon2"] - results["lon1"])
                
                a = sin(delta_lat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon/2)**2
                c = 2 * atan2(sqrt(a), sqrt(1-a))
                total_distance = R * c
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown('<p style="color: #1f1f1f; font-weight: 600;">Person 1 Location:</p>', unsafe_allow_html=True)
                    st.json({
                        "address": results["address1"],
                        "latitude": results["lat1"],
                        "longitude": results["lon1"],
                        "geocoding_service": "Nominatim (OpenStreetMap)"
                    })
                
                with col2:
                    st.markdown('<p style="color: #1f1f1f; font-weight: 600;">Person 2 Location:</p>', unsafe_allow_html=True)
                    st.json({
                        "address": results["address2"],
                        "latitude": results["lat2"],
                        "longitude": results["lon2"],
                        "geocoding_service": "Nominatim (OpenStreetMap)"
                    })
                
                st.markdown('<p style="color: #1f1f1f; font-weight: 600;">Calculated Midpoint:</p>', unsafe_allow_html=True)
                st.json({
                    "latitude": results["mid_lat"],
                    "longitude": results["mid_lon"],
                    "method": "Spherical geometry (Cartesian coordinates)",
                    "distance_between_addresses_m": round(total_distance, 2),
                    "distance_between_addresses_km": round(total_distance / 1000, 2),
                    "average_distance_to_midpoint_m": round(total_distance / 2, 2)
                })
                
                st.markdown("""
                <div style="color: #1f1f1f;">
                <p><strong>Midpoint Calculation Formula:</strong></p>
                <ol>
                    <li>Convert lat/lon to radians</li>
                    <li>Convert to 3D Cartesian coordinates (x, y, z)</li>
                    <li>Average the Cartesian coordinates</li>
                    <li>Convert back to lat/lon</li>
                </ol>
                <p>This ensures geographic accuracy on a sphere (Earth's surface).</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("---")
                st.markdown('<h3 style="color: #ff5c93;">🔍 Search Parameters</h3>', unsafe_allow_html=True)
                st.json({
                    "search_radius_meters": results["search_radius"],
                    "search_radius_kilometers": round(results["search_radius"] / 1000, 2),
                    "max_results_requested": results["max_results"],
                    "actual_results_returned": len(results["venues"]),
                    "selected_category": results["selected_category"],
                    "category_filter_applied": results["selected_category"] != "All Categories"
                })
                
                st.markdown("---")
                st.markdown('<h3 style="color: #ff5c93;">📊 Data Quality Analysis</h3>', unsafe_allow_html=True)
                
                if results["venues"]:
                    venues_with_rating = sum(1 for v in results["venues"] if v.get("rating") and v.get("rating") != "N/A")
                    venues_with_price = sum(1 for v in results["venues"] if v.get("price"))
                    venues_with_category = sum(1 for v in results["venues"] if v.get("category"))
                    venues_with_address = sum(1 for v in results["venues"] if v.get("address"))
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Has Rating", f"{venues_with_rating}/{len(results['venues'])}")
                    with col2:
                        st.metric("Has Price", f"{venues_with_price}/{len(results['venues'])}")
                    with col3:
                        st.metric("Has Category", f"{venues_with_category}/{len(results['venues'])}")
                    with col4:
                        st.metric("Has Address", f"{venues_with_address}/{len(results['venues'])}")
                    
                    # Distance distribution
                    distances = [v.get("distance", 0) for v in results["venues"]]
                    st.markdown('<p style="color: #1f1f1f; font-weight: 600;">Distance Distribution:</p>', unsafe_allow_html=True)
                    st.json({
                        "min_distance_m": round(min(distances), 2),
                        "max_distance_m": round(max(distances), 2),
                        "avg_distance_m": round(sum(distances) / len(distances), 2),
                        "median_distance_m": round(sorted(distances)[len(distances)//2], 2)
                    })
                
                st.markdown("---")
                st.markdown('<h3 style="color: #ff5c93;">🗃️ Database Connection Info</h3>', unsafe_allow_html=True)
                
                venues_collection = get_database()
                if venues_collection is not None:
                    try:
                        # Get collection stats
                        total_venues = venues_collection.count_documents({})
                        indexes = venues_collection.list_indexes()
                        index_info = [{"name": idx["name"], "keys": dict(idx["key"])} for idx in indexes]
                        
                        st.json({
                            "database": "Equidate_db",
                            "collection": "Venues",
                            "total_venues_in_db": total_venues,
                            "connection_status": "✅ Connected",
                            "indexes": index_info
                        })
                        
                        st.markdown("""
                        <div style="color: #1f1f1f;">
                        <p><strong>Index Explanation:</strong></p>
                        <ul>
                            <li><strong>2dsphere index on 'loc'</strong>: Enables efficient geospatial queries</li>
                            <li>This index is critical for the $geoNear aggregation to work</li>
                            <li>Without it, queries would be much slower (full collection scan)</li>
                        </ul>
                        </div>
                        """, unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Could not fetch collection stats: {e}")
                else:
                    st.error("❌ Database connection failed")
                
                st.markdown("---")
                st.markdown('<h3 style="color: #ff5c93;">📋 Raw Venue Data</h3>', unsafe_allow_html=True)
                
                if results["venues"]:
                    debug_rows = []
                    for v in results["venues"]:
                        coords = v.get("loc", {}).get("coordinates", [None, None])
                        debug_rows.append({
                            "name": v.get("name", ""),
                            "address": v.get("address", ""),
                            "category": v.get("category", None),
                            "rating": v.get("rating", None),
                            "price": v.get("price", None),
                            "lat": coords[1],
                            "lon": coords[0],
                            "distance_m": round(v.get("distance", 0), 2),
                            "place_id": v.get("place_id", None),
                            "data_id": v.get("data_id", None),
                            "data_cid": v.get("data_cid", None),
                        })
                    
                    st.markdown(f'<p style="color: #1f1f1f; font-weight: 600;">All {len(debug_rows)} Venues (Table View):</p>', unsafe_allow_html=True)
                    st.dataframe(pd.DataFrame(debug_rows), use_container_width=True)
                    
                    st.markdown('<p style="color: #1f1f1f; font-weight: 600;">Raw JSON (First 3 Venues):</p>', unsafe_allow_html=True)
                    for i, v in enumerate(results["venues"][:3], 1):
                        st.markdown(f'<p style="color: #ff5c93; font-weight: 600; margin-top: 1rem;">Venue {i}: {v.get("name", "Unknown")}</p>', unsafe_allow_html=True)
                        st.json(v)
                
                st.markdown("</div>", unsafe_allow_html=True)

    else:
        # Welcome message when no search has been performed
        st.markdown(
            """
        <div style="
            text-align: center;
            padding: 3rem;
            background: #ffffff;
            border-radius: 12px;
            margin: 2rem 0;
            border: 1px solid rgba(0,0,0,0.05);
            box-shadow: 0 4px 12px rgba(255,92,147,0.15);
        ">
            <h2 style="color: #1f1f1f;">👋 Welcome to <span style="color:#ff5c93;">Equidate</span>!</h2>
            <p style="color: #333; font-size: 1.05rem; max-width: 650px; margin: 1rem auto; line-height: 1.6;">
                Finding a fair place to meet shouldn't be complicated. Enter two addresses
                in the sidebar, choose a venue category, and we'll find the midpoint and show nearby spots.
            </p>
            <p style="color: #777; font-size: 0.9rem; max-width: 650px; margin: 0.5rem auto;">
                We use <b>geopy</b> to geocode, spherical geometry to compute the midpoint, and
                <b>MongoDB $geoNear</b> to fetch real venues around that point.
            </p>
            <p style="color: #888; font-size: 0.9rem; margin-top: 1rem;">
                🔵 Person 1 &nbsp;&nbsp;→&nbsp;&nbsp; ⭐ Midpoint &nbsp;&nbsp;←&nbsp;&nbsp; 🟢 Person 2
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Feature highlights
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(
                """
            <div style="text-align: center; padding: 1.5rem;">
                <h3 style="color:#1f1f1f;">📍 Midpoint Calculation</h3>
                <p style="color: #666;">Uses spherical geometry so the midpoint is geographically accurate.</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown(
                """
            <div style="text-align: center; padding: 1.5rem;">
                <h3 style="color:#1f1f1f;">🍽️ Real Venues</h3>
                <p style="color: #666;">Sourced Directly From <b>Google!</b></p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col3:
            st.markdown(
                """
            <div style="text-align: center; padding: 1.5rem;">
                <h3 style="color:#1f1f1f;">🗺️ Interactive Map</h3>
                <p style="color: #666;">See both users, the midpoint, and all suggested venues at a glance.</p>
            </div>
            """,
                unsafe_allow_html=True,
            )


if __name__ == "__main__":
    main()