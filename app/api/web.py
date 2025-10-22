"""
Web UI Endpoints
================
Endpoints for serving HTML templates and web interface pages.

Routes:
- GET / - Homepage
- GET /search - Publication search page
- GET /organizations - Organization listing page
- GET /organizations/{org_id} - Organization detail page
- GET /about - About page
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import Depends

from app.database import get_db, Organization, Publication

router = APIRouter(tags=["Web UI"])


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Homepage with statistics and featured organizations."""
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader("app/templates"))
    template = env.get_template("index.html")
    return template.render(request=request)


@router.get("/search", response_class=HTMLResponse)
async def search(request: Request):
    """Publication search page."""
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader("app/templates"))
    template = env.get_template("search.html")
    return template.render(request=request)


@router.get("/analytics", response_class=HTMLResponse)
async def analytics(request: Request):
    """Analytics and insights dashboard."""
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader("app/templates"))
    template = env.get_template("analytics.html")
    return template.render(request=request)


@router.get("/organizations", response_class=HTMLResponse)
async def organizations_list(request: Request):
    """Organization listing page."""
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader("app/templates"))
    template = env.get_template("organizations.html")
    return template.render(request=request)


@router.get("/organizations/{org_id}", response_class=HTMLResponse)
async def organization_detail(org_id: str, request: Request, db: Session = Depends(get_db)):
    """Organization detail page."""
    from jinja2 import Environment, FileSystemLoader

    # Get organization
    org = db.query(Organization).filter(Organization.id == org_id).first()

    if not org:
        return "<h1>Organization not found</h1>"

    env = Environment(loader=FileSystemLoader("app/templates"))
    template = env.get_template("organization_detail.html")

    return template.render(request=request, organization=org)


@router.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    """About page."""
    from jinja2 import Environment, FileSystemLoader

    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>About - Austrian Research Metadata Platform</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-50">
        <nav class="sticky top-0 z-50 bg-white border-b border-gray-200 shadow-sm">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div class="flex justify-between items-center h-16">
                    <a href="/" class="flex items-center space-x-3">
                        <div class="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                            <span class="text-white font-bold text-lg">🔍</span>
                        </div>
                        <div>
                            <div class="font-bold text-gray-900">ARMP</div>
                            <div class="text-xs text-gray-500">Austrian Research</div>
                        </div>
                    </a>
                    <div class="hidden md:flex items-center space-x-8">
                        <a href="/" class="text-gray-700 hover:text-blue-600 transition">Home</a>
                        <a href="/search" class="text-gray-700 hover:text-blue-600 transition">Search</a>
                        <a href="/organizations" class="text-gray-700 hover:text-blue-600 transition">Organizations</a>
                        <a href="/about" class="text-gray-700 hover:text-blue-600 transition">About</a>
                    </div>
                    <a href="/docs" target="_blank" class="hidden md:inline px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm font-medium">
                        API Docs
                    </a>
                </div>
            </div>
        </nav>

        <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
            <h1 class="text-4xl font-bold mb-8">About ARMP</h1>

            <div class="space-y-8 text-gray-700">
                <section>
                    <h2 class="text-2xl font-bold mb-4 text-gray-900">What is ARMP?</h2>
                    <p class="mb-4">
                        The Austrian Research Metadata Platform (ARMP) is an open-source initiative to aggregate and
                        make discoverable Austrian research publications, datasets, and projects from the country's leading
                        universities and research institutions.
                    </p>
                    <p>
                        ARMP demonstrates that comprehensive national research infrastructure can be built rapidly using
                        openly available data sources and modern open-source technologies, without vendor lock-in.
                    </p>
                </section>

                <section>
                    <h2 class="text-2xl font-bold mb-4 text-gray-900">Data Sources</h2>
                    <div class="space-y-3">
                        <div class="bg-white rounded-lg p-4 border-l-4 border-blue-600">
                            <h3 class="font-bold text-gray-900">OpenAIRE</h3>
                            <p class="text-sm text-gray-600">European research infrastructure aggregating publications, datasets, and metadata from institutional repositories and national systems.</p>
                        </div>
                        <div class="bg-white rounded-lg p-4 border-l-4 border-purple-600">
                            <h3 class="font-bold text-gray-900">Crossref</h3>
                            <p class="text-sm text-gray-600">Scholarly publication metadata database covering 150+ million DOIs from academic publishers.</p>
                        </div>
                        <div class="bg-white rounded-lg p-4 border-l-4 border-green-600">
                            <h3 class="font-bold text-gray-900">ORCID</h3>
                            <p class="text-sm text-gray-600">International researcher identifiers enabling disambiguation and profile enrichment.</p>
                        </div>
                        <div class="bg-white rounded-lg p-4 border-l-4 border-yellow-600">
                            <h3 class="font-bold text-gray-900">FWF Research Radar</h3>
                            <p class="text-sm text-gray-600">Austrian Science Fund project data and funding information.</p>
                        </div>
                    </div>
                </section>

                <section>
                    <h2 class="text-2xl font-bold mb-4 text-gray-900">Coverage</h2>
                    <p class="mb-4">ARMP currently covers research from 15+ major Austrian research institutions:</p>
                    <ul class="list-disc list-inside space-y-1 text-sm">
                        <li>University of Vienna</li>
                        <li>TU Wien</li>
                        <li>University of Innsbruck</li>
                        <li>University of Graz</li>
                        <li>JKU Linz</li>
                        <li>Medical University of Vienna</li>
                        <li>TU Graz</li>
                        <li>University of Salzburg</li>
                        <li>And others...</li>
                    </ul>
                </section>

                <section>
                    <h2 class="text-2xl font-bold mb-4 text-gray-900">Technology</h2>
                    <p class="mb-4">ARMP is built with modern, open-source technologies:</p>
                    <ul class="list-disc list-inside space-y-1 text-sm">
                        <li><strong>FastAPI</strong> - High-performance Python web framework</li>
                        <li><strong>SQLAlchemy</strong> - Object-relational mapper for database access</li>
                        <li><strong>PostgreSQL/SQLite</strong> - Relational database</li>
                        <li><strong>Tailwind CSS</strong> - Utility-first CSS framework</li>
                        <li><strong>Chart.js</strong> - Data visualization</li>
                    </ul>
                </section>

                <section>
                    <h2 class="text-2xl font-bold mb-4 text-gray-900">Open Source & License</h2>
                    <p>
                        ARMP is open-source software released under the MIT License. The source code, documentation,
                        and all components are freely available and can be modified, distributed, and used for any purpose.
                    </p>
                </section>

                <section>
                    <h2 class="text-2xl font-bold mb-4 text-gray-900">Contact & Contribution</h2>
                    <p class="mb-4">
                        Interested in contributing or have questions? We welcome feedback, suggestions, and contributions
                        from the research community.
                    </p>
                    <p>Email: research@example.at</p>
                </section>
            </div>
        </div>

        <footer class="bg-gray-900 text-gray-100 mt-20">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                <div class="border-t border-gray-800 pt-8">
                    <p class="text-center text-gray-400 text-sm">© 2024 Austrian Research Metadata Platform. All rights reserved.</p>
                </div>
            </div>
        </footer>
    </body>
    </html>
    """
    return html
