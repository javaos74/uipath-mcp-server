#!/usr/bin/env python3
"""Test script for Arguments parsing logic."""

import json

def parse_input_arguments(arguments):
    """Test the Arguments parsing logic."""
    input_params = []
    
    if arguments:
        try:
            args = json.loads(arguments) if isinstance(arguments, str) else arguments
            
            if isinstance(args, dict):
                # Check for Input (JSON string format) or InputArguments (dict format)
                if "Input" in args:
                    # Input is a JSON string containing array of parameter definitions
                    input_str = args.get("Input")
                    if isinstance(input_str, str):
                        input_array = json.loads(input_str)
                        if isinstance(input_array, list):
                            for param_def in input_array:
                                if isinstance(param_def, dict):
                                    param_name = param_def.get("name", "")
                                    param_type_full = param_def.get("type", "")
                                    param_required = param_def.get("required", False)
                                    param_has_default = param_def.get("hasDefault", False)
                                    
                                    # Parse .NET type to simple type
                                    param_type = "string"  # default
                                    if "System.String" in param_type_full:
                                        param_type = "string"
                                    elif "System.Int" in param_type_full or "System.Double" in param_type_full or "System.Decimal" in param_type_full:
                                        param_type = "number"
                                    elif "System.Boolean" in param_type_full:
                                        param_type = "boolean"
                                    elif "[]" in param_type_full:
                                        param_type = "array"
                                    elif "System.Object" in param_type_full or "System.Collections" in param_type_full:
                                        param_type = "object"
                                    
                                    input_params.append({
                                        "name": param_name,
                                        "type": param_type,
                                        "description": f"Parameter {param_name}",
                                        "required": param_required and not param_has_default,
                                    })
                
                elif "InputArguments" in args:
                    # InputArguments is a dict with key-value pairs
                    args_dict = args.get("InputArguments")
                    if isinstance(args_dict, dict):
                        for key, value in args_dict.items():
                            param_type = "string"
                            if isinstance(value, bool):
                                param_type = "boolean"
                            elif isinstance(value, (int, float)):
                                param_type = "number"
                            elif isinstance(value, list):
                                param_type = "array"
                            elif isinstance(value, dict):
                                param_type = "object"

                            input_params.append({
                                "name": key,
                                "type": param_type,
                                "description": f"Parameter {key}",
                                "required": False,
                            })
        except Exception as e:
            print(f"Error parsing arguments: {str(e)}")
    
    return input_params


# Test Case 1: Input format (JSON string)
print("=" * 80)
print("Test Case 1: Input format (JSON string)")
print("=" * 80)

arguments_input = {
    "Input": '[\n  {\n    "name": "ApplicantId",\n    "type": "System.String, System.Private.CoreLib, Version=8.0.0.0, Culture=neutral, PublicKeyToken=7cec85d7bea7798e",\n    "required": false,\n    "hasDefault": true\n  }\n]',
    "Output": '[\n  {\n    "name": "Documents",\n    "type": "System.String[], System.Private.CoreLib, Version=8.0.0.0, Culture=neutral, PublicKeyToken=7cec85d7bea7798e"\n  }\n]'
}

result1 = parse_input_arguments(arguments_input)
print(json.dumps(result1, indent=2))

# Test Case 2: InputArguments format (dict)
print("\n" + "=" * 80)
print("Test Case 2: InputArguments format (dict)")
print("=" * 80)

arguments_input_args = {
    "InputArguments": {
        "username": "test_user",
        "age": 25,
        "is_active": True,
        "tags": ["tag1", "tag2"],
        "metadata": {"key": "value"}
    }
}

result2 = parse_input_arguments(arguments_input_args)
print(json.dumps(result2, indent=2))

# Test Case 3: Multiple parameters with different types
print("\n" + "=" * 80)
print("Test Case 3: Multiple parameters with different .NET types")
print("=" * 80)

arguments_multiple = {
    "Input": json.dumps([
        {
            "name": "StringParam",
            "type": "System.String, System.Private.CoreLib",
            "required": True,
            "hasDefault": False
        },
        {
            "name": "IntParam",
            "type": "System.Int32, System.Private.CoreLib",
            "required": False,
            "hasDefault": True
        },
        {
            "name": "BoolParam",
            "type": "System.Boolean, System.Private.CoreLib",
            "required": True,
            "hasDefault": False
        },
        {
            "name": "ArrayParam",
            "type": "System.String[], System.Private.CoreLib",
            "required": False,
            "hasDefault": True
        }
    ])
}

result3 = parse_input_arguments(arguments_multiple)
print(json.dumps(result3, indent=2))

print("\n" + "=" * 80)
print("All tests completed!")
print("=" * 80)
