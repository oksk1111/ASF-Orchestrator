from __future__ import annotations

from app.domain.models import CheckoutEnvelope, CheckoutRequest, CheckoutResponse
from app.repositories.in_memory import InMemoryRepository
from app.services.pricing import apply_dynamic_pricing


class CheckoutService:
    def __init__(self, repository: InMemoryRepository) -> None:
        self.repository = repository

    def process_checkout(self, request: CheckoutRequest) -> CheckoutEnvelope:
        user = self.repository.get_user(request.user_id)
        if user is None:
            raise ValueError("user not found")

        original_total = 0.0
        discounted_total = 0.0
        earned_points = 0
        line_items: list[dict] = []

        for entry in request.basket_items:
            product = self.repository.get_product(entry.product_code)
            if product is None:
                continue

            discounted_price, discount_rate = apply_dynamic_pricing(
                product.base_price, product.oversupply_risk_index
            )
            quantity = entry.quantity

            original_total += product.base_price * quantity
            discounted_total += discounted_price * quantity
            earned_points += int((product.oversupply_risk_index * 100 + discount_rate * 50) * quantity)

            line_items.append(
                {
                    "product_code": product.product_code,
                    "quantity": quantity,
                    "unit_price": discounted_price,
                }
            )

        wallet = self.repository.get_wallet_points(request.user_id)
        points_used = 0
        if request.use_points:
            points_used = min(wallet, int(discounted_total))

        final_amount = max(0.0, round(discounted_total - points_used, 2))
        new_wallet_balance = wallet - points_used + earned_points
        self.repository.set_wallet_points(request.user_id, new_wallet_balance)

        order = self.repository.append_order(
            {
                "user_id": request.user_id,
                "items": line_items,
                "total_amount": final_amount,
                "discount_amount": round(original_total - discounted_total + points_used, 2),
                "earned_esg_points": earned_points,
            }
        )

        payload = CheckoutResponse(
            order_id=order["order_id"],
            user_id=request.user_id,
            total_amount=final_amount,
            discount_amount=round(original_total - final_amount, 2),
            points_used=points_used,
            earned_esg_points=earned_points,
            wallet_balance=new_wallet_balance,
        )
        return CheckoutEnvelope(data=payload)
