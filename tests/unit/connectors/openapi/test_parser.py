"""Unit tests for OpenAPI parser."""

import unittest

from agentic_patterns.core.connectors.openapi.extraction.openapi_v3_parser import OpenApiV3Parser


class TestOpenApiV3Parser(unittest.TestCase):
    def test_parse_simple_spec(self):
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0", "description": "A test API"},
            "servers": [{"url": "https://api.example.com"}],
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "listUsers",
                        "summary": "List all users",
                        "responses": {"200": {"description": "Success"}},
                    }
                }
            },
        }

        parser = OpenApiV3Parser(spec, "test_api")
        api_info = parser.parse()

        self.assertEqual(api_info.api_id, "test_api")
        self.assertEqual(api_info.title, "Test API")
        self.assertEqual(api_info.version, "1.0.0")
        self.assertEqual(api_info.base_url, "https://api.example.com")
        self.assertEqual(len(api_info.endpoints), 1)

        endpoint = api_info.endpoints[0]
        self.assertEqual(endpoint.path, "/users")
        self.assertEqual(endpoint.method, "GET")
        self.assertEqual(endpoint.operation_id, "listUsers")

    def test_parse_with_parameters(self):
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users/{user_id}": {
                    "get": {
                        "operationId": "getUser",
                        "parameters": [
                            {
                                "name": "user_id",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string"},
                                "description": "User ID",
                            },
                            {
                                "name": "include_details",
                                "in": "query",
                                "required": False,
                                "schema": {"type": "boolean", "default": False},
                            },
                        ],
                        "responses": {"200": {"description": "Success"}},
                    }
                }
            },
        }

        parser = OpenApiV3Parser(spec, "test_api")
        api_info = parser.parse()

        endpoint = api_info.endpoints[0]
        self.assertEqual(len(endpoint.parameters), 2)

        path_param = endpoint.parameters[0]
        self.assertEqual(path_param.name, "user_id")
        self.assertEqual(path_param.location, "path")
        self.assertTrue(path_param.required)

        query_param = endpoint.parameters[1]
        self.assertEqual(query_param.name, "include_details")
        self.assertEqual(query_param.location, "query")
        self.assertFalse(query_param.required)

    def test_parse_with_request_body(self):
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "operationId": "createUser",
                        "requestBody": {
                            "description": "User object",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object", "properties": {"name": {"type": "string"}}}
                                }
                            },
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }

        parser = OpenApiV3Parser(spec, "test_api")
        api_info = parser.parse()

        endpoint = api_info.endpoints[0]
        self.assertIsNotNone(endpoint.request_body)
        self.assertEqual(endpoint.request_body.content_type, "application/json")

    def test_base_url_override(self):
        """Test that config base_url overrides spec's servers section."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "servers": [{"url": "https://production.api.example.com"}],
            "paths": {"/test": {"get": {"operationId": "test", "responses": {"200": {"description": "OK"}}}}},
        }

        # Without override - should use spec's server URL
        parser = OpenApiV3Parser(spec, "test_api")
        api_info = parser.parse()
        self.assertEqual(api_info.base_url, "https://production.api.example.com")

        # With override - should use provided base_url
        parser_override = OpenApiV3Parser(spec, "test_api", base_url="http://localhost:8000")
        api_info_override = parser_override.parse()
        self.assertEqual(api_info_override.base_url, "http://localhost:8000")

    def test_base_url_fallback_when_no_servers(self):
        """Test fallback to empty string when spec has no servers and no override."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {"/test": {"get": {"operationId": "test", "responses": {"200": {"description": "OK"}}}}},
        }

        # Without servers and without override
        parser = OpenApiV3Parser(spec, "test_api")
        api_info = parser.parse()
        self.assertEqual(api_info.base_url, "")

        # With override when no servers
        parser_override = OpenApiV3Parser(spec, "test_api", base_url="https://api.example.com")
        api_info_override = parser_override.parse()
        self.assertEqual(api_info_override.base_url, "https://api.example.com")


if __name__ == "__main__":
    unittest.main()
