from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session
from .database import SessionLocal, Base
from . import models, deps

app = FastAPI()

@app.get("/products", response_model=List[models.Product], dependencies=[deps.get_db])
async def read_products():
    """
    Retrieve all products.
    """
    products = models.Product.query.all()
    return products

@app.post("/products", response_model=models.Product, status_code=201, dependencies=[deps.get_db])
async def create_product(product: models.Product, db: Session = Depends(deps.get_db)):
    """
    Create a new product.
    """
    db.add(product)
    db.commit()
    return product

@app.get("/products/{product_id}", response_model=models.Product, dependencies=[deps.get_db])
async def read_product(product_id: int, db: Session = Depends(deps.get_db)):
    """
    Retrieve a specific product by ID.
    """
    product = models.Product.query.get(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.put("/products/{product_id}", response_model=models.Product, dependencies=[deps.get_db])
async def update_product(product_id: int, product: models.Product, db: Session = Depends(deps.get_db)):
    """
    Update a specific product by ID.
    """
    product.id = product_id
    db.query(models.Product).filter(models.Product.id == product_id).update(product)
    db.commit()
    return product

@app.delete("/products/{product_id}", dependencies=[deps.get_db])
async def delete_product(product_id: int, db: Session = Depends(deps.get_db)):
    """
    Delete a specific product by ID.
    """
    product = models.Product.query.get(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"message": "Product deleted successfully"}