import { LegalPage } from "@/components/legal/LegalPage";

export default function RefundsPage() {
  return <LegalPage title="Payments & Refunds" summary={<p>The current LedgerPilot AI development build does not sell subscriptions, accounting services, licences, or other paid products through its website and does not contain a customer checkout flow.</p>} sections={[
    { title: "No website purchases", body: <p>There are currently no card payments, recurring charges, paid plans, or website purchases to cancel or refund in this public prototype.</p> },
    { title: "Prototype access is not a professional engagement", body: <p>Accessing a demo, repository, or review workflow does not create an accountant-client, tax-adviser, audit, bookkeeping, software-subscription, or consulting engagement.</p> },
    { title: "Before any future commercial launch", body: <p>If LedgerPilot later charges users, the deployed product must publish accurate seller identity, pricing, billing frequency, cancellation rules, refund terms, statutory consumer rights, payment-provider disclosures, and privacy information before checkout is enabled.</p> },
  ]} />;
}
