# Equidate Frontend

**Streamlit-based web interface for the Equidate meetup finder application**

This is the frontend component of Equidate, a meet-in-the-middle venue finder that helps two people find fair places to meet using geographic midpoint calculations and MongoDB geospatial queries.

🔗 **Live Demo**: [Your Streamlit Cloud URL here]

---

## About This Frontend

The Equidate frontend is built with **Streamlit** and provides an intuitive web interface for:
- Entering two addresses
- Calculating the geographic midpoint
- Displaying nearby venues on an interactive map
- Filtering venues by category and distance
- Viewing detailed venue information

---

## Features

### User Interface
- **Clean, Modern Design**: Pink gradient theme with responsive layout
- **Interactive Map**: Powered by Folium, showing both locations, midpoint, and venues
- **Scrollable Venue Cards**: Beautiful cards with ratings, prices, and Google Maps integration
- **Real-time Search**: Instant results when clicking "Find Meetup Spots"
- **Category Filtering**: Filter by Restaurant, Cafe, Bar, and more
- **Adjustable Search Radius**: 500m to 3000m range

### Developer Features
- **Debug Mode**: Comprehensive backend insights including:
  - MongoDB query performance metrics
  - Aggregation pipeline details
  - Geocoding information
  - Data quality analysis
  - Database connection stats

---

## Technical Architecture

### Frontend Stack
- **Framework**: Streamlit 1.28.0
- **Mapping**: Folium 0.14.0 + streamlit-folium
- **Geocoding**: GeoPy (Nominatim/OpenStreetMap)
- **Data Display**: Pandas for debug tables

### Key Components

**1. Geocoding Service**
- Uses Nominatim API for address-to-coordinate conversion
- Rate-limited to 1 request/second
- Results cached for 1 hour using `@st.cache_data`

**2. Midpoint Calculation**
- Spherical geometry algorithm using Cartesian coordinates
- Ensures geographic accuracy on Earth's curved surface
- Formula:
  1. Convert lat/lon to radians
  2. Transform to 3D Cartesian (x, y, z)
  3. Average coordinates
  4. Convert back to lat/lon

**3. Map Visualization**
- Blue marker: Person 1's location
- Green marker: Person 2's location  
- Red star: Calculated midpoint
- Purple markers: Suggested venues
- Circle overlay: Search radius visualization

**4. Venue Cards**
- Gradient pink background
- White text for readability
- Star ratings
- Price range indicators
- Direct Google Maps links
- Scrollable container (max 600px height)

---

## User Flow

1. User enters Address 1 and Address 2 in sidebar
2. User selects optional filters (category, radius, max results)
3. User clicks "🔍 Find Meetup Spots"
4. Frontend geocodes both addresses via Nominatim
5. Midpoint calculated using spherical geometry
6. MongoDB query sent via backend connection
7. Results displayed on map and in scrollable venue list
8. User can click venues for details or open in Google Maps

---

## Backend Integration

### MongoDB Connection
- Connects to `Equidate_db.Venues` collection
- Uses environment variable `MONGO_URI` from Streamlit secrets
- Creates 2dsphere index on `loc` field if not exists

### Geospatial Query
The app uses MongoDB's `$geoNear` aggregation:

```javascript
{
  "$geoNear": {
    "near": {
      "type": "Point",
      "coordinates": [longitude, latitude]
    },
    "distanceField": "distance",
    "maxDistance": 1500,  // in meters
    "spherical": true,
    "query": {
      "category": {"$regex": "Restaurant", "$options": "i"}
    }
  }
}
```

## Venue Data Structure

The frontend expects venue documents with this schema:

```json
{
  "name": "Sushi Damo",
  "address": "330 W 58th St, New York, NY 10019",
  "category": "Sushi restaurant",
  "rating": "4.3",
  "price": "$30-50",
  "loc": {
    "type": "Point",
    "coordinates": [-73.9857, 40.7484]  // [longitude, latitude]
  },
  "place_id": "ChIJxxxxx",
  "data_id": "12345",
  "data_cid": "67890"
}
```

Required fields:
- `name` (string)
- `loc.coordinates` (array: [lon, lat])

Optional but recommended:
- `address`, `category`, `rating`, `price`

---

## UI/UX Design Decisions


### Layout
- **Sidebar**: Input controls and filters (sticky)
- **Main area**: Split into map (60%) and venues (40%)
- **Scrollable venues**: Prevents long pages
- **Stats boxes**: Key metrics at the top
- **Developer debug**: Collapsible at bottom

