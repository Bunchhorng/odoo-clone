from django.conf import settings
from django.test import RequestFactory, TestCase, override_settings
from django.urls import URLPattern, URLResolver, path
from django.views import View

from apps.core.views import health
from .endpoint_registry import is_explicitly_public, registered_methods, rule_for, view_key
from .permission_audit import audit_request


def _leaves(patterns, prefix=""):
    for item in patterns:
        route = prefix + str(item.pattern)
        if isinstance(item, URLResolver):
            yield from _leaves(item.url_patterns, route)
        elif isinstance(item, URLPattern):
            yield route, item.callback


def unmapped_routes(patterns):
    missing = []
    for route, callback in _leaves(patterns):
        if is_explicitly_public(route):
            continue
        methods = registered_methods(callback)
        if not methods and hasattr(callback, "view_class"):
            methods = tuple(method.upper() for method in callback.view_class.http_method_names
                            if hasattr(callback.view_class, method))
        # DRF router closures expose an action map, but ordinary function views
        # do not have reliable method metadata.  Mark those as unknown so a
        # future route cannot silently escape the registry.
        if not methods and hasattr(callback, "actions"):
            methods = tuple(method.upper() for method in callback.actions)
        if not methods:
            methods = ("UNKNOWN",)
        for method in methods:
            if rule_for(callback, method) is None:
                missing.append((route, method, view_key(callback)))
    return missing


class EndpointRegistryTests(TestCase):
    def test_every_non_public_api_route_is_mapped(self):
        from config.urls import urlpatterns
        self.assertEqual(unmapped_routes(urlpatterns), [])

    def test_dummy_unmapped_route_is_detected_then_removed(self):
        from config.urls import urlpatterns
        def dummy_function(_request):
            return health(_request)
        dummy = path("api/v1/dummy-unmapped/", dummy_function)
        urlpatterns.append(dummy)
        try:
            self.assertIn(("api/v1/dummy-unmapped/", "UNKNOWN", f"{__name__}.dummy_function"), unmapped_routes(urlpatterns))
        finally:
            urlpatterns.pop()
        self.assertEqual(unmapped_routes(urlpatterns), [])

    def test_dummy_class_route_is_detected_then_removed(self):
        from config.urls import urlpatterns
        class DummyView(View):
            def get(self, request):
                return health(request)
        dummy = path("api/v1/dummy-class-unmapped/", DummyView.as_view())
        urlpatterns.append(dummy)
        try:
            self.assertIn(("api/v1/dummy-class-unmapped/", "GET", "apps.companies.test_endpoint_registry.view"), unmapped_routes(urlpatterns))
        finally:
            urlpatterns.pop()
        self.assertEqual(unmapped_routes(urlpatterns), [])

    @override_settings(PERMISSION_MODE="off")
    def test_off_mode_adds_zero_queries(self):
        request = RequestFactory().get("/api/v1/companies/1/erp/dashboard/")
        request.user = type("User", (), {"pk": 1, "is_authenticated": True})()
        view = type("View", (), {"__module__": "apps.business.views", "__name__": "dashboard"})
        with self.assertNumQueries(0):
            audit_request(request, view, {"company_id": 1})
