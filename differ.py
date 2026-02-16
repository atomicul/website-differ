#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from bs4 import BeautifulSoup, Tag

LANDMARK_TAGS = frozenset(
    {"header", "nav", "main", "aside", "footer", "section", "article"}
)
IGNORED_TAGS = frozenset(
    {"script", "style", "link", "meta", "noscript", "template"}
)

LANDMARK_WEIGHT = 0.40
SKELETON_WEIGHT = 0.60

TAG_WEIGHT = 0.30
CLASS_WEIGHT = 0.30
ID_WEIGHT = 0.20
CHILD_COUNT_WEIGHT = 0.20


def main() -> None:
    parser = argparse.ArgumentParser(
        description="HTML structural diffing engine"
    )
    parser.add_argument("old", type=Path, help="Path to the old HTML file")
    parser.add_argument("new", type=Path, help="Path to the new HTML file")
    args = parser.parse_args()

    for path in (args.old, args.new):
        if not path.is_file():
            print(f"Error: {path} is not a file", file=sys.stderr)
            sys.exit(1)

    score = diff_score(args.old, args.new)
    print(f"Diff Score: {score:.4f}")
    print(interpret_score(score))


@dataclass(frozen=True)
class NodeProfile:
    tag: str
    id_attr: str
    classes: tuple[str, ...]
    child_count: int


def parse_html(path: Path) -> BeautifulSoup:
    return BeautifulSoup(path.read_text(), "html.parser")


def extract_landmarks(soup: BeautifulSoup) -> list[str]:
    return [
        tag.name for tag in soup.find_all(LANDMARK_TAGS) if isinstance(tag, Tag)
    ]


def _make_profile(element: Tag) -> NodeProfile:
    id_raw = element.get("id")
    class_raw = element.get("class")
    return NodeProfile(
        tag=element.name,
        id_attr=id_raw if isinstance(id_raw, str) else "",
        classes=tuple(class_raw) if isinstance(class_raw, list) else (),
        child_count=sum(1 for c in element.children if isinstance(c, Tag)),
    )


def extract_skeleton(soup: BeautifulSoup) -> list[NodeProfile]:
    body = soup.find("body")
    if not isinstance(body, Tag):
        return []
    profiles: list[NodeProfile] = []
    for child in body.children:
        if not isinstance(child, Tag) or child.name in IGNORED_TAGS:
            continue
        profiles.append(_make_profile(child))
        for grandchild in child.children:
            if (
                not isinstance(grandchild, Tag)
                or grandchild.name in IGNORED_TAGS
            ):
                continue
            profiles.append(_make_profile(grandchild))
    return profiles


def landmark_diff(old: list[str], new: list[str]) -> float:
    if not old and not new:
        return 0.0
    return 1.0 - SequenceMatcher(None, old, new).ratio()


def node_diff(old: NodeProfile, new: NodeProfile) -> float:
    tag_diff = 0.0 if old.tag == new.tag else 1.0

    old_classes = set(old.classes)
    new_classes = set(new.classes)
    if old_classes or new_classes:
        class_diff = 1.0 - len(old_classes & new_classes) / len(
            old_classes | new_classes
        )
    else:
        class_diff = 0.0

    id_diff = 0.0 if old.id_attr == new.id_attr else 1.0

    max_children = max(old.child_count, new.child_count)
    child_diff = (
        abs(old.child_count - new.child_count) / max_children
        if max_children > 0
        else 0.0
    )

    return (
        tag_diff * TAG_WEIGHT
        + class_diff * CLASS_WEIGHT
        + id_diff * ID_WEIGHT
        + child_diff * CHILD_COUNT_WEIGHT
    )


def skeleton_diff(old: list[NodeProfile], new: list[NodeProfile]) -> float:
    if not old and not new:
        return 0.0
    if not old or not new:
        return 1.0

    matcher = SequenceMatcher(None, old, new)
    total_diff = 0.0
    total_positions = 0

    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            total_positions += i2 - i1
        elif op == "replace":
            old_slice = old[i1:i2]
            new_slice = new[j1:j2]
            count = max(len(old_slice), len(new_slice))
            total_positions += count
            for k in range(count):
                if k < len(old_slice) and k < len(new_slice):
                    total_diff += node_diff(old_slice[k], new_slice[k])
                else:
                    total_diff += 1.0
        elif op == "insert":
            count = j2 - j1
            total_positions += count
            total_diff += count
        elif op == "delete":
            count = i2 - i1
            total_positions += count
            total_diff += count

    return total_diff / total_positions if total_positions > 0 else 0.0


def diff_score(old_path: Path, new_path: Path) -> float:
    old_soup = parse_html(old_path)
    new_soup = parse_html(new_path)

    l_diff = landmark_diff(
        extract_landmarks(old_soup), extract_landmarks(new_soup)
    )
    s_diff = skeleton_diff(
        extract_skeleton(old_soup), extract_skeleton(new_soup)
    )

    return l_diff * LANDMARK_WEIGHT + s_diff * SKELETON_WEIGHT


def interpret_score(score: float) -> str:
    if score > 0.40:
        return "Major structural rewrite detected"
    if score > 0.15:
        return "Significant layout modifications detected"
    return "Minor structural changes"


if __name__ == "__main__":
    main()
