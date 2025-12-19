import random

def categorize_descriptions(descriptions):
    # Dummy categorizer
    categories = []
    for desc in descriptions:
        if "salary" in desc.lower():
            categories.append("Salary")
        elif "food" in desc.lower():
            categories.append("Food")
        elif "rent" in desc.lower():
            categories.append("Rent")
        else:
            categories.append("Other")
    return categories

def forecast(values, periods=4):
    # Dummy forecast: just repeat average
    avg = sum(values) / len(values) if values else 0
    return [round(avg + random.uniform(-0.1, 0.1) * avg, 2) for _ in range(periods)]

def detect_anomalies(values):
    # Dummy anomaly: flag values > 2x average
    avg = sum(values) / len(values) if values else 0
    return [i for i, v in enumerate(values) if abs(v) > 2 * avg]