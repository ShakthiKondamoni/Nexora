"""Strict selected-document retrieval for Document Chat (History + Geography).

Every test uses the isolated temporary database from tests/conftest.py; no personal DB
or real Ollama endpoint is touched.
"""
import base64
import json
import time
import uuid

import pytest
import requests
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.main import app
from backend.database.connection import q as Q
from backend.services import document_chat_service, knowledge_index, knowledge_service
from backend.services.document_chat_service import citation, prepare, selection, verify_answer


def make_source(title, pages, doc_type=None, status='ready', indexed=True):
    """Insert a Knowledge Base source with pages and (optionally) its chunk index."""
    doc_type = doc_type or ('pdf' if title.lower().endswith('.pdf') else 'text')
    sid = uuid.uuid4().hex
    Q('INSERT INTO sources(id,coll_id,type,title,path,hash,status,error,ocr_model,added) '
      'VALUES(?,?,?,?,?,?,?,?,?,?)',
      sid, 'test-coll', doc_type, title, '/tmp/' + sid, sid, status, None, '', time.time())
    for loc, text in pages:
        kind = 'page' if doc_type == 'pdf' else 'text'
        Q('INSERT INTO pages(source_id,loc,kind,status,text,error) VALUES(?,?,?,?,?,?)',
          sid, loc, kind, 'ok', text, None)
    if indexed:
        knowledge_index.index_source(sid)
    return sid


class Reply:
    """Minimal stand-in for a streamed Ollama response."""

    def __init__(self, lines, status=200):
        self.lines = lines
        self.status_code = status
        self.text = 'simulated response'

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def iter_lines(self):
        return iter(self.lines)


def streamed(text):
    return Reply([json.dumps({'message': {'content': text}}).encode()])


def new_chat():
    return TestClient(app).post('/api/chats').json()['id']


# ---------- document resolution ----------
def test_selection_resolves_history_and_geography_ids():
    history = make_source('History.pdf', [(1, 'The French Revolution began in 1789 in Paris.')])
    geography = make_source('Geography.pdf', [(1, 'Tectonic plates move continents slowly.')])
    biology = make_source('Biology.pdf', [(1, 'Photosynthesis happens inside chloroplasts.')])
    report = selection()
    assert [d['id'] for d in report['documents']] == [history, geography]
    assert [d['title'] for d in report['documents']] == ['History.pdf', 'Geography.pdf']
    assert biology not in [d['id'] for d in report['documents']]
    assert report['missing'] == [] and report['not_indexed'] == [] and report['ready'] is True
    assert report['selected_names'] == ['History', 'Geography']


def test_missing_documents_never_fall_back_to_all_documents():
    make_source('History.pdf', [(1, 'The French Revolution began in 1789.')])
    make_source('Biology.pdf', [(1, 'Photosynthesis happens inside chloroplasts.')])
    report = selection()
    assert report['missing'] == ['Geography'] and report['ready'] is False
    with pytest.raises(HTTPException) as error:
        prepare('When did the French Revolution begin?')
    assert error.value.status_code == 404 and 'Geography' in error.value.detail
    # The unselected Biology document is never substituted for the missing selection.
    assert 'photosynthesis' not in json.dumps(selection()).lower()


def test_empty_selection_is_rejected():
    make_source('History.pdf', [(1, 'The French Revolution began in 1789.')])
    assert selection([])['ready'] is False
    with pytest.raises(HTTPException) as error:
        prepare('anything', names=[])
    assert error.value.status_code == 422


def test_unindexed_document_blocks_instead_of_silently_falling_back():
    make_source('History.pdf', [(1, 'The French Revolution began in 1789.')])
    make_source('Geography.pdf', [(1, 'Tectonic plates move continents.')], indexed=False)
    report = selection()
    assert report['not_indexed'] == ['Geography.pdf'] and report['ready'] is False
    with pytest.raises(HTTPException) as error:
        prepare('Where do tectonic plates move?')
    assert error.value.status_code == 409 and 'Re-index' in error.value.detail


# ---------- hard filtering of every retrieval path ----------
def test_keyword_search_and_reranking_exclude_unselected_documents():
    history = make_source('History.pdf', [(1, 'The French Revolution began in 1789 in Paris.')])
    geography = make_source('Geography.pdf', [(1, 'Tectonic plates move continents slowly over time.')])
    biology = make_source('Biology.pdf', [(1, 'Photosynthesis converts light energy in chloroplasts.')])
    # The index really does contain the unselected document ...
    assert knowledge_index.search_chunks('photosynthesis chloroplasts', [history, geography, biology], 5)
    # ... but an allowed set that excludes it returns nothing, before and after reranking.
    assert knowledge_index.search_chunks('photosynthesis chloroplasts', [history, geography, biology], 5,
                                         allowed_source_ids={history, geography}) == []
    result = prepare('photosynthesis chloroplasts')
    assert result['status'] == 'insufficient_evidence' and result['passages'] == []
    assert result['citations'] == []


