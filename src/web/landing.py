"""Landing page for Reflex Executive Assistant SaaS platform."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["landing"])
templates = Jinja2Templates(directory="src/web/templates")


@router.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Main landing page for the SaaS platform."""
    
    context = {
        "request": request,
        "features": [
            {
                "icon": "fas fa-robot",
                "title": "AI-Powered Assistant",
                "description": "Your personal AI assistant that understands your business and helps you work smarter, not harder.",
                "color": "blue"
            },
            {
                "icon": "fas fa-comments",
                "title": "Multi-Platform Integration",
                "description": "Seamlessly works across Slack, Gmail, and Asana to keep you connected and productive.",
                "color": "purple"
            },
            {
                "icon": "fas fa-project-diagram",
                "title": "Smart Workflows",
                "description": "Automate repetitive tasks and create intelligent workflows that adapt to your needs.",
                "color": "green"
            },
            {
                "icon": "fas fa-chart-line",
                "title": "Analytics & Insights",
                "description": "Get valuable insights into your productivity and team performance with detailed analytics.",
                "color": "orange"
            }
        ],
        "testimonials": [
            {
                "name": "Sarah Johnson",
                "role": "Marketing Director",
                "company": "TechCorp",
                "content": "Reflex has transformed how our team communicates and collaborates. The AI assistant is incredibly intuitive and saves us hours every week.",
                "avatar": "SJ"
            },
            {
                "name": "Michael Chen",
                "role": "Product Manager",
                "company": "StartupXYZ",
                "content": "The workflow automation features are game-changing. What used to take days now happens automatically in minutes.",
                "avatar": "MC"
            },
            {
                "name": "Emily Rodriguez",
                "role": "Operations Lead",
                "company": "GrowthCo",
                "content": "Finally, an AI assistant that actually understands our business context and helps us make better decisions.",
                "avatar": "ER"
            }
        ],
        "pricing_plans": [
            {
                "name": "Free",
                "price": "$0",
                "period": "forever",
                "description": "Perfect for individuals getting started",
                "features": [
                    "50 conversations per month",
                    "25 workflows per month",
                    "Slack integration",
                    "Basic support",
                    "1 team member"
                ],
                "cta": "Get Started Free",
                "popular": False
            },
            {
                "name": "Starter",
                "price": "$29",
                "period": "per month",
                "description": "Great for small teams and growing businesses",
                "features": [
                    "500 conversations per month",
                    "250 workflows per month",
                    "Slack & Gmail integration",
                    "Email support",
                    "3 team members",
                    "Custom workflows"
                ],
                "cta": "Start Free Trial",
                "popular": True
            },
            {
                "name": "Professional",
                "price": "$99",
                "period": "per month",
                "description": "For teams that need advanced features",
                "features": [
                    "2,000 conversations per month",
                    "1,000 workflows per month",
                    "All integrations (Slack, Gmail, Asana)",
                    "Priority support",
                    "10 team members",
                    "Advanced analytics",
                    "Custom integrations"
                ],
                "cta": "Start Free Trial",
                "popular": False
            },
            {
                "name": "Enterprise",
                "price": "$299",
                "period": "per month",
                "description": "For large organizations with custom needs",
                "features": [
                    "Unlimited conversations",
                    "Unlimited workflows",
                    "All integrations + custom",
                    "Dedicated support",
                    "Unlimited team members",
                    "Advanced analytics",
                    "SSO & custom domain",
                    "API access"
                ],
                "cta": "Contact Sales",
                "popular": False
            }
        ]
    }
    
    return templates.TemplateResponse("landing/index.html", context)


@router.get("/features", response_class=HTMLResponse)
async def features_page(request: Request):
    """Detailed features page."""
    
    context = {
        "request": request,
        "features": {
            "ai_assistant": {
                "title": "AI-Powered Executive Assistant",
                "description": "Your intelligent companion that understands your business context and helps you make better decisions.",
                "capabilities": [
                    "Natural language processing",
                    "Context-aware responses",
                    "Learning from your preferences",
                    "Multi-language support",
                    "24/7 availability"
                ]
            },
            "integrations": {
                "title": "Seamless Integrations",
                "description": "Works with the tools you already use, so you don't have to change your workflow.",
                "platforms": [
                    {
                        "name": "Slack",
                        "description": "Real-time communication and team collaboration",
                        "icon": "fab fa-slack",
                        "color": "purple"
                    },
                    {
                        "name": "Gmail",
                        "description": "Email management and automated responses",
                        "icon": "fas fa-envelope",
                        "color": "red"
                    },
                    {
                        "name": "Asana",
                        "description": "Project management and task automation",
                        "icon": "fas fa-tasks",
                        "color": "orange"
                    }
                ]
            },
            "workflows": {
                "title": "Smart Workflow Automation",
                "description": "Create intelligent workflows that adapt to your business needs and automate repetitive tasks.",
                "examples": [
                    "Automated email responses",
                    "Meeting scheduling and reminders",
                    "Task creation and assignment",
                    "Report generation",
                    "Data analysis and insights"
                ]
            },
            "analytics": {
                "title": "Advanced Analytics & Insights",
                "description": "Get deep insights into your productivity, team performance, and business metrics.",
                "metrics": [
                    "Conversation analytics",
                    "Workflow performance",
                    "Team productivity",
                    "Response times",
                    "Usage patterns"
                ]
            }
        }
    }
    
    return templates.TemplateResponse("landing/features.html", context)


