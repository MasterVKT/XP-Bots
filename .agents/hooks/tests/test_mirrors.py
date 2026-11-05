"""Generated copies: synchronisation, the five negative cases, path rewriting and line endings."""
from __future__ import annotations

from pathlib import Path
import shutil
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import RepoCopy  # noqa: E402

MCL = '.claude/skills/mcl-matryoshka-construction-layers/SKILL.md'


class MirrorTests(unittest.TestCase):
    def setUp(self):
        self.repo = RepoCopy(git=False)

    def tearDown(self):
        self.repo.close()

    def check(self):
        result = self.repo.python('.agents/hooks/skill_mirrors.py', '--check')
        return result.returncode, result.stdout.decode('utf-8')

    def test_initial_copies_are_synchronised(self):
        self.assertEqual(self.check()[0], 0)

    def test_hand_edited_copy_detected(self):
        path = self.repo.path(MCL)
        path.write_text(path.read_text(encoding='utf-8') + '\nretouche manuelle\n', encoding='utf-8')
        code, output = self.check()
        self.assertEqual(code, 1)
        self.assertIn('éditée à la main', output)

    def test_stale_copy_detected_and_removed_by_write(self):
        shutil.rmtree(self.repo.path('.agents/skills/xp-bots-deployment-readiness'))
        code, output = self.check()
        self.assertEqual(code, 1)
        self.assertIn('copie périmée', output)
        self.repo.python('.agents/hooks/skill_mirrors.py', '--write')
        self.assertFalse(self.repo.path('.claude/skills/xp-bots-deployment-readiness').exists())

    def test_tool_only_skill_detected_and_left_intact(self):
        target = self.repo.path('.claude/skills/outil-seulement/SKILL.md')
        target.parent.mkdir()
        target.write_text('---\nname: outil-seulement\ndescription: "x"\n---\nCorps.\n', encoding='utf-8')
        code, output = self.check()
        self.assertEqual(code, 1)
        self.assertIn('seulement côté outil', output)
        self.repo.python('.agents/hooks/skill_mirrors.py', '--write')
        self.assertTrue(target.exists())

    def test_parasite_file_detected(self):
        self.repo.path('.claude/skills/mcl-matryoshka-construction-layers/notes.md').write_text('x', encoding='utf-8')
        code, output = self.check()
        self.assertEqual(code, 1)
        self.assertIn('fichier parasite', output)

    def test_unpropagated_source_change_detected(self):
        source = self.repo.path('.agents/skills/xp-bots-london-breakout/SKILL.md')
        source.write_text(source.read_text(encoding='utf-8') + '\n- Garde-fou ajouté.\n', encoding='utf-8')
        code, output = self.check()
        self.assertEqual(code, 1)
        self.repo.python('.agents/hooks/skill_mirrors.py', '--write')
        self.assertEqual(self.check()[0], 0)

    def test_paths_rewritten_only_when_target_exists(self):
        text = self.repo.path(MCL).read_text(encoding='utf-8')
        self.assertIn('`.agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py`', text)
        self.assertIn('<répertoire du skill>/scripts/mcl.py', text)
        self.assertNotIn('`references/01-socle-commun.md`', text)
        self.assertFalse(list(self.repo.path('.claude/skills/mcl-matryoshka-construction-layers').glob('references')))

    def test_crlf_source_line_endings_preserved(self):
        source = self.repo.path('.agents/skills/xp-bots-london-breakout/SKILL.md')
        source.write_bytes(source.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
        self.repo.python('.agents/hooks/skill_mirrors.py', '--write')
        copy = self.repo.path('.claude/skills/xp-bots-london-breakout/SKILL.md').read_bytes()
        self.assertNotIn(b'\n', copy.replace(b'\r\n', b''))
        self.assertEqual(self.check()[0], 0)


if __name__ == '__main__':
    unittest.main()
