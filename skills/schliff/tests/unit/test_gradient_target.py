"""A gradient is applied only to the file its `target` names (ADR 0015).

`generate_patches` filters on confidence and effort and never on target, while
eleven gradients in `text_gradient.py` name `eval-suite.json` and `apply_patches`
only ever writes `skill_path`. Two of those eleven already satisfy the filter
(`:480`, `:491`) and are inert only because no handler exists for their issue
strings — an accident of handler coverage, not a guard.
"""
import text_gradient as tg

SKILL_WITHOUT_FRONTMATTER = "# deploy-helper\n\nDeploys the service.\n"


def _write(tmp_path, content=SKILL_WITHOUT_FRONTMATTER):
    p = tmp_path / "SKILL.md"
    p.write_text(content, encoding="utf-8")
    return str(p)


def _gradient(target):
    """A gradient that generate_patches would otherwise turn into a patch."""
    return {
        "dimension": "structure",
        "issue": "no_frontmatter",
        "target": target,
        "op": "insert",
        "instruction": "Add YAML frontmatter",
        "delta": 6.0,
        "confidence": "high",
        "effort": tg.EFFORT_SIMPLE,
    }


class TestForeignTargetIsNeverPatched:
    def test_gradient_naming_another_file_produces_no_patch(self, tmp_path):
        skill = _write(tmp_path)

        patches = tg.generate_patches(skill, [_gradient("eval-suite.json")])

        assert patches == [], "a gradient for another file must not patch the skill"

    def test_gradient_naming_an_arbitrary_other_file_produces_no_patch(self, tmp_path):
        skill = _write(tmp_path)

        patches = tg.generate_patches(skill, [_gradient("references/api.md")])

        assert patches == []


class TestInFileTargetsStillPatch:
    """The guard must not disturb the targets that mean 'somewhere in this file'."""

    def test_in_file_locator_still_produces_a_patch(self, tmp_path):
        skill = _write(tmp_path)

        patches = tg.generate_patches(skill, [_gradient("line:1")])

        assert len(patches) == 1

    def test_section_name_still_produces_a_patch(self, tmp_path):
        skill = _write(tmp_path)

        patches = tg.generate_patches(skill, [_gradient("frontmatter")])

        assert len(patches) == 1

    def test_naming_the_skill_itself_still_produces_a_patch(self, tmp_path):
        skill = _write(tmp_path)

        patches = tg.generate_patches(skill, [_gradient("SKILL.md")])

        assert len(patches) == 1
