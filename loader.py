import json


def load_dataset(path="clean_data/dataset_structured.json"):

    with open(path, encoding="utf-8") as f:
        return json.load(f)