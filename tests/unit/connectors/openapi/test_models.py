"""Unit tests for OpenAPI data models."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agentic_patterns.core.connectors.openapi.models import (
    ApiInfo,
    EndpointInfo,
    ParameterInfo,
)


class TestParameterInfo(unittest.TestCase):
    def test_to_dict_from_dict(self):
        param = ParameterInfo(
            name="user_id",
            location="path",
            required=True,
            schema_type="string",
            description="User ID",
            example="123",
        )
        data = param.to_dict()
        param2 = ParameterInfo.from_dict(data)
        self.assertEqual(param.name, param2.name)
        self.assertEqual(param.location, param2.location)
        self.assertEqual(param.required, param2.required)
        self.assertEqual(param.schema_type, param2.schema_type)


class TestEndpointInfo(unittest.TestCase):
    def test_to_dict_from_dict(self):
        endpoint = EndpointInfo(
            path="/users/{user_id}",
            method="GET",
            operation_id="getUser",
            summary="Get user by ID",
            parameters=[
                ParameterInfo(
                    name="user_id",
                    location="path",
                    required=True,
                    schema_type="string",
                )
            ],
        )
        data = endpoint.to_dict()
        endpoint2 = EndpointInfo.from_dict(data)
        self.assertEqual(endpoint.path, endpoint2.path)
        self.assertEqual(endpoint.method, endpoint2.method)
        self.assertEqual(len(endpoint.parameters), len(endpoint2.parameters))


class TestApiInfo(unittest.TestCase):
    def test_to_dict_from_dict(self):
        api_info = ApiInfo(
            api_id="test_api",
            title="Test API",
            version="1.0.0",
            description="A test API",
            base_url="https://api.example.com",
        )
        api_info.add_endpoint(
            EndpointInfo(
                path="/test",
                method="GET",
                operation_id="test",
                summary="Test endpoint",
            )
        )

        data = api_info.to_dict()
        api_info2 = ApiInfo.from_dict(data)

        self.assertEqual(api_info.api_id, api_info2.api_id)
        self.assertEqual(api_info.title, api_info2.title)
        self.assertEqual(len(api_info.endpoints), len(api_info2.endpoints))

    def test_save_load(self):
        with TemporaryDirectory() as tmpdir:
            api_info = ApiInfo(
                api_id="test_api",
                title="Test API",
                version="1.0.0",
                base_url="https://api.example.com",
            )
            api_info.add_endpoint(
                EndpointInfo(
                    path="/test",
                    method="GET",
                    operation_id="test",
                )
            )

            # Save
            output_path = Path(tmpdir) / "test_api.api_info.json"
            api_info.save(output_path)
            self.assertTrue(output_path.exists())

            # Load
            loaded = ApiInfo.load(input_path=output_path)
            self.assertEqual(api_info.api_id, loaded.api_id)
            self.assertEqual(len(api_info.endpoints), len(loaded.endpoints))

    def test_get_endpoint(self):
        api_info = ApiInfo(
            api_id="test_api",
            title="Test API",
            version="1.0.0",
        )
        api_info.add_endpoint(
            EndpointInfo(
                path="/users",
                method="GET",
                operation_id="listUsers",
            )
        )

        endpoint = api_info.get_endpoint("GET", "/users")
        self.assertIsNotNone(endpoint)
        self.assertEqual(endpoint.operation_id, "listUsers")

        # Case insensitive method
        endpoint = api_info.get_endpoint("get", "/users")
        self.assertIsNotNone(endpoint)

        # Non-existent endpoint
        endpoint = api_info.get_endpoint("POST", "/users")
        self.assertIsNone(endpoint)


if __name__ == "__main__":
    unittest.main()
