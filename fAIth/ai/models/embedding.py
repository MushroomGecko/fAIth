from django.db import models
from django.utils.text import slugify

class EmbeddingModelManager(models.Manager):
    def get_latest_active(self):
        """Return the most recently updated active embedding model, or None."""
        return (
            self.filter(is_active=True)
            .order_by("-updated_at", "-created_at")
            .first()
        )

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
        unique=True,
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
    )
    model_repo = models.CharField(
        max_length=255,
        help_text="The repository of the embedding model. This is used to identify the embedding model in the runner.",
        blank=True,
        null=True,
    )
    model_id = models.CharField(
        max_length=255,
        help_text="The ID of the embedding model. This is used to identify the embedding model in the runner.",
        blank=False,
        null=False,
    )
    is_active = models.BooleanField(
        default=True,
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
        verbose_name = "Embedding model"
        verbose_name_plural = "Embedding models"
        ordering = ["name"]

    objects = EmbeddingModelManager()

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_latest_active(self):
        """Return the most recently updated active embedding model, or None."""
        return self.objects.get_latest_active()