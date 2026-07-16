import pytest

@pytest.mark.unit
def test_dspy_module_compile():
    try:
        import dspy
        class RAG(dspy.Module):
            def __init__(self):
                super().__init__()
                self.generate_answer = dspy.ChainOfThought("context, question -> answer")
            
            def forward(self, question, context):
                return self.generate_answer(context=context, question=question)
                
        # Just ensure the class compiles
        rag = RAG()
        assert rag is not None
    except ImportError:
        pytest.skip("DSPy not installed")
    except Exception as e:
        pytest.fail(f"DSPy integration failed: {e}")
