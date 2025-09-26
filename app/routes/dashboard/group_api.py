# app/routes/group_api.py - API endpoints for group-specific data

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, Group, User, Balance, Settlement, Expense, RecurringPayment
from app.services.tracker.expense_service import ExpenseService
from sqlalchemy import func
from datetime import datetime

group_api_bp = Blueprint("group_api", __name__, url_prefix="/api/group")


@group_api_bp.route("/<int:group_id>/balances", methods=["GET"])
@login_required
def get_group_balances(group_id):
    """Get balances for a specific group"""
    group = Group.query.get_or_404(group_id)

    if current_user not in group.members:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        balances = Balance.query.filter_by(group_id=group_id).join(User).all()

        balance_data = []
        for balance in balances:
            if abs(balance.amount) > 0.01:  # Only show non-zero balances
                balance_data.append(
                    {
                        "user_id": balance.user_id,
                        "user_name": balance.user.name,
                        "amount": round(balance.amount, 2),
                    }
                )

        return jsonify({"balances": balance_data})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@group_api_bp.route("/<int:group_id>/settlements", methods=["GET"])
@login_required
def get_group_settlements(group_id):
    """Get settlement suggestions for a specific group"""
    group = Group.query.get_or_404(group_id)

    if current_user not in group.members:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        balances = Balance.query.filter_by(group_id=group_id).join(User).all()

        suggestions = []
        debtors = []
        creditors = []

        for balance in balances:
            if balance.amount < -0.01:
                debtors.append(
                    {
                        "user_id": balance.user_id,
                        "user_name": balance.user.name,
                        "amount": abs(balance.amount),
                    }
                )
            elif balance.amount > 0.01:
                creditors.append(
                    {
                        "user_id": balance.user_id,
                        "user_name": balance.user.name,
                        "amount": balance.amount,
                    }
                )

        debtors.sort(key=lambda x: x["amount"], reverse=True)
        creditors.sort(key=lambda x: x["amount"], reverse=True)

        i, j = 0, 0
        while i < len(debtors) and j < len(creditors):
            debtor = debtors[i]
            creditor = creditors[j]

            settlement_amount = min(debtor["amount"], creditor["amount"])

            if settlement_amount > 0.01:
                suggestions.append(
                    {
                        "payer_id": debtor["user_id"],
                        "payer_name": debtor["user_name"],
                        "receiver_id": creditor["user_id"],
                        "receiver_name": creditor["user_name"],
                        "amount": round(settlement_amount, 2),
                    }
                )

            debtor["amount"] -= settlement_amount
            creditor["amount"] -= settlement_amount

            if debtor["amount"] <= 0.01:
                i += 1
            if creditor["amount"] <= 0.01:
                j += 1

        return jsonify({"suggestions": suggestions})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@group_api_bp.route("/<int:group_id>/settlements", methods=["POST"])
@login_required
def add_group_settlement(group_id):
    """Add a settlement/payment within a group"""
    group = Group.query.get_or_404(group_id)

    if current_user not in group.members:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        data = request.get_json()
        required_fields = ["amount", "payer_id", "receiver_id"]

        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        payer = User.query.get(data["payer_id"])
        receiver = User.query.get(data["receiver_id"])

        if not payer or payer not in group.members:
            return jsonify({"error": "Payer must be a group member"}), 400
        if not receiver or receiver not in group.members:
            return jsonify({"error": "Receiver must be a group member"}), 400
        if payer.id == receiver.id:
            return jsonify({"error": "Payer and receiver cannot be the same person"}), 400

        settlement = Settlement(
            amount=float(data["amount"]),
            payer_id=data["payer_id"],
            receiver_id=data["receiver_id"],
            group_id=group_id,
            description=data.get("description", ""),
            date=datetime.strptime(
                data.get("date", datetime.now().strftime("%Y-%m-%d")), "%Y-%m-%d"
            ).date(),
        )

        db.session.add(settlement)
        db.session.commit()

        ExpenseService._recalculate_group_balances(group_id)

        return jsonify({"success": True, "settlement_id": settlement.id})

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@group_api_bp.route("/<int:group_id>/expenses", methods=["GET"])
@login_required
def get_group_expenses(group_id):
    """Get all expenses for a group"""
    group = Group.query.get_or_404(group_id)

    if current_user not in group.members:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        expenses = (
            Expense.query.filter_by(group_id=group_id)
            .join(User, Expense.payer_id == User.id)
            .order_by(Expense.date.desc())
            .all()
        )

        expense_data = [
            {
                "id": exp.id,
                "amount": round(exp.amount, 2),
                "description": exp.description,
                "payer_id": exp.payer_id,
                "payer_name": exp.payer.name,
                "date": exp.date.strftime("%Y-%m-%d"),
            }
            for exp in expenses
        ]

        return jsonify({"expenses": expense_data})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@group_api_bp.route("/<int:group_id>/recurring", methods=["GET"])
@login_required
def get_group_recurring_payments(group_id):
    """Get recurring payments for a group"""
    group = Group.query.get_or_404(group_id)

    if current_user not in group.members:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        recurring = RecurringPayment.query.filter_by(group_id=group_id).all()
        recurring_data = [
            {
                "id": rp.id,
                "amount": round(rp.amount, 2),
                "description": rp.description,
                "interval": rp.interval,
                "next_date": rp.next_date.strftime("%Y-%m-%d")
                if rp.next_date
                else None,
            }
            for rp in recurring
        ]

        return jsonify({"recurring": recurring_data})

    except Exception as e:
        return jsonify({"error": str(e)}), 500