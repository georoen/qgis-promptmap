"""Offline OpenAI tests: QT_QPA_PLATFORM=offscreen python3 tests/test_openai.py."""

import base64
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import requests
from qgis.core import QgsApplication, QgsProcessingContext, QgsProcessingFeedback
from qgis.PyQt.QtCore import QBuffer, QIODevice
from qgis.PyQt.QtGui import QImage

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

from promptmap.clients.openai_image import COMPLEXITIES, MODELS, QUALITIES, OpenAIImageAlgorithm, OpenAIImageAPIClient


def png(width=1024, height=1024):
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(0xff336699)
    buffer = QBuffer()
    assert buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    assert image.save(buffer, 'PNG')
    return bytes(buffer.data())


class OpenAITests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'input.png'
        self.image = png()
        self.path.write_bytes(self.image)
        self.data = base64.b64encode(self.image).decode()
        self.body = {'data': [{'b64_json': self.data}], 'output_format': 'png',
                     'usage': {'input_tokens': 100, 'output_tokens': 20, 'total_tokens': 120,
                               'input_tokens_details': {'image_tokens': 96, 'text_tokens': 4}}}

    @patch('requests.post')
    def test_models_and_quality_payload(self, post):
        post.return_value = Mock(status_code=200, json=lambda: self.body)
        for idx, (_, model) in enumerate(MODELS):
            for quality in QUALITIES:
                with self.subTest(model=model, quality=quality):
                    result = OpenAIImageAPIClient('test-key', idx).process_image(self.path, 'Remove all cars', quality, None)
                    self.assertEqual(result, {'success': True, 'data': self.data, 'model': model, 'usage': self.body['usage']})
                    args, kwargs = post.call_args
                    self.assertEqual(args[0], 'https://api.openai.com/v1/images/edits')
                    self.assertEqual(kwargs['headers'], {'Authorization': 'Bearer test-key'})
                    self.assertEqual(kwargs['data'], {'model': model, 'prompt': 'Remove all cars', 'n': '1',
                                                     'size': '1024x1024', 'quality': quality, 'complexity': 'high', 'output_format': 'png'})
                    self.assertEqual(kwargs['files']['image[]'], ('input.png', self.image, 'image/png'))
                    self.assertEqual(kwargs['timeout'], 180)

    @patch('requests.post')
    def test_complexity_modes_and_validation(self, post):
        post.return_value = Mock(status_code=200, json=lambda: self.body)
        client = OpenAIImageAPIClient('key')
        for complexity in COMPLEXITIES:
            result = client.process_image(self.path, 'Edit', 'medium', None, complexity=complexity)
            self.assertTrue(result['success'])
            self.assertEqual(post.call_args.kwargs['data']['complexity'], complexity)
        post.reset_mock()
        self.assertFalse(client.process_image(self.path, 'Edit', 'medium', None, complexity='invalid')['success'])
        post.assert_not_called()

    @patch('requests.post')
    def test_exact_widescreen_and_square_sizes(self, post):
        for width, height in [(2048, 2048), (1280, 720), (1536, 864)]:
            self.path.write_bytes(png(width, height))
            data = base64.b64encode(self.path.read_bytes()).decode()
            post.return_value = Mock(status_code=200, json=lambda: {'data': [{'b64_json': data}]})
            result = OpenAIImageAPIClient('key').process_image(self.path, 'Edit', 'medium', None)
            self.assertTrue(result['success'])
            self.assertEqual(post.call_args.kwargs['data']['size'], f'{width}x{height}')
            self.assertIsNone(result['usage'])

    @patch('requests.post')
    def test_invalid_input_never_sends_request(self, post):
        client = OpenAIImageAPIClient('key')
        self.assertFalse(client.process_image(self.path, 'Edit', 'invalid', None)['success'])
        for width, height in [(64, 64), (1000, 1024), (400, 2000), (4096, 1024)]:
            self.path.write_bytes(png(width, height))
            self.assertFalse(client.process_image(self.path, 'Edit', 'medium', None)['success'])
        self.path.write_bytes(b'not a PNG')
        self.assertFalse(client.process_image(self.path, 'Edit', 'medium', None)['success'])
        self.path.unlink()
        self.assertFalse(client.process_image(self.path, 'Edit', 'medium', None)['success'])
        for idx in (-1, len(MODELS)):
            with self.assertRaises(ValueError):
                OpenAIImageAPIClient('key', idx)
        post.assert_not_called()

    @patch('requests.post')
    def test_invalid_response_never_returns_success(self, post):
        bodies = [None, {}, {'data': []}, {'data': None}, {'data': [{}]},
                  {'data': [{'b64_json': 'bad-base64'}]},
                  {'data': [{'b64_json': base64.b64encode(b'not PNG').decode()}]},
                  {'data': [{'b64_json': self.data}], 'output_format': 'jpeg'},
                  {'data': [{'b64_json': base64.b64encode(png(1024, 512)).decode()}]}]
        for body in bodies:
            post.return_value = Mock(status_code=200, json=lambda: body)
            self.assertFalse(OpenAIImageAPIClient('key').process_image(self.path, 'Edit', 'medium', None)['success'])
        post.return_value.json.side_effect = ValueError('invalid JSON')
        self.assertFalse(OpenAIImageAPIClient('key').process_image(self.path, 'Edit', 'medium', None)['success'])

    @patch('requests.post')
    def test_http_network_errors_and_redaction(self, post):
        client = OpenAIImageAPIClient('test-key')
        post.return_value = Mock(status_code=403, text='Access denied for test-key')
        result = client.process_image(self.path, 'Edit', 'medium', None)
        self.assertIn('403', result['error'])
        self.assertNotIn('test-key', result['error'])
        post.side_effect = requests.Timeout('test-key timed out')
        result = client.process_image(self.path, 'Edit', 'medium', None)
        self.assertFalse(result['success'])
        self.assertNotIn('test-key', result['error'])

    @patch('requests.post')
    def test_cancellation_before_and_after_request(self, post):
        feedback = QgsProcessingFeedback()
        feedback.cancel()
        client = OpenAIImageAPIClient('key')
        self.assertFalse(client.process_image(self.path, 'Edit', 'medium', feedback)['success'])
        post.assert_not_called()
        feedback = QgsProcessingFeedback()
        def canceled(*args, **kwargs):
            feedback.cancel()
            return Mock(status_code=200, json=lambda: self.body)
        post.side_effect = canceled
        self.assertFalse(client.process_image(self.path, 'Edit', 'medium', feedback)['success'])
        self.assertEqual(post.call_count, 1)

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-openai', 'GEMINI_API_KEY': 'test-google', 'BFL_API_KEY': 'test-bfl'}, clear=True)
    @patch('requests.post')
    def test_processing_defaults_and_key_provider(self, post):
        post.return_value = Mock(status_code=200, json=lambda: self.body)
        algorithm = OpenAIImageAlgorithm()
        algorithm.initAlgorithm()
        self.assertEqual(algorithm.parameterDefinition('API_KEY').defaultValue(), 'test-openai')
        self.assertEqual(algorithm.name(), 'openai_image_editing')
        self.assertEqual(len(algorithm.parameterDefinition('MODEL').options()), 2)
        self.assertEqual(algorithm.parameterDefinition('COMPLEXITY').defaultValue(), 2)
        for idx, (_, model) in enumerate(MODELS):
            result = algorithm.execute_api('key', str(self.path), 'Edit', '1:1', {'MODEL': idx},
                                           QgsProcessingContext(), QgsProcessingFeedback())
            self.assertEqual(result['model'], model)
            self.assertEqual(post.call_args.kwargs['data']['quality'], 'medium')
            self.assertEqual(post.call_args.kwargs['data']['complexity'], 'high')
        for idx, complexity in enumerate(COMPLEXITIES):
            algorithm.execute_api('key', str(self.path), 'Edit', '1:1', {'COMPLEXITY': idx},
                                  QgsProcessingContext(), QgsProcessingFeedback())
            self.assertEqual(post.call_args.kwargs['data']['complexity'], complexity)
        self.assertIsInstance(algorithm.createInstance(), OpenAIImageAlgorithm)


if __name__ == '__main__':
    try:
        unittest.main()
    finally:
        app.exitQgis()
