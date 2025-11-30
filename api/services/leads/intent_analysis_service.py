"""
Intent analysis service for leads.
Uses Dify Workflow to analyze purchase intent from comments.
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

from core.app.apps.workflow.app_generator import WorkflowAppGenerator
from core.app.entities.app_invoke_entities import InvokeFrom
from extensions.ext_database import db
from models.model import App, AppMode, EndUser
from services.workflow_service import WorkflowService

logger = logging.getLogger(__name__)


@dataclass
class IntentAnalysisResult:
    """Result of intent analysis."""

    score: int  # 0-100
    tags: list[str]
    reason: str


class IntentAnalysisError(Exception):
    """Error during intent analysis."""


class IntentAnalysisService:
    """
    Service for analyzing purchase intent from lead comments.

    Uses a Dify Workflow app to perform AI-based analysis of comment content
    to determine the likelihood of purchase intent.

    Configuration via environment variables:
        - INTENT_ANALYSIS_APP_ID: The Dify app ID for intent analysis workflow
        - INTENT_ANALYSIS_ENABLED: Enable/disable intent analysis (default: false)

    The workflow should accept a 'comment' input and return JSON with:
        - score: int (0-100)
        - tags: list of strings (e.g., ["price_sensitive", "ready_to_buy"])
        - reason: string explaining the score
    """

    # Environment configuration
    APP_ID = os.getenv("INTENT_ANALYSIS_APP_ID", "")
    ENABLED = os.getenv("INTENT_ANALYSIS_ENABLED", "false").lower() == "true"

    @classmethod
    def is_configured(cls) -> bool:
        """Check if intent analysis is properly configured."""
        return cls.ENABLED and bool(cls.APP_ID)

    @classmethod
    def analyze_comment(
        cls,
        tenant_id: str,
        comment: str,
        additional_context: dict[str, Any] | None = None,
    ) -> IntentAnalysisResult:
        """
        Analyze a comment for purchase intent.

        Args:
            tenant_id: The tenant ID
            comment: The comment text to analyze
            additional_context: Optional additional context (video title, etc.)

        Returns:
            IntentAnalysisResult with score, tags, and reason

        Raises:
            IntentAnalysisError: If analysis fails
        """
        if not cls.is_configured():
            logger.warning("Intent analysis not configured, returning default score")
            return IntentAnalysisResult(score=0, tags=[], reason="Analysis not configured")

        if not comment or not comment.strip():
            return IntentAnalysisResult(score=0, tags=[], reason="Empty comment")

        try:
            # Get the app model
            app = (
                db.session.query(App)
                .filter_by(
                    id=cls.APP_ID,
                    tenant_id=tenant_id,
                )
                .first()
            )

            if not app:
                logger.error("Intent analysis app not found: %s", cls.APP_ID)
                raise IntentAnalysisError(f"App not found: {cls.APP_ID}")

            if app.mode != AppMode.WORKFLOW:
                raise IntentAnalysisError(f"App {cls.APP_ID} is not a workflow app")

            # Get the workflow
            workflow_service = WorkflowService()
            workflow = workflow_service.get_published_workflow(app_model=app)

            if not workflow:
                raise IntentAnalysisError("Workflow not published")

            # Prepare inputs
            inputs = {
                "comment": comment,
            }
            if additional_context:
                inputs.update(additional_context)

            # Create an EndUser for the analysis
            end_user = cls._get_or_create_end_user(tenant_id, app.id)

            # Execute workflow (non-streaming)
            result = cls._execute_workflow(app, workflow, end_user, inputs)

            # Parse result
            return cls._parse_result(result)

        except IntentAnalysisError:
            raise
        except Exception as e:
            logger.exception("Intent analysis failed for comment")
            raise IntentAnalysisError(f"Analysis failed: {e}") from e

    @classmethod
    def _get_or_create_end_user(cls, tenant_id: str, app_id: str) -> EndUser:
        """Get or create an EndUser for intent analysis."""
        # Use a fixed session ID for internal analysis
        session_id = "intent-analysis-internal"

        end_user = (
            db.session.query(EndUser)
            .filter_by(
                tenant_id=tenant_id,
                app_id=app_id,
                session_id=session_id,
            )
            .first()
        )

        if not end_user:
            end_user = EndUser(
                tenant_id=tenant_id,
                app_id=app_id,
                session_id=session_id,
                type="service",
            )
            db.session.add(end_user)
            db.session.commit()

        return end_user

    @classmethod
    def _execute_workflow(
        cls,
        app: App,
        workflow: Any,
        end_user: EndUser,
        inputs: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the workflow and collect results."""
        args = {
            "inputs": inputs,
            "query": "",
            "files": [],
            "conversation_id": None,
        }

        # Generate workflow response (non-streaming)
        generator = WorkflowAppGenerator().generate(
            app_model=app,
            workflow=workflow,
            user=end_user,
            args=args,
            invoke_from=InvokeFrom.SERVICE_API,
            streaming=False,
            root_node_id=None,
            call_depth=0,
        )

        # Collect all events
        result: dict[str, Any] = {}
        for event in generator:
            if hasattr(event, "outputs"):
                result = event.outputs or {}
                break

        return result

    @classmethod
    def _parse_result(cls, result: dict[str, Any] | str) -> IntentAnalysisResult:
        """Parse workflow output into IntentAnalysisResult."""
        # Try to parse as JSON if it's a string
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                return IntentAnalysisResult(
                    score=0,
                    tags=[],
                    reason=result[:500],
                )

        # Extract fields with defaults
        score = result.get("score", 0)
        if isinstance(score, str):
            try:
                score = int(score)
            except ValueError:
                score = 0

        # Clamp score to 0-100
        score = max(0, min(100, score))

        tags = result.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        reason = result.get("reason", "")
        if not isinstance(reason, str):
            reason = str(reason)

        return IntentAnalysisResult(
            score=score,
            tags=tags,
            reason=reason[:1000],  # Limit reason length
        )

    @classmethod
    def analyze_batch(
        cls,
        tenant_id: str,
        comments: list[tuple[str, str]],  # List of (lead_id, comment)
    ) -> dict[str, IntentAnalysisResult]:
        """
        Analyze multiple comments in batch.

        Args:
            tenant_id: The tenant ID
            comments: List of (lead_id, comment) tuples

        Returns:
            Dictionary mapping lead_id to IntentAnalysisResult
        """
        results: dict[str, IntentAnalysisResult] = {}

        for lead_id, comment in comments:
            try:
                result = cls.analyze_comment(tenant_id, comment)
                results[lead_id] = result
            except IntentAnalysisError as e:
                logger.warning("Failed to analyze lead %s: %s", lead_id, e)
                results[lead_id] = IntentAnalysisResult(
                    score=0,
                    tags=[],
                    reason=f"Analysis failed: {e}",
                )

        return results


def create_intent_analysis_service() -> IntentAnalysisService:
    """Factory function to create intent analysis service."""
    return IntentAnalysisService()
