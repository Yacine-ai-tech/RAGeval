from rageval.evaluator import RAGEvaluator
ev = RAGEvaluator()
print(ev.score_retrieval_relevance("What is the capital?", ["The capital is Paris."]))
print(ev.score_faithfulness("The capital is Paris.", ["The capital is Paris."]))
