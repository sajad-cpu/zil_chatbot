#!/usr/bin/env python3
"""
Training script: scrape Zil Money details and load them into the vector store.

Usage:
    python train_zilmoney.py

Requires:
    - GEMINI_API_KEY in .env
    - DATABASE_URL in .env (Postgres with pgvector)
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# Load .env first
load_dotenv()

from services.chunker import chunk_text
from services.gemini import embed_batch
from vector_db import store

# Zil Money company details (scraped from zilmoney.com)
ZIL_MONEY_CONTENT = """
Zil Money - Your Complete Business Payment Platform

What is Zil Money?
Zil Money is an all-in-one fintech platform (not a bank) designed to streamline business payments and payment operations. We help businesses send money, receive money, and automate everything—all from one platform.

Core Mission
We eliminate transaction fees and help businesses earn rewards on their payment operations. Most businesses pay thousands monthly in transaction fees. With Zil Money, you pay $0 on eligible transactions and earn cash back on qualifying payments.

Key Statistics
- $100B+ processed
- 1M+ businesses using Zil Money
- 22K+ bank integrations
- $0 fees on eligible wallet payments
- Real savings: Average business saves $2,400 monthly in transaction fees

Payment Methods Supported
1. ACH Transfers: Send and receive domestic payments. $0 fees on eligible wallet payments.
2. Wire Transfers: Fast fund transfers, same-day ACH available.
3. Digital Checks: Create custom-branded checks, send digitally or by mail. $0 fees on eligible wallet payments.
4. Check Mailing Service: We print, envelope, and mail your checks professionally via USPS First Class. Processing within 1-2 business days. Starting at $1.25 per check.
5. International Payments: Ripple-powered global payments that settle in minutes, not 3-5 days. Lower fees than traditional wires. Available to 7+ countries.
6. Virtual Cards: Issue unlimited virtual cards with custom limits for vendors, employees, or projects. Complete spending control.
7. Credit Card Payments: Pay vendors and run payroll with credit cards to earn rewards and get 30-45 day payment float.
8. Bill Payments: Automated bill payments. Set up once and never worry about late fees. $0 fees on eligible wallet payments.

Zil Money Wallet - The Heart of the Platform
Load your Zil Money Wallet from your bank account to unlock:
- $0 fees on eligible transactions (no ACH fees, no wire fees, no check fees)
- Cash back on qualifying wallet payments
- Complete control over all your payment methods
- Real-time visibility into every transaction

Payment Method Comparison
Traditional Payment Methods (What most businesses pay):
- ACH transfer: $3 per transaction
- Wire transfer: $25-50 per transaction
- Check payment: $5-8 per check
- Bill payment: $2-5 per payment
- International wire: $45+ per transaction
- Typical monthly cost: $2,400+

Zil Money Wallet (What you pay):
- ACH transfer: $0 on eligible transactions
- Wire transfer: $0 on eligible transactions
- Check payment: $0 on eligible transactions
- Bill payment: $0 on eligible transactions
- Plus: Cash back on qualifying transactions
- Monthly cost: $0 on eligible payments + earn cash back

Special Features
1. Bulk Payment Processing: Upload CSV files and process hundreds or thousands of payments at once. Quick validation, real-time tracking. Perfect for payroll and vendor payments.
2. Auto-reconciliation: Automatically reconcile with accounting software.
3. Vendor Payments: Pay any vendor with your credit card and earn rewards—even if they don't accept cards. Get 30-45 day float.
4. Payroll with Credit Cards: Pay employees with your credit card. Earn rewards on every paycheck. Get payment float.
5. Real-time Tracking: Get hours back every week with automated operations.

Security & Compliance
Zil Money exceeds industry security standards:
- 256-Bit Military-Grade Encryption: All data encrypted in transit and at rest
- SOC 1 Certification
- SOC 2 Certification
- ISO 27001 Certification
- ISO 20000 Certification
- ISO 9001 Certification
- GDPR Compliance
- PCI DSS Compliance
- CCPA Compliance
- NIST 800-53 Compliance
- HIPAA Compliance
- Advanced Multi-Factor Authentication
- 24/7 Real-Time Fraud Monitoring with AI-powered systems
- FDIC Member Bank Partners: Banking services through partnerships with FDIC member banks

Trusted Bank Partnerships
Zil Money integrates with 22,000+ banks and financial institutions, providing:
- Secure, real-time connectivity for payments
- FDIC-backed protection
- Bank-grade secure connections

Business Tools & Integrations
- Accounting Software: Automated sync with QuickBooks, Xero, and other accounting platforms
- Banking Integrations: Connect with 22,000+ banks for easy payments
- Group Mailing: Track group mailings with full status, cost, and reports
- Positive Pay: Prevent check fraud by matching issued checks with records
- Shipping Labels: Generate shipping labels quickly
- Email Writer: Generate high-quality email content instantly
- Knowledge Base: Create and publish knowledge base articles quickly

Industries We Serve
- Real Estate: Rent collection, security deposits, commission distribution, vendor payments
- Healthcare: Insurance claims, patient refunds, provider payments, medical billing
- Legal Services: Client trust accounts, settlement payments, court fees, retainer management
- E-commerce: Supplier payments, customer refunds, marketplace settlements, international orders
- Professional Services: Client invoicing, contractor payments, subscription billing, expense management
- Manufacturing: Vendor payments, payroll, international suppliers, bulk transactions
- Construction: Subcontractor payments, material suppliers, equipment purchases, payroll
- Technology: Global contractor payments, SaaS subscriptions, vendor management, payroll
- Government & Utilities
- Healthcare Industry
- Education
- Insurance
- Retail & Food & Beverage

