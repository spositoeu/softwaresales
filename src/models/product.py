# src/models/product.py
from django.db import models
from django.urls import reverse

class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    vendor_id = models.UUIDField()
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    short_desc = models.CharField(max_length=255)
    category = models.CharField(max_length=255)
    tags = models.JSONField()
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=datetime.utcnow)
    updated_at = models.DateTimeField(default=datetime.utcnow)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('product_detail', kwargs={'slug': self.slug})