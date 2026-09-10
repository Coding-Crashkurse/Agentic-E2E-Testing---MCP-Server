from __future__ import annotations

from enum import StrEnum


class RunMode(StrEnum):
    VERIFY = "verify"
    REPRODUCE = "reproduce"


class RunKind(StrEnum):
    TICKET = "ticket"
    SCENARIO = "scenario"


class StepKind(StrEnum):
    ACTION = "action"
    ASSERTION = "assertion"


class StepPhase(StrEnum):
    PRECONDITIONS = "preconditions"
    STEPS = "steps"


class StepStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


class Outcome(StrEnum):
    CRITERIA_MET = "criteria_met"
    CRITERIA_NOT_MET = "criteria_not_met"
    ERROR = "error"


class Verdict(StrEnum):
    FIXED = "fixed"
    STILL_BROKEN = "still_broken"
    REPRODUCED = "reproduced"
    NOT_REPRODUCED = "not_reproduced"
    PASSED = "passed"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"


class CriterionStatus(StrEnum):
    MET = "met"
    NOT_MET = "not_met"
    UNKNOWN = "unknown"


class ErrorCategory(StrEnum):
    ASSERTION = "assertion"
    TIMEOUT = "timeout"
    ELEMENT_NOT_FOUND = "element_not_found"
    AMBIGUOUS_TARGET = "ambiguous_target"
    NAVIGATION = "navigation"
    HOST_NOT_ALLOWED = "host_not_allowed"
    BROWSER = "browser"
    PRECONDITION = "precondition"
    RUN_TIMEOUT = "run_timeout"
    INPUT = "input"
    INTERNAL = "internal"


class ArtifactKind(StrEnum):
    VIDEO = "video"
    VIDEO_MP4 = "video_mp4"
    TRACE = "trace"
    REPORT = "report"
    RESULT = "result"
    SCREENSHOT = "screenshot"
    CONSOLE_LOG = "console_log"
    NETWORK_LOG = "network_log"
    HAR = "har"
    CHAPTERS = "chapters"
    TICKET = "ticket"


class ScreenshotMode(StrEnum):
    EACH_STEP = "each_step"
    FAILURE_ONLY = "failure_only"
    NONE = "none"


class HighlightSource(StrEnum):
    STEP = "step"
    PREVIOUS_ACTION = "previous_action"


class SchemaKind(StrEnum):
    TICKET = "ticket"
    SCENARIO = "scenario"
    RUN_OPTIONS = "run_options"
    RUN_RESULT = "run_result"
    STEP = "step"


class AnnotationTone(StrEnum):
    INFO = "info"
    SUCCESS = "success"
    FAILURE = "failure"
