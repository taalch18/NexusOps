import os
from typing import List, Dict
try:
    from ragas import evaluate
    from ragas.metrics import faithfulness, answer_relevancy, context_precision
    from datasets import Dataset
    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False

class Evaluator:
    def __init__(self):
        self.metrics = [faithfulness, answer_relevancy, context_precision] if RAGAS_AVAILABLE else []

    def evaluate_run(self, query: str, context: List[str], response: str, ground_truth: str = None) -> Dict[str, float]:
        """
        Evaluates a single RAG run.
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not RAGAS_AVAILABLE or not api_key or "YOUR_API_KEY" in api_key:
            # Mock Evaluation for prototype/demo without burning tokens
            return {
                "faithfulness": 0.95,
                "answer_relevancy": 0.92,
                "context_precision": 0.88,
                "mock": True
            }

        # RAGAS specific data format
        data_samples = {
            'question': [query],
            'answer': [response],
            'contexts': [context],
        }
        if ground_truth:
            data_samples['ground_truth'] = [ground_truth]
            # Newer RAGAS versions might interpret 'reference' equivalent to ground_truth
            data_samples['reference'] = [ground_truth]
        else:
             # Some metrics require ground truth, avoid them if not provided
             # For this demo, let's provide a dummy ground truth if missing to avoid schema error
             data_samples['ground_truth'] = ["Fix OOM by increasing memory limits."]
             data_samples['reference'] = ["Fix OOM by increasing memory limits."]

        dataset = Dataset.from_dict(data_samples)
        
        try:
            results = evaluate(dataset, metrics=self.metrics)
            return results
        except Exception as e:
            print(f"RAGAS Evaluation failed: {e}")
            return {"error": 0.0}

evaluator = Evaluator()
