import time
import logging
import statistics
from typing import List, Dict, Any

# Standard SRE logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - NexusEval - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NexusOpsEvaluator:
    """
    Automated evaluation harness for SRE Agent performance.
    Tracks retrieval precision, routing fidelity, and P95 latency distributions.
    """
    def __init__(self):
        self.metrics = {
            "retrieval": [],
            "reasoning": [],
            "e2e": []
        }

    def evaluate_retrieval_hit(self, ground_truth_id: str, results: List[Dict]) -> bool:
        """
        Validates Top-K retrieval. Returns True if the correct playbook 
        was surfaced in the context window.
        """
        hit_ids = {doc.get("id") for doc in results}
        return ground_truth_id in hit_ids

    def calculate_routing_fidelity(self, expected: List[str], actual: List[str]) -> float:
        """
        Measures tool-use accuracy. Uses set intersection to account for 
        parallel tool calls while penalizing missing or extraneous actions.
        """
        if not expected and not actual:
            return 1.0
        
        expected_set = set(expected)
        actual_set = set(actual)
        
        intersection = expected_set.intersection(actual_set)
        # Jaccard-like similarity to capture precision and recall of tool selection
        union = expected_set.union(actual_set)
        
        return len(intersection) / len(union) if union else 0.0

    def log_latency(self, component: str, duration: float):
        """Captures execution time for performance benchmarking."""
        if component in self.metrics:
            self.metrics[component].append(duration)
        else:
            logger.warning(f"Attempted to log unknown metric type: {component}")

    def _get_p95(self, data: List[float]) -> float:
        """Calculates 95th percentile to identify tail-end performance issues."""
        if len(data) < 2:
            return data[0] if data else 0.0
        return sorted(data)[int(0.95 * len(data))]

    def run_benchmark_report(self, test_suite: List[Dict[str, Any]]):
        """
        Executes test cases and generates a professional SRE performance report.
        """
        if not test_suite:
            logger.error("Evaluation failed: No test cases found.")
            return

        hit_count = 0
        total_routing_score = 0.0

        print("\n" + "═"*60)
        print("  NEXUSOPS SRE PERFORMANCE BENCHMARK  ")
        print("═"*60)

        for idx, case in enumerate(test_suite):
            has_hit = self.evaluate_retrieval_hit(case["expected_doc_id"], case["retrieved_docs"])
            routing_score = self.calculate_routing_fidelity(case["expected_tools"], case["executed_tools"])
            
            hit_count += 1 if has_hit else 0
            total_routing_score += routing_score

            status = "✅ PASS" if has_hit and routing_score > 0.8 else "❌ FAIL"
            print(f"[{idx+1:02}] {case['name']:<30} | {status} | Routing: {routing_score*100:>3.0f}%")

        print("─" * 60)
        print(f"FINAL ACCURACY | Top-K Hit Rate: {hit_count/len(test_suite)*100:.1f}%")
        print(f"FINAL ACCURACY | Routing Fidelity: {total_routing_score/len(test_suite)*100:.1f}%")

    def display_latency_profile(self):
        """Summarizes system speed for architectural review."""
        print("\n" + "═"*60)
        print("  SYSTEM LATENCY PROFILE (S)  ")
        print("═"*60)
        print(f"{'Component':<15} | {'Average':<10} | {'P95 (Tail)':<10}")
        print("─" * 60)

        for comp, vals in self.metrics.items():
            if not vals:
                continue
            avg = sum(vals) / len(vals)
            p95 = self._get_p95(vals)
            print(f"{comp.capitalize():<15} | {avg:<10.3f} | {p95:<10.3f}")
        print("═"*60)

# --- Runtime Simulator ---
if __name__ == "__main__":
    suite = NexusOpsEvaluator()
    
    # Mock latency data reflecting the 20x improvement
    suite.log_latency("retrieval", 0.012) # 12ms target
    suite.log_latency("retrieval", 0.015)
    suite.log_latency("reasoning", 1.20)
    suite.log_latency("e2e", 1.215)

    cases = [
        {
            "name": "OOMKill Diagnostics",
            "expected_doc_id": "kb-001",
            "retrieved_docs": [{"id": "kb-001"}],
            "expected_tools": ["get_logs", "search_kb", "submit_pr"],
            "executed_tools": ["get_logs", "search_kb", "submit_pr"]
        },
        {
            "name": "Network Timeout",
            "expected_doc_id": "kb-099",
            "retrieved_docs": [{"id": "kb-100"}], # Simulated miss
            "expected_tools": ["get_logs", "search_kb"],
            "executed_tools": ["search_kb"] # Missing a tool
        }
    ]

    suite.run_benchmark_report(cases)
    suite.display_latency_profile()
