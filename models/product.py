class Product:
    def __init__(self, id: int, name: str, price: float, description: str = ""):
        if not isinstance(id, int):
            raise TypeError(f"id must be an int, got {type(id).__name__}")
        if not isinstance(name, str):
            raise TypeError(f"name must be a str, got {type(name).__name__}")
        if not isinstance(price, (int, float)):
            raise TypeError(f"price must be a float, got {type(price).__name__}")
        if not isinstance(description, str):
            raise TypeError(f"description must be a str, got {type(description).__name__}")
        if id <= 0:
            raise ValueError("id must be a positive integer")
        if not name.strip():
            raise ValueError("name must not be empty")
        if price < 0:
            raise ValueError("price must be non-negative")

        self.id = id
        self.name = name
        self.price = float(price)
        self.description = description

    def __repr__(self) -> str:
        return (
            f"Product(id={self.id!r}, name={self.name!r}, "
            f"price={self.price!r}, description={self.description!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Product):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)