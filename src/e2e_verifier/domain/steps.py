from __future__ import annotations

from typing import Annotated, ClassVar, Literal, Self

from pydantic import Field, model_validator

from e2e_verifier.domain.aria import AriaRole
from e2e_verifier.domain.common import Identifier, StrictModel, TimeoutMs
from e2e_verifier.domain.enums import StepKind

MASKED_VALUE = "***"
MAX_SLEEP_MS = 5000


class RoleTarget(StrictModel):
    role: AriaRole
    name: str | None = None
    exact: bool = False


class TextTarget(StrictModel):
    text: str = Field(min_length=1)
    exact: bool = False


class Target(StrictModel):
    role: RoleTarget | None = Field(default=None, description="ARIA role plus accessible name")
    text: TextTarget | None = Field(default=None, description="Visible text content")
    label: str | None = Field(default=None, description="Associated form label text")
    placeholder: str | None = Field(default=None, description="Placeholder attribute text")
    test_id: str | None = Field(default=None, description="data-testid attribute value")
    css: str | None = Field(default=None, description="CSS selector")
    xpath: str | None = Field(default=None, description="XPath expression")
    within: Target | None = Field(default=None, description="Parent target to scope the search")
    has_text: str | None = Field(default=None, description="Filter matches by contained text")
    nth: int | None = Field(default=None, ge=0, description="Zero-based index among matches")

    STRATEGIES: ClassVar[tuple[str, ...]] = (
        "role",
        "text",
        "label",
        "placeholder",
        "test_id",
        "css",
        "xpath",
    )

    @model_validator(mode="after")
    def _exactly_one_strategy(self) -> Self:
        chosen = [name for name in self.STRATEGIES if getattr(self, name) is not None]
        if len(chosen) != 1:
            raise ValueError(
                f"Target needs exactly one of {list(self.STRATEGIES)}, got {chosen or 'none'}"
            )
        return self

    @property
    def strategy(self) -> str:
        return next(name for name in self.STRATEGIES if getattr(self, name) is not None)

    def describe(self) -> str:
        text = self._describe_primary()
        if self.has_text:
            text = f'{text} containing "{self.has_text}"'
        if self.nth is not None:
            text = f"{text} #{self.nth + 1}"
        if self.within is not None:
            text = f"{text} within {self.within.describe()}"
        return text

    def _describe_primary(self) -> str:
        if self.role is not None:
            return f'{self.role.role} "{self.role.name}"' if self.role.name else self.role.role
        if self.text is not None:
            return f'text "{self.text.text}"'
        templates = {
            "label": 'field "{}"',
            "placeholder": 'field with placeholder "{}"',
            "test_id": "[data-testid={}]",
            "css": "css {}",
            "xpath": "xpath {}",
        }
        return templates[self.strategy].format(getattr(self, self.strategy))


class StepBase(StrictModel):
    id: Identifier = Field(description="Unique step id within the ticket")
    title: str | None = Field(default=None, max_length=200, description="Overrides the HUD text")
    timeout_ms: TimeoutMs | None = Field(default=None, description="Overrides step_timeout_ms")

    kind: ClassVar[StepKind]
    title_template: ClassVar[str]

    def title_fields(self) -> dict[str, str]:
        return {}

    def default_title(self) -> str:
        return self.title_template.format(**self.title_fields())

    def display_title(self) -> str:
        return self.title or self.default_title()

    @property
    def is_assertion(self) -> bool:
        return self.kind is StepKind.ASSERTION

    @property
    def target_or_none(self) -> Target | None:
        return None


class TargetStep(StepBase):
    target: Target

    def title_fields(self) -> dict[str, str]:
        return {"target": self.target.describe()}

    @property
    def target_or_none(self) -> Target | None:
        return self.target


class GotoStep(StepBase):
    action: Literal["goto"] = "goto"
    url: str = Field(min_length=1, description="Absolute URL or path relative to the ticket URL")
    wait_until: Literal["load", "domcontentloaded", "networkidle"] = "load"

    kind = StepKind.ACTION
    title_template = 'Open page "{url}"'

    def title_fields(self) -> dict[str, str]:
        return {"url": self.url}


class ClickStep(TargetStep):
    action: Literal["click"] = "click"
    button: Literal["left", "right", "middle"] = "left"
    click_count: int = Field(default=1, ge=1, le=3)
    force: bool = False

    kind = StepKind.ACTION
    title_template = "Click {target}"


