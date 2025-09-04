from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

# Pre-approved congregation names
class Name(Base):
    __tablename__ = "names"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, unique=True, nullable=False)

    bookings = relationship("Booking", back_populates="name")


# Bookings
class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, nullable=False)
    booking_date = Column(Date, nullable=False)
    time_slot = Column(String, nullable=False)  # Store as string like "16:00-17:00"
    cancellation_code = Column(String, nullable=False, unique=True)

    # Link to pre-approved Name
    name_id = Column(Integer, ForeignKey("names.id"), nullable=False)
    name = relationship("Name", back_populates="bookings")

