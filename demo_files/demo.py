"""Demo Python file for testing the typing app."""


def greet(name: str) -> str:
    """Return a greeting message."""
    return f"Hello, {name}!"


def calculate_sum(numbers: list) -> int:
    """Calculate the sum of a list of numbers."""
    total = 0
    for num in numbers:
        total += num
    return total


class Person:
    """A simple Person class."""
    
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age
    
    def introduce(self):
        """Introduce the person."""
        print(f"Hi, I'm {self.name} and I'm {self.age} years old.")


if __name__ == "__main__":
    # Test the functions
    print(greet("World"))
    print(calculate_sum([1, 2, 3, 4, 5]))
    
    # Test the class
    person = Person("Alice", 30)
    person.introduce()
