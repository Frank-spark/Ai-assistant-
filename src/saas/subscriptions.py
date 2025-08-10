"""Subscription and billing management for SaaS platform."""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import stripe
from pydantic import BaseModel

from src.saas.models import User, Subscription, BillingHistory, UsageLog, PlanType, SubscriptionStatus
from src.config import get_settings


# Plan definitions
PLANS = {
    PlanType.FREE: {
        "name": "Free",
        "price": 0,
        "billing_cycle": "monthly",
        "features": {
            "conversations_per_month": 50,
            "workflows_per_month": 25,
            "api_calls_per_month": 100,
            "integrations": ["slack"],
            "support": "community",
            "customization": False,
            "team_members": 1,
            "storage_gb": 1
        },
        "limits": {
            "max_conversation_length": 1000,
            "max_workflow_complexity": "basic",
            "response_time": "standard"
        }
    },
    PlanType.STARTER: {
        "name": "Starter",
        "price": 29,
        "billing_cycle": "monthly",
        "features": {
            "conversations_per_month": 500,
            "workflows_per_month": 250,
            "api_calls_per_month": 1000,
            "integrations": ["slack", "gmail"],
            "support": "email",
            "customization": True,
            "team_members": 3,
            "storage_gb": 10
        },
        "limits": {
            "max_conversation_length": 5000,
            "max_workflow_complexity": "advanced",
            "response_time": "fast"
        }
    },
    PlanType.PROFESSIONAL: {
        "name": "Professional",
        "price": 99,
        "billing_cycle": "monthly",
        "features": {
            "conversations_per_month": 2000,
            "workflows_per_month": 1000,
            "api_calls_per_month": 5000,
            "integrations": ["slack", "gmail", "asana"],
            "support": "priority",
            "customization": True,
            "team_members": 10,
            "storage_gb": 50,
            "advanced_analytics": True,
            "custom_workflows": True
        },
        "limits": {
            "max_conversation_length": 10000,
            "max_workflow_complexity": "expert",
            "response_time": "instant"
        }
    },
    PlanType.ENTERPRISE: {
        "name": "Enterprise",
        "price": 299,
        "billing_cycle": "monthly",
        "features": {
            "conversations_per_month": "unlimited",
            "workflows_per_month": "unlimited",
            "api_calls_per_month": "unlimited",
            "integrations": ["slack", "gmail", "asana", "custom"],
            "support": "dedicated",
            "customization": True,
            "team_members": "unlimited",
            "storage_gb": "unlimited",
            "advanced_analytics": True,
            "custom_workflows": True,
            "sso": True,
            "custom_domain": True,
            "api_access": True
        },
        "limits": {
            "max_conversation_length": "unlimited",
            "max_workflow_complexity": "unlimited",
            "response_time": "instant"
        }
    }
}


