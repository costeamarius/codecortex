import unittest

from codecortex.execution.validators import (
    get_validator_for_path,
    validate_content,
    validate_json,
    validate_python,
)


class ExecutionValidatorsTests(unittest.TestCase):
    def test_validate_json_success(self):
        result = validate_json("config.json", '{"timeout": 30}')
        self.assertTrue(result.passed)
        self.assertEqual(result.validator, "json")

    def test_validate_json_failure(self):
        result = validate_json("config.json", '{"timeout": }')
        self.assertFalse(result.passed)
        self.assertEqual(result.validator, "json")
        self.assertTrue(result.errors)

    def test_validate_python_success(self):
        result = validate_python("main.py", "x = 1\n")
        self.assertTrue(result.passed)
        self.assertEqual(result.validator, "python_compile")

    def test_validate_python_failure(self):
        result = validate_python("main.py", "def broken(:\n")
        self.assertFalse(result.passed)
        self.assertEqual(result.validator, "python_compile")
        self.assertTrue(result.errors)

    def test_get_validator_for_path(self):
        self.assertIsNotNone(get_validator_for_path("config.json"))
        self.assertIsNotNone(get_validator_for_path("main.py"))
        self.assertIsNone(get_validator_for_path("README.md"))

    def test_validate_content_without_validator_passes(self):
        result = validate_content("README.md", "# hello\n")
        self.assertTrue(result.passed)
        self.assertIsNone(result.validator)
        self.assertEqual(result.errors, [])


if __name__ == "__main__":
    unittest.main()
