"""
A comprehensive calculator application with multiple features.
Supports basic arithmetic operations, history tracking, and error handling.
"""

import math


class Calculator:
    """A calculator class with various operations and features."""
    
    def __init__(self):
        self.history = []
        self.errors = []
    
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b
    
    def multiply(self, a, b):
        return a * b
    
    def divide(self, a, b):
        if b == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        return a / b
    
    def power(self, base, exponent):
        return base ** exponent
    
    def square(self, number):
        return number ** 2
    
    def cube(self, number):
        return number ** 3
    
    def factorial(self, number):
        if number < 0:
            raise ValueError("Factorial is not defined for negative numbers")
        result = 1
        for i in range(2, number + 1):
            result *= i
        return result
    
    def sqrt(self, number):
        if number < 0:
            raise ValueError("Cannot calculate square root of negative number")
        return math.sqrt(number)


def create_calculator():
    calculator = Calculator()
    return calculator


def main():
    print("=" * 50)
    print("Welcome to the Calculator!")
    print("=" * 50)
    
    calculator = create_calculator()
    
    # Test operations
    test_cases = [
        ("Addition", 10, 5),
        ("Subtraction", 20, 8),
        ("Multiplication", 7, 4),
        ("Division", 20, 4),
        ("Power", 2, 3),
        ("Square", 5),
        ("Cube", 3),
        ("Factorial", 5),
        ("Square Root", 16),
    ]
    
    print("\n--- Testing Calculator ---\n")
    
    for test_case in test_cases:
        name, a = test_case[:2]
        b = test_case[2] if len(test_case) == 3 else None
        if name == "Addition":
            result = calculator.add(a, b)
        elif name == "Subtraction":
            result = calculator.subtract(a, b)
        elif name == "Multiplication":
            result = calculator.multiply(a, b)
        elif name == "Division":
            result = calculator.divide(a, b)
        elif name == "Power":
            result = calculator.power(a, b)
        elif name == "Square":
            result = calculator.square(a)
        elif name == "Cube":
            result = calculator.cube(a)
        elif name == "Factorial":
            result = calculator.factorial(a)
        elif name == "Square Root":
            result = calculator.sqrt(a)
        else:
            print(f"Unknown operation: {name}")
            continue
        
        if result is not None:
            if b is None:
                print(f"{name}: {a} = {result}")
            else:
                print(f"{name}: {a}, {b} = {result}")
    
    # Test error handling
    print("\n--- Testing Error Handling ---\n")
    
    test_errors = [
        ("Division by zero", 10, 0),
        ("Invalid operation", 5, "invalid"),
    ]
    
    for name, a, b in test_errors:
        if name == "Division by zero":
            try:
                result = calculator.divide(a, b)
            except ZeroDivisionError as e:
                print(f"{name}: {e}")
        elif name == "Invalid operation":
            try:
                result = calculator.add(a, b)
            except TypeError as e:
                print(f"{name}: {e}")
    
    # Display history and errors
    print("\n--- History ---")
    for entry in calculator.history:
        print(entry)
    
    print("\n--- Errors ---")
    for error in calculator.errors:
        print(error)
    
    print("\n" + "=" * 50)
    print("Calculator demonstration complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