class SubscriptionService:
    """Service for managing subscriptions and billing."""
    
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        
        # Initialize Stripe
        if self.settings.stripe_secret_key:
            stripe.api_key = self.settings.stripe_secret_key
    
    def create_subscription(self, user: User, plan_type: PlanType, stripe_token: Optional[str] = None) -> Subscription:
        """Create a new subscription for a user."""
        
        plan = PLANS[plan_type]
        
        # Create Stripe customer if payment is required
        stripe_customer_id = None
        stripe_subscription_id = None
        
        if plan_type != PlanType.FREE and stripe_token:
            try:
                # Create Stripe customer
                customer = stripe.Customer.create(
                    email=user.email,
                    source=stripe_token,
                    metadata={
                        "user_id": str(user.id),
                        "company": user.company_name or ""
                    }
                )
                stripe_customer_id = customer.id
                
                # Create Stripe subscription
                stripe_subscription = stripe.Subscription.create(
                    customer=customer.id,
                    items=[{"price": self._get_stripe_price_id(plan_type)}],
                    trial_period_days=14 if user.subscription_status == SubscriptionStatus.TRIAL.value else None
                )
                stripe_subscription_id = stripe_subscription.id
                
            except stripe.error.StripeError as e:
                raise ValueError(f"Stripe error: {str(e)}")
        
        # Calculate billing period
        now = datetime.utcnow()
        if plan["billing_cycle"] == "monthly":
            period_end = now + timedelta(days=30)
        else:  # yearly
            period_end = now + timedelta(days=365)
        
        # Create subscription record
        subscription = Subscription(
            user_id=user.id,
            plan_type=plan_type.value,
            plan_name=plan["name"],
            plan_description=plan.get("description", ""),
            amount=plan["price"],
            currency="USD",
            billing_cycle=plan["billing_cycle"],
            status=SubscriptionStatus.ACTIVE.value,
            current_period_start=now,
            current_period_end=period_end,
            trial_start=now if user.subscription_status == SubscriptionStatus.TRIAL.value else None,
            trial_end=now + timedelta(days=14) if user.subscription_status == SubscriptionStatus.TRIAL.value else None,
            stripe_subscription_id=stripe_subscription_id,
            stripe_customer_id=stripe_customer_id,
            features=plan["features"],
            limits=plan["limits"]
        )
        
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        
        # Update user subscription status
        user.subscription_status = SubscriptionStatus.ACTIVE.value
        user.plan_type = plan_type.value
        if plan_type != PlanType.FREE:
            user.subscription_ends_at = period_end
        
        self.db.commit()
        
        return subscription
    
    def cancel_subscription(self, user: User) -> bool:
        """Cancel a user's subscription."""
        
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE.value
        ).first()
        
        if not subscription:
            return False
        
        # Cancel Stripe subscription if exists
        if subscription.stripe_subscription_id:
            try:
                stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=True
                )
            except stripe.error.StripeError:
                pass  # Continue with local cancellation
        
        # Update subscription status
        subscription.status = SubscriptionStatus.CANCELLED.value
        user.subscription_status = SubscriptionStatus.CANCELLED.value
        
        self.db.commit()
        return True
    
    def upgrade_subscription(self, user: User, new_plan: PlanType, stripe_token: Optional[str] = None) -> Subscription:
        """Upgrade a user's subscription to a higher plan."""
        
        current_subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE.value
        ).first()
        
        if current_subscription and current_subscription.stripe_subscription_id:
            # Update Stripe subscription
            try:
                stripe.Subscription.modify(
                    current_subscription.stripe_subscription_id,
                    items=[{
                        "id": stripe.Subscription.retrieve(current_subscription.stripe_subscription_id)["items"]["data"][0]["id"],
                        "price": self._get_stripe_price_id(new_plan)
                    }]
                )
            except stripe.error.StripeError as e:
                raise ValueError(f"Stripe error: {str(e)}")
        
        # Cancel current subscription and create new one
        if current_subscription:
            current_subscription.status = SubscriptionStatus.CANCELLED.value
        
        return self.create_subscription(user, new_plan, stripe_token)
    
    def check_usage_limits(self, user: User, usage_type: str) -> bool:
        """Check if user has exceeded their usage limits."""
        
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE.value
        ).first()
        
        if not subscription:
            return False
        
        plan = PLANS[PlanType(subscription.plan_type)]
        features = plan["features"]
        
        # Get current month usage
        start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        if usage_type == "conversations":
            limit = features["conversations_per_month"]
            if limit == "unlimited":
                return True
            
            current_usage = self.db.query(UsageLog).filter(
                UsageLog.user_id == user.id,
                UsageLog.usage_type == "conversation",
                UsageLog.created_at >= start_of_month
            ).count()
            
            return current_usage < limit
        
        elif usage_type == "workflows":
            limit = features["workflows_per_month"]
            if limit == "unlimited":
                return True
            
            current_usage = self.db.query(UsageLog).filter(
                UsageLog.user_id == user.id,
                UsageLog.usage_type == "workflow",
                UsageLog.created_at >= start_of_month
            ).count()
            
            return current_usage < limit
        
        elif usage_type == "api_calls":
            limit = features["api_calls_per_month"]
            if limit == "unlimited":
                return True
            
            current_usage = self.db.query(UsageLog).filter(
                UsageLog.user_id == user.id,
                UsageLog.usage_type == "api_call",
                UsageLog.created_at >= start_of_month
            ).count()
            
            return current_usage < limit
        
        return True
    
    def log_usage(self, user: User, usage_type: str, resource_id: Optional[str] = None, 
                  platform: Optional[str] = None, tokens_used: int = 0, 
                  duration_seconds: float = 0.0, metadata: Optional[Dict] = None) -> UsageLog:
        """Log usage for billing and analytics."""
        
        # Calculate estimated cost
        estimated_cost = self._calculate_usage_cost(usage_type, tokens_used, duration_seconds)
        
        usage_log = UsageLog(
            user_id=user.id,
            usage_type=usage_type,
            resource_id=resource_id,
            platform=platform,
            tokens_used=tokens_used,
            api_calls=1,
            duration_seconds=duration_seconds,
            estimated_cost=estimated_cost,
            currency="USD",
            metadata=metadata or {}
        )
        
        self.db.add(usage_log)
        self.db.commit()
        self.db.refresh(usage_log)
        
        # Update user's monthly usage counters
        if usage_type == "conversation":
            user.monthly_conversations += 1
        elif usage_type == "workflow":
            user.monthly_workflows += 1
        
        user.last_activity_at = datetime.utcnow()
        self.db.commit()
        
        return usage_log
    
    def get_user_usage_summary(self, user: User) -> Dict[str, Any]:
        """Get a summary of user's current usage."""
        
        start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Get current subscription
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE.value
        ).first()
        
        if not subscription:
            return {"error": "No active subscription"}
        
        plan = PLANS[PlanType(subscription.plan_type)]
        features = plan["features"]
        
        # Get usage counts
        conversations_used = self.db.query(UsageLog).filter(
            UsageLog.user_id == user.id,
            UsageLog.usage_type == "conversation",
            UsageLog.created_at >= start_of_month
        ).count()
        
        workflows_used = self.db.query(UsageLog).filter(
            UsageLog.user_id == user.id,
            UsageLog.usage_type == "workflow",
            UsageLog.created_at >= start_of_month
        ).count()
        
        api_calls_used = self.db.query(UsageLog).filter(
            UsageLog.user_id == user.id,
            UsageLog.usage_type == "api_call",
            UsageLog.created_at >= start_of_month
        ).count()
        
        # Calculate total cost
        total_cost = self.db.query(UsageLog).filter(
            UsageLog.user_id == user.id,
            UsageLog.created_at >= start_of_month
        ).with_entities(db.func.sum(UsageLog.estimated_cost)).scalar() or 0.0
        
        return {
            "plan": {
                "name": plan["name"],
                "type": subscription.plan_type,
                "price": plan["price"]
            },
            "usage": {
                "conversations": {
                    "used": conversations_used,
                    "limit": features["conversations_per_month"],
                    "remaining": features["conversations_per_month"] - conversations_used if features["conversations_per_month"] != "unlimited" else "unlimited"
                },
                "workflows": {
                    "used": workflows_used,
                    "limit": features["workflows_per_month"],
                    "remaining": features["workflows_per_month"] - workflows_used if features["workflows_per_month"] != "unlimited" else "unlimited"
                },
                "api_calls": {
                    "used": api_calls_used,
                    "limit": features["api_calls_per_month"],
                    "remaining": features["api_calls_per_month"] - api_calls_used if features["api_calls_per_month"] != "unlimited" else "unlimited"
                }
            },
            "billing": {
                "total_cost": total_cost,
                "currency": "USD",
                "period_start": start_of_month,
                "period_end": start_of_month + timedelta(days=30)
            }
        }
    
    def _get_stripe_price_id(self, plan_type: PlanType) -> str:
        """Get Stripe price ID for a plan type."""
        # This would be configured in your Stripe dashboard
        price_ids = {
            PlanType.STARTER: "price_starter_monthly",
            PlanType.PROFESSIONAL: "price_professional_monthly",
            PlanType.ENTERPRISE: "price_enterprise_monthly"
        }
        return price_ids.get(plan_type, "")
    
    def _calculate_usage_cost(self, usage_type: str, tokens_used: int, duration_seconds: float) -> float:
        """Calculate estimated cost for usage."""
        
        # Base costs (these would be configured based on your actual costs)
        costs = {
            "conversation": 0.01,  # $0.01 per conversation
            "workflow": 0.05,      # $0.05 per workflow
            "api_call": 0.001,     # $0.001 per API call
            "token": 0.000002      # $0.000002 per token (GPT-4 pricing)
        }
        
        base_cost = costs.get(usage_type, 0.0)
        token_cost = tokens_used * costs["token"]
        
        return base_cost + token_cost


