import io
import json
import os
import unittest
import urllib.error
from unittest.mock import patch
import watch

class SummaryTests(unittest.TestCase):
  def test_no_key_skips_api(self):
    with patch.dict(os.environ, {}, clear=True), patch('urllib.request.urlopen') as send:
      self.assertIsNone(watch.ai_summary({'commits': []}))
      send.assert_not_called()

  def test_gemini_request_and_text(self):
    response = {'candidates': [{'content': {'parts': [{'text': '내부 추론', 'thought': True}, {'text': '변경 요약'}]}, 'finishReason': 'STOP'}]}
    with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-only'}), patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(response).encode())) as send:
      self.assertEqual(watch.ai_summary({'commits': []}), '변경 요약')
      request = send.call_args.args[0]
      self.assertNotIn('test-only', request.full_url)
      self.assertEqual(request.get_header('X-goog-api-key'), 'test-only')
      self.assertIn('contents', json.loads(request.data))

  def test_api_failure_keeps_notification(self):
    failure = urllib.error.HTTPError('https://example.invalid', 429, 'quota', {}, None)
    with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-only'}), patch('urllib.request.urlopen', side_effect=failure), patch('watch.time.sleep'):
      self.assertIn('429', watch.ai_summary({'commits': []}))

  def test_transient_error_retries(self):
    failure = urllib.error.HTTPError('https://example.invalid', 503, 'busy', {}, None)
    response = io.BytesIO(json.dumps({'candidates': [{'content': {'parts': [{'text': '재시도 성공'}]}}]}).encode())
    with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-only'}), patch('urllib.request.urlopen', side_effect=[failure, response]) as send, patch('watch.time.sleep'):
      self.assertEqual(watch.ai_summary({'commits': []}), '재시도 성공')
      self.assertEqual(send.call_count, 2)

  def test_empty_result(self):
    with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-only'}), patch('urllib.request.urlopen', return_value=io.BytesIO(b'{}')):
      self.assertIn('생성 결과 없음', watch.ai_summary({'commits': []}))

class FallbackTests(unittest.TestCase):
  def test_backup_key_after_service_error(self):
    fail = urllib.error.HTTPError('https://example.invalid', 503, 'busy', {}, None)
    ok = io.BytesIO(json.dumps({'candidates': [{'content': {'parts': [{'text': 'ok'}]}}]}).encode())
    with patch.dict(os.environ, {'GEMINI_API_KEY': 'first', 'GEMINI_API_KEY_BACKUP': 'second'}, clear=True), patch('urllib.request.urlopen', side_effect=[fail, ok]) as send, patch('watch.time.sleep'):
      self.assertEqual(watch.ai_summary({'commits': []}), 'ok')
      self.assertEqual([c.args[0].get_header('X-goog-api-key') for c in send.call_args_list], ['first', 'second'])

  def test_quota_does_not_rotate_keys(self):
    fail = urllib.error.HTTPError('https://example.invalid', 429, 'quota', {}, None)
    with patch.dict(os.environ, {'GEMINI_API_KEY': 'first', 'GEMINI_API_KEY_BACKUP': 'second'}, clear=True), patch('urllib.request.urlopen', side_effect=fail) as send:
      self.assertIn('429', watch.ai_summary({'commits': []}))
      self.assertEqual(send.call_count, 1)

  def test_groq_fallback_is_bounded_and_labeled(self):
    ok = io.BytesIO(json.dumps({'choices': [{'finish_reason': 'stop', 'message': {'content': '백업 요약'}}]}).encode())
    cmp = {'commits': [{'sha': 'abc', 'commit': {'message': '한글' * 10000}}]}
    with patch.dict(os.environ, {'GROQ_API_KEY': 'test-only'}, clear=True), patch('urllib.request.urlopen', return_value=ok) as send:
      result = watch.ai_summary(cmp)
      self.assertIn('Groq 백업 · 일부 발췌', result)
      payload = json.loads(send.call_args.args[0].data)
      self.assertEqual(send.call_args.args[0].get_header('User-agent'), 'carrot-wip-watch/1.0')
      self.assertLess(sum(len(m['content'].encode()) for m in payload['messages']), 6000)

  def test_gemini_failure_uses_groq(self):
    with patch.dict(os.environ, {'GEMINI_API_KEY': 'first', 'GROQ_API_KEY': 'test-only'}, clear=True), patch('watch.gemini_summary', return_value='(AI 요약 실패: API 503)'), patch('watch.groq_summary', return_value='backup') as groq:
      self.assertEqual(watch.ai_summary({'commits': []}), 'backup')
      groq.assert_called_once()

if __name__ == '__main__':
  unittest.main()