class DblClickStep(TargetStep):
    action: Literal["dblclick"] = "dblclick"

    kind = StepKind.ACTION
    title_template = "Double-click {target}"


class FillStep(TargetStep):
    action: Literal["fill"] = "fill"
    value: str
    secret: bool = Field(default=False, description="Mask the value in HUD, report and logs")

    kind = StepKind.ACTION
    title_template = 'Fill {target} with "{value}"'

    def title_fields(self) -> dict[str, str]:
        shown = MASKED_VALUE if self.secret else self.value
        return {"target": self.target.describe(), "value": shown}


class TypeStep(TargetStep):
    action: Literal["type"] = "type"
    text: str
    delay_ms: int = Field(default=0, ge=0, le=500)

    kind = StepKind.ACTION
    title_template = 'Type "{text}" into {target}'

    def title_fields(self) -> dict[str, str]:
        return {"target": self.target.describe(), "text": self.text}


class PressStep(StepBase):
    action: Literal["press"] = "press"
    target: Target | None = None
    key: str = Field(min_length=1)

    kind = StepKind.ACTION
    title_template = 'Press key "{key}"'

    def title_fields(self) -> dict[str, str]:
        return {"key": self.key}

    @property
    def target_or_none(self) -> Target | None:
        return self.target


class CheckStep(TargetStep):
    action: Literal["check"] = "check"

    kind = StepKind.ACTION
    title_template = "Check {target}"


class UncheckStep(TargetStep):
    action: Literal["uncheck"] = "uncheck"

    kind = StepKind.ACTION
    title_template = "Uncheck {target}"


class SelectOptionStep(TargetStep):
    action: Literal["select_option"] = "select_option"
    value: str | list[str]

    kind = StepKind.ACTION
    title_template = 'Select "{value}" in {target}'

    def title_fields(self) -> dict[str, str]:
        value = self.value if isinstance(self.value, str) else ", ".join(self.value)
        return {"target": self.target.describe(), "value": value}


class HoverStep(TargetStep):
    action: Literal["hover"] = "hover"

    kind = StepKind.ACTION
    title_template = "Hover {target}"


class ScrollIntoViewStep(TargetStep):
    action: Literal["scroll_into_view"] = "scroll_into_view"

    kind = StepKind.ACTION
    title_template = "Scroll {target} into view"


class WaitForStep(StepBase):
    action: Literal["wait_for"] = "wait_for"
    target: Target | None = None
    state: Literal["visible", "hidden", "attached", "detached"] = "visible"
    load_state: Literal["load", "domcontentloaded", "networkidle"] | None = None

    kind = StepKind.ACTION
    title_template = "Wait for {what}"

    @model_validator(mode="after")
    def _target_or_load_state(self) -> Self:
        if (self.target is None) == (self.load_state is None):
            raise ValueError("wait_for needs exactly one of target or load_state")
        return self

    def title_fields(self) -> dict[str, str]:
        if self.target is not None:
            return {"what": f"{self.target.describe()} to be {self.state}"}
        return {"what": f"load state {self.load_state}"}

    @property
    def target_or_none(self) -> Target | None:
        return self.target


class SleepStep(StepBase):
    action: Literal["sleep"] = "sleep"
    ms: int = Field(ge=1, le=MAX_SLEEP_MS)

    kind = StepKind.ACTION
    title_template = "Wait {ms} ms"

    def title_fields(self) -> dict[str, str]:
        return {"ms": str(self.ms)}


class ReloadStep(StepBase):
    action: Literal["reload"] = "reload"

    kind = StepKind.ACTION
    title_template = "Reload page"


class GoBackStep(StepBase):
    action: Literal["go_back"] = "go_back"

    kind = StepKind.ACTION
    title_template = "Navigate back"


class SetViewportStep(StepBase):
    action: Literal["set_viewport"] = "set_viewport"
    width: int = Field(ge=200, le=4000)
    height: int = Field(ge=200, le=4000)

    kind = StepKind.ACTION
    title_template = "Set viewport to {width}x{height}"

    def title_fields(self) -> dict[str, str]:
        return {"width": str(self.width), "height": str(self.height)}