def test_every_fallback_path_respects_the_selection():
    history = make_source('History.pdf', [(1, 'The French Revolution began in 1789 in Paris.')])
    geography = make_source('Geography.pdf', [(1, 'Tectonic plates move continents slowly over time.')])
    # Scope "all" (unrestricted) still cannot leak a source outside the allowed set.
    scoped = knowledge_service.retrieve('French Revolution', [{'t': 'all'}], 6, allowed_source_ids={geography})
    assert scoped and all(hit['sid'] == geography for hit in scoped)
    # The generic-request sampling fallback is filtered out entirely.
    assert knowledge_service.retrieve('make a quiz', [{'t': 'src', 'id': history}], 3,
                                      allow_sample=True, allowed_source_ids={geography}) == []
    # Sampled fallback stays inside the selected document.
    sampled = knowledge_service.retrieve('make a quiz', [{'t': 'src', 'id': geography}], 3,
                                         allow_sample=True, allowed_source_ids={geography})
    assert sampled and all(hit['sid'] == geography for hit in sampled)


# ---------- citations ----------
def test_citation_labels_use_real_names_and_never_invent_pages():
    assert citation('History.pdf', 'pdf', 12) == '[History.pdf, p. 12]'
    assert citation('Geography.pdf', 'pdf', None) == '[Geography.pdf]'
    assert citation('Notes.md', 'text', 3) == '[Notes.md, part 3]'
    assert citation('Cells.ipynb', 'notebook', 2) == '[Cells.ipynb, cell 2]'


def test_retrieved_passages_carry_the_document_citation():
    make_source('History.pdf', [(12, 'The Treaty of Versailles was signed in 1919.')])
    make_source('Geography.pdf', [(1, 'Tectonic plates move continents slowly over time.')])
    result = prepare('When was the Treaty of Versailles signed?')
    assert result['status'] == 'answered'
    assert result['passages'][0]['citation'] == '[History.pdf, p. 12]'
    assert result['citations'][0]['citation'] == '[History.pdf, p. 12]'
    assert result['citations'][0]['filename'] == 'History.pdf'


def test_fabricated_citations_are_removed_and_verified_sources_listed():
    citations = [{'citation': '[History.pdf, p. 12]'}, {'citation': '[Geography.pdf, p. 3]'}]
    kept = verify_answer('The treaty was signed in 1919 [History.pdf, p. 12].', citations)
    assert '[History.pdf, p. 12]' in kept and 'unverified' not in kept
    fabricated = verify_answer('A claim [Geography.pdf, p. 999].', citations)
    assert '[Geography.pdf, p. 999]' not in fabricated
    assert '[unverified citation removed]' in fabricated
    assert 'Sources: [Geography.pdf, p. 3], [History.pdf, p. 12]' in fabricated
    linked = verify_answer('A linked claim [Geography.pdf, p. 500](http://example.invalid/x).', citations)
    assert 'p. 500' not in linked and '[unverified citation removed]' in linked
    uncited = verify_answer('No citation at all.', citations)
    assert 'Sources: [Geography.pdf, p. 3], [History.pdf, p. 12]' in uncited


# ---------- chat pipeline ----------
def test_document_chat_endpoint_sends_only_selected_passages(monkeypatch):
    history = make_source('History.pdf', [(12, 'The Treaty of Versailles was signed in 1919.')])
    make_source('Geography.pdf', [(4, 'The Alps formed from a tectonic plate collision.')])
    biology = make_source('Biology.pdf', [(1, 'Photosynthesis converts light in chloroplasts.')])
    seen = []

    def post(*args, **kwargs):
        seen.append(kwargs['json'])
        return streamed('It was signed in 1919 [History.pdf, p. 12].')

    monkeypatch.setattr(requests, 'post', post)
    client = TestClient(app)
    cid = client.post('/api/chats').json()['id']
    response = client.post(
        f'/api/chats/{cid}/send',
        data={'text': 'When was the Treaty of Versailles signed?', 'model': 'local',
              'doc_mode': 'true', 'web_mode': 'search_first',
              'kb': json.dumps([{'t': 'src', 'id': biology}])},
    )
    assert response.status_code == 200
    payload = seen[-1]
    wire = json.dumps(payload)
    assert 'Treaty of Versailles was signed in 1919' in wire
    assert 'Photosynthesis' not in wire and 'chloroplasts' not in wire
    assert 'tools' not in payload                      # web search disabled
    assert payload['messages'][0]['content'].startswith('Answer ONLY from the supplied excerpts')
    assert 'History.pdf, Geography.pdf' in payload['messages'][0]['content']
    assert 'Biology.pdf' not in wire
    assert payload['messages'][-1]['content'].startswith('SELECTED DOCUMENT EXCERPTS')
    assert '[History.pdf, p. 12]' in payload['messages'][-1]['content']
    assert response.text.strip() == 'It was signed in 1919 [History.pdf, p. 12].'
    sources = json.loads(base64.b64decode(response.headers['X-Sources']))
    assert [s['sid'] for s in sources] == [history]
    assert sources[0]['citation'] == '[History.pdf, p. 12]'
    stored = json.loads(client.get(f'/api/chats/{cid}/messages').json()[-1]['sources'])
    assert stored[0]['citation'] == '[History.pdf, p. 12]'


