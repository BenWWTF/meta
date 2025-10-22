# Web UI Guide - Austrian Research Metadata Platform

The ARMP now includes a complete web interface built with Tailwind CSS for easy exploration of Austrian research.

## Quick Start

### 1. Start the API Server

```bash
cd /Users/Missbach/Desktop/claude/meta
source venv/bin/activate
python -m uvicorn app.main:app --reload
```

### 2. Open Web Interface

Navigate to **http://localhost:8000** in your browser

## Pages & Features

### 🏠 Homepage (`/`)

**What you can do:**
- See platform statistics (total publications, organizations, open access %)
- View research trends by year and publication type
- Search publications directly
- Browse featured universities
- Learn about ARMP

**Key Features:**
- **Interactive charts** showing publications over time
- **Quick search bar** with year range and type filters
- **Featured organizations** showing top universities
- **Open access statistics** tracking percentage

---

### 🔍 Search Publications (`/search`)

**Advanced search interface** with full filtering capabilities.

**Filters:**
- Keywords (title, abstract, author)
- Year range (from/to)
- Organization (filter by university)
- Publication type (article, book, dataset, software, etc.)
- Open access only toggle

**Results:**
- Publication title and abstract
- Author list
- Publication year and type
- Journal name (if applicable)
- DOI with link to publication
- Open access badge (if applicable)

**Pagination:**
- 20 results per page
- Previous/Next navigation
- Result count

---

### 🏫 Organizations (`/organizations`)

Browse all 15+ Austrian universities and research institutions.

**For Each Organization:**
- Publication count
- Researcher count
- Type (University, Research Institute, etc.)
- Direct links to:
  - View detailed organization page
  - Search that organization's publications
  - Visit organization website

**Features:**
- Search/filter by name
- Load more organizations
- Sort by publication count
- Responsive grid layout

---

### 📊 Organization Details (`/organizations/{org_id}`)

Detailed view of a specific organization's research output.

**Statistics:**
- Total publications
- Number of researchers
- Open access percentage

**Visualizations:**
- Publications by year (line chart)
- Publications by type (bar chart)
- Recent publications list

**Navigation:**
- Link to search this organization's publications
- Website link (if available)

---

### ℹ️ About Page (`/about`)

Learn about ARMP, its mission, and data sources.

**Sections:**
- What is ARMP
- Data sources (OpenAIRE, Crossref, ORCID, FWF)
- Coverage (15+ institutions)
- Technology stack
- Open source license
- Contact information

---

### 📞 Contact Page (`/contact`)

Get in touch with the ARMP team.

**Features:**
- Contact form
- Email address
- General inquiries

---

## Navigation

**Top Navigation Bar:**
- **Logo** - Links to homepage
- **Menu Links** - Home, Search, Organizations, About
- **API Docs** - Link to `/docs` for advanced users
- **Mobile Menu** - Responsive hamburger menu for small screens

**Footer:**
- Quick links
- About section
- Contact information
- Copyright and policies

---

## Features by Page

### Homepage
```
✓ Statistics dashboard
✓ Interactive charts
✓ Quick search
✓ Featured organizations
✓ About section
```

### Search
```
✓ Advanced filtering
✓ Full-text search
✓ Year range filter
✓ Organization filter
✓ Publication type filter
✓ Open access filter
✓ Pagination
✓ Result preview
```

### Organizations
```
✓ Organization listing
✓ Search/filter
✓ Sort by publication count
✓ Links to details and publications
✓ Responsive grid
```

### Organization Detail
```
✓ Statistics summary
✓ Publications by year chart
✓ Publications by type chart
✓ Recent publications list
✓ Direct publication search link
```

---

## Design Features

### Responsive Design
- ✓ Mobile-first approach
- ✓ Tablets, laptops, and desktop support
- ✓ Touch-friendly buttons and inputs
- ✓ Hamburger menu on mobile

