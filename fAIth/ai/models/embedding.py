from django.db import models
from django.utils.text import slugify
from ai import globals
import logging
import torch
import gc

logger = logging.getLogger(__name__)

class EmbeddingModelManager(models.Manager):
    def get_latest_active(self):
        """Return the most recently updated active embedding model, or None."""
        latest_active = self.filter(is_active=True).order_by("-updated_at", "-created_at").first()
        if latest_active is None:
            return self.order_by("-updated_at", "-created_at").first()
        return latest_active
    
    def list_active(self):
        """Return a list of all active embedding models."""
        return self.filter(is_active=True)

class EmbeddingModel(models.Model):
    """Stores metadata about available embedding models used for vectorization."""

    CHOICES = [
        ("hf_sentence_transformers", "Hugging Face Sentence Transformers"),
        ("llama_cpp_python", "Llama CPP Python"),
        ("ollama", "Ollama"),
        ("docker_model_runner", "Docker Model Runner"),
    ]
    
    name = models.CharField(
        max_length=255,
        blank=False,
        null=False,
        help_text="Required. Human‑readable name of the embedding model.",
    )
    slug = models.SlugField(
        unique=True,
        blank=True,
        help_text="Auto-generated from name if left blank. Must be unique.",
    )
    description = models.TextField(
        blank=True,
        null=False,
        help_text="Optional. Long-form description of the embedding model (capabilities, size, provider).",
    )
    runner = models.CharField(
        max_length=255,
        choices=CHOICES,
        help_text="The runner used to run the embedding model.",
        blank=False,
        null=False,
    )
    model_id = models.CharField(
        max_length=255,
        help_text="The ID of the embedding model. This is used to identify the embedding model in the runner.",
        blank=False,
        null=False,
    )
    model_repo = models.CharField(
        max_length=255,
        help_text="The repository of the embedding model. This is used to identify the embedding model in the runner. (Mainly used for the Llama CPP Python runner)",
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(
        default=False,
        help_text="Whether the embedding model is active.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        editable=False,
        help_text="Timestamp when the embedding model was created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        editable=False,
        help_text="Timestamp when the embedding model was last updated.",
    )

    class Meta:
        verbose_name = "Embedding Model"
        verbose_name_plural = "Embedding Models"
        ordering = ["name", "runner"]
        unique_together = ["name", "runner"]

    objects = EmbeddingModelManager()

    def __str__(self):
        return f"{self.name} ({self.get_runner_display()})"

    def save(self, *args, **kwargs):
        previous_active = self.get_latest_active()
        if not self.slug:
            self.slug = slugify(f"{self.name}-{self.runner}")
        super().save(*args, **kwargs)
        current_active = self.get_latest_active()

        # If the embedding engine is not initialized, initialize it
        if not globals.EMBEDDING_ENGINE:
            globals.EMBEDDING_ENGINE = globals.get_embedding_engine()
            print(f"Embedding engine was not initialized, initializing with {self.slug}")

        # If the embedding engine is not the same as the current active embedding model, change it
        elif previous_active.slug != current_active.slug:
            # Very aggressive closing of the embedding engine to ensure that memory is freed
            # (This is mainly for the HF Sentence Transformers runner as it is a nuisance to unload it properly)
            globals.EMBEDDING_ENGINE.kill()
            del globals.EMBEDDING_ENGINE
            torch.cuda.empty_cache()
            gc.collect()

            # Re-initialize the embedding engine
            globals.EMBEDDING_ENGINE = globals.get_embedding_engine()
            print(f"Embedding engine was changed, changing embedding engine to {current_active.slug}")

        # Print the slugs for debugging
        print(f"This slug: {self.slug}")
        print(f"Previous active slug: {previous_active.slug}")
        print(f"Current active slug: {current_active.slug}")

    @classmethod
    def get_latest_active(cls):
        """Return the most recently updated active embedding model, or None."""
        return cls.objects.get_latest_active()
