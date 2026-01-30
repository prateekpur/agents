"""
Sample Python code for testing the code analysis agent.
This code intentionally has some issues for the agent to detect.
"""

def calculate_tax(amount):
    """Calculate tax on an amount."""
    return amount * 0.18

def process_data(data):
    # Process some data
    result = []
    for i in data:
        if i > 0:
            result.append(i * 2)
    return result

class DataProcessor:
    def __init__(self):
        self.data = []
    
    def add(self, item):
        self.data.append(item)
    
    def process(self):
        processed = []
        for d in self.data:
            processed.append(d * 2)
        return processed
