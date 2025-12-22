"""
Lead acquisition services module.

This module provides services for social media automation:
- Instagram/Twitter HTTP API services (browser-less, high concurrency)
- Session management with Redis persistence
- Anti-detect browser integration (fallback)
- Smart scheduling and rate limiting
- Analytics and conversion tracking
"""

# Advanced features
from .analytics_service import LeadsAnalyticsService
from .antidetect_browser_service import (
    AntiDetectBrowserError,
    AntiDetectBrowserService,
    BrowserNotConfiguredError,
    BrowserProfile,
    BrowserProvider,
    BrowserSession,
    ProfileNotFoundError,
    SessionStartError,
    create_antidetect_browser_service,
)
from .automation_executor_service import (
    ActionLog,
    ActionResult,
    AutomationExecutorService,
    BatchExecutionResult,
    ExecutionContext,
    ExecutionStatus,
    create_automation_executor_service,
    run_concurrent_sessions,
)

# Browser Pool (for login-only scenarios)
from .browser_pool_service import (
    BrowserInstance,
    BrowserInstanceStatus,
    BrowserPoolService,
    LoginResult,
    create_browser_pool_service,
)

# Configuration and workflow binding services
from .config_service import LeadsConfigService
from .content_sync_service import (
    ContentSyncError,
    ContentSyncJob,
    ContentSyncService,
    ContentType,
    ScrapedContent,
    SyncStatus,
    create_content_sync_service,
)
from .conversation_flow_service import (
    ConversationFlow,
    ConversationFlowService,
    ConversationIntent,
    ConversationState,
    FlowNode,
    FlowNodeType,
    FlowResponse,
    create_conversation_flow_service,
)
from .crawler_service import (
    CrawledComment,
    CrawlerExecutionError,
    CrawlerNotConfiguredError,
    CrawlerServiceError,
    DouyinCrawlerService,
    create_crawler_service,
)
from .follow_back_detector_service import (
    BatchDetectionResult,
    DetectionResult,
    FollowBackDetectorService,
    FollowRelationship,
    FollowStatus,
    create_follow_back_detector_service,
)

# HTTP API Services (browser-less, high concurrency)
from .instagram_api_service import (
    AccountStatus as InstagramAccountStatus,
)
from .instagram_api_service import (
    DMResult as InstagramDMResult,
)
from .instagram_api_service import (
    FollowResult as InstagramFollowResult,
)
from .instagram_api_service import (
    InstagramAPIError,
    InstagramAPIService,
    InstagramSession,
    create_instagram_api_service,
)
from .instagram_api_service import (
    LoginError as InstagramLoginError,
)
from .instagram_api_service import (
    RateLimitError as InstagramRateLimitError,
)
from .instagram_api_service import (
    UserInfo as InstagramUserInfo,
)
from .intent_analysis_service import (
    IntentAnalysisError,
    IntentAnalysisResult,
    IntentAnalysisService,
    create_intent_analysis_service,
)
from .proxy_pool_service import (
    NoAvailableProxyError,
    ProxyConfig,
    ProxyPoolError,
    ProxyPoolService,
    ProxyQuality,
    ProxyStatus,
    ProxyType,
    create_proxy_pool_service,
)
from .session_manager_service import (
    Platform,
    SessionManagerService,
    StoredSession,
    create_session_manager_service,
)
from .smart_scheduler_service import (
    AccountAgeCategory,
    AccountScheduleState,
    ActionType,
    RateLimitConfig,
    ScheduledAction,
    SmartSchedulerService,
    create_smart_scheduler_service,
)
from .social_account_service import (
    FollowerTargetService,
    HealthCheckResult,
    ImportResult,
    OutreachTaskService,
    SubAccountService,
    TargetKOLService,
    create_follower_target_service,
    create_outreach_task_service,
    create_sub_account_service,
    create_target_kol_service,
)
from .social_scraper_service import (
    ApifyAPIError,
    ApifyNotConfiguredError,
    ScrapedFollower,
    SocialScraperError,
    SocialScraperService,
    create_social_scraper_service,
    scrape_kol_followers,
)
from .spintax_service import (
    GeneratedMessage,
    MessageTemplate,
    SpintaxService,
    create_spintax_service,
)
from .timezone_scheduler_service import (
    RegionSchedule,
    ScheduledSlot,
    TimezoneSchedulerService,
    TimezoneWindow,
    create_timezone_scheduler_service,
)
from .twitter_api_service import (
    AccountStatus as TwitterAccountStatus,
)
from .twitter_api_service import (
    DMResult as TwitterDMResult,
)
from .twitter_api_service import (
    FollowResult as TwitterFollowResult,
)
from .twitter_api_service import (
    LoginError as TwitterLoginError,
)
from .twitter_api_service import (
    RateLimitError as TwitterRateLimitError,
)
from .twitter_api_service import (
    TwitterAPIError,
    TwitterAPIService,
    TwitterSession,
    create_twitter_api_service,
)
from .twitter_api_service import (
    UserInfo as TwitterUserInfo,
)
from .workflow_binding_service import WorkflowBindingService
from .workflow_result_handler import WorkflowResultHandler

