import { LegalPage } from "@/components/legal/LegalPage";

export default function TermsPage() {
  return (
    <LegalPage
      title="Terms of Use"
      summary={
        <p>
          LedgerPilot AI is a development prototype for attributable,
          human-reviewed accounting workflows. It is not an autonomous accountant,
          tax adviser, audit opinion, bookkeeping service, or production accounting
          system.
        </p>
      }
      sections={[
        {
          title: "Synthetic-data requirement",
          body: (
            <p>
              Only synthetic demonstration data may be submitted to the
              public/development build. Do not upload real client, employee,
              taxpayer, banking, invoice, receipt, or confidential business
              information.
            </p>
          ),
        },
        {
          title: "Human review is authoritative",
          body: (
            <p>
              AI extraction and accounting recommendations are assistive outputs.
              An authorised human reviewer remains responsible for validating source
              evidence, accounting treatment, tax treatment, journal entries, and
              any downstream action.
            </p>
          ),
        },
        {
          title: "No professional advice or guarantee",
          body: (
            <p>
              Demo rules, tax codes, journals, confidence scores, and
              recommendations are synthetic or experimental. They must not be relied
              on as accounting, tax, legal, audit, investment, or other professional
              advice, and no accuracy or regulatory-compliance guarantee is made.
            </p>
          ),
        },
        {
          title: "Security and acceptable use",
          items: [
            "Do not attempt to access another tenant/client context without authority.",
            "Do not upload malware or probe the service for unauthorised access.",
            "Do not bypass human-review gates or represent demo output as a certified professional decision.",
          ],
        },
        {
          title: "Intellectual property and third parties",
          body: (
            <p>
              Original project code and materials are subject to the repository
              licence and applicable copyright law. Third-party libraries, services,
              names, and marks remain subject to their own terms.
            </p>
          ),
        },
        {
          title: "Production boundary",
          body: (
            <p>
              Production use requires separate approval covering privacy,
              information security, retention, processor contracts, professional
              obligations, accounting/tax validation, incident response, and
              applicable Malaysian law. These website terms do not provide that
              approval.
            </p>
          ),
        },
      ]}
    />
  );
}
