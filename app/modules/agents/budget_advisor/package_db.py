from sqlalchemy import Column, Integer, String, Date, Boolean
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import Session
import random
from datetime import date, timedelta
from app.modules.destination_registry import all_destinations

Base = declarative_base()


class Package(Base):
    __tablename__ = "packages"

    PackageID = Column(Integer, primary_key=True)
    destination = Column(String)
    depart_date = Column(Date)
    nights = Column(Integer)
    flight_price = Column(Integer)
    hotel_name = Column(String)
    hotel_price = Column(Integer)
    total_price = Column(Integer)
    available = Column(Boolean)


engine = create_engine("sqlite:///data/packages.db")


def init_db():
    Base.metadata.create_all(engine)


def seed_packages():
    random.seed(42)
    with Session(engine) as session:
        session.query(Package).delete()  # clear old rows so re-running stays clean
        for dest in all_destinations():
            for _ in range(8):  # 8 packages per destination
                nights = random.choice([3, 5, 7])
                flight_price = random.randint(150, 700)
                hotel_price = random.randint(60, 250) * nights
                package = Package(
                    destination=dest.name,
                    depart_date=date(2026, 1, 1) + timedelta(days=random.randint(0, 729)),
                    nights=nights,
                    flight_price=flight_price,
                    hotel_name=f"{dest.name} Stay {random.randint(1, 5)}",
                    hotel_price=hotel_price,
                    total_price=flight_price + hotel_price,
                    available=random.random() < 0.85,
                )
                session.add(package)
        session.commit()


def get_packages(destination, max_budget=None, earliest_departure=None, n=3):
    """Return the n cheapest available packages to `destination`, as plain dicts.

    Both filters are optional: a price cap is applied only when `max_budget` is
    given, and the soft date anchor only when `earliest_departure` is given.
    Dicts (not ORM rows) so the data outlives the session.
    """
    with Session(engine) as session:
        query = session.query(Package).filter(
            Package.destination == destination,
            Package.available == True,  # noqa: E712 — SQLAlchemy filters need ==, not `is`
        )

        # Soft date anchor: never show trips before the requested departure.
        if earliest_departure is not None:
            query = query.filter(Package.depart_date >= earliest_departure)

        # No budget stated -> no price cap.
        if max_budget is not None:
            query = query.filter(Package.total_price <= max_budget)

        # Cheapest first, capped at n.
        rows = query.order_by(Package.total_price).limit(n).all()

        return [
            {
                "package_id": p.PackageID,
                "destination": p.destination,
                "depart_date": p.depart_date,
                "nights": p.nights,
                "flight_price": p.flight_price,
                "hotel_name": p.hotel_name,
                "hotel_price": p.hotel_price,
                "total_price": p.total_price,
            }
            for p in rows
        ]


if __name__ == "__main__":
    init_db()
    seed_packages()
    print("packages.db seeded")