class UploadFileStep(TargetStep):
    action: Literal["upload_file"] = "upload_file"
    path: str = Field(min_length=1, description="Path relative to E2E_FIXTURE_DIR")

    kind = StepKind.ACTION
    title_template = 'Upload "{path}" into {target}'

    def title_fields(self) -> dict[str, str]:
        return {"target": self.target.describe(), "path": self.path}


class ExpectVisibleStep(TargetStep):
    action: Literal["expect_visible"] = "expect_visible"

    kind = StepKind.ASSERTION
    title_template = "Expect {target} to be visible"


class ExpectHiddenStep(TargetStep):
    action: Literal["expect_hidden"] = "expect_hidden"

    kind = StepKind.ASSERTION
    title_template = "Expect {target} to be hidden"


class ExpectTextStep(TargetStep):
    action: Literal["expect_text"] = "expect_text"
    text: str
    exact: bool = False

    kind = StepKind.ASSERTION
    title_template = 'Expect {target} to {mode} "{text}"'

    def title_fields(self) -> dict[str, str]:
        mode = "have text" if self.exact else "contain"
        return {"target": self.target.describe(), "text": self.text, "mode": mode}


class ExpectValueStep(TargetStep):
    action: Literal["expect_value"] = "expect_value"
    value: str

    kind = StepKind.ASSERTION
    title_template = 'Expect {target} to have value "{value}"'

    def title_fields(self) -> dict[str, str]:
        return {"target": self.target.describe(), "value": self.value}


class ExpectAttributeStep(TargetStep):
    action: Literal["expect_attribute"] = "expect_attribute"
    name: str = Field(min_length=1)
    value: str | None = None

    kind = StepKind.ASSERTION
    title_template = "Expect {target} to have attribute {name}{value}"

    def title_fields(self) -> dict[str, str]:
        value = "" if self.value is None else f'="{self.value}"'
        return {"target": self.target.describe(), "name": self.name, "value": value}


class ExpectEnabledStep(TargetStep):
    action: Literal["expect_enabled"] = "expect_enabled"

    kind = StepKind.ASSERTION
    title_template = "Expect {target} to be enabled"


class ExpectDisabledStep(TargetStep):
    action: Literal["expect_disabled"] = "expect_disabled"

    kind = StepKind.ASSERTION
    title_template = "Expect {target} to be disabled"


class ExpectCheckedStep(TargetStep):
    action: Literal["expect_checked"] = "expect_checked"
    checked: bool = True

    kind = StepKind.ASSERTION
    title_template = "Expect {target} to be {state}"

    def title_fields(self) -> dict[str, str]:
        state = "checked" if self.checked else "unchecked"
        return {"target": self.target.describe(), "state": state}


class ExpectCountStep(TargetStep):
    action: Literal["expect_count"] = "expect_count"
    count: int = Field(ge=0)

    kind = StepKind.ASSERTION
    title_template = "Expect {count} x {target}"

    def title_fields(self) -> dict[str, str]:
        return {"target": self.target.describe(), "count": str(self.count)}


class ExpectUrlStep(StepBase):
    action: Literal["expect_url"] = "expect_url"
    pattern: str = Field(min_length=1, description="Glob pattern or regex with re: prefix")

    kind = StepKind.ASSERTION
    title_template = 'Expect URL to match "{pattern}"'

    def title_fields(self) -> dict[str, str]:
        return {"pattern": self.pattern}


class ExpectTitleStep(StepBase):
    action: Literal["expect_title"] = "expect_title"
    text: str = Field(min_length=1)

    kind = StepKind.ASSERTION
    title_template = 'Expect page title to contain "{text}"'

    def title_fields(self) -> dict[str, str]:
        return {"text": self.text}


