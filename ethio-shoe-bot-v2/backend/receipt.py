# backend/receipt.py - Receipt generation
# Ethio Shoe Store Telegram Bot

import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import io

def generate_receipt_image(order):
    """Generate a receipt image for the order."""
    try:
        # Create a new image with white background
        width = 400
        height = 600
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)

        # Try to load a font, fall back to default if not available
        try:
            # Try common font locations
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "AbyssinicaSIL-Regular.ttf",  # For Amharic text
                None  # Will use default
            ]
            font = None
            font_bold = None
            for path in font_paths:
                if path and os.path.exists(path):
                    font = ImageFont.truetype(path, 16)
                    font_bold = ImageFont.truetype(path, 18)
                    break
            if not font:
                font = ImageFont.load_default()
                font_bold = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
            font_bold = ImageFont.load_default()

        y_position = 20

        # Header
        draw.text((width//2, y_position), "ETHIO SHOE STORE", font=font_bold, fill='black', anchor='mt')
        y_position += 30
        draw.text((width//2, y_position), "Receipt", font=font, fill='gray', anchor='mt')
        y_position += 40

        # Separator line
        draw.line([(20, y_position), (width-20, y_position)], fill='black', width=2)
        y_position += 20

        # Order details
        order_id = str(order.get('id', 'N/A'))[:8]
        draw.text((20, y_position), f"Order ID: #{order_id}", font=font, fill='black')
        y_position += 25

        # Date
        created_at = order.get('created_at', datetime.now().isoformat())
        if isinstance(created_at, str):
            date_str = created_at[:19]  # Remove timezone
        else:
            date_str = str(created_at)[:19]
        draw.text((20, y_position), f"Date: {date_str}", font=font, fill='black')
        y_position += 30

        # Separator line
        draw.line([(20, y_position), (width-20, y_position)], fill='gray', width=1)
        y_position += 20

        # Customer info
        user = order.get('users', {})
        customer_name = user.get('first_name', 'Customer') if user else 'Customer'
        draw.text((20, y_position), f"Customer: {customer_name}", font=font, fill='black')
        y_position += 25
        draw.text((20, y_position), f"Phone: {order.get('contact_phone', 'N/A')}", font=font, fill='black')
        y_position += 30

        # Separator line
        draw.line([(20, y_position), (width-20, y_position)], fill='gray', width=1)
        y_position += 20

        # Items
        draw.text((20, y_position), "Items:", font=font_bold, fill='black')
        y_position += 25

        items = order.get('order_items', [])
        if not items:
            items = [{'product_name': 'Product', 'quantity': 1, 'price_per_unit': order.get('total_amount', 0)}]

        subtotal = 0
        for item in items:
            product_name = item.get('product_name', 'Product')
            quantity = item.get('quantity', 1)
            price = item.get('price_per_unit', 0)
            item_total = price * quantity
            subtotal += item_total

            draw.text((40, y_position), f"{product_name}", font=font, fill='black')
            y_position += 20
            draw.text((40, y_position), f"  Qty: {quantity} x {price} ETB = {item_total} ETB", font=font, fill='gray')
            y_position += 25

        y_position += 10

        # Separator line
        draw.line([(20, y_position), (width-20, y_position)], fill='black', width=2)
        y_position += 20

        # Totals
        delivery_fee = order.get('delivery_fee', 50)
        total = order.get('total_amount', subtotal + delivery_fee)

        draw.text((20, y_position), f"Subtotal: {subtotal} ETB", font=font, fill='black')
        y_position += 25
        draw.text((20, y_position), f"Delivery: {delivery_fee} ETB", font=font, fill='black')
        y_position += 25
        draw.text((20, y_position), f"TOTAL: {total} ETB", font=font_bold, fill='black')
        y_position += 30

        # Payment status
        payment_status = "VERIFIED" if order.get('payments', [{}])[0].get('payment_status', 'pending') == 'verified' else "PENDING"
        payment_color = 'green' if payment_status == "VERIFIED" else 'orange'
        draw.text((20, y_position), f"Payment: {payment_status}", font=font_bold, fill=payment_color)
        y_position += 30

        # Footer
        draw.line([(20, y_position), (width-20, y_position)], fill='gray', width=1)
        y_position += 20
        draw.text((width//2, y_position), "Thank you for shopping with us!", font=font, fill='gray', anchor='mt')
        y_position += 25
        draw.text((width//2, y_position), "Ethio Shoe Store", font=font, fill='gray', anchor='mt')

        # Save to temporary file
        temp_path = f"/tmp/receipt_{order_id}.png"
        img.save(temp_path, 'PNG')

        return temp_path

    except Exception as e:
        print(f"Error generating receipt: {e}")
        return None
