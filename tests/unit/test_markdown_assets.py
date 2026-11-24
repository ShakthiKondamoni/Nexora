from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def test_safe_markdown_assets_present():
 assert (ROOT/'frontend/assets/vendor/marked.umd.js').is_file()
 assert (ROOT/'frontend/assets/vendor/purify.min.js').is_file()
 s=(ROOT/'frontend/assets/js/markdown.js').read_text(encoding='utf-8');assert 'DOMPurify.sanitize' in s and 'normalizeStudioMarkdown' in s
