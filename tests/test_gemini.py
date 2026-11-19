"""Offline API tests: QT_QPA_PLATFORM=offscreen python3 tests/test_gemini.py."""

import base64
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests
from qgis.core import QgsApplication, QgsProcessingContext, QgsProcessingFeedback

ROOT = Path(__file__).resolve().parents[1]
app = QgsApplication([], False)
app.initQgis()
sys.path.insert(0, str(Path(QgsApplication.pkgDataPath()) / 'python/plugins'))
spec = importlib.util.spec_from_file_location(
    'promptmap', ROOT / '__init__.py', submodule_search_locations=[str(ROOT)],
)
module = importlib.util.module_from_spec(spec)
sys.modules['promptmap'] = module
spec.loader.exec_module(module)

from promptmap.clients.gemini_3_pro_image import (
    MODELS, Gemini3ProImageAlgorithm, Gemini3ProImageAPIClient,
)

PNG = base64.b64encode(bytes.fromhex(
    '89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489'
    '0000000b49444154789c636000020000050001a5f645400000000049454e44ae426082'
)).decode()


def completed():
    return {'status': 'completed', 'steps': [
        {'type': 'thought', 'summary': [{'type': 'image', 'data': 'not-final'}]},
        {'type': 'model_output', 'content': [
            {'type': 'text', 'text': 'Done'},
            {'type': 'image', 'mime_type': 'image/png', 'data': PNG},
        ]},
    ]}


class GeminiTests(unittest.TestCase):
    @patch('requests.post')
    def test_each_model_request_and_final_image(self, post):
        post.return_value = Mock(status_code=200, json=completed)
        for idx, (_, model, size) in enumerate(MODELS):
            with self.subTest(model=model):
                client = Gemini3ProImageAPIClient('test-key', idx)
                result = client.process_image(PNG, 'Edit the map', '16:9', None)
                self.assertEqual(result, {'success': True, 'data': PNG, 'model': model})
                args, kwargs = post.call_args
                self.assertEqual(args[0], 'https://generativelanguage.googleapis.com/v1beta/interactions')
                payload = kwargs['json']
                self.assertEqual(payload['model'], model)
                self.assertEqual(payload['input'], [
                    {'type': 'text', 'text': 'Edit the map'},
                    {'type': 'image', 'mime_type': 'image/png', 'data': PNG},
                ])
                self.assertFalse(payload['store'])
                self.assertEqual(payload['response_format']['aspect_ratio'], '16:9')
                self.assertEqual(payload['response_format']['mime_type'], 'image/png')
                if size:
                    self.assertEqual(payload['response_format']['image_size'], size)
                else:
                    self.assertNotIn('image_size', payload['response_format'])
                self.assertEqual(kwargs['headers']['x-goog-api-key'], 'test-key')
                self.assertEqual(kwargs['headers']['Api-Revision'], '2026-05-20')
                self.assertEqual(kwargs['timeout'], 120)

    @patch('requests.post')
    def test_invalid_responses(self, post):
        cases = [
            {}, {'status': 'failed'}, {'status': 'completed', 'steps': []},
            {'status': 'completed', 'steps': None},
            {'status': 'completed', 'steps': [{'type': 'model_output', 'content': [
                {'type': 'image', 'mime_type': 'image/jpeg', 'data': PNG},
            ]}]},
        ]
        for data in ('bad-base64', base64.b64encode(b'not a PNG').decode(), None):
            response = completed()
            response['steps'][1]['content'][1]['data'] = data
            cases.append(response)
        for body in cases:
            with self.subTest(body=body):
                post.return_value = Mock(status_code=200, json=lambda: body)
                self.assertFalse(Gemini3ProImageAPIClient('key').process_image(PNG, 'Edit', '1:1', None)['success'])
        post.return_value.json.side_effect = ValueError('invalid JSON')
        self.assertFalse(Gemini3ProImageAPIClient('key').process_image(PNG, 'Edit', '1:1', None)['success'])

    @patch('requests.post')
    def test_http_and_network_errors(self, post):
        post.return_value = Mock(status_code=429, text='Quota exceeded')
        client = Gemini3ProImageAPIClient('key')
        self.assertIn('429', client.process_image(PNG, 'Edit', '1:1', None)['error'])
        post.side_effect = requests.Timeout('timed out')
        self.assertIn('Request failed', client.process_image(PNG, 'Edit', '1:1', None)['error'])

    @patch('requests.post')
    def test_validation_and_cancellation_do_not_send_requests(self, post):
        client = Gemini3ProImageAPIClient('key')
        self.assertFalse(client.process_image(PNG, 'Edit', '123:97', None)['success'])
        feedback = QgsProcessingFeedback()
        feedback.cancel()
        self.assertFalse(client.process_image(PNG, 'Edit', '1:1', feedback)['success'])
        for idx in (-1, len(MODELS)):
            with self.assertRaises(ValueError):
                Gemini3ProImageAPIClient('key', idx)
        post.assert_not_called()

    @patch('requests.post')
    def test_extended_ratios(self, post):
        post.return_value = Mock(status_code=200, json=completed)
        for idx, (_, model, _) in enumerate(MODELS):
            supported = model in {'gemini-nano-banana-2.1', 'gemini-3.1-flash-image'}
            self.assertEqual(Gemini3ProImageAPIClient('key', idx).process_image(
                PNG, 'Edit', '8:1', None,
            )['success'], supported)

    @patch.object(Gemini3ProImageAlgorithm, 'read_image_as_base64', return_value=PNG)
    @patch('requests.post')
    def test_processing_selection_and_legacy_id(self, post, read_image):
        post.return_value = Mock(status_code=200, json=completed)
        algorithm = Gemini3ProImageAlgorithm()
        algorithm.initAlgorithm()
        self.assertEqual(algorithm.name(), 'gemini_3_image')
        self.assertEqual(len(algorithm.parameterDefinition('MODEL').options()), 5)
        context = QgsProcessingContext()
        feedback = QgsProcessingFeedback()
        for idx, (_, model, _) in enumerate(MODELS):
            result = algorithm.execute_api('key', 'unused.png', 'Edit', '1:1',
                                           {'MODEL': idx}, context, feedback)
            self.assertEqual(result['model'], model)
        result = algorithm.execute_api('key', 'unused.png', 'Edit', '1:1', {}, context, feedback)
        self.assertEqual(result['model'], 'gemini-3-pro-image')


if __name__ == '__main__':
    try:
        unittest.main()
    finally:
        app.exitQgis()
