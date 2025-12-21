"""
Spintax message template service.
Generates dynamic message variations to avoid spam detection.
"""

import logging
import random
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MessageTemplate:
    """A message template with spintax support."""
    id: str
    name: str
    template: str
    variables: list[str] = field(default_factory=list)
    category: str = "general"  # opening, follow_up, conversion, objection
    platform: str = "all"  # instagram, x, all
    language: str = "en"
    success_count: int = 0
    total_used: int = 0
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def success_rate(self) -> float:
        if self.total_used == 0:
            return 0.0
        return self.success_count / self.total_used

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "template": self.template,
            "variables": self.variables,
            "category": self.category,
            "platform": self.platform,
            "language": self.language,
            "success_rate": self.success_rate,
            "total_used": self.total_used,
        }


@dataclass
class GeneratedMessage:
    """A generated message from a template."""
    template_id: str
    content: str
    variables_used: dict[str, str]
    generated_at: datetime = field(default_factory=datetime.now)


class SpintaxService:
    """
    Service for generating dynamic messages using Spintax syntax.
    
    Spintax syntax: {option1|option2|option3}
    Nested spintax: {Hello|Hi {there|friend}|Hey}
    Variables: [follower_name], [kol_name], [whatsapp_link]
    """

    # Spintax pattern: matches {option1|option2|...}
    SPINTAX_PATTERN = re.compile(r"\{([^{}]+)\}")

    # Variable pattern: matches [variable_name]
    VARIABLE_PATTERN = re.compile(r"\[([a-zA-Z_][a-zA-Z0-9_]*)\]")

    def __init__(self):
        self._templates: dict[str, MessageTemplate] = {}
        self._load_default_templates()

    def _load_default_templates(self) -> None:
        """Load default message templates for common scenarios."""
        defaults = [
            MessageTemplate(
                id="opening_friendly",
                name="Friendly Opening",
                template="{Hey|Hi|Hello} [follower_name]! {👋|✨|😊} "
                         "I noticed you follow [kol_name] too! "
                         "{Love their content|Such great insights|Amazing posts right}? "
                         "{What's your favorite topic|What got you interested|Been following long}?",
                variables=["follower_name", "kol_name"],
                category="opening",
            ),
            MessageTemplate(
                id="opening_professional",
                name="Professional Opening",
                template="{Hi|Hello} [follower_name], "
                         "I'm [assistant_name], {part of|working with} [kol_name]'s team. "
                         "{Great to connect|Nice to meet you|Pleased to connect}! "
                         "I saw you're interested in {finance|investing|markets}.",
                variables=["follower_name", "assistant_name", "kol_name"],
                category="opening",
            ),
            MessageTemplate(
                id="value_proposition",
                name="Value Proposition",
                template="We've got an {exclusive|private|VIP} {group|community|channel} "
                         "where [kol_name] shares {daily insights|real-time analysis|premium content} "
                         "{not available anywhere else|before anyone else|for serious investors}. "
                         "{Would you be interested|Want to check it out|Interested in joining}?",
                variables=["kol_name"],
                category="follow_up",
            ),
            MessageTemplate(
                id="whatsapp_invite",
                name="WhatsApp Invitation",
                template="{Here's the link|Join us here|Here you go}: [whatsapp_link] 📱 "
                         "{See you inside|Looking forward to seeing you|Welcome aboard}! "
                         "{Feel free to ask anything|Don't hesitate to reach out|Let me know if you have questions}.",
                variables=["whatsapp_link"],
                category="conversion",
            ),
            MessageTemplate(
                id="objection_why_whatsapp",
                name="Objection: Why WhatsApp",
                template="{Great question|Good point|I understand}! "
                         "We use WhatsApp for {personal|real-time|exclusive} updates "
                         "{without algorithm limits|directly to you|faster than social media}. "
                         "{Plus|Also|And} it's {completely free|no spam, promise|a small focused group}.",
                variables=[],
                category="objection",
            ),
            MessageTemplate(
                id="objection_trust",
                name="Objection: Trust Issues",
                template="{Totally understand|Makes sense|Fair enough}! "
                         "{Security is important|Trust is everything|I get the hesitation}. "
                         "You can check [kol_name]'s {main profile|verified account|public content} "
                         "{to verify we're legit|for confirmation|if you want}. "
                         "{No pressure at all|Take your time|Just wanted to offer}!",
                variables=["kol_name"],
                category="objection",
            ),
            MessageTemplate(
                id="follow_up_no_reply",
                name="Follow-up: No Reply",
                template="{Hey|Hi} [follower_name]! 👋 "
                         "{Just checking in|Wanted to follow up|Quick reminder} "
                         "{about the group|on my last message|re: the community}. "
                         "{No worries if you're busy|Totally understand if not interested|Let me know either way}!",
                variables=["follower_name"],
                category="follow_up",
            ),
        ]

        for template in defaults:
            self._templates[template.id] = template

    def add_template(self, template: MessageTemplate) -> None:
        """Add a custom message template."""
        # Extract variables from template
        variables = self.VARIABLE_PATTERN.findall(template.template)
        template.variables = list(set(variables))
        self._templates[template.id] = template
        logger.info("Added template: %s", template.id)

    def get_template(self, template_id: str) -> MessageTemplate | None:
        """Get a template by ID."""
        return self._templates.get(template_id)

    def list_templates(
        self,
        category: str | None = None,
        platform: str | None = None,
    ) -> list[MessageTemplate]:
        """List templates with optional filtering."""
        templates = list(self._templates.values())
        if category:
            templates = [t for t in templates if t.category == category]
        if platform:
            templates = [t for t in templates if t.platform in (platform, "all")]
        return templates

    def spin(self, text: str) -> str:
        """
        Process spintax in text and return a random variation.
        Handles nested spintax by processing from innermost to outermost.
        """
        result = text
        # Keep processing until no more spintax patterns
        max_iterations = 10  # Prevent infinite loops
        for _ in range(max_iterations):
            match = self.SPINTAX_PATTERN.search(result)
            if not match:
                break
            options = match.group(1).split("|")
            chosen = random.choice(options)  # noqa: S311
            result = result[:match.start()] + chosen + result[match.end():]
        return result

    def replace_variables(
        self,
        text: str,
        variables: dict[str, str],
    ) -> str:
        """Replace [variable] placeholders with actual values."""
        result = text
        for var_name, value in variables.items():
            pattern = f"[{var_name}]"
            result = result.replace(pattern, value)
        return result

    def generate_message(
        self,
        template_id: str,
        variables: dict[str, str],
    ) -> GeneratedMessage | None:
        """Generate a message from a template with variable substitution."""
        template = self._templates.get(template_id)
        if not template:
            logger.warning("Template not found: %s", template_id)
            return None

        # First, replace variables
        content = self.replace_variables(template.template, variables)

        # Then, process spintax
        content = self.spin(content)

        # Update usage stats
        template.total_used += 1

        return GeneratedMessage(
            template_id=template_id,
            content=content,
            variables_used=variables,
        )

    def generate_random_message(
        self,
        category: str,
        variables: dict[str, str],
        platform: str = "all",
    ) -> GeneratedMessage | None:
        """Generate a random message from templates in a category."""
        templates = self.list_templates(category=category, platform=platform)
        if not templates:
            return None

        # Weight by success rate (with minimum weight for untested templates)
        weights = []
        for t in templates:
            if t.total_used == 0:
                weights.append(0.5)  # Default weight for new templates
            else:
                weights.append(max(0.1, t.success_rate))

        template = random.choices(templates, weights=weights, k=1)[0]  # noqa: S311
        return self.generate_message(template.id, variables)

    def record_success(self, template_id: str) -> bool:
        """Record a successful conversion for a template."""
        template = self._templates.get(template_id)
        if template:
            template.success_count += 1
            return True
        return False

    def generate_conversation_sequence(
        self,
        variables: dict[str, str],
        include_objection: bool = False,
    ) -> list[GeneratedMessage]:
        """Generate a full conversation sequence."""
        sequence = []

        # Opening message
        opening = self.generate_random_message("opening", variables)
        if opening:
            sequence.append(opening)

        # Value proposition
        value = self.generate_random_message("follow_up", variables)
        if value:
            sequence.append(value)

        # Objection handling (optional)
        if include_objection:
            objection = self.generate_random_message("objection", variables)
            if objection:
                sequence.append(objection)

        # Conversion message
        conversion = self.generate_random_message("conversion", variables)
        if conversion:
            sequence.append(conversion)

        return sequence

    def preview_template(
        self,
        template_id: str,
        variables: dict[str, str],
        variations: int = 5,
    ) -> list[str]:
        """Preview multiple variations of a template."""
        template = self._templates.get(template_id)
        if not template:
            return []

        previews = []
        for _ in range(variations):
            content = self.replace_variables(template.template, variables)
            content = self.spin(content)
            previews.append(content)

        return previews

    def validate_template(self, template_text: str) -> dict[str, Any]:
        """Validate a template's syntax and extract info."""
        issues = []
        variables = self.VARIABLE_PATTERN.findall(template_text)

        # Check for unbalanced braces
        open_count = template_text.count("{")
        close_count = template_text.count("}")
        if open_count != close_count:
            issues.append(f"Unbalanced braces: {open_count} open, {close_count} close")

        # Check for empty options
        for match in self.SPINTAX_PATTERN.finditer(template_text):
            options = match.group(1).split("|")
            if any(opt.strip() == "" for opt in options):
                issues.append(f"Empty option in spintax: {match.group(0)}")

        # Generate sample
        sample = None
        if not issues:
            sample = self.spin(template_text)

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "variables": list(set(variables)),
            "sample": sample,
        }


def create_spintax_service() -> SpintaxService:
    """Factory function to create SpintaxService."""
    return SpintaxService()