### Accessibility
- ✓ Semantic HTML
- ✓ ARIA labels where needed
- ✓ Keyboard navigation support
- ✓ Color contrast compliance

### Performance
- ✓ CDN-delivered Tailwind CSS (no build step)
- ✓ Lightweight JavaScript (Alpine.js)
- ✓ Chart.js for efficient visualizations
- ✓ Async API calls
- ✓ Optimized database queries

### Visual Design
- ✓ Professional color scheme (blue and purple gradients)
- ✓ Consistent card-based layout
- ✓ Smooth animations and transitions
- ✓ Clear hierarchy and spacing
- ✓ Interactive hover states

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `/` | Focus search (coming soon) |
| `Escape` | Close mobile menu |
| `Enter` | Submit form |
| `Tab` | Navigate form elements |

---

## Example Use Cases

### Finding Publications
```
1. Go to /search
2. Enter keyword (e.g., "quantum computing")
3. Filter by year (2020-2024)
4. Click "Search"
5. Browse results, click DOI links to publications
```

### Comparing Universities
```
1. Go to /organizations
2. Click on University of Vienna
3. Note statistics and trends
4. Click back and view TU Wien
5. Compare publication trends
```

### Exploring Recent Research
```
1. Go to homepage
2. View publications by year chart
3. Click "Start Searching"
4. Set year_from to 2023
5. Browse recent publications
```

### Finding Researchers
```
1. Go to /search
2. Search by author name
3. View all publications by that author
4. See co-authors and collaboration patterns
```

---

## Browser Support

**Fully Supported:**
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

**Mobile Browsers:**
- iOS Safari 14+
- Chrome Mobile
- Firefox Mobile

---

## Tips & Tricks

1. **Advanced Search**: Combine multiple filters for precise results
2. **Organization Comparison**: Compare research output across universities
3. **Trending Topics**: Check the year chart on homepage to see research trends
4. **Publication Details**: Click DOI link to access full paper on publisher's website
5. **Export Results**: Copy results directly from search page

---

## Feedback & Issues

Found a bug or have a feature request?

**Report Issues:**
- Email: research@example.at
- Visit: /about or /contact pages

**Common Issues:**

**Q: Charts not loading?**
A: Ensure JavaScript is enabled. Try refreshing the page.

**Q: Search not returning results?**
A: Try broadening your search query or removing some filters.

**Q: Organization page not found?**
A: Ensure the organization exists in the /organizations list.

---

## Next Features (Coming Soon)

- [ ] Researcher profiles with publication history
- [ ] Co-author network visualization
- [ ] Project-publication linking
- [ ] Export search results (CSV, JSON)
- [ ] Advanced filters (subject area, funding)
- [ ] Saved searches and preferences
- [ ] Bookmarking favorite publications

---

## Developer Notes

### Technologies Used
- **FastAPI** - Backend framework
- **Jinja2** - Template rendering
- **Tailwind CSS** - Styling
- **Chart.js** - Visualizations
- **Alpine.js** - Lightweight interactivity
- **Fetch API** - Async data loading

### Template Structure
```
app/templates/
├── base.html              # Base layout with nav/footer
├── index.html            # Homepage
├── search.html           # Publication search
├── organizations.html    # Organization listing
├── organization_detail.html  # Organization detail
├── about.html            # About page
└── contact.html          # Contact page
```

### Adding a New Page

1. Create template in `app/templates/newpage.html`
2. Extend `base.html`
3. Add route in `app/api/web.py`
4. Add nav link in `base.html`

---

## API Integration

All web pages fetch data from the REST API endpoints:

```
GET  /api/publications
GET  /api/organizations
GET  /api/organizations/{id}
GET  /api/organizations/{id}/stats
GET  /api/publications/stats/overview
GET  /api/publications/by-organization/{org_id}
```

See `/docs` for full API documentation.

---

**Happy exploring!** 🚀
