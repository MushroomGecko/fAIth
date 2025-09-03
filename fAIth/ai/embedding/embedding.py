from fAIth.ai.models.embedding import EmbeddingModel

class Embedding:
    def __init__():
        pass

    def get_runner(self):
        model = EmbeddingModel.get_latest_active()
        if model.runner == "hf_sentence_transformers":
            from fAIth.ai.embedding.runners.hf_sentence_transformers import EmbeddingRunner as Runner
            return Runner(model.model_id)
        elif model.runner == "llama_cpp_python":
            from fAIth.ai.embedding.runners.llama_cpp_python import EmbeddingRunner as Runner
            return Runner(model.model_id)
        elif model.runner == "ollama":
            from fAIth.ai.embedding.runners.ollama import EmbeddingRunner as Runner
            return Runner(model.model_id)
        elif model.runner == "docker_model_runner":
            from fAIth.ai.embedding.runners.docker_model_runner import EmbeddingRunner as Runner
            return Runner(model.model_id)

    def embed(self, batch: list[str], prompt_type: str = "query"):
        runner = self.get_runner()
        return runner.embed(batch, prompt_type)