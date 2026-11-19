"""Offline FLUX 3 tests: QT_QPA_PLATFORM=offscreen python3 tests/test_flux_3.py."""

import base64
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

from qgis.core import QgsApplication, QgsCoordinateReferenceSystem, QgsProcessingContext
from qgis.core import QgsProcessingFeedback, QgsRectangle, QgsVectorLayer
from qgis.PyQt.QtGui import QImage

ROOT = Path(__file__).resolve().parents[1]
app = QgsApplication([], False)
app.initQgis()
sys.path.insert(0, str(Path(QgsApplication.pkgDataPath()) / 'python/plugins'))
package = types.ModuleType('promptmap')
package.__path__ = [str(ROOT)]
sys.modules['promptmap'] = package

from promptmap.clients import base
from promptmap.clients.flux_2_editing import Flux2APIClient
from promptmap.clients.flux_3_editing import Flux3APIClient, Flux3EditingAlgorithm

POLL = 'https://api.eu1.bfl.ai/v1/get_result?id=task'
SAMPLE = 'https://delivery.eu1.bfl.ai/result.jpg?signature=example'


def response(body=None, status=200, content=b''):
    return Mock(status_code=status, json=Mock(return_value=body), content=content)


class Flux3Tests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.directory = Path(tmp.name)
        self.canvas = self.make_image('input.png', 1280, 720)
        self.jpeg = self.make_image('result.jpg', 1280, 720).read_bytes()

    def make_image(self, filename, width, height):
        path = self.directory / filename
        image = QImage(width, height, QImage.Format.Format_RGB32)
        image.fill(0xff336699)
        self.assertTrue(image.save(str(path)))
        return path

    @patch('requests.post')
    @patch('requests.get')
    @patch('promptmap.clients.bfl_base.time.sleep')
    def test_both_models_request_and_convert(self, sleep, get, post):
        for idx, (model, extra) in enumerate([
            ('flux-3-image', {'grounding': False}),
            ('flux-3-image-klein', {'output_format': 'png'}),
        ]):
            with self.subTest(model=model):
                post.return_value = response({'polling_url': POLL, 'cost': 12})
                get.reset_mock()
                get.side_effect = [response({'status': 'Generating'}), response({
                    'status': 'Ready', 'result': {'sample': SAMPLE}, 'cost': 0,
                }), response(content=self.jpeg)]
                result = Flux3APIClient('test-key', idx).process_image(str(self.canvas), 'Remove cars', None)
                self.assertTrue(result['success'], result)
                self.assertEqual(result['model'], model)
                self.assertEqual((result['cost_credits'], result['cost_basis']), (0, 'settled'))
                data = base64.b64decode(result['data'])
                self.assertTrue(data.startswith(b'\x89PNG\r\n\x1a\n'))
                payload = post.call_args.kwargs['json']
                self.assertEqual(post.call_args.args[0], f'https://api.eu.bfl.ai/v1/{model}')
                self.assertEqual(payload, {'prompt': 'Remove cars', 'images': [base64.b64encode(self.canvas.read_bytes()).decode()],
                                           'width': 1280, 'height': 720, **extra})
                self.assertEqual(post.call_args.kwargs['headers']['x-key'], 'test-key')
                self.assertFalse(post.call_args.kwargs['allow_redirects'])
                self.assertEqual([call.args[0] for call in get.call_args_list], [POLL, POLL, SAMPLE])
                self.assertEqual(get.call_args_list[0].kwargs['headers']['x-key'], 'test-key')
                self.assertNotIn('headers', get.call_args.kwargs)
                self.assertFalse(get.call_args.kwargs['allow_redirects'])

    @patch('requests.post')
    @patch('requests.get')
    def test_shared_polling_cost_and_terminal_status(self, get, post):
        post.return_value = response({'polling_url': POLL, 'cost': 2.1})
        client = Flux2APIClient('test-key', 0)
        get.return_value = response({'status': 'Ready', 'result': {'sample': SAMPLE}})
        self.assertEqual(client.post_and_poll({}, None), {
            'success': True, 'url': SAMPLE, 'cost_credits': 2.1, 'cost_basis': 'submission',
        })
        for status in ('Error', 'Content Moderated', 'Task not found', 'No Card Generated'):
            get.reset_mock()
            get.return_value = response({'status': status}, 503 if status == 'Error' else 200)
            result = client.post_and_poll({}, None)
            self.assertFalse(result['success'])
            self.assertIn(status, result['error'])
            get.assert_called_once()

    @patch('requests.post')
    @patch('requests.get')
    def test_polling_does_not_forward_credentials_to_untrusted_url(self, get, post):
        for url in (None, 'http://api.bfl.ai/task', 'https://api.bfl.ai.example.com/task',
                    'https://other.example.com\\@api.bfl.ai/task'):
            post.return_value = response({'polling_url': url})
            self.assertFalse(Flux3APIClient('test-key', 0).post_and_poll({}, None)['success'])
        get.assert_not_called()

    @patch('requests.post')
    @patch('requests.get')
    def test_invalid_size_and_wrong_aspect_ratio(self, get, post):
        client = Flux3APIClient('key', 0)
        small = self.make_image('tiny.png', 128, 128)
        self.assertFalse(client.process_image(str(small), 'Edit', None)['success'])
        post.assert_not_called()
        post.return_value = response({'polling_url': POLL})
        wrong = self.make_image('wrong.png', 256, 256)
        get.side_effect = [response({'status': 'Ready', 'result': {'sample': SAMPLE}}), response(content=wrong.read_bytes())]
        self.assertIn('aspect ratio', client.process_image(str(self.canvas), 'Edit', None)['error'])

    @patch('requests.post')
    @patch('requests.get')
    def test_qgis_algorithm_exports_model_and_credits(self, get, post):
        post.return_value = response({'polling_url': POLL, 'cost': 4})
        get.side_effect = [response({'status': 'Ready', 'result': {'sample': SAMPLE}}), response(content=self.jpeg)]
        alg = Flux3EditingAlgorithm()
        alg.initAlgorithm()
        crs = QgsCoordinateReferenceSystem('EPSG:3857')
        canvas = types.SimpleNamespace(extent=lambda: QgsRectangle(0, 0, 160, 90),
                                       mapSettings=lambda: types.SimpleNamespace(destinationCrs=lambda: crs))
        with (patch.object(base, 'iface', types.SimpleNamespace(mapCanvas=lambda: canvas)),
              patch.object(alg, '_render_map'), patch.object(alg, '_load_raster_layer'),
              patch.object(alg, '_load_vector_layer')):
            output = alg.processAlgorithm({'API_KEY': 'key', 'MODEL': 1, 'PROMPT': 'Edit', 'TILE_SIZE': 1,
                                           'OUTPUT_DIR': str(self.directory)},
                                          QgsProcessingContext(), QgsProcessingFeedback())
        self.assertTrue(Path(output['OUTPUT']).is_file())
        layer = QgsVectorLayer(str(Path(output['OUTPUT']).with_suffix('.gpkg')), 'metadata', 'ogr')
        feature = next(layer.getFeatures())
        self.assertEqual((feature['model'], feature['cost_credits'], feature['cost_basis']),
                         ('flux-3-image-klein', '4', 'submission'))


if __name__ == '__main__':
    try:
        unittest.main()
    finally:
        app.exitQgis()
