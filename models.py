from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False)

class Customer(Base):
    __tablename__ = 'customers'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    phone = Column(String)
    email = Column(String)
    address = Column(String)
    note = Column(String)
    status = Column(String)
    assigned_agent_id = Column(Integer, ForeignKey('users.id'))
    assignments = relationship('LeadAssignment', back_populates='customer')

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    price = Column(Float)
    description = Column(String)
    quantity = Column(Integer, default=0)
    status = Column(String)

class LeadAssignment(Base):
    __tablename__ = 'lead_assignments'
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey('customers.id'))
    agent_id = Column(Integer, ForeignKey('users.id'))
    assigned_at = Column(DateTime, default=datetime.utcnow)
    customer = relationship('Customer', back_populates='assignments')
    agent = relationship('User')

class Sale(Base):
    __tablename__ = 'sales'
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey('customers.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    agent_id = Column(Integer, ForeignKey('users.id'))
    status = Column(String, default='Interested')
    note = Column(String)
    follow_up = Column(DateTime)
    closed_at = Column(DateTime)
    customer = relationship('Customer')
    product = relationship('Product')

class PackingRequest(Base):
    __tablename__ = 'packing_requests'
    id = Column(Integer, primary_key=True)
    sale_id = Column(Integer, ForeignKey('sales.id'))
    status = Column(String, default='Pending')
    shipping_info = Column(String)
    updated_at = Column(DateTime, default=datetime.utcnow)
    sale = relationship('Sale')
