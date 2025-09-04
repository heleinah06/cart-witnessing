from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import calendar
from datetime import date, datetime

import random, string

import models
from database import get_db
from models import Booking, Name

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(
    SessionMiddleware,
    secret_key="supersecretkeyplus123",
    max_age=None  # Cookie expires when the browser closes
)

templates = Jinja2Templates(directory="templates")


# -------------------- TEST ROUTE --------------------
@app.get("/test-bookings")
def test_bookings(db: Session = Depends(get_db)):
    return db.query(Booking).all()


# -------------------- LOGIN --------------------
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(request: Request, congregation_number: str = Form(...)):
    if congregation_number == "152551":
        request.session.clear()
        request.session["logged_in"] = True
        return RedirectResponse(url="/locations", status_code=303)
    return templates.TemplateResponse(
        "login.html", {"request": request, "error": "Invalid congregation number"}
    )


# -------------------- LOCATIONS --------------------
@app.get("/locations", response_class=HTMLResponse)
async def locations(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("locations.html", {"request": request})


# -------------------- AUTH MIDDLEWARE --------------------
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Paths that don't require login
        public_paths = ["/", "/login", "/static", "/favicon.ico"]

        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)

        if not request.session.get("logged_in"):
            return RedirectResponse(url="/", status_code=303)

        return await call_next(request)


app.add_middleware(AuthMiddleware)


# -------------------- CALENDAR VIEW --------------------
@app.get("/calendar/{cart_id}", response_class=HTMLResponse)
async def show_calendar(
    request: Request, cart_id: int, month: int = None, year: int = None
):
    if not request.session.get("logged_in"):
        return RedirectResponse(url="/", status_code=303)

    today = date.today()
    if month is None:
        month = today.month
    if year is None:
        year = today.year

    cal = calendar.Calendar(firstweekday=6)
    start_weekday, days_in_month = calendar.monthrange(year, month)

    # Temporary example bookings
    bookings = {3: 0, 4: 1, 10: 2, 17: 0, 18: 1, 24: 2}

    return templates.TemplateResponse(
        "calendar.html",
        {
            "request": request,
            "cart_id": cart_id,
            "month": month,
            "year": year,
            "month_name": calendar.month_name[month],
            "prev_month": month - 1 if month > 1 else 12,
            "next_month": month + 1 if month < 12 else 1,
            "start_blank": start_weekday,
            "days": list(range(1, days_in_month + 1)),
            "bookings": bookings,
        },
    )


# -------------------- HOURLY VIEW --------------------
@app.get("/hours/{cart_id}/{year}/{month}/{day}", response_class=HTMLResponse)
async def show_hours(
    request: Request,
    cart_id: int,
    year: int,
    month: int,
    day: int,
    db: Session = Depends(get_db),
):
    if not request.session.get("logged_in"):
        return RedirectResponse(url="/", status_code=303)

    selected_date = date(year, month, day)

    # Fetch existing bookings from DB
    bookings = (
        db.query(Booking)
        .filter(Booking.cart_id == cart_id, Booking.booking_date == selected_date)
        .all()
    )

    # Define fixed time slots
    time_slots = [
        "4:00 PM - 5:00 PM",
        "5:00 PM - 6:00 PM",
        "6:00 PM - 7:00 PM",
        "7:00 PM - 8:00 PM",
        "8:00 PM - 9:00 PM",
    ]

    # Count bookings per slot
    slot_status = {slot: 0 for slot in time_slots}
    for booking in bookings:
        slot_status[booking.time_slot] += 1

    # Fetch allowed names (for dropdown)
    names = db.query(Name).all()

    return templates.TemplateResponse(
        "hours.html",
        {
            "request": request,
            "cart_id": cart_id,
            "date": selected_date,
            "time_slots": time_slots,
            "slot_status": slot_status,
            "names": names,
        },
    )


# -------------------- BOOKING --------------------
@app.post("/book")
async def book(
    request: Request,
    cart_id: int = Form(...),
    date_str: str = Form(...),
    time_slot: str = Form(...),
    name_id: int = Form(...),
    db: Session = Depends(get_db),
):
    # Generate cancellation code
    cancellation_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))

    # Store booking in DB (SQLAlchemy instead of raw psycopg2)
    new_booking = Booking(
        cart_id=cart_id,
        booking_date=datetime.strptime(date_str, "%Y-%m-%d").date(),
        time_slot=time_slot,
        name_id=name_id,
        cancellation_code=cancellation_code,
    )
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)

    # Return JSON for HTMX popup
    return JSONResponse({"cancellation_code": cancellation_code})