__all__ = [
    # Smart Scheduler
    "AccountAgeCategory",
    "AccountScheduleState",
    "ActionType",
    # Anti-detect Browser
    "AntiDetectBrowserError",
    "AntiDetectBrowserService",
    # Social Scraper
    "ApifyAPIError",
    "ApifyNotConfiguredError",
    # Browser Pool (login-only)
    "BrowserInstance",
    "BrowserInstanceStatus",
    "BrowserNotConfiguredError",
    "BrowserPoolService",
    "BrowserProfile",
    "BrowserProvider",
    "BrowserSession",
    # Content Sync
    "ContentSyncError",
    "ContentSyncJob",
    "ContentSyncService",
    "ContentType",
    # Crawler
    "CrawledComment",
    "CrawlerExecutionError",
    "CrawlerNotConfiguredError",
    "CrawlerServiceError",
    "DouyinCrawlerService",
    # Social Account
    "FollowerTargetService",
    "HealthCheckResult",
    "ImportResult",
    "InstagramAPIError",
    "InstagramAPIService",
    # Instagram HTTP API (browser-less)
    "InstagramAccountStatus",
    "InstagramDMResult",
    "InstagramFollowResult",
    "InstagramLoginError",
    "InstagramRateLimitError",
    "InstagramSession",
    "InstagramUserInfo",
    # Intent Analysis
    "IntentAnalysisError",
    "IntentAnalysisResult",
    "IntentAnalysisService",
    # Configuration
    "LeadsAnalyticsService",
    "LeadsConfigService",
    "LoginResult",
    # Proxy Pool
    "NoAvailableProxyError",
    "OutreachTaskService",
    # Session Management
    "Platform",
    "ProfileNotFoundError",
    "ProxyConfig",
    "ProxyPoolError",
    "ProxyPoolService",
    "ProxyQuality",
    "ProxyStatus",
    "ProxyType",
    "RateLimitConfig",
    # Timezone Scheduler
    "RegionSchedule",
    "ScheduledAction",
    "ScheduledSlot",
    "ScrapedContent",
    "ScrapedFollower",
    "SessionManagerService",
    "SessionStartError",
    "SmartSchedulerService",
    "SocialScraperError",
    "SocialScraperService",
    "StoredSession",
    "SubAccountService",
    "SyncStatus",
    "TargetKOLService",
    "TimezoneSchedulerService",
    "TimezoneWindow",
    "TwitterAPIError",
    "TwitterAPIService",
    # Twitter HTTP API (browser-less)
    "TwitterAccountStatus",
    "TwitterDMResult",
    "TwitterFollowResult",
    "TwitterLoginError",
    "TwitterRateLimitError",
    "TwitterSession",
    "TwitterUserInfo",
    # Workflow Binding
    "WorkflowBindingService",
    "WorkflowResultHandler",
    # Factory functions
    "create_antidetect_browser_service",
    "create_automation_executor_service",
    "create_browser_pool_service",
    "create_content_sync_service",
    "create_crawler_service",
    "create_follower_target_service",
    "create_instagram_api_service",
    "create_intent_analysis_service",
    "create_outreach_task_service",
    "create_proxy_pool_service",
    "create_session_manager_service",
    "create_smart_scheduler_service",
    "create_social_scraper_service",
    "create_sub_account_service",
    "create_target_kol_service",
    "create_timezone_scheduler_service",
    "create_twitter_api_service",
    "run_concurrent_sessions",
    "scrape_kol_followers",
]
