"""Populate the database with demo data for the EatEarn campus app.

Run with:  python manage.py seed_demo

Idempotent: it removes previously-seeded demo content (vendors, menu, orders,
notifications, approvals and the four demo accounts) and recreates it. Any
extra users / superusers you created are left untouched.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from approvals.models import ApprovalRequest
from catalog.models import MenuItem, Vendor
from notifications.models import Notification
from orders.models import Order, OrderItem

# University of Dodoma (UDOM) campus area, Tanzania.
CAMPUS_CENTER = (-6.2647, 35.9540)

VENDORS = [
    {
        "key": "bp",
        "name": "BP Humanity",
        "cuisine": "Rice, Stew & Local Meals",
        "location": "Humanity Block",
        "eta_minutes": 18,
        "rating": 4.6,
        "is_open": True,
        "latitude": -6.2660,
        "longitude": 35.9525,
        "image_url": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=900&q=80",
    },
    {
        "key": "alpha",
        "name": "Alpha COED",
        "cuisine": "Fast Food & Breakfast",
        "location": "COED Area",
        "eta_minutes": 14,
        "rating": 4.4,
        "is_open": True,
        "latitude": -6.2632,
        "longitude": 35.9558,
        "image_url": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=900&q=80",
    },
    {
        "key": "blessed",
        "name": "Blessed HO",
        "cuisine": "Snacks & Beverages",
        "location": "Hostel Zone HO",
        "eta_minutes": 10,
        "rating": 4.2,
        "is_open": True,
        "latitude": -6.2618,
        "longitude": 35.9501,
        "image_url": "https://images.unsplash.com/photo-1470337458703-46ad1756a187?auto=format&fit=crop&w=900&q=80",
    },
    {
        "key": "cive",
        "name": "CIVE Plaza",
        "cuisine": "Grill & Dinner",
        "location": "CIVE Main Plaza",
        "eta_minutes": 22,
        "rating": 4.7,
        "is_open": False,
        "latitude": -6.2689,
        "longitude": 35.9572,
        "image_url": "https://images.unsplash.com/photo-1466978913421-dad2ebd01d17?auto=format&fit=crop&w=900&q=80",
    },
]

MENU = [
    ("bp", "Rice and Coconut Beans", "Steamed rice with coconut beans.", "Lunch", 2500, True,
     "https://images.unsplash.com/photo-1512058564366-18510be2db19?auto=format&fit=crop&w=900&q=80"),
    ("bp", "Ugali with Fried Fish", "Whole-grain ugali served with fried fish.", "Lunch", 4500, True,
     "https://images.unsplash.com/photo-1562967916-eb82221dfb92?auto=format&fit=crop&w=900&q=80"),
    ("bp", "Chicken and Fries", "Crispy fries with quarter chicken.", "Dinner", 7000, True,
     "https://images.unsplash.com/photo-1513639776629-7b61b0ac49cb?auto=format&fit=crop&w=900&q=80"),
    ("bp", "Plantain with Beef Stew", "Cooked plantain served with beef stew.", "Lunch", 5000, True,
     "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?auto=format&fit=crop&w=900&q=80"),
    ("alpha", "Beef Burger", "Burger with cheese and fresh lettuce.", "Fast Food", 6000, True,
     "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=900&q=80"),
    ("alpha", "Chicken Wrap", "Spicy chicken wrap with crisp vegetables.", "Fast Food", 5500, True,
     "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?auto=format&fit=crop&w=900&q=80"),
    ("alpha", "Pilau Box", "Spiced rice with beef and fresh salad.", "Lunch", 5000, True,
     "https://images.unsplash.com/photo-1539136788836-5699e78bfc75?auto=format&fit=crop&w=900&q=80"),
    ("alpha", "French Fries", "Plain fries for a side order.", "Snacks", 3000, True,
     "https://images.unsplash.com/photo-1576107232684-1279f390859f?auto=format&fit=crop&w=900&q=80"),
    ("blessed", "Passion Fruit Juice", "Fresh passion fruit juice.", "Drinks", 2000, True,
     "https://images.unsplash.com/photo-1622597467836-f3285f2131b8?auto=format&fit=crop&w=900&q=80"),
    ("blessed", "Milk Tea", "Hot milk tea.", "Drinks", 1000, True,
     "https://images.unsplash.com/photo-1576092768241-dec231879fc3?auto=format&fit=crop&w=900&q=80"),
    ("blessed", "Beef Samosa Pair", "Two beef samosas.", "Snacks", 1500, True,
     "https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=900&q=80"),
    ("blessed", "Coffee", "Black coffee or milk blend.", "Drinks", 2500, True,
     "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?auto=format&fit=crop&w=900&q=80"),
    ("cive", "Grilled Chicken Plate", "Grilled chicken served with salad.", "Dinner", 8500, False,
     "https://images.unsplash.com/photo-1600891964599-f61ba0e24092?auto=format&fit=crop&w=900&q=80"),
    ("cive", "Rice Beef Stew", "Rice with tender beef stew.", "Lunch", 6000, False,
     "https://images.unsplash.com/photo-1603133872878-684f208fb84b?auto=format&fit=crop&w=900&q=80"),
    ("cive", "Mango Smoothie", "Mango smoothie with milk.", "Drinks", 3500, False,
     "https://images.unsplash.com/photo-1623065422902-30a2d299bbe4?auto=format&fit=crop&w=900&q=80"),
    ("cive", "Chapati Beans", "Two chapatis served with beans.", "Breakfast", 3000, False,
     "https://images.unsplash.com/photo-1532634896-26909d0d4b6d?auto=format&fit=crop&w=900&q=80"),
]

DEMO_PASSWORD = "123456"


class Command(BaseCommand):
    help = "Seed the database with demo vendors, menu, users, orders and notifications."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Clearing previous demo data...")
        OrderItem.objects.all().delete()
        Order.objects.all().delete()
        Notification.objects.all().delete()
        ApprovalRequest.objects.all().delete()
        MenuItem.objects.all().delete()
        Vendor.objects.all().delete()
        User.objects.filter(
            email__in=[
                "student@eatearn.app",
                "vendor@eatearn.app",
                "delivery@eatearn.app",
                "admin@eatearn.app",
            ]
        ).delete()

        # ---- Vendors + menu ----
        vendor_by_key = {}
        for v in VENDORS:
            fields = {k: val for k, val in v.items() if k != "key"}
            vendor_by_key[v["key"]] = Vendor.objects.create(**fields)

        menu_by_name = {}
        for key, name, desc, category, price, available, image in MENU:
            item = MenuItem.objects.create(
                vendor=vendor_by_key[key],
                name=name,
                description=desc,
                category=category,
                price=price,
                is_available=available,
                image_url=image,
            )
            menu_by_name[name] = item

        # ---- Demo users ----
        student = User.objects.create_user(
            email="student@eatearn.app", password=DEMO_PASSWORD, full_name="Amina Mtei",
            phone="+255710100100", role=User.Role.STUDENT, student_id="2023-04-12345",
            department="Computer Science", hostel_block="Block H, Room 14",
            latitude=-6.2641, longitude=35.9533, is_verified=True,
        )
        User.objects.create_user(
            email="vendor@eatearn.app", password=DEMO_PASSWORD, full_name="BP Humanity Manager",
            phone="+255710200200", role=User.Role.VENDOR, vendor=vendor_by_key["bp"],
            cafeteria_name="BP Humanity", business_tag="UDOM-Food-23", is_verified=True,
        )
        User.objects.create_user(
            email="delivery@eatearn.app", password=DEMO_PASSWORD, full_name="John Mwambe",
            phone="+255710300300", role=User.Role.DELIVERY, delivery_mode="motorbike",
            pickup_zone="Near CIVE roundabout", latitude=-6.2655, longitude=35.9548,
            is_verified=True,
        )
        delivery = User.objects.get(email="delivery@eatearn.app")
        User.objects.create_superuser(
            email="admin@eatearn.app", password=DEMO_PASSWORD, full_name="Admin UDOM",
            phone="+255710400400",
        )

        # ---- Sample orders ----
        order1 = Order.objects.create(
            student=student, vendor=vendor_by_key["bp"], delivery_agent=delivery,
            delivery_type="delivery", delivery_fee=1000, status="OUT_FOR_DELIVERY",
            delivery_location="Hostel Block H, Room 14", latitude=-6.2641, longitude=35.9533,
        )
        for name, qty in [("Rice and Coconut Beans", 1), ("Passion Fruit Juice", 1)]:
            mi = menu_by_name[name]
            OrderItem.objects.create(order=order1, menu_item=mi, name=mi.name, unit_price=mi.price, quantity=qty)
        order1.recalculate_totals()
        order1.save()

        order2 = Order.objects.create(
            student=student, vendor=vendor_by_key["alpha"], delivery_type="pickup",
            delivery_fee=0, status="READY", delivery_location="Pickup at vendor counter",
        )
        mi = menu_by_name["Beef Burger"]
        OrderItem.objects.create(order=order2, menu_item=mi, name=mi.name, unit_price=mi.price, quantity=1)
        order2.recalculate_totals()
        order2.save()

        # ---- Notifications ----
        Notification.objects.create(
            user=student, user_role="student",
            title=f"Order #{order1.id} is on the way",
            body="The delivery agent has picked up your order. ETA is 7-10 minutes.",
        )
        Notification.objects.create(
            user_role="vendor", title="New order received",
            body="A customer placed Chicken Wrap x2. Please confirm quickly.",
        )
        Notification.objects.create(
            user=delivery, user_role="delivery", title="Task assigned", is_read=True,
            body="Pick up order from BP Humanity cafeteria.",
        )
        Notification.objects.create(
            user_role="admin", title="New delivery application",
            body="Applicant: Baraka Lema is waiting for approval.",
        )

        # ---- Approval requests ----
        ApprovalRequest.objects.create(
            type="delivery", applicant_name="Baraka Lema",
            details="Year 2 BIT, owns a personal motorcycle.", status="pending",
        )
        ApprovalRequest.objects.create(
            type="vendor", applicant_name="Mama Rehema Kitchen",
            details="Wants to register a lunch and breakfast menu.", status="pending",
        )
        ApprovalRequest.objects.create(
            type="delivery", applicant_name="Sifa Bwire",
            details="Year 3 BIS, available 11am-3pm.", status="approved",
        )

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully."))
        self.stdout.write("Demo accounts (password: 123456):")
        for email in ["student@eatearn.app", "vendor@eatearn.app", "delivery@eatearn.app", "admin@eatearn.app"]:
            self.stdout.write(f"  - {email}")
