# src/models/product.py
from datetime import datetime
from django.db import models
from django.urls import reverse

class Product(models.Model):
    vendor_id = models.IntegerField()
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    short_desc = models.CharField(max_length=255)
    category = models.CharField(max_length=255)
    tags = models.CharField(max_length=255, blank=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=datetime.utcnow)
    updated_at = models.DateTimeField(default=datetime.utcnow)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('product_detail', kwargs={'slug': self.slug})