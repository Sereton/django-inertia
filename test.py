import os
from unittest import TestCase
from unittest.mock import MagicMock

import django
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.test import RequestFactory

from inertia.middleware import InertiaMiddleware
from inertia.share import share
from inertia.version import get_version
from inertia.views import location, render_inertia

settings.configure(
    VERSION=1,
    DEBUG=True,
    TEMPLATES=[
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "APP_DIRS": True,
            "DIRS": [
                os.path.join("testutils"),
            ],
        }
    ],
    INERTIA_SHARE="test.share_custom_func",
)
django.setup()


def share_custom_func(request):
    share(request, "custom_data", "custom_value")


class TestInertia(TestCase):
    def test_views(self):
        requestfactory = RequestFactory()
        request = requestfactory.get("/")
        self.set_session(request)
        response = render_inertia(request, "Index")
        self.assertTrue(b'id="page"' in response.content)

    def set_session(self, request):
        dict_sessions = {"share": {}}
        request.session = MagicMock()
        request.session.__getitem__.side_effect = lambda key: dict_sessions[key]

    def test_simple_view(self):
        request = RequestFactory().get("/")
        self.set_session(request)
        response = InertiaMiddleware(lambda x: HttpResponse())(request)
        self.assertTrue(response.status_code == 200, response.status_code)

    def test_middlware_missing_header(self):
        defaults = {
            "X-Inertia": "true",
            "X-Requested-With": "XMLHttpRequest",
            "X-Inertia-Version": str(get_version() + 1),
        }
        request = RequestFactory().get("/")
        request.headers = defaults
        self.set_session(request)
        response = InertiaMiddleware(lambda x: HttpResponse())(request)
        self.assertTrue(response.status_code == 409, response.status_code)

    def test_middleware(self):
        defaults = {
            "x-Inertia": "true",
            "X-Inertia-Version": get_version(),
            "x-Requested-With": "XMLHttpRequest",
        }
        request = RequestFactory().get("/")  # , **defaults)
        request.headers = defaults
        self.set_session(request)
        response = InertiaMiddleware(lambda request: HttpResponse())(request)
        self.assertTrue(response.status_code == 200, response.status_code)

    def test_share_custom_data(self):
        requestfactory = RequestFactory()
        request = requestfactory.get("/")
        self.set_session(request)
        render_inertia(request, "Index")
        self.assertDictEqual({"custom_data": "custom_value"}, request.session["share"])
        # self.assertTrue(b'share_custom_value"' in response.content)

    def test_redirect_303_for_put_patch_delete_requests(self):
        request = RequestFactory().put("/users/1")
        self.set_session(request)
        response = InertiaMiddleware(lambda x: HttpResponseRedirect(redirect_to="/users"))(request)
        self.assertTrue(response.status_code == 303, response.status_code)

        request = RequestFactory().patch("/users/1")
        self.set_session(request)
        response = InertiaMiddleware(lambda x: HttpResponseRedirect(redirect_to="/users"))(request)
        self.assertTrue(response.status_code == 303, response.status_code)

        request = RequestFactory().delete("/users/1")
        self.set_session(request)
        response = InertiaMiddleware(lambda x: HttpResponseRedirect(redirect_to="/users"))(request)
        self.assertTrue(response.status_code == 303, response.status_code)

    def test_resolve_lazy_loading_props(self):
        requestfactory = RequestFactory()
        request = requestfactory.get("/")
        self.set_session(request)

        def lazy_loaded_prop():
            return "2"

        response = render_inertia(request, "Index", {"a": "1", "b": lazy_loaded_prop})
        self.assertTrue(b'"props": {"a": "1", "b": "2"}' in response.content)

    def test_partial_loading(self):
        defaults = {
            "X-Inertia": "true",
            "X-Inertia-Version": get_version(),
            "X-Requested-With": "XMLHttpRequest",
            "X-Inertia-Partial-Data": ["a"],
            "X-Inertia-Partial-Component": "Index",
        }
        requestfactory = RequestFactory()
        request = requestfactory.get("/")
        request.headers = defaults
        self.set_session(request)

        def lazy_loaded_prop():
            return "2"

        response = render_inertia(request, "Index", {"a": "1", "b": lazy_loaded_prop})
        # check that b is not returned because we only ask for a
        self.assertIn(b'"props": {"a": "1"},', response.content)

    def test_location(self):
        response = location("https://github.com")
        self.assertEqual(409, response.status_code)
        self.assertEqual(
            ("X-Inertia-Location", "https://github.com"), response._headers["x-inertia-location"]
        )
