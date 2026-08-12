"""Interview template routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.db import get_db

logger = logging.getLogger(__name__)


class CreateTemplateRequest(BaseModel):
    """Request model for creating an interview template"""

    name: str = Field(min_length=1, max_length=200)
    interview_type: str
    description: str | None = None
    duration_minutes: int = 60
    question_count: int = 10
    category_distribution: dict[str, float] | None = None
    difficulty_distribution: dict[str, float] | None = None


def create_template_routes(interview_template_manager) -> APIRouter:
    """Create interview template routes.

    Args:
        interview_template_manager: InterviewTemplateManager instance

    Returns:
        APIRouter with template routes
    """

    router = APIRouter()

    @router.get("/templates")
    async def list_templates(interview_type: str | None = None, limit: int = 100):
        """List interview templates with optional type filter"""
        try:
            templates = interview_template_manager.list_templates(
                interview_type=interview_type, limit=limit
            )
            return {"count": len(templates), "templates": templates}
        except Exception as e:
            logger.error(f"Error listing templates: {e!s}")
            raise HTTPException(status_code=500, detail="Error listing templates")

    @router.post("/templates")
    async def create_template(
        request: CreateTemplateRequest,
        session_db: Session = Depends(get_db),
    ):
        """Create a new interview template"""
        try:
            template = interview_template_manager.create_template(
                name=request.name,
                interview_type=request.interview_type,
                description=request.description,
                duration_minutes=request.duration_minutes,
                question_count=request.question_count,
                category_distribution=request.category_distribution,
                difficulty_distribution=request.difficulty_distribution,
            )
            return template
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error creating template: {e!s}")
            raise HTTPException(status_code=500, detail="Error creating template")

    @router.get("/templates/{template_id}")
    async def get_template(template_id: str):
        """Get a single interview template by ID"""
        template = interview_template_manager.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        return template

    @router.put("/templates/{template_id}")
    async def update_template(template_id: str, request: CreateTemplateRequest):
        """Update an existing interview template"""
        try:
            template = interview_template_manager.update_template(
                template_id,
                name=request.name,
                interview_type=request.interview_type,
                description=request.description,
                duration_minutes=request.duration_minutes,
                question_count=request.question_count,
                category_distribution=request.category_distribution,
                difficulty_distribution=request.difficulty_distribution,
            )
            if not template:
                raise HTTPException(status_code=404, detail="Template not found")
            return template
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating template: {e}")
            raise HTTPException(status_code=500, detail="Error updating template")

    @router.delete("/templates/{template_id}")
    async def delete_template(template_id: str):
        """Delete an interview template"""
        deleted = interview_template_manager.delete_template(template_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Template not found")
        return {"deleted": True, "template_id": template_id}

    @router.get("/templates/{template_id}/question-plan")
    async def get_question_plan(template_id: str):
        """Get the question breakdown this template maps to, for the question system"""
        plan = interview_template_manager.get_question_plan(template_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Template not found")
        return plan

    return router