type HttpMethod = Literal["ANY", "GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]


class ExpectRequestStep(StepBase):
    action: Literal["expect_request"] = "expect_request"
    method: HttpMethod = "ANY"
    url_pattern: str = Field(min_length=1, description="Glob pattern or regex with re: prefix")
    status: int | None = Field(default=None, ge=100, le=599)
    body_contains: str | None = None

    kind = StepKind.ASSERTION
    title_template = "Expect request {method} {url_pattern}"

    def title_fields(self) -> dict[str, str]:
        return {"method": self.method, "url_pattern": self.url_pattern}


class ExpectNoRequestStep(StepBase):
    action: Literal["expect_no_request"] = "expect_no_request"
    method: HttpMethod = "ANY"
    url_pattern: str = Field(min_length=1)
    within_ms: int = Field(default=2000, ge=100, le=30_000)

    kind = StepKind.ASSERTION
    title_template = "Expect no request {method} {url_pattern}"

    def title_fields(self) -> dict[str, str]:
        return {"method": self.method, "url_pattern": self.url_pattern}


class ExpectNoConsoleErrorsStep(StepBase):
    action: Literal["expect_no_console_errors"] = "expect_no_console_errors"
    ignore_patterns: list[str] = Field(default_factory=list)

    kind = StepKind.ASSERTION
    title_template = "Expect no console errors"


type ConsoleLevel = Literal["log", "info", "warning", "error", "debug"]


class ExpectConsoleContainsStep(StepBase):
    action: Literal["expect_console_contains"] = "expect_console_contains"
    level: ConsoleLevel | None = None
    pattern: str = Field(min_length=1)

    kind = StepKind.ASSERTION
    title_template = 'Expect console message matching "{pattern}"'

    def title_fields(self) -> dict[str, str]:
        return {"pattern": self.pattern}


class ExpectDialogStep(StepBase):
    action: Literal["expect_dialog"] = "expect_dialog"
    dialog_type: Literal["alert", "confirm", "prompt"] = Field(alias="type")
    message_contains: str | None = None
    accept: bool = True

    kind = StepKind.ASSERTION
    title_template = "Expect {dialog_type} dialog"

    def title_fields(self) -> dict[str, str]:
        return {"dialog_type": self.dialog_type}


class ExpectStorageStep(StepBase):
    action: Literal["expect_storage"] = "expect_storage"
    kind_of_storage: Literal["local", "session"] = Field(alias="kind")
    key: str = Field(min_length=1)
    value: str | None = None

    kind = StepKind.ASSERTION
    title_template = 'Expect {storage}Storage key "{key}"'

    def title_fields(self) -> dict[str, str]:
        return {"storage": self.kind_of_storage, "key": self.key}


class ExpectDownloadStep(StepBase):
    action: Literal["expect_download"] = "expect_download"
    filename_pattern: str | None = None

    kind = StepKind.ASSERTION
    title_template = "Expect a download"


type Step = Annotated[
    GotoStep
    | ClickStep
    | DblClickStep
    | FillStep
    | TypeStep
    | PressStep
    | CheckStep
    | UncheckStep
    | SelectOptionStep
    | HoverStep
    | ScrollIntoViewStep
    | WaitForStep
    | SleepStep
    | ReloadStep
    | GoBackStep
    | SetViewportStep
    | UploadFileStep
    | ExpectVisibleStep
    | ExpectHiddenStep
    | ExpectTextStep
    | ExpectValueStep
    | ExpectAttributeStep
    | ExpectEnabledStep
    | ExpectDisabledStep
    | ExpectCheckedStep
    | ExpectCountStep
    | ExpectUrlStep
    | ExpectTitleStep
    | ExpectRequestStep
    | ExpectNoRequestStep
    | ExpectNoConsoleErrorsStep
    | ExpectConsoleContainsStep
    | ExpectDialogStep
    | ExpectStorageStep
    | ExpectDownloadStep,
    Field(discriminator="action"),
]

STEP_TYPES: tuple[type[StepBase], ...] = (
    GotoStep,
    ClickStep,
    DblClickStep,
    FillStep,
    TypeStep,
    PressStep,
    CheckStep,
    UncheckStep,
    SelectOptionStep,
    HoverStep,
    ScrollIntoViewStep,
    WaitForStep,
    SleepStep,
    ReloadStep,
    GoBackStep,
    SetViewportStep,
    UploadFileStep,
    ExpectVisibleStep,
    ExpectHiddenStep,
    ExpectTextStep,
    ExpectValueStep,
    ExpectAttributeStep,
    ExpectEnabledStep,
    ExpectDisabledStep,
    ExpectCheckedStep,
    ExpectCountStep,
    ExpectUrlStep,
    ExpectTitleStep,
    ExpectRequestStep,
    ExpectNoRequestStep,
    ExpectNoConsoleErrorsStep,
    ExpectConsoleContainsStep,
    ExpectDialogStep,
    ExpectStorageStep,
    ExpectDownloadStep,
)


def action_name(step_type: type[StepBase]) -> str:
    default = step_type.model_fields["action"].default
    if not isinstance(default, str):
        raise TypeError(f"{step_type.__name__} has no literal action default")
    return default
