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
    with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-only'}), patch('urllib.request.urlopen', side_effect=failure):
      self.assertIn('429', watch.ai_summary({'commits': []}))

  def test_empty_result(self):
    with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-only'}), patch('urllib.request.urlopen', return_value=io.BytesIO(b'{}')):
      self.assertIn('생성 결과 없음', watch.ai_summary({'commits': []}))

if __name__ == '__main__':
  unittest.main()