class BillingService:
    """Service for managing billing and invoices."""
    
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        
        if self.settings.stripe_secret_key:
            stripe.api_key = self.settings.stripe_secret_key
    
    def create_invoice(self, user: User, amount: float, description: str, 
                      metadata: Optional[Dict] = None) -> BillingHistory:
        """Create an invoice for a user."""
        
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE.value
        ).first()
        
        # Create Stripe invoice if customer exists
        stripe_invoice_id = None
        if subscription and subscription.stripe_customer_id:
            try:
                invoice = stripe.Invoice.create(
                    customer=subscription.stripe_customer_id,
                    amount=int(amount * 100),  # Convert to cents
                    currency="usd",
                    description=description,
                    metadata=metadata or {}
                )
                stripe_invoice_id = invoice.id
            except stripe.error.StripeError:
                pass
        
        # Create billing history record
        billing_record = BillingHistory(
            user_id=user.id,
            subscription_id=subscription.id if subscription else None,
            amount=amount,
            currency="USD",
            status="pending",
            invoice_number=f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{user.id}",
            stripe_invoice_id=stripe_invoice_id,
            description=description,
            metadata=metadata or {},
            billing_period_start=datetime.utcnow(),
            billing_period_end=datetime.utcnow() + timedelta(days=30)
        )
        
        self.db.add(billing_record)
        self.db.commit()
        self.db.refresh(billing_record)
        
        return billing_record
    
    def get_billing_history(self, user: User, limit: int = 50) -> List[BillingHistory]:
        """Get user's billing history."""
        
        return self.db.query(BillingHistory).filter(
            BillingHistory.user_id == user.id
        ).order_by(BillingHistory.created_at.desc()).limit(limit).all()
    
    def process_webhook(self, event_data: Dict) -> bool:
        """Process Stripe webhook events."""
        
        try:
            event = stripe.Event.construct_from(event_data, self.settings.stripe_webhook_secret)
        except ValueError:
            return False
        
        if event.type == "invoice.payment_succeeded":
            return self._handle_payment_succeeded(event.data.object)
        elif event.type == "invoice.payment_failed":
            return self._handle_payment_failed(event.data.object)
        elif event.type == "customer.subscription.deleted":
            return self._handle_subscription_cancelled(event.data.object)
        
        return True
    
    def _handle_payment_succeeded(self, invoice_data: Dict) -> bool:
        """Handle successful payment webhook."""
        
        billing_record = self.db.query(BillingHistory).filter(
            BillingHistory.stripe_invoice_id == invoice_data["id"]
        ).first()
        
        if billing_record:
            billing_record.status = "paid"
            billing_record.paid_at = datetime.utcnow()
            self.db.commit()
        
        return True
    
    def _handle_payment_failed(self, invoice_data: Dict) -> bool:
        """Handle failed payment webhook."""
        
        billing_record = self.db.query(BillingHistory).filter(
            BillingHistory.stripe_invoice_id == invoice_data["id"]
        ).first()
        
        if billing_record:
            billing_record.status = "failed"
            self.db.commit()
        
        return True
    
    def _handle_subscription_cancelled(self, subscription_data: Dict) -> bool:
        """Handle subscription cancellation webhook."""
        
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_data["id"]
        ).first()
        
        if subscription:
            subscription.status = SubscriptionStatus.CANCELLED.value
            subscription.user.subscription_status = SubscriptionStatus.CANCELLED.value
            self.db.commit()
        
        return True 