APIs & Developer Solutions
For SaaS platforms, fintech companies, and custom integrations:
- Comprehensive APIs for all payment types
- Developer-friendly documentation
- Sandbox environment
- Dedicated technical support

White Label Platform
For financial institutions, enterprises, and platform businesses:
- Your brand, our proven technology
- Deploy in weeks, not years
- Complete customization
- 22,000+ banking integrations included

Pricing Plans
1. Free Plan: $0/month
   - Getting started tier
   - Create account and explore platform
   - Basic payment features
   - Limited monthly transactions
   - Standard support
   - Core integrations

2. Business Plan: Custom Pricing
   - Most businesses
   - All payment methods available
   - Zil Money Wallet ($0 on eligible transactions)
   - Unlimited transactions
   - Cash back on qualifying payments
   - Credit card vendor payments
   - Credit card payroll processing
   - Priority support
   - All integrations
   - Bulk payment processing
   - Advanced reporting

3. Enterprise Plan: Custom Pricing
   - Large organizations
   - Everything in Business plan
   - Enterprise API access
   - White label platform options
   - Dedicated account manager
   - Custom integrations
   - SLA guarantees
   - Volume-based pricing
   - White glove onboarding
   - Advanced security features

Onboarding Process
1. Create your account: Sign up with your business information. Quick identity verification. No credit card required to start exploring.
2. Fund your Wallet: Load your Zil Money Wallet from your bank account to unlock $0 fees on eligible transactions. Or connect your credit card for vendor and payroll payments.
3. Make your first payment: Choose your payment method, enter recipient details, send your payment. Track everything in real-time with complete visibility.
4. Save and earn continuously: Zero fees on eligible wallet transactions. Cash back on qualifying payments. Credit card rewards on vendor and payroll payments.

Customer Testimonials
Real businesses report real savings and excellent support experiences.

Common Questions
- How do I actually pay $0 in transaction fees? By loading your Zil Money Wallet from your bank account and using eligible payment methods.
- How does paying vendors with a credit card work? You can pay any vendor with your credit card (even if they don't accept cards). You earn rewards on every transaction and get 30-45 day payment float.
- Can I really run payroll with a credit card? Yes. Pay employees with your credit card, earn rewards on every paycheck, and get payment float.
- What's the catch with cash back on payments? There is no catch. Zil Money makes money from banking partnerships and payment processing, not from transaction fees.
- Is this actually better than my current payment setup? For most businesses paying thousands monthly in fees, yes. Calculate your savings at zilmoney.com.
- How quickly can I start using Zil Money? Simple setup, immediate value. No complicated onboarding. Start in minutes, not days.
- What if I only need one or two features? Start with the free plan or contact us for a custom quote tailored to your needs.
- Do you integrate with QuickBooks, Xero, or my accounting software? Yes, Zil Money integrates with all major accounting platforms for automated reconciliation.
- What kind of support do I get if I need help? All plans include support. Business and Enterprise plans include priority support and dedicated account managers.

Contact & Get Started
Visit zilmoney.com to:
- Start a free account (no credit card required)
- Calculate your potential savings
- View detailed pricing
- Schedule a demo
- Contact sales

FDIC Coverage
Zil Money is a fintech, not a bank. FDIC coverage is provided through our partner banks, specifically Texas National Bank.

Last Updated: 2024
For the most current information, visit https://zilmoney.com/
"""


async def main():
    """Scrape and train the chatbot with Zil Money data."""
    print("🚀 Starting Zil Money training...")
    print()

    # Check API key
    if not os.environ.get("GEMINI_API_KEY"):
        print("❌ ERROR: GEMINI_API_KEY not set in .env")
        sys.exit(1)

    # Check database connection
    try:
        count = await store.count()
        print(f"✓ Database connection OK (currently {count} chunks)")
    except Exception as e:
        print(f"❌ ERROR: Cannot connect to database: {e}")
        print("   Make sure DATABASE_URL is set in .env")
        sys.exit(1)

    print()
    print("📝 Chunking Zil Money content...")
    chunks = chunk_text(ZIL_MONEY_CONTENT)
    print(f"   Created {len(chunks)} chunks")

    print()
    print("🧠 Generating embeddings (this may take a minute)...")
    try:
        embeddings = await embed_batch(chunks)
        print(f"   ✓ Generated {len(embeddings)} embeddings")
    except Exception as e:
        print(f"❌ ERROR: Cannot generate embeddings: {e}")
        sys.exit(1)

    print()
    print("💾 Loading into database...")
    entries = [
        {"text": text, "embedding": emb} for text, emb in zip(chunks, embeddings)
    ]
    total = await store.add(entries)
    print(f"   ✓ Database now has {total} total chunks")

    print()
    print("✅ Training complete!")
    print()
    print("You can now ask the bot questions about Zil Money, like:")
    print("  - 'What payment methods does Zil Money support?'")
    print("  - 'How much do ACH transfers cost?'")
    print("  - 'What industries does Zil Money serve?'")
    print("  - 'How secure is Zil Money?'")


if __name__ == "__main__":
    asyncio.run(main())
