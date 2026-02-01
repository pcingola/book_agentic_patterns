"""Example demonstrating JSON connector operations."""

import json
import tempfile
from pathlib import Path

from agentic_patterns.core.connectors.json import JsonConnector


def main():
    """Demonstrate JSON connector operations."""
    connector = JsonConnector()

    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_root = Path(temp_dir) / "default_user" / "default_session"
        workspace_root.mkdir(parents=True)

        import agentic_patterns.core.workspace as workspace_module
        original_workspace_dir = workspace_module.WORKSPACE_DIR
        workspace_module.WORKSPACE_DIR = Path(temp_dir)

        try:
            config_file = workspace_root / "config.json"
            sample_data = {
                "app": {
                    "name": "MyApp",
                    "version": "1.0.0",
                    "features": {
                        "rollout": {"enabled": True, "percent": 50, "regions": ["us-east-1", "eu-west-1"]},
                        "darkMode": True,
                        "analytics": {"enabled": True, "provider": "mixpanel"},
                    },
                },
                "users": [{"id": "u-001", "name": "Alice", "role": "admin"}, {"id": "u-002", "name": "Bob", "role": "user"}],
            }
            with open(config_file, "w") as f:
                json.dump(sample_data, f, indent=2)

            print("JSON Connector Example")
            print("=" * 60)

            print("\n1. Head of root (first 5 keys):")
            print(connector.head("/workspace/config.json", "$", n=5))

            print("\n2. Tail of users array:")
            print(connector.tail("/workspace/config.json", "$.users", n=1))

            print("\n3. Validate JSON:")
            print(connector.validate("/workspace/config.json"))

            print("\n4. List keys at root:")
            print(connector.keys("/workspace/config.json", "$"))

            print("\n5. List keys in app.features:")
            print(connector.keys("/workspace/config.json", "$.app.features"))

            print("\n6. Get rollout percent:")
            print(connector.get("/workspace/config.json", "$.app.features.rollout.percent"))

            print("\n7. Get rollout config:")
            print(connector.get("/workspace/config.json", "$.app.features.rollout"))

            print("\n8. Get first user:")
            print(connector.get("/workspace/config.json", "$.users[0]"))

            print("\n9. Update rollout percent to 75:")
            print(connector.set("/workspace/config.json", "$.app.features.rollout.percent", "75"))

            print("\n10. Add new feature 'beta':")
            print(connector.set("/workspace/config.json", "$.app.features.beta", '{"enabled": true, "users": []}'))

            print("\n11. Merge updates into rollout config:")
            print(connector.merge("/workspace/config.json", "$.app.features.rollout", '{"percent": 100, "complete": true}'))

            print("\n12. Add new user:")
            print(connector.append("/workspace/config.json", "$.users", '{"id": "u-003", "name": "Charlie", "role": "user"}'))

            print("\n13. Delete darkMode feature:")
            print(connector.delete_key("/workspace/config.json", "$.app.features.darkMode"))

            print("\n14. Head of final state:")
            print(connector.head("/workspace/config.json", "$", n=10))

        finally:
            workspace_module.WORKSPACE_DIR = original_workspace_dir


if __name__ == "__main__":
    main()
