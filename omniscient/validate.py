import json
import sys
from typing import Optional

from jsonschema import validate
from jsonschema.exceptions import SchemaError, ValidationError


def config_validate(
    config: Optional[str] = "config.json", schema: Optional[str] = "config-schema.json"
) -> list:

    errors = []

    # Open the config file and the schema file
    try:
        with open(config, "r") as file:
            config = json.load(file)
        with open("config-schema.json", "r") as file:
            schema = json.load(file)
    except FileNotFoundError:
        errors.append(f"File {config} not found")
    except json.JSONDecodeError as e:
        errors.append(f"File {config} is not a valid JSON file: {e}")
    except Exception as e:
        errors.append(f"An error occurred: {e}")

    # Validate the config file against the schema
    try:
        validate(config, schema)
    except ValidationError as e:
        errors.append(f"Validation error: {e.message}")
    except SchemaError as e:
        errors.append(f"Schema error: {e}")
    except Exception as e:
        errors.append(f"An error schema validation error occurred: {e}")

    if errors:
        for num, error in enumerate(errors):
            print(f"{num}: {error}")
            sys.exit(1)


if __name__ == "__main__":
    errors = config_validate("config.json")
