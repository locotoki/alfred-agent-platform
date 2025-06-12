"""Social Intelligence Service Main Application"""

# type: ignore
import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict

import redis
import structlog
import yaml
from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

from agents.social_intel.agent import SocialIntelAgent
from app.blueprint import SeedToBlueprint
from app.niche_scout import NicheScout
from app.workflow_endpoints import (
    get_scheduled_workflows,
    get_workflow_history,
    get_workflow_result,
    schedule_workflow,
)
from libs.a2a_adapter import PolicyMiddleware, PubSubTransport, SupabaseTransport
from libs.agent_core.health import create_health_app

logger = structlog.get_logger(__name__)
# Initialize services
pubsub_transport = PubSubTransport(project_id=os.getenv("GCP_PROJECT_ID", "alfred-agent-platform"))

supabase_transport = SupabaseTransport(database_url=os.getenv("DATABASE_URL"))

redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379"))
policy_middleware = PolicyMiddleware(redis_client)

# Initialize agent
social_agent = SocialIntelAgent(
    pubsub_transport=pubsub_transport,
    supabase_transport=supabase_transport,
    policy_middleware=policy_middleware,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Import database module here to avoid circular imports

    from app.database import close_pool, get_pool

    # Startup
    await supabase_transportconnect()

    # Initialize database connection pool
    try:
        await get_pool()
        logger.info("Database connection pool initialized")
    except Exception as e:
        logger.error("Failed to initialize database connection pool", error=str(e))

    # Start agent
    asyncio.create_task(social_agent.start())

    logger.info("social_intel_service_started")
    yield

    # Shutdown
    await social_agentstop()
    await supabase_transportdisconnect()

    # Close database connection pool
    try:
        await close_pool()
        logger.info("Database connection pool closed")
    except Exception as e:
        logger.error("Failed to close database connection pool", error=str(e))

    logger.info("social_intel_service_stopped")


app = FastAPI(
    title="Social Intelligence Service",
    description="Trend analysis and social media monitoring service",
    version="1.0.0",
    lifespan=lifespan,
)

# Add health check endpoints
health_app = create_health_app("social-intel", "1.0.0")
app.mount("/health", health_app)


@app.get("/status")
async def get_status():
    """Get agent status"""
    return {
        "agent": "social-intel",
        "version": "1.0.0",
        "status": "running" if social_agent.is_running else "stopped",
        "supported_intents": social_agent.supported_intents,
    }


@app.post("/force-analyze")
async def force_analyze(query: str):
    """Force an immediate trend analysis"""
    try:
        result = await social_agent_analyze_trend({"query": query})
        return result
    except Exception as e:
        logger.error("force_analyze_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/niche-scout")
async def run_niche_scout(
    request: Request,
    query: str = Query(None, description="Optional query to focus the niche analysis"),
    category: str = Query(None, description="Main content category (e.g., 'tech', 'kids')"),
    subcategory: str = Query(None, description="Specific subcategory (e.g., 'kids.nursery')"),
):
    """Run the Niche-Scout workflow to find trending YouTube niches"""
    # Log that we entered the endpoint handler
    print(
        f"DEBUG: Entered niche-scout endpoint handler with "
        f"query={query}, category={category}, subcategory={subcategory}"
    )
    logger.info("Entered niche-scout endpoint", path="/niche-scout", method="POST")
    try:
        # Try to parse JSON body if present
        json_data = {}
        try:
            # Get request body
            body = await requestbody()
            print(f"DEBUG: Request body: {body}")

            # Parse JSON
            json_data = await requestjson()
            print(f"DEBUG: Parsed JSON: {json_data}")
            logger.info("Received JSON payload", payload=json_data)

            # If this is an A2A envelope, extract the relevant fields
            if json_data.get("intent") == "YOUTUBE_NICHE_SCOUT":
                # Extract data from A2A envelope
                data = json_data.get("data", {})
                queries = data.get("queries", [])
                if queries and isinstance(queries, list):
                    query = queries[0]  # Use the first query
                    logger.info("Extracted query from JSON payload", query=query)

                # Extract category from JSON payload
                json_category = data.get("category")
                if json_category and json_category != "All":
                    category = json_category
                    logger.info("Using category from JSON payload", category=category)
                elif json_category == "All":
                    category = None

                # Extract subcategory from JSON payload
                json_subcategory = data.get("subcategory")
                if json_subcategory:
                    subcategory = json_subcategory
                    logger.info("Using subcategory from JSON payload", subcategory=subcategory)
        except Exception as e:
            logger.error("Failed to parse JSON body, using query parameters", error=str(e))

        # Log the final parameter values being used
        logger.info(
            "niche_scout_request",
            query=query,
            category=category,
            subcategory=subcategory,
            received_json=bool(json_data),
            task_id=json_data.get("task_id", "none"),
        )
        niche_scout = NicheScout()
        result, json_path, report_path = await niche_scoutrun(query, category, subcategory)

        # Add file paths to the result
        result["_files"] = {"json_report": json_path, "report_file": report_path}

        # Add a unique ID for result retrieval
        result["_id"] = f"niche-scout-{int(datetime.now().timestamp())}"

        return result
    except Exception as e:
        logger.error(
            "niche_scout_failed",
            error=str(e),
            query=query,
            category=category,
            subcategory=subcategory,
        )
        raise HTTPException(status_code=500, detail=str(e))


# Alternative routes for Niche-Scout workflow
@app.post("/youtube/niche-scout")
async def run_niche_scout_alt1(
    request: Request,
    query: str = Query(None, description="Optional query to focus the niche analysis"),
    category: str = Query(None, description="Main content category (e.g., 'tech', 'kids')"),
    subcategory: str = Query(None, description="Specific subcategory (e.g., 'kids.nursery')"),
):
    """Alternative path for Niche-Scout workflow"""
    return await run_niche_scout(request, query, category, subcategory)


@app.post("/api/youtube/niche-scout")
async def run_niche_scout_alt2(
    request: Request,
    query: str = Query(None, description="Optional query to focus the niche analysis"),
    category: str = Query(None, description="Main content category (e.g., 'tech', 'kids')"),
    subcategory: str = Query(None, description="Specific subcategory (e.g., 'kids.nursery')"),
):
    """Alternative path for Niche-Scout workflow"""
    return await run_niche_scout(request, query, category, subcategory)


@app.post("/seed-to-blueprint")
async def run_seed_to_blueprint(
    request: Request,
    video_url: str = Query(None, description="URL of the seed video to analyze"),
    niche: str = Query(None, description="Niche to analyze if no seed video is provided"),
):
    """Run the Seed-to-Blueprint workflow to create a channel strategy"""
    try:
        # Try to parse JSON body if present
        json_data = {}
        try:
            json_data = await requestjson()
            logger.info("Received JSON payload for blueprint", payload=json_data)

            # If this is an A2A envelope, extract the relevant fields
            if json_data.get("intent") == "YOUTUBE_BLUEPRINT":
                # Extract data from A2A envelope
                data = json_data.get("data", {})
                video_url = data.get("video_url", video_url)
                niche = data.get("niche", niche)
        except Exception as e:
            logger.debug("Failed to parse JSON body, using query parameters", error=str(e))

        if not video_url and not niche:
            raise HTTPException(
                status_code=400,
                detail="Either video_url or niche parameter must be provided",
            )

        logger.info(
            "seed_to_blueprint_request",
            video_url=video_url,
            niche=niche,
            received_json=bool(json_data),
        )

        blueprint = SeedToBlueprint()
        result, json_path, report_path = await blueprintrun(video_url, niche)

        # Add file paths to the result
        result["_files"] = {"json_report": json_path, "report_file": report_path}

        # Add a unique ID for result retrieval
        result["_id"] = f"blueprint-{int(datetime.now().timestamp())}"

        return result
    except Exception as e:
        logger.error("seed_to_blueprint_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Alternative routes for Seed-to-Blueprint workflow
@app.post("/youtube/blueprint")
async def run_seed_to_blueprint_alt1(
    request: Request,
    video_url: str = Query(None, description="URL of the seed video to analyze"),
    niche: str = Query(None, description="Niche to analyze if no seed video is provided"),
):
    """Alternative path for Seed-to-Blueprint workflow"""
    return await run_seed_to_blueprint(request, video_url, niche)


@app.post("/api/youtube/blueprint")
async def run_seed_to_blueprint_alt2(
    request: Request,
    video_url: str = Query(None, description="URL of the seed video to analyze"),
    niche: str = Query(None, description="Niche to analyze if no seed video is provided"),
):
    """Alternative path for Seed-to-Blueprint workflow"""
    return await run_seed_to_blueprint(request, video_url, niche)


# Workflow result retrieval endpoint
@app.get("/workflow-result/{result_id}")
async def get_workflow_result_endpoint(
    result_id: str,
    type: str = Query(
        ...,
        description="Type of workflow result to retrieve (niche-scout or seed-to-blueprint)",
    ),
):
    """Retrieve previously generated workflow results by ID"""
    return await get_workflow_result(result_id, type)


# Alternative routes for workflow results
@app.get("/youtube/workflow-result/{result_id}")
async def get_workflow_result_alt1(
    result_id: str,
    type: str = Query(..., description="Type of workflow result to retrieve"),
):
    """Alternative path for workflow results"""
    return await get_workflow_result(result_id, type)


@app.get("/api/youtube/workflow-result/{result_id}")
async def get_workflow_result_alt2(
    result_id: str,
    type: str = Query(..., description="Type of workflow result to retrieve"),
):
    """Alternative path for workflow results"""
    return await get_workflow_result(result_id, type)


# Workflow history endpoint
@app.get("/workflow-history")
async def get_workflow_history_endpoint():
    """Retrieve history of workflow executions"""
    return await get_workflow_history()


# Alternative routes for workflow history
@app.get("/youtube/workflow-history")
async def get_workflow_history_alt1():
    """Alternative path for workflow history"""
    return await get_workflow_history()


@app.get("/api/youtube/workflow-history")
async def get_workflow_history_alt2():
    """Alternative path for workflow history"""
    return await get_workflow_history()


# Scheduled workflows endpoint
@app.get("/scheduled-workflows")
async def get_scheduled_workflows_endpoint():
    """Retrieve scheduled workflows"""
    return await get_scheduled_workflows()


# Alternative routes for scheduled workflows
@app.get("/youtube/scheduled-workflows")
async def get_scheduled_workflows_alt1():
    """Alternative path for scheduled workflows"""
    return await get_scheduled_workflows()


@app.get("/api/youtube/scheduled-workflows")
async def get_scheduled_workflows_alt2():
    """Alternative path for scheduled workflows"""
    return await get_scheduled_workflows()


# Schedule workflow endpoint
@app.post("/schedule-workflow")
async def schedule_workflow_endpoint(
    workflow_type: str = Body(..., description="Type of workflow to schedule"),
    parameters: Dict[str, Any] = Body(..., description="Workflow parameters"),
    frequency: str = Body(..., description="Schedule frequency (daily, weekly, monthly, once)"),
    next_run: str = Body(..., description="Next scheduled run time"),
):
    """Schedule a new workflow execution"""
    return await schedule_workflow(workflow_type, parameters, frequency, next_run)


# Alternative routes for scheduling workflows
@app.post("/youtube/schedule-workflow")
async def schedule_workflow_alt1(
    workflow_type: str = Body(..., description="Type of workflow to schedule"),
    parameters: Dict[str, Any] = Body(..., description="Workflow parameters"),
    frequency: str = Body(..., description="Schedule frequency (daily, weekly, monthly, once)"),
    next_run: str = Body(..., description="Next scheduled run time"),
):
    """Alternative path for scheduling workflows"""
    return await schedule_workflow(workflow_type, parameters, frequency, next_run)


@app.post("/api/youtube/schedule-workflow")
async def schedule_workflow_alt2(
    workflow_type: str = Body(..., description="Type of workflow to schedule"),
    parameters: Dict[str, Any] = Body(..., description="Workflow parameters"),
    frequency: str = Body(..., description="Schedule frequency (daily, weekly, monthly, once)"),
    next_run: str = Body(..., description="Next scheduled run time"),
):
    """Alternative path for scheduling workflows"""
    return await schedule_workflow(workflow_type, parameters, frequency, next_run)


# ----- API Documentation Routes -----


@app.get("/openapi.yaml", include_in_schema=False)
async def get_custom_openapi_yaml():
    """Serve the custom OpenAPI YAML file"""
    with open("api/openapi.yaml", "r") as f:
        yaml_content = f.read()
    return JSONResponse(content=yaml.safe_load(yaml_content))


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Serve Swagger UI with the custom OpenAPI definition"""
    swagger_ui_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Social Intelligence API - Swagger UI</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui.css" rel="stylesheet">
        <style>
            html {{
                box-sizing: border-box;
                overflow: -moz-scrollbars-vertical;
                overflow-y: scroll;
            }}

            *,
            *:before,
            *:after {{
                box-sizing: inherit;
            }}

            body {{
                margin: 0;
                background: #fafafa;
            }}
        </style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-bundle.js"></script>
        <script>
            window.onload = function() {{
                const ui = SwaggerUIBundle({{
                    url: "/openapi.yaml",
                    dom_id: '#swagger-ui',
                    deepLinking: true,
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIBundle.SwaggerUIStandalonePreset
                    ],
                    layout: "BaseLayout",
                    supportedSubmitMethods: ['get', 'post', 'put', 'delete', 'patch']
                }});
                window.ui = ui;
            }};
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=swagger_ui_html)


# Disable the default FastAPI OpenAPI schema
def custom_openapi():
    """Override the default OpenAPI schema with a custom one"""
    with open("api/openapi.yaml", "r") as f:
        return yaml.safe_load(f)


app.openapi = custom_openapi
