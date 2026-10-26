"""MTQ-3b1: gọi Handler trực tiếp, không mở server hoặc kết nối CSDL."""

import io
import json
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from kho_tri_thuc.giao_dien import ma_tran_tham_quyen as mtq_http
from kho_tri_thuc.giao_dien.server import ASSETS, Handler


class MtqHttpDispatchTests(unittest.TestCase):
    def setUp(self):
        self.app = SimpleNamespace(mutation_lock=threading.Lock(), token="TOKEN-DEMO-MTQ", is_that=False)

    def handler(self, path):
        h = Handler.__new__(Handler)
        h.path = path
        h.server = SimpleNamespace(app=self.app, server_port=8765)
        h.headers = {"Host": "127.0.0.1:8765", "X-KTT-Token": self.app.token}
        h.wfile = io.BytesIO()
        h.send_response = Mock()
        h.send_header = Mock()
        h.end_headers = Mock()
        return h

    def dispatch(self, post, path):
        h = self.handler(path)

        def module(handler, app, is_post, route, query):
            self.assertFalse(app.mutation_lock.locked())
            return handler.send_content(200, {"demo": True})

        with patch.object(mtq_http, "dieu_huong", side_effect=module) as route:
            (h.do_POST if post else h.do_GET)()
        route.assert_called_once_with(h, self.app, post, path, {})
        h.send_response.assert_called_once_with(200)
        self.assertEqual(json.loads(h.wfile.getvalue()), {"demo": True})

    def test_get_cua_toi_chuyen_module_khong_giu_khoa(self):
        self.dispatch(False, "/api/tham-quyen/cua-toi")

    def test_post_luu_nhap_chuyen_module_khong_giu_khoa(self):
        self.dispatch(True, "/api/tham-quyen/luu-nhap")

    def test_csrf_am_chan_truoc_module_tung_route(self):
        for post, paths in ((False, mtq_http.GET), (True, mtq_http.POST)):
            for path in paths:
                for invalid in ('thieu_token', 'origin_la'):
                    with self.subTest(post=post, path=path, invalid=invalid):
                        h = self.handler(path)
                        if invalid == 'thieu_token':
                            h.headers.pop('X-KTT-Token')
                            code = 'SESSION_TOKEN'
                        else:
                            h.headers['Origin'] = 'https://example.invalid'
                            code = 'CROSS_ORIGIN'
                        with patch.object(mtq_http, 'dieu_huong') as route:
                            (h.do_POST if post else h.do_GET)()
                        route.assert_not_called()
                        h.send_response.assert_called_once_with(403)
                        self.assertEqual(json.loads(h.wfile.getvalue())['error'], code)
                        self.assertFalse(self.app.mutation_lock.locked())

    def test_bootstrap_qua_module_tra_404(self):
        for post in (False, True):
            with self.subTest(post=post):
                h = self.handler("/api/tham-quyen/bootstrap")
                with patch.object(mtq_http, "dieu_huong", wraps=mtq_http.dieu_huong) as route:
                    (h.do_POST if post else h.do_GET)()
                route.assert_called_once_with(h, self.app, post, h.path, {})
                h.send_response.assert_called_once_with(404)
                self.assertEqual(json.loads(h.wfile.getvalue())["error"], "NOT_FOUND")
                self.assertFalse(self.app.mutation_lock.locked())

    def test_asset_ma_tran_duoc_phuc_vu(self):
        h = self.handler("/ma_tran_tham_quyen.js")
        h.do_GET()
        h.send_response.assert_called_once_with(200)
        h.send_header.assert_any_call("Content-Type", "text/javascript; charset=utf-8")
        self.assertEqual(h.wfile.getvalue(), (ASSETS / "ma_tran_tham_quyen.js").read_bytes())
        self.assertTrue(h.wfile.getvalue())

    def test_khong_mo_rong_phuc_vu_asset_tuy_y(self):
        for path in ("/tuy_y.js", "/../server.py", "/assets/ma_tran_tham_quyen.js"):
            with self.subTest(path=path):
                h = self.handler(path)
                h.do_GET()
                h.send_response.assert_called_once_with(404)
                self.assertEqual(json.loads(h.wfile.getvalue())["error"], "NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
