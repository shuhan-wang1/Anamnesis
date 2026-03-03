"""Track section/subsection/subsubsection hierarchy and shared theorem counter."""

import re

SECTION_PATTERN = re.compile(
    r'\\(section|subsection|subsubsection)\{([^}]+)\}'
)

# Environments that share the [theorem] counter (numbered per section)
NUMBERED_ENVS = {
    'definition', 'theorem', 'lemma', 'corollary', 'proposition',
    'remark', 'example', 'exercise', 'note', 'computation',
    'question', 'warning', 'claim',
}

# Separately numbered
SEPARATE_COUNTER_ENVS = {'problem'}

# Unnumbered
UNNUMBERED_ENVS = {'proof', 'proof-sketch'}


class SectionTracker:
    """Tracks current section path and theorem counter."""

    def __init__(self):
        self.section_num = 0
        self.subsection_num = 0
        self.subsubsection_num = 0
        self.section_title = ""
        self.subsection_title = ""
        self.subsubsection_title = ""
        self.theorem_counter = 0
        self.problem_counter = 0

    def update_section(self, level: str, title: str):
        if level == 'section':
            self.section_num += 1
            self.subsection_num = 0
            self.subsubsection_num = 0
            self.section_title = title
            self.subsection_title = ""
            self.subsubsection_title = ""
            self.theorem_counter = 0  # reset per section
        elif level == 'subsection':
            self.subsection_num += 1
            self.subsubsection_num = 0
            self.subsection_title = title
            self.subsubsection_title = ""
        elif level == 'subsubsection':
            self.subsubsection_num += 1
            self.subsubsection_title = title

    def get_section_path(self) -> list[str]:
        path = []
        if self.section_title:
            path.append(f"{self.section_num}. {self.section_title}")
        if self.subsection_title:
            path.append(f"{self.section_num}.{self.subsection_num} {self.subsection_title}")
        if self.subsubsection_title:
            path.append(
                f"{self.section_num}.{self.subsection_num}.{self.subsubsection_num} "
                f"{self.subsubsection_title}"
            )
        return path

    def next_number(self, env_type: str) -> str | None:
        """Increment counter and return display number, or None if unnumbered."""
        if env_type in UNNUMBERED_ENVS:
            return None
        if env_type in SEPARATE_COUNTER_ENVS:
            self.problem_counter += 1
            return str(self.problem_counter)
        if env_type in NUMBERED_ENVS:
            self.theorem_counter += 1
            return f"{self.section_num}.{self.theorem_counter}"
        return None