def test_document_chat_rejects_fabricated_citations_from_the_model(monkeypatch):
    make_source('History.pdf', [(12, 'The Treaty of Versailles was signed in 1919.')])
    make_source('Geography.pdf', [(4, 'The Alps formed from a tectonic plate collision.')])
    monkeypatch.setattr(requests, 'post', lambda *a, **k: streamed('Signed in 1919 [History.pdf, p. 999].'))
    client = TestClient(app)
    cid = client.post('/api/chats').json()['id']
    response = client.post(f'/api/chats/{cid}/send',
                           data={'text': 'When was the Treaty of Versailles signed?', 'model': 'local',
                                 'doc_mode': 'true'})
    assert response.status_code == 200
    assert '[History.pdf, p. 999]' not in response.text
    assert '[unverified citation removed]' in response.text
    assert 'Sources: [History.pdf, p. 12]' in response.text


def test_unsupported_question_reports_insufficient_evidence_without_calling_the_model(monkeypatch):
    # The documents contain "of"/"the" so only a content word may count as evidence.
    make_source('History.pdf', [(1, 'The French Revolution began in 1789 in the city of Paris.')])
    make_source('Geography.pdf', [(1, 'Tectonic plates move the continents slowly.')])
    calls = []
    monkeypatch.setattr(requests, 'post', lambda *a, **kw: calls.append(kw))
    client = TestClient(app)
    cid = client.post('/api/chats').json()['id']
    response = client.post(f'/api/chats/{cid}/send',
                           data={'text': 'What is the capital of Mars?', 'model': 'local', 'doc_mode': 'true'})
    assert response.status_code == 200 and calls == []
    assert 'do not contain enough evidence' in response.text
    stored = client.get(f'/api/chats/{cid}/messages').json()
    assert stored[-1]['role'] == 'assistant' and 'enough evidence' in stored[-1]['content']


def test_document_chat_endpoint_reports_missing_selected_documents():
    make_source('History.pdf', [(1, 'The French Revolution began in 1789.')])
    client = TestClient(app)
    cid = client.post('/api/chats').json()['id']
    response = client.post(f'/api/chats/{cid}/send',
                           data={'text': 'When did it begin?', 'model': 'local', 'doc_mode': 'true'})
    assert response.status_code == 404 and 'Geography' in response.json()['detail']
    # The rejected question is not persisted as an orphan turn.
    assert client.get(f'/api/chats/{cid}/messages').json() == []


def test_unrestricted_chat_behavior_is_preserved(monkeypatch):
    make_source('History.pdf', [(1, 'The French Revolution began in 1789 in Paris.')])
    make_source('Geography.pdf', [(1, 'Tectonic plates move continents slowly over time.')])
    seen = []

    def post(*args, **kwargs):
        seen.append(kwargs['json'])
        return streamed('Both sources are used [S1].')

    monkeypatch.setattr(requests, 'post', post)
    client = TestClient(app)
    cid = client.post('/api/chats').json()['id']
    response = client.post(f'/api/chats/{cid}/send',
                           data={'text': 'Tell me about the French Revolution and tectonic plates',
                                 'model': 'local', 'kb': json.dumps([{'t': 'all'}])})
    assert response.status_code == 200
    payload = seen[-1]
    wire = json.dumps(payload['messages'])
    assert payload['messages'][0]['content'].startswith('Use Knowledge Base sources')
    assert 'SELECTED DOCUMENT EXCERPTS' not in wire
    assert 'French Revolution' in wire and 'Tectonic plates' in wire
    assert 'KNOWLEDGE BASE SOURCES' in payload['messages'][-1]['content']