### Responsive Design
- Columns adapt to screen width
- Map and venue list stack on mobile
- Touch-friendly buttons and cards
- Readable font sizes (0.95rem - 2.5rem)

---

## Debug Mode Features

Perfect for demonstrating technical depth to professors:

**MongoDB Metrics**
- Query execution time (milliseconds)
- Number of results returned
- Full aggregation pipeline JSON
- Pipeline stage explanations

**Geocoding Details**
- Raw coordinates for both addresses
- Distance between addresses
- Midpoint coordinates
- Geocoding service used

**Data Quality**
- Venues with/without ratings
- Venues with/without prices
- Completeness metrics
- Distance distribution (min/max/avg/median)

**Database Stats**
- Total venues in collection
- Active indexes
- Index types (2dsphere)
- Connection status

**Raw Data**
- Tabular view of all results
- Full JSON for first 3 venues
- All document fields visible

---

## Deployment Configuration

### Streamlit Cloud Settings

**Secrets (`.streamlit/secrets.toml`):**
```toml
MONGO_URI = "mongodb+srv://username:password@cluster.mongodb.net/"
```

**Config (`config.toml`):**
```toml
[theme]
primaryColor = "#ff5c93"
backgroundColor = "#ffeaf3"
secondaryBackgroundColor = "#ffffff"
textColor = "#1f1f1f"

[server]
maxUploadSize = 5
enableXsrfProtection = true
```

---

## Current Limitations

- **Geographic Scope**: Optimized for Manhattan, New York venues only
- **Geocoding Rate Limit**: 1 request/second (Nominatim free tier)
- **No User Authentication**: Public access, no saved preferences
- **Static Venue Data**: Not connected to live APIs (Google Places, Yelp, etc.)
- **Two Users Only**: Doesn't support group meetups (3+ people)

---

## Future Frontend Enhancements

### Short-term
- [ ] Add loading animations/skeletons
- [ ] Mobile-responsive improvements
- [ ] Dark mode toggle
- [ ] Share results via URL
- [ ] Print/PDF export

### Long-term  
- [ ] User accounts and saved searches
- [ ] Favorite venues
- [ ] Multiple location pins (3+ people)
- [ ] Travel time overlay (driving/transit/walking)
- [ ] Venue photos from APIs
- [ ] Real-time availability/reservations
- [ ] Filter by dietary restrictions, accessibility
- [ ] Multi-language support

---

## Key Files

```
frontend/
├── app2.py              # Main Streamlit application (1006 lines)
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

**app2.py Structure:**
- Lines 1-33: Imports and configuration
- Lines 35-166: Custom CSS styling
- Lines 168-209: Database connection and caching
- Lines 211-244: Geocoding functions
- Lines 246-271: Midpoint calculation
- Lines 273-314: MongoDB query function
- Lines 316-410: Map creation with Folium
- Lines 412-1006: Main Streamlit UI and logic

---

## Academic Context

This frontend was built as part of a database systems course project to demonstrate:

✅ **Geospatial Indexing**: Practical use of MongoDB 2dsphere indexes  
✅ **Query Optimization**: Efficient $geoNear aggregation vs. naive approaches  
✅ **Full-stack Integration**: Frontend ↔ Database communication  
✅ **Real-world Application**: Solving a practical problem (fair meetups)  
✅ **UI/UX Design**: Professional, user-friendly interface  
✅ **Documentation**: Production-ready code comments and debug tools  

---

## Known Issues

- Scrollable venue container may not work in older browsers (use Chrome/Firefox)
- Very long venue names may overflow cards on mobile
- Map markers can cluster at very close distances
- Emoji rendering varies by operating system

---

## Credits

**Built with:**
- [Streamlit](https://streamlit.io) - Web framework
- [Folium](https://python-visualization.github.io/folium/) - Interactive maps
- [GeoPy](https://geopy.readthedocs.io/) - Geocoding
- [OpenStreetMap](https://www.openstreetmap.org/) - Map tiles and geocoding
- [MongoDB](https://www.mongodb.com/) - Geospatial database

**Icons & Emojis:**
- Font Awesome (via Folium markers)
- Native emoji support

---

## Support

For issues or questions about the frontend:
- Check the Developer Debug section in the app
- Review error messages in the Streamlit interface
- Verify MongoDB connection in secrets

---

**Frontend Version**: 1.0.0  
**Last Updated**: December 2024  
**Streamlit Version**: 1.28.0