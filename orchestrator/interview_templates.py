"""
Interview Templates Module
Manages interview structure templates, usage tracking, and success rates
"""

import logging
import uuid
from typing import Any

from sqlalchemy import select

from database.db import SessionLocal
from database.models import InterviewTemplate
from orchestrator.time_utils import utcnow

logger = logging.getLogger(__name__)


class InterviewTemplateManager:
    """Manages interview templates and their usage statistics"""

    INTERVIEW_TYPES = ["technical", "behavioral", "mixed"]

    def __init__(self):
        pass

    def create_template(
        self,
        name: str,
        interview_type: str,
        description: str | None = None,
        duration_minutes: int = 60,
        question_count: int = 10,
        category_distribution: dict[str, float] | None = None,
        difficulty_distribution: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Create a new interview template"""
        interview_type = interview_type.strip().lower()

        if interview_type not in self.INTERVIEW_TYPES:
            raise ValueError(
                f"Invalid interview type: {interview_type}. Must be one of: {self.INTERVIEW_TYPES}"
            )
        self._validate_distribution(category_distribution, "category_distribution")
        self._validate_distribution(difficulty_distribution, "difficulty_distribution")
        
        template_id = f"tmpl_{uuid.uuid4().hex[:12]}"
        now = utcnow()

        db = SessionLocal()
        try:
            template = InterviewTemplate(
                template_id=template_id,
                name=name.strip(),
                description=description,
                interview_type=interview_type,
                duration_minutes=duration_minutes,
                question_count=question_count,
                category_distribution=category_distribution or {},
                difficulty_distribution=difficulty_distribution or {},
                usage_count=0,
                success_rate=None,
                created_at=now,
                updated_at=now,
            )
            db.add(template)
            db.commit()

            logger.info(f"Created template {template_id}: {name} ({interview_type})")
            return {
                "template_id": template_id,
                "name": name.strip(),
                "description": description,
                "interview_type": interview_type,
                "duration_minutes": duration_minutes,
                "question_count": question_count,
                "category_distribution": category_distribution or {},
                "difficulty_distribution": difficulty_distribution or {},
                "usage_count": 0,
                "success_rate": None,
                "created_at": now.isoformat(),
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating template: {e}")
            raise
        finally:
            db.close()

    def get_template(self, template_id: str) -> dict[str, Any] | None:
        """Get a template by ID"""
        db = SessionLocal()
        try:
            t = db.execute(
                select(InterviewTemplate).where(
                    InterviewTemplate.template_id == template_id
                )
            ).scalar_one_or_none()
            if not t:
                return None
            return {
                "template_id": t.template_id,
                "name": t.name,
                "description": t.description,
                "interview_type": t.interview_type,
                "duration_minutes": t.duration_minutes,
                "question_count": t.question_count,
                "category_distribution": t.category_distribution or {},
                "difficulty_distribution": t.difficulty_distribution or {},
                "usage_count": t.usage_count,
                "success_rate": t.success_rate,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
        finally:
            db.close()

    def list_templates(
        self,
        interview_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List templates with optional type filter"""
        db = SessionLocal()
        try:
            stmt = select(InterviewTemplate)
            if interview_type:
                stmt = stmt.where(
                    InterviewTemplate.interview_type == interview_type.strip().lower()
                )
            stmt = stmt.order_by(InterviewTemplate.created_at.desc()).limit(limit)
            rows = db.execute(stmt).scalars().all()

            return [
                {
                    "template_id": t.template_id,
                    "name": t.name,
                    "description": t.description,
                    "interview_type": t.interview_type,
                    "duration_minutes": t.duration_minutes,
                    "question_count": t.question_count,
                    "category_distribution": t.category_distribution or {},
                    "difficulty_distribution": t.difficulty_distribution or {},
                    "usage_count": t.usage_count,
                    "success_rate": t.success_rate,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in rows
            ]
        finally:
            db.close()

    def record_usage(self, template_id: str, success: bool = True) -> bool:
        """Record a template usage and update success rate"""
        db = SessionLocal()
        try:
            t = db.execute(
                select(InterviewTemplate).where(
                    InterviewTemplate.template_id == template_id
                )
            ).scalar_one_or_none()
            if not t:
                return False

            t.usage_count = (t.usage_count or 0) + 1
            count = t.usage_count
            if t.success_rate is None:
                t.success_rate = 1.0 if success else 0.0
            else:
                t.success_rate = (
                    (t.success_rate * (count - 1)) + (1.0 if success else 0.0)
                ) / count
            t.updated_at = utcnow()
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error recording template usage: {e}")
            return False
        finally:
            db.close()


    def _validate_distribution(self, distribution: dict[str, float] | None, field_name: str) -> None:
        """Ensure a percentage distribution sums to 100 if provided."""
        if not distribution:
            return
        total = sum(distribution.values())
        if any(pct < 0 for pct in distribution.values()):
            raise ValueError(f"{field_name} percentages cannot be negative")
        if abs(total - 100) > 0.01:
            raise ValueError(f"{field_name} must sum to 100, got {total}")

    def update_template(
        self,
        template_id: str,
        name: str | None = None,
        interview_type: str | None = None,
        description: str | None = None,
        duration_minutes: int | None = None,
        question_count: int | None = None,
        category_distribution: dict[str, float] | None = None,
        difficulty_distribution: dict[str, float] | None = None,
    ) -> dict[str, Any] | None:
        """Update an existing interview template. Only provided fields change."""
        if interview_type is not None:
            interview_type = interview_type.strip().lower()
            if interview_type not in self.INTERVIEW_TYPES:
                raise ValueError(
                    f"Invalid interview type: {interview_type}. Must be one of: {self.INTERVIEW_TYPES}"
                )

        self._validate_distribution(category_distribution, "category_distribution")
        self._validate_distribution(difficulty_distribution, "difficulty_distribution")

        db = SessionLocal()
        try:
            t = db.execute(
                select(InterviewTemplate).where(
                    InterviewTemplate.template_id == template_id
                )
            ).scalar_one_or_none()
            if not t:
                return None

            if name is not None:
                t.name = name.strip()
            if interview_type is not None:
                t.interview_type = interview_type
            if description is not None:
                t.description = description
            if duration_minutes is not None:
                t.duration_minutes = duration_minutes
            if question_count is not None:
                t.question_count = question_count
            if category_distribution is not None:
                t.category_distribution = category_distribution
            if difficulty_distribution is not None:
                t.difficulty_distribution = difficulty_distribution
            t.updated_at = utcnow()

            db.commit()
            logger.info(f"Updated template {template_id}")
            return {
                "template_id": t.template_id,
                "name": t.name,
                "description": t.description,
                "interview_type": t.interview_type,
                "duration_minutes": t.duration_minutes,
                "question_count": t.question_count,
                "category_distribution": t.category_distribution or {},
                "difficulty_distribution": t.difficulty_distribution or {},
                "usage_count": t.usage_count,
                "success_rate": t.success_rate,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating template {template_id}: {e}")
            raise
        finally:
            db.close()

    def delete_template(self, template_id: str) -> bool:
        """Delete an interview template by ID."""
        db = SessionLocal()
        try:
            t = db.execute(
                select(InterviewTemplate).where(
                    InterviewTemplate.template_id == template_id
                )
            ).scalar_one_or_none()
            if not t:
                return False
            db.delete(t)
            db.commit()
            logger.info(f"Deleted template {template_id}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting template {template_id}: {e}")
            raise
        finally:
            db.close()

    def get_question_plan(self, template_id: str) -> dict[str, Any] | None:
        """
        Connects a template to the question system: given a template's
        question_count and category_distribution, returns how many
        questions to pull from each category.
        """
        template = self.get_template(template_id)
        if not template:
            return None
        question_count = template["question_count"]
        distribution = template["category_distribution"] or {}
        plan = {
            category: round(question_count * pct / 100)
            for category, pct in distribution.items()
        }
        return {"template_id": template_id, "question_plan": plan}

interview_template_manager = InterviewTemplateManager()
