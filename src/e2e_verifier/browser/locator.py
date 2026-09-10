from __future__ import annotations

from collections.abc import Callable

from playwright.async_api import Locator, Page

from e2e_verifier.domain.steps import Target

type Root = Page | Locator


class LocatorResolver:
    def __init__(self, page: Page) -> None:
        self._page = page
        self._builders: dict[str, Callable[[Root, Target], Locator]] = {
            "role": self._by_role,
            "text": self._by_text,
            "label": lambda root, target: root.get_by_label(str(target.label)),
            "placeholder": lambda root, target: root.get_by_placeholder(str(target.placeholder)),
            "test_id": lambda root, target: root.get_by_test_id(str(target.test_id)),
            "css": lambda root, target: root.locator(str(target.css)),
            "xpath": lambda root, target: root.locator(f"xpath={target.xpath}"),
        }
        self._descriptions: dict[str, Callable[[Target], str]] = {
            "role": self._describe_role,
            "text": self._describe_text,
            "label": lambda target: f"get_by_label({target.label!r})",
            "placeholder": lambda target: f"get_by_placeholder({target.placeholder!r})",
            "test_id": lambda target: f"get_by_test_id({target.test_id!r})",
            "css": lambda target: f"locator({target.css!r})",
            "xpath": lambda target: f"locator({'xpath=' + str(target.xpath)!r})",
        }

    def resolve(self, target: Target) -> Locator:
        root: Root = self._page if target.within is None else self.resolve(target.within)
        locator = self._builders[target.strategy](root, target)
        if target.has_text is not None:
            locator = locator.filter(has_text=target.has_text)
        if target.nth is not None:
            locator = locator.nth(target.nth)
        return locator

    def describe(self, target: Target) -> str:
        text = self._descriptions[target.strategy](target)
        if target.has_text is not None:
            text += f".filter(has_text={target.has_text!r})"
        if target.nth is not None:
            text += f".nth({target.nth})"
        if target.within is not None:
            text = f"{self.describe(target.within)}.{text}"
        return text

    @staticmethod
    def _by_role(root: Root, target: Target) -> Locator:
        if target.role is None:
            raise ValueError("role strategy without role")
        return root.get_by_role(target.role.role, name=target.role.name, exact=target.role.exact)

    @staticmethod
    def _by_text(root: Root, target: Target) -> Locator:
        if target.text is None:
            raise ValueError("text strategy without text")
        return root.get_by_text(target.text.text, exact=target.text.exact)

    @staticmethod
    def _describe_role(target: Target) -> str:
        if target.role is None:
            return "get_by_role(?)"
        name = f", name={target.role.name!r}" if target.role.name else ""
        exact = ", exact=True" if target.role.exact else ""
        return f"get_by_role({target.role.role!r}{name}{exact})"

    @staticmethod
    def _describe_text(target: Target) -> str:
        if target.text is None:
            return "get_by_text(?)"
        exact = ", exact=True" if target.text.exact else ""
        return f"get_by_text({target.text.text!r}{exact})"
