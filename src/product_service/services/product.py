from typing import List, Optional
from uuid import UUID
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .database import Product, Category, Tag, db

app = FastAPI()

class ProductModel(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    category_id: UUID
    tag_ids: List[UUID]

@app.get("/products/", response_model=List[Product])
async def get_products():
    products = db.query(Product).all()
    return products

@app.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: UUID):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.post("/products/", response_model=Product)
async def create_product(product: ProductModel):
    new_product = Product(
        id=str(UUID.uuid4()),
        name=product.name,
        description=product.description,
        price=product.price,
        category_id=product.category_id,
        tag_ids=product.tag_ids
    )
    db.add(new_product)
    db.commit()
    return new_product

@app.put("/products/{product_id}", response_model=Product)
async def update_product(product_id: UUID, product: ProductModel):
    product_exists = db.query(Product).filter(Product.id == product_id).first()
    if product_exists is None:
        raise HTTPException(status_code=404, detail="Product not found")
    product.id = product_id
    db.query(Product).filter(Product.id == product_id).update(product)
    db.commit()
    return product_exists

@app.delete("/products/{product_id}", status_code=204)
async def delete_product(product_id: UUID):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    db.query(Product).filter(Product.id == product_id).delete()
    db.commit()