@router.get("/pricing", response_class=HTMLResponse)
async def pricing_page(request: Request):
    """Detailed pricing page."""
    
    context = {
        "request": request,
        "plans": [
            {
                "name": "Free",
                "price": "$0",
                "period": "forever",
                "description": "Perfect for individuals getting started with AI assistance",
                "features": [
                    "50 conversations per month",
                    "25 workflows per month",
                    "100 API calls per month",
                    "Slack integration",
                    "Community support",
                    "1 team member",
                    "1GB storage",
                    "Basic customization"
                ],
                "limitations": [
                    "No advanced analytics",
                    "No custom workflows",
                    "No priority support"
                ],
                "cta": "Get Started Free",
                "cta_url": "/auth/register",
                "popular": False
            },
            {
                "name": "Starter",
                "price": "$29",
                "period": "per month",
                "description": "Great for small teams and growing businesses",
                "features": [
                    "500 conversations per month",
                    "250 workflows per month",
                    "1,000 API calls per month",
                    "Slack & Gmail integration",
                    "Email support",
                    "3 team members",
                    "10GB storage",
                    "Custom workflows",
                    "Advanced customization",
                    "Basic analytics"
                ],
                "limitations": [
                    "No Asana integration",
                    "No priority support",
                    "Limited team size"
                ],
                "cta": "Start Free Trial",
                "cta_url": "/auth/register?plan=starter",
                "popular": True
            },
            {
                "name": "Professional",
                "price": "$99",
                "period": "per month",
                "description": "For teams that need advanced features and integrations",
                "features": [
                    "2,000 conversations per month",
                    "1,000 workflows per month",
                    "5,000 API calls per month",
                    "All integrations (Slack, Gmail, Asana)",
                    "Priority support",
                    "10 team members",
                    "50GB storage",
                    "Advanced analytics",
                    "Custom integrations",
                    "Workflow templates",
                    "Team collaboration features"
                ],
                "limitations": [
                    "No SSO",
                    "No custom domain",
                    "No dedicated support"
                ],
                "cta": "Start Free Trial",
                "cta_url": "/auth/register?plan=professional",
                "popular": False
            },
            {
                "name": "Enterprise",
                "price": "$299",
                "period": "per month",
                "description": "For large organizations with custom needs and requirements",
                "features": [
                    "Unlimited conversations",
                    "Unlimited workflows",
                    "Unlimited API calls",
                    "All integrations + custom",
                    "Dedicated support",
                    "Unlimited team members",
                    "Unlimited storage",
                    "Advanced analytics",
                    "Custom integrations",
                    "SSO & custom domain",
                    "API access",
                    "Custom training",
                    "SLA guarantees",
                    "On-premise options"
                ],
                "limitations": [
                    "Requires annual commitment",
                    "Custom pricing for large deployments"
                ],
                "cta": "Contact Sales",
                "cta_url": "/contact",
                "popular": False
            }
        ],
        "faqs": [
            {
                "question": "Can I change my plan at any time?",
                "answer": "Yes! You can upgrade or downgrade your plan at any time. Changes take effect immediately, and we'll prorate any billing adjustments."
            },
            {
                "question": "Is there a free trial?",
                "answer": "Yes! All paid plans come with a 14-day free trial. No credit card required to start your trial."
            },
            {
                "question": "What happens if I exceed my usage limits?",
                "answer": "We'll notify you when you're approaching your limits. You can either upgrade your plan or wait until your usage resets the next month."
            },
            {
                "question": "Do you offer refunds?",
                "answer": "We offer a 30-day money-back guarantee. If you're not satisfied, contact our support team for a full refund."
            },
            {
                "question": "Can I cancel my subscription?",
                "answer": "Yes, you can cancel your subscription at any time from your account settings. You'll continue to have access until the end of your billing period."
            }
        ]
    }
    
    return templates.TemplateResponse("landing/pricing.html", context)


@router.get("/contact", response_class=HTMLResponse)
async def contact_page(request: Request):
    """Contact and support page."""
    
    context = {
        "request": request,
        "support_options": [
            {
                "title": "Email Support",
                "description": "Get help from our support team",
                "email": "support@reflex.ai",
                "response_time": "Within 24 hours",
                "icon": "fas fa-envelope"
            },
            {
                "title": "Live Chat",
                "description": "Chat with our support team in real-time",
                "availability": "Monday-Friday, 9AM-6PM EST",
                "icon": "fas fa-comments"
            },
            {
                "title": "Help Center",
                "description": "Browse our comprehensive documentation",
                "url": "/dashboard/help",
                "icon": "fas fa-book"
            },
            {
                "title": "Community Forum",
                "description": "Connect with other users and share tips",
                "url": "#",
                "icon": "fas fa-users"
            }
        ]
    }
    
    return templates.TemplateResponse("landing/contact.html", context) 