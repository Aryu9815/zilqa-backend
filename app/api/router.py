from fastapi import APIRouter

from app.api import (
    admin,
    addresses,
    analytics,
    auth,
    cart,
    categories,
    countries,
    offers,
    orders,
    products,
    reviews,
    users,
    wishlist,
)

api_router = APIRouter()

# Admin
api_router.include_router(admin.router)

# Authentication
api_router.include_router(auth.router)

# User Profile & Addresses
api_router.include_router(users.router)
api_router.include_router(addresses.router)

# Countries (Public & Admin)
api_router.include_router(countries.public_router)
api_router.include_router(countries.admin_router)

# Categories (Public & Admin)
api_router.include_router(categories.public_router)
api_router.include_router(categories.admin_router)

# Products (Public & Admin)
api_router.include_router(products.public_router)
api_router.include_router(products.admin_router)

# Offers & Discounts (Public & Admin)
api_router.include_router(offers.public_router)
api_router.include_router(offers.admin_router)

# Reviews (Public, Customer & Admin)
api_router.include_router(reviews.public_router)
api_router.include_router(reviews.user_router)
api_router.include_router(reviews.admin_router)

# Cart & Wishlist
api_router.include_router(cart.router)
api_router.include_router(wishlist.router)

# Orders (Customer & Admin)
api_router.include_router(orders.user_router)
api_router.include_router(orders.admin_router)

# Admin Dashboard Analytics
api_router.include_router(analytics.router